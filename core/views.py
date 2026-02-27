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
from .joel.charts import generate_charts_from_markdown
from .joel.ai_images import generate_report_images

logger = logging.getLogger(__name__)

# Timeout máximo para processamento (segundos)
PROCESSING_TIMEOUT = int(os.environ.get("JOEL_TIMEOUT", 120))  # 2 min hard limit


@login_required
def upload_view(request):
    """
    GET: Mostra formulário de upload + configuração.
    POST: Recebe documento(s) e configuração, inicia análise.
    Suporta 4 modos: document, multi_document, enhancement, free_form.
    """
    if request.method == "POST":
        config_form = AnalysisConfigForm(request.POST)
        upload_form = DocumentUploadForm(request.POST, request.FILES)
        
        analysis_mode = request.POST.get("analysis_mode", "document")
        uploaded_files = request.FILES.getlist("file")
        
        if config_form.is_valid():
            # --- Free form: no document needed ---
            if analysis_mode == "free_form":
                analysis = AnalysisRequest.objects.create(
                    analysis_mode=analysis_mode,
                    document=None,
                    user_objective=config_form.cleaned_data["user_objective"],
                    professional_area=config_form.cleaned_data["professional_area"],
                    professional_area_detail=config_form.cleaned_data.get("professional_area_detail", ""),
                    geolocation=config_form.cleaned_data.get("geolocation", ""),
                    language=config_form.cleaned_data.get("language", "pt-BR"),
                    include_market_references=config_form.cleaned_data.get("include_market_references", True),
                    source_count=config_form.cleaned_data.get("source_count", 5),
                    include_images=config_form.cleaned_data.get("include_images", False),
                    search_scope=config_form.cleaned_data.get("search_scope", ""),
                    report_type=config_form.cleaned_data.get("report_type", "analitico"),
                    requested_by=request.user,
                )
                messages.info(request, "Análise livre iniciada! Joel está pesquisando e produzindo seu relatório...")
                return redirect("analysis_status", analysis_id=analysis.pk)
            
            # --- Document-based modes: need at least one file ---
            if not uploaded_files:
                messages.error(request, "Envie ao menos um documento para este modo de análise.")
            else:
                # Create Document objects for each file
                docs = []
                for uf in uploaded_files:
                    doc = Document.objects.create(
                        file=uf,
                        original_filename=uf.name,
                        file_type=os.path.splitext(uf.name)[1].lower().lstrip("."),
                        file_size=uf.size,
                        uploaded_by=request.user,
                    )
                    docs.append(doc)
                
                primary_doc = docs[0]
                additional_docs = docs[1:] if len(docs) > 1 else []
                
                # Determine effective mode
                if len(docs) > 1 and analysis_mode == "document":
                    analysis_mode = "multi_document"
                
                analysis = AnalysisRequest.objects.create(
                    analysis_mode=analysis_mode,
                    document=primary_doc,
                    user_objective=config_form.cleaned_data["user_objective"],
                    professional_area=config_form.cleaned_data["professional_area"],
                    professional_area_detail=config_form.cleaned_data.get("professional_area_detail", ""),
                    geolocation=config_form.cleaned_data.get("geolocation", ""),
                    language=config_form.cleaned_data.get("language", "pt-BR"),
                    include_market_references=config_form.cleaned_data.get("include_market_references", True),
                    source_count=config_form.cleaned_data.get("source_count", 5),
                    include_images=config_form.cleaned_data.get("include_images", False),
                    search_scope=config_form.cleaned_data.get("search_scope", ""),
                    report_type="enhancement" if analysis_mode == "enhancement" else config_form.cleaned_data.get("report_type", "analitico"),
                    requested_by=request.user,
                )
                
                # Add additional documents (M2M requires pk)
                if additional_docs:
                    analysis.additional_documents.set(additional_docs)
                
                mode_labels = {
                    "document": "Documento recebido!",
                    "multi_document": f"{len(docs)} documentos recebidos!",
                    "enhancement": "Documento recebido para aprimoramento!",
                }
                messages.info(request, f"{mode_labels.get(analysis_mode, 'Recebido!')} Sua análise está sendo processada...")
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
    
    Modos suportados:
    - document: análise de documento único
    - multi_document: análise conjunta de múltiplos documentos
    - enhancement: aprimoramento do documento com IA
    - free_form: análise livre sem documento (apenas pesquisa)
    
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
        # === ETAPA 1: Extrair texto ===
        analysis.status = AnalysisRequest.Status.EXTRACTING
        analysis.save(update_fields=["status"])
        
        extracted_text = ""
        
        if analysis.is_free_form:
            # Free-form: no document, use objective as the topic
            analysis.append_log("Modo Análise Livre — sem documento, pesquisando do zero...")
            extracted_text = ""  # Will rely on Joel + Tavily for research
        else:
            # Extract from all documents
            all_docs = analysis.all_documents
            analysis.append_log(f"Processando {len(all_docs)} documento(s)...")
            
            text_parts = []
            for doc in all_docs:
                existing = (doc.extracted_text or "").strip()
                if existing:
                    analysis.append_log(f"  ✓ {doc.original_filename} (já processado)")
                    text_parts.append(f"### DOCUMENTO: {doc.original_filename}\n\n{existing}")
                else:
                    analysis.append_log(f"  → Processando: {doc.original_filename} ({doc.file_size_display})")
                    try:
                        parsed = parse_document(doc.file.path)
                        doc_text = parsed.get("text", "")
                        metadata = parsed.get("metadata", {})
                        
                        if doc_text:
                            doc.extracted_text = doc_text
                            doc.extraction_metadata = metadata
                            doc.save(update_fields=["extracted_text", "extraction_metadata"])
                            text_parts.append(f"### DOCUMENTO: {doc.original_filename}\n\n{doc_text}")
                            analysis.append_log(f"    {len(doc_text)} caracteres extraídos")
                        else:
                            analysis.append_log(f"    ⚠ Não foi possível extrair texto de {doc.original_filename}")
                    except Exception as e:
                        analysis.append_log(f"    ⚠ Erro ao processar {doc.original_filename}: {str(e)[:80]}")
            
            extracted_text = "\n\n---\n\n".join(text_parts)
            
            if not extracted_text and not analysis.is_free_form:
                analysis.mark_error("Não foi possível extrair texto de nenhum documento enviado.")
                return
            
            analysis.append_log(f"Total: {len(extracted_text)} caracteres extraídos de {len(text_parts)} documento(s)")
        
        check_timeout("extração")
        
        # === ETAPA 2: Joel analisa ===
        analysis.status = AnalysisRequest.Status.ANALYZING
        analysis.save(update_fields=["status"])
        
        mode_labels = {
            "document": "análise de documento",
            "multi_document": "análise multi-documento",
            "enhancement": "aprimoramento de documento",
            "free_form": "análise livre com pesquisa",
        }
        analysis.append_log(f"Iniciando {mode_labels.get(analysis.analysis_mode, 'análise')}...")
        if analysis.include_market_references:
            analysis.append_log(f"Pesquisa habilitada — buscando até {analysis.source_count} fontes.")
        if analysis.include_images:
            analysis.append_log("Geração de imagens por IA habilitada.")
        
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
            analysis_mode=analysis.analysis_mode,
            source_count=analysis.source_count,
            include_images=analysis.include_images,
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
        
        # Generate charts from data in the markdown
        charts_base64 = []
        try:
            charts_base64 = generate_charts_from_markdown(content_markdown, max_charts=4)
            if charts_base64:
                analysis.append_log(f"{len(charts_base64)} visualizações geradas automaticamente.")
        except Exception as e:
            logger.warning(f"Erro ao gerar gráficos: {e}")
        
        # Generate AI images if requested
        ai_images_base64 = []
        if analysis.include_images:
            try:
                ai_images_base64 = generate_report_images(
                    content_markdown=content_markdown,
                    professional_area=analysis.professional_area,
                    analysis_mode=analysis.analysis_mode,
                    max_images=3,
                )
                if ai_images_base64:
                    analysis.append_log(f"{len(ai_images_base64)} imagens profissionais geradas.")
            except Exception as e:
                logger.warning(f"Erro ao gerar imagens: {e}")
                analysis.append_log("Aviso: imagens de IA indisponíveis para este relatório.")
        
        # Combine charts and AI images (both are list[dict] with keys: base64, title)
        all_visuals = charts_base64 + ai_images_base64
        
        content_html = markdown_to_html(content_markdown, charts_base64=all_visuals)
        
        if analysis.document:
            title = f"Relatório — {analysis.document.original_filename}"
            if analysis.is_multi_doc:
                names = ", ".join(analysis.document_names[:3])
                if len(analysis.document_names) > 3:
                    names += f" (+{len(analysis.document_names) - 3})"
                title = f"Relatório — {names}"
        else:
            title = f"Relatório — {analysis.user_objective[:60]}"
        
        references = refs
        
        # Get display labels for area/type
        area_display = analysis.get_professional_area_display()
        type_display = analysis.get_report_type_display()
        
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
            pdf_buffer = generate_pdf(
                content_markdown, title,
                charts_base64=all_visuals,
                professional_area=area_display,
                report_type=type_display,
            )
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
            docx_buffer = generate_docx(
                content_markdown, title,
                charts_base64=all_visuals,
                professional_area=area_display,
                report_type=type_display,
            )
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
            xlsx_buffer = generate_xlsx(
                content_markdown, references, title,
                charts_base64=all_visuals,
            )
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
        import traceback as tb
        full_tb = tb.format_exc()
        logger.error(f"Erro na análise #{analysis_id}: {e}\n{full_tb}")
        try:
            # Salva o erro real no log da análise para diagnóstico
            analysis.append_log(f"ERRO: {type(e).__name__}: {str(e)[:300]}")
            analysis.append_log(f"Traceback: {full_tb[-500:]}")
            analysis.mark_error(
                f"Erro ao processar: {type(e).__name__}: {str(e)[:200]}. "
                f"Tente novamente ou envie um documento diferente."
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
                analysis_mode=original.analysis_mode,
                document=original.document,
                user_objective=config_form.cleaned_data["user_objective"],
                professional_area=config_form.cleaned_data["professional_area"],
                professional_area_detail=config_form.cleaned_data.get("professional_area_detail", ""),
                geolocation=config_form.cleaned_data.get("geolocation", ""),
                language=config_form.cleaned_data.get("language", "pt-BR"),
                include_market_references=config_form.cleaned_data.get("include_market_references", True),
                source_count=config_form.cleaned_data.get("source_count", 5),
                include_images=config_form.cleaned_data.get("include_images", False),
                search_scope=config_form.cleaned_data.get("search_scope", ""),
                report_type=config_form.cleaned_data.get("report_type", "analitico"),
                requested_by=request.user,
            )
            
            # Copy additional documents if multi-doc
            if original.additional_documents.exists():
                new_analysis.additional_documents.set(original.additional_documents.all())
            
            messages.info(request, "Análise reenviada! Processando com as novas configurações.")
            return redirect("analysis_status", analysis_id=new_analysis.pk)
        else:
            messages.error(request, "Verifique os campos e tente novamente.")
    else:
        # Pré-preencher formulário com dados da análise original
        config_form = AnalysisConfigForm(initial={
            "analysis_mode": original.analysis_mode,
            "user_objective": original.user_objective,
            "professional_area": original.professional_area,
            "professional_area_detail": original.professional_area_detail,
            "geolocation": original.geolocation,
            "language": original.language,
            "include_market_references": original.include_market_references,
            "source_count": original.source_count,
            "include_images": original.include_images,
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
    
    base_name = analysis.document.original_filename.rsplit('.', 1)[0] if analysis.document else "analise_livre"
    filename = f"relatorio_{base_name}{extension}"
    
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
    filename = doc.original_filename if doc else "Análise Livre"
    
    # Collect additional documents
    additional_docs = list(analysis.additional_documents.all()) if analysis.pk else []
    
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
    
    # Deletar documentos se não tem mais análises associadas
    all_docs = ([doc] if doc else []) + additional_docs
    for d in all_docs:
        if not d.analyses.exists() and not d.additional_analyses.exists():
            if d.file:
                try:
                    d.file.delete(save=False)
                except Exception:
                    pass
            d.delete()
    
    logger.info("Análise de '%s' excluída por %s", filename, request.user.username)
    messages.success(request, f"Análise de \"{filename}\" excluída com sucesso.")
    return redirect("history")
