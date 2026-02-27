"""
core/views.py — Views do interpretador de documentos.

Fluxo principal:
1. upload_view: Upload do documento + configuração da análise
2. process_analysis: Executa a análise (Docling → Joel → Report)
3. report_view: Exibe o relatório na tela
4. download_view: Download do relatório em PDF/DOCX/XLSX/TXT
5. history_view: Histórico de análises do usuário
"""

import os
import time
import logging
import threading
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile

from .models import Document, AnalysisRequest, Report
from .forms import DocumentUploadForm, AnalysisConfigForm
from .joel.tools import parse_document
from .joel.agent import run_analysis
from .joel.report_generator import (
    markdown_to_html,
    generate_pdf,
    generate_docx,
    generate_xlsx,
    generate_txt,
)

logger = logging.getLogger(__name__)

# Timeout máximo para processamento (segundos)
PROCESSING_TIMEOUT = int(os.environ.get("JOEL_TIMEOUT", 300))  # 5 min default


@login_required
def upload_view(request):
    """
    GET: Mostra formulário de upload + configuração.
    POST: Recebe documento e configuração, inicia análise.
    """
    if request.method == "POST":
        upload_form = DocumentUploadForm(request.POST, request.FILES)
        config_form = AnalysisConfigForm(request.POST)
        
        if upload_form.is_valid() and config_form.is_valid():
            uploaded_file = request.FILES["file"]
            
            # Criar Document
            doc = Document.objects.create(
                file=uploaded_file,
                original_filename=uploaded_file.name,
                file_type=os.path.splitext(uploaded_file.name)[1].lower().lstrip("."),
                file_size=uploaded_file.size,
                uploaded_by=request.user,
            )
            
            # Criar AnalysisRequest
            analysis = AnalysisRequest.objects.create(
                document=doc,
                user_objective=config_form.cleaned_data["user_objective"],
                professional_area=config_form.cleaned_data["professional_area"],
                professional_area_detail=config_form.cleaned_data.get("professional_area_detail", ""),
                geolocation=config_form.cleaned_data.get("geolocation", ""),
                language=config_form.cleaned_data.get("language", "pt-BR"),
                include_market_references=config_form.cleaned_data.get("include_market_references", True),
                search_scope=config_form.cleaned_data.get("search_scope", ""),
                report_type=config_form.cleaned_data.get("report_type", "analitico"),
                requested_by=request.user,
            )
            
            messages.info(request, "Documento recebido! Joel está analisando...")
            return redirect("analysis_status", analysis_id=analysis.pk)
        else:
            messages.error(request, "Verifique os campos e tente novamente.")
    else:
        upload_form = DocumentUploadForm()
        config_form = AnalysisConfigForm()
    
    return render(request, "pages/upload.html", {
        "upload_form": upload_form,
        "config_form": config_form,
        "page_title": "Nova Análise",
    })


@login_required
def analysis_status_view(request, analysis_id):
    """Exibe status da análise e inicia processamento se ainda pendente."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    # Se pendente, iniciar processamento
    if analysis.status == AnalysisRequest.Status.PENDING:
        # Executar em thread para não bloquear (temporário — futuro: Celery)
        thread = threading.Thread(target=process_analysis, args=(analysis.pk,))
        thread.daemon = True
        thread.start()
    
    return render(request, "pages/analysis.html", {
        "analysis": analysis,
        "page_title": "Analisando...",
        "debug": settings.DEBUG,
    })


@login_required
def retry_view(request, analysis_id):
    """Reprocessa uma análise que falhou sem precisar re-submeter tudo."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    if analysis.status == AnalysisRequest.Status.ERROR:
        # Limpar estado anterior
        analysis.status = AnalysisRequest.Status.PENDING
        analysis.error_message = ""
        analysis.processing_log = ""
        analysis.started_at = None
        analysis.completed_at = None
        analysis.save(update_fields=["status", "error_message", "processing_log", "started_at", "completed_at"])
        
        # Limpar relatório anterior se existir
        Report.objects.filter(analysis=analysis).delete()
        
        messages.info(request, "Reprocessando análise...")
    
    return redirect("analysis_status", analysis_id=analysis.pk)


@login_required
def analysis_poll_view(request, analysis_id):
    """API endpoint para polling do status (HTMX/AJAX)."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    data = {
        "status": analysis.status,
        "status_display": analysis.get_status_display(),
        "completed": analysis.status == AnalysisRequest.Status.COMPLETED,
        "error": analysis.status == AnalysisRequest.Status.ERROR,
        "error_message": analysis.error_message,
        "elapsed": analysis.elapsed_seconds,
    }
    
    # Incluir log se DEBUG está ativo
    if settings.DEBUG:
        data["processing_log"] = analysis.processing_log or ""
    
    if analysis.status == AnalysisRequest.Status.COMPLETED:
        data["report_url"] = f"/report/{analysis.pk}/"
    
    return JsonResponse(data)


def process_analysis(analysis_id: int):
    """
    Processa a análise completa (executada em thread/celery).
    
    Etapas:
    1. Extrair texto com Docling
    2. Executar análise com Joel (Agno + OpenAI)
    3. Gerar relatório em múltiplos formatos
    
    Inclui timeout de PROCESSING_TIMEOUT segundos.
    """
    import django
    django.setup()
    
    try:
        analysis = AnalysisRequest.objects.get(pk=analysis_id)
    except AnalysisRequest.DoesNotExist:
        logger.error(f"AnalysisRequest {analysis_id} não encontrada")
        return
    
    start_time = time.time()
    analysis.mark_started()
    
    def check_timeout(step_name: str):
        """Levanta TimeoutError se excedeu o limite."""
        elapsed = time.time() - start_time
        if elapsed > PROCESSING_TIMEOUT:
            raise TimeoutError(
                f"Timeout de {PROCESSING_TIMEOUT}s excedido na etapa '{step_name}' "
                f"(tempo decorrido: {elapsed:.0f}s)"
            )
    
    try:
        # === ETAPA 1: Extrair texto ===
        analysis.status = AnalysisRequest.Status.EXTRACTING
        analysis.save(update_fields=["status"])
        analysis.append_log("Iniciando extração de texto com Docling...")
        analysis.append_log(f"Arquivo: {analysis.document.original_filename} ({analysis.document.file_size_display})")
        
        file_path = analysis.document.file.path
        parsed = parse_document(file_path)
        
        extracted_text = parsed.get("text", "")
        metadata = parsed.get("metadata", {})
        analysis.append_log(f"Extração concluída: {len(extracted_text)} caracteres extraídos")
        if metadata.get("num_pages"):
            analysis.append_log(f"Páginas detectadas: {metadata['num_pages']}")
        
        if not extracted_text:
            analysis.mark_error("Não foi possível extrair texto do documento.")
            return
        
        analysis.document.extracted_text = extracted_text
        analysis.document.extraction_metadata = metadata
        analysis.document.save(update_fields=["extracted_text", "extraction_metadata"])
        
        check_timeout("extração")
        
        # === ETAPA 2: Joel analisa ===
        analysis.status = AnalysisRequest.Status.ANALYZING
        analysis.save(update_fields=["status"])
        analysis.append_log("Enviando para Joel (GPT-4o) analisar...")
        if analysis.include_market_references:
            analysis.append_log("Busca de referências de mercado ativada (Tavily)")
        
        result = run_analysis(
            extracted_text=extracted_text,
            user_objective=analysis.user_objective,
            professional_area=analysis.professional_area,
            professional_area_detail=analysis.professional_area_detail,
            geolocation=analysis.geolocation,
            language=analysis.language,
            include_market_references=analysis.include_market_references,
            search_scope=analysis.search_scope,
            report_type=analysis.report_type,
        )
        
        content_markdown = result.get("content_markdown", "")
        refs = result.get("references", [])
        analysis.append_log(f"Joel concluiu: {len(content_markdown)} chars de markdown, {len(refs)} referências")
        
        if not content_markdown:
            analysis.mark_error("Joel não conseguiu gerar o relatório.")
            return
        
        check_timeout("análise")
        
        # === ETAPA 3: Gerar formatos ===
        analysis.status = AnalysisRequest.Status.GENERATING
        analysis.save(update_fields=["status"])
        analysis.append_log("Gerando relatório em múltiplos formatos...")
        
        content_html = markdown_to_html(content_markdown)
        title = f"Relatório — {analysis.document.original_filename}"
        references = refs
        
        report = Report.objects.create(
            analysis=analysis,
            content_html=content_html,
            content_markdown=content_markdown,
            references=references,
            search_results_raw=result.get("search_results_raw", []),
            joel_reasoning=result.get("joel_reasoning", ""),
        )
        
        # Gerar PDF
        try:
            pdf_buffer = generate_pdf(content_markdown, title)
            report.file_pdf.save(
                f"relatorio_{analysis.pk}.pdf",
                ContentFile(pdf_buffer.read()),
                save=False,
            )
            analysis.append_log("PDF gerado")
        except Exception as e:
            logger.warning(f"Erro ao gerar PDF: {e}")
            analysis.append_log(f"AVISO: Falha ao gerar PDF — {e}")
        
        # Gerar DOCX
        try:
            docx_buffer = generate_docx(content_markdown, title)
            report.file_docx.save(
                f"relatorio_{analysis.pk}.docx",
                ContentFile(docx_buffer.read()),
                save=False,
            )
            analysis.append_log("DOCX gerado")
        except Exception as e:
            logger.warning(f"Erro ao gerar DOCX: {e}")
            analysis.append_log(f"AVISO: Falha ao gerar DOCX — {e}")
        
        # Gerar XLSX
        try:
            xlsx_buffer = generate_xlsx(content_markdown, references, title)
            report.file_xlsx.save(
                f"relatorio_{analysis.pk}.xlsx",
                ContentFile(xlsx_buffer.read()),
                save=False,
            )
            analysis.append_log("XLSX gerado")
        except Exception as e:
            logger.warning(f"Erro ao gerar XLSX: {e}")
            analysis.append_log(f"AVISO: Falha ao gerar XLSX — {e}")
        
        # Gerar TXT
        try:
            txt_buffer = generate_txt(content_markdown, title)
            report.file_txt.save(
                f"relatorio_{analysis.pk}.txt",
                ContentFile(txt_buffer.read()),
                save=False,
            )
            analysis.append_log("TXT gerado")
        except Exception as e:
            logger.warning(f"Erro ao gerar TXT: {e}")
            analysis.append_log(f"AVISO: Falha ao gerar TXT — {e}")
        
        report.save()
        
        # === CONCLUÍDO ===
        elapsed = time.time() - start_time
        analysis.append_log(f"Todos os formatos gerados. Tempo total: {elapsed:.1f}s")
        analysis.mark_completed()
        logger.info(f"Análise #{analysis.pk} concluída com sucesso em {elapsed:.1f}s")
        
    except TimeoutError as e:
        logger.error(f"Timeout na análise #{analysis_id}: {e}")
        try:
            analysis.mark_error(str(e))
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Erro na análise #{analysis_id}: {e}", exc_info=True)
        try:
            analysis.mark_error(str(e)[:500])
        except Exception:
            pass


@login_required
def edit_analysis_view(request, analysis_id):
    """Exibe formulário pré-preenchido para editar e re-executar uma análise."""
    original = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    if request.method == "POST":
        config_form = AnalysisConfigForm(request.POST)
        
        if config_form.is_valid():
            # Criar nova AnalysisRequest reutilizando o mesmo documento
            new_analysis = AnalysisRequest.objects.create(
                document=original.document,
                user_objective=config_form.cleaned_data["user_objective"],
                professional_area=config_form.cleaned_data["professional_area"],
                professional_area_detail=config_form.cleaned_data.get("professional_area_detail", ""),
                geolocation=config_form.cleaned_data.get("geolocation", ""),
                language=config_form.cleaned_data.get("language", "pt-BR"),
                include_market_references=config_form.cleaned_data.get("include_market_references", True),
                search_scope=config_form.cleaned_data.get("search_scope", ""),
                report_type=config_form.cleaned_data.get("report_type", "analitico"),
                requested_by=request.user,
            )
            
            messages.info(request, "Análise reenviada! Joel está processando com as novas configurações.")
            return redirect("analysis_status", analysis_id=new_analysis.pk)
        else:
            messages.error(request, "Verifique os campos e tente novamente.")
    else:
        # Pré-preencher formulário com dados da análise original
        config_form = AnalysisConfigForm(initial={
            "user_objective": original.user_objective,
            "professional_area": original.professional_area,
            "professional_area_detail": original.professional_area_detail,
            "geolocation": original.geolocation,
            "language": original.language,
            "include_market_references": original.include_market_references,
            "search_scope": original.search_scope,
            "report_type": original.report_type,
        })
    
    return render(request, "pages/edit_analysis.html", {
        "analysis": original,
        "config_form": config_form,
        "page_title": "Editar Análise",
    })


@login_required
def report_view(request, analysis_id):
    """Exibe o relatório gerado na tela."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    if analysis.status != AnalysisRequest.Status.COMPLETED:
        return redirect("analysis_status", analysis_id=analysis.pk)
    
    report = get_object_or_404(Report, analysis=analysis)
    
    return render(request, "pages/report.html", {
        "analysis": analysis,
        "report": report,
        "page_title": "Relatório",
    })


@login_required
def download_view(request, analysis_id, format):
    """Download do relatório em formato específico."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    report = get_object_or_404(Report, analysis=analysis)
    
    format_map = {
        "pdf": (report.file_pdf, "application/pdf", ".pdf"),
        "docx": (report.file_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
        "xlsx": (report.file_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
        "txt": (report.file_txt, "text/plain", ".txt"),
    }
    
    if format not in format_map:
        messages.error(request, f"Formato '{format}' não suportado.")
        return redirect("report", analysis_id=analysis.pk)
    
    file_field, content_type, extension = format_map[format]
    
    if not file_field:
        messages.error(request, f"Arquivo {format.upper()} não disponível para este relatório.")
        return redirect("report", analysis_id=analysis.pk)
    
    filename = f"relatorio_{analysis.document.original_filename.rsplit('.', 1)[0]}{extension}"
    
    response = HttpResponse(file_field.read(), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def history_view(request):
    """Histórico de análises do usuário."""
    analyses = AnalysisRequest.objects.filter(
        requested_by=request.user
    ).select_related("document").order_by("-created_at")
    
    return render(request, "pages/history.html", {
        "analyses": analyses,
        "page_title": "Histórico",
    })
