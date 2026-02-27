"""
core/views.py — Views do interpretador de documentos.

Fluxo principal:
1. upload_view: Upload do documento + configuração da análise
2. process_analysis: Executa a análise (extração → IA → relatório)
3. report_view: Exibe o relatório na tela
4. download_view: Download do relatório em PDF/DOCX/XLSX/TXT
5. history_view: Histórico de análises do usuário
6. cancel_analysis: Cancela análise em andamento
7. delete_analysis: Exclui análise e arquivos associados
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
from django.views.decorators.http import require_POST

from .models import Document, AnalysisRequest, Report, Suggestion
from .forms import DocumentUploadForm, AnalysisConfigForm, SuggestionForm
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
PROCESSING_TIMEOUT = int(os.environ.get("JOEL_TIMEOUT", 120))  # 2 min hard limit


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
            
            messages.info(request, "Documento recebido! Sua análise está sendo processada...")
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
        "page_title": "Processando...",
    })


@login_required
def retry_view(request, analysis_id):
    """Reprocessa uma análise que falhou sem precisar re-submeter tudo."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    if analysis.status in (AnalysisRequest.Status.ERROR, AnalysisRequest.Status.CANCELLED):
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
    
    data["cancelled"] = analysis.status == AnalysisRequest.Status.CANCELLED
    
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
                f"Tempo limite de {PROCESSING_TIMEOUT}s excedido. "
                f"Tente novamente com um documento menor ou objetivo mais específico."
            )
        # Check if user cancelled
        analysis.refresh_from_db(fields=["status"])
        if analysis.status == AnalysisRequest.Status.CANCELLED:
            raise InterruptedError("Análise cancelada pelo usuário.")
    
    try:
        # === ETAPA 1: Extrair texto (skip se já existe) ===
        existing_text = (analysis.document.extracted_text or "").strip()
        
        if existing_text:
            # Texto já extraído anteriormente
            analysis.status = AnalysisRequest.Status.EXTRACTING
            analysis.save(update_fields=["status"])
            analysis.append_log("Documento já processado anteriormente, aproveitando dados.")
            extracted_text = existing_text
        else:
            analysis.status = AnalysisRequest.Status.EXTRACTING
            analysis.save(update_fields=["status"])
            analysis.append_log("Aplicando capacidade computacional ao documento...")
            analysis.append_log(f"Arquivo: {analysis.document.original_filename} ({analysis.document.file_size_display})")
            
            file_path = analysis.document.file.path
            parsed = parse_document(file_path)
            
            extracted_text = parsed.get("text", "")
            metadata = parsed.get("metadata", {})
            analysis.append_log(f"Documento processado: {len(extracted_text)} caracteres extraídos")
            if parsed.get("error"):
                analysis.append_log("Aviso: parte do conteúdo pode requerer processamento adicional.")
            
            if not extracted_text:
                analysis.mark_error("Não foi possível extrair texto do documento.")
                return
            
            analysis.document.extracted_text = extracted_text
            analysis.document.extraction_metadata = metadata
            analysis.document.save(update_fields=["extracted_text", "extraction_metadata"])
        
        check_timeout("extração")
        
        # === ETAPA 2: Joel analisa (busca + relatório integrados) ===
        analysis.status = AnalysisRequest.Status.ANALYZING
        analysis.save(update_fields=["status"])
        analysis.append_log("Iniciando análise inteligente do conteúdo...")
        if analysis.include_market_references:
            analysis.append_log("Pesquisa de referências de mercado habilitada.")
        
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
        analysis.append_log(f"Análise concluída: {len(refs)} referências encontradas.")
        
        if not content_markdown:
            analysis.mark_error("Não foi possível gerar o relatório. Tente novamente.")
            return
        
        check_timeout("análise")
        
        # === ETAPA 3: Gerar formatos ===
        analysis.status = AnalysisRequest.Status.GENERATING
        analysis.save(update_fields=["status"])
        analysis.append_log("Elaborando relatório profissional em múltiplos formatos...")
        
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
            analysis.append_log("Formato PDF pronto.")
        except Exception as e:
            logger.warning(f"Erro ao gerar PDF: {e}")
            analysis.append_log("Aviso: formato PDF indisponível para este relatório.")
        
        # Gerar DOCX
        try:
            docx_buffer = generate_docx(content_markdown, title)
            report.file_docx.save(
                f"relatorio_{analysis.pk}.docx",
                ContentFile(docx_buffer.read()),
                save=False,
            )
            analysis.append_log("Formato Word pronto.")
        except Exception as e:
            logger.warning(f"Erro ao gerar DOCX: {e}")
            analysis.append_log("Aviso: formato Word indisponível para este relatório.")
        
        # Gerar XLSX
        try:
            xlsx_buffer = generate_xlsx(content_markdown, references, title)
            report.file_xlsx.save(
                f"relatorio_{analysis.pk}.xlsx",
                ContentFile(xlsx_buffer.read()),
                save=False,
            )
            analysis.append_log("Formato Excel pronto.")
        except Exception as e:
            logger.warning(f"Erro ao gerar XLSX: {e}")
            analysis.append_log("Aviso: formato Excel indisponível para este relatório.")
        
        # Gerar TXT
        try:
            txt_buffer = generate_txt(content_markdown, title)
            report.file_txt.save(
                f"relatorio_{analysis.pk}.txt",
                ContentFile(txt_buffer.read()),
                save=False,
            )
            analysis.append_log("Formato texto pronto.")
        except Exception as e:
            logger.warning(f"Erro ao gerar TXT: {e}")
            analysis.append_log("Aviso: formato texto indisponível para este relatório.")
        
        report.save()
        
        # === CONCLUÍDO ===
        elapsed = time.time() - start_time
        analysis.append_log("Relatório finalizado com sucesso!")
        analysis.mark_completed()
        logger.info(f"Análise #{analysis.pk} concluída com sucesso em {elapsed:.1f}s")
        
    except TimeoutError as e:
        logger.error(f"Timeout na análise #{analysis_id}: {e}")
        try:
            analysis.mark_error(str(e))
        except Exception:
            pass
    except InterruptedError:
        logger.info(f"Análise #{analysis_id} cancelada pelo usuário")
    except Exception as e:
        logger.error(f"Erro na análise #{analysis_id}: {e}", exc_info=True)
        try:
            analysis.mark_error(
                "Ocorreu um erro ao processar sua análise. "
                "Tente novamente ou envie um documento diferente."
            )
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
            
            messages.info(request, "Análise reenviada! Processando com as novas configurações.")
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
        "suggestion_form": SuggestionForm(),
    })


@login_required
@require_POST
def submit_suggestion(request):
    """Recebe sugestão de melhoria do usuário. POST only, redirect back."""
    form = SuggestionForm(request.POST)
    if form.is_valid():
        suggestion = form.save(commit=False)
        suggestion.user = request.user
        suggestion.save()
        logger.info("Sugestão #%s criada por %s: %s", suggestion.pk, request.user.username, suggestion.title)
        messages.success(request, "Sugestão enviada com sucesso! Analisaremos em breve. Obrigado!")
    else:
        messages.error(request, "Preencha todos os campos da sugestão (título e descrição são obrigatórios).")
    
    # Redirect back to the referring page, default to history
    referer = request.META.get("HTTP_REFERER", "")
    if referer:
        return redirect(referer)
    return redirect("history")


@login_required
@require_POST
def cancel_analysis(request, analysis_id):
    """Cancela uma análise em andamento."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    active_statuses = [
        AnalysisRequest.Status.PENDING,
        AnalysisRequest.Status.EXTRACTING,
        AnalysisRequest.Status.ANALYZING,
        AnalysisRequest.Status.SEARCHING,
        AnalysisRequest.Status.GENERATING,
    ]
    
    if analysis.status in active_statuses:
        analysis.status = AnalysisRequest.Status.CANCELLED
        analysis.error_message = "Cancelado pelo usuário."
        analysis.save(update_fields=["status", "error_message"])
        logger.info("Análise #%s cancelada por %s", analysis.pk, request.user.username)
        messages.info(request, "Análise cancelada.")
    
    return redirect("history")


@login_required
@require_POST
def delete_analysis(request, analysis_id):
    """Exclui uma análise e seus dados associados (documento, relatório, arquivos)."""
    analysis = get_object_or_404(
        AnalysisRequest, pk=analysis_id, requested_by=request.user
    )
    
    doc = analysis.document
    filename = doc.original_filename
    
    # Deletar relatório e arquivos gerados
    try:
        report = Report.objects.filter(analysis=analysis).first()
        if report:
            for field in [report.file_pdf, report.file_docx, report.file_xlsx, report.file_txt]:
                if field:
                    try:
                        field.delete(save=False)
                    except Exception:
                        pass
            report.delete()
    except Exception:
        pass
    
    # Deletar análise
    analysis.delete()
    
    # Deletar documento se não tem mais análises associadas
    if not doc.analyses.exists():
        if doc.file:
            try:
                doc.file.delete(save=False)
            except Exception:
                pass
        doc.delete()
    
    logger.info("Análise de '%s' excluída por %s", filename, request.user.username)
    messages.success(request, f"Análise de \"{filename}\" excluída com sucesso.")
    return redirect("history")
