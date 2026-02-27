"""
Joel Tools — Ferramentas de parsing para o agente Joel.

Estratégia de extração (otimizada para < 60s):
1. PDFs: pypdf primeiro (< 3s). Se extrair texto suficiente, PRONTO.
2. PDFs escaneados (pypdf falhou): Docling SEM OCR, com timeout de 45s.
3. Outros formatos (DOCX, XLSX, etc.): Docling com timeout de 45s.
4. Último fallback: leitura como texto puro.

Busca via Tavily é nativa do Agno (TavilyTools) — não precisa de classe aqui.
"""

import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Limites
# ---------------------------------------------------------------------------
EXTRACTION_TIMEOUT = 45      # segundos máx para extração de texto
MAX_NUM_PAGES = 50           # páginas máx (protege contra docs enormes)
MAX_FILE_SIZE = 30_000_000   # 30 MB
MIN_TEXT_RATIO = 50          # caracteres mínimos por página para considerar "bom"

# ---------------------------------------------------------------------------
# Docling converter singleton (lazy, thread-safe)
# ---------------------------------------------------------------------------
_converter = None
_converter_lock = threading.Lock()


def _get_converter():
    """Retorna (ou cria) o DocumentConverter singleton — SEM OCR para velocidade."""
    global _converter
    if _converter is not None:
        return _converter

    with _converter_lock:
        if _converter is not None:
            return _converter

        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TableFormerMode,
                TableStructureOptions,
            )
            from docling.document_converter import DocumentConverter, PdfFormatOption

            pdf_options = PdfPipelineOptions(
                document_timeout=EXTRACTION_TIMEOUT,

                # OCR DESLIGADO — é o maior vilão de performance.
                # pypdf já extrai texto de PDFs com camada de texto.
                # Só PDFs 100% escaneados perdem, mas é trade-off aceito.
                do_ocr=False,

                # Tabelas FAST (~2x mais rápido que ACCURATE)
                do_table_structure=True,
                table_structure_options=TableStructureOptions(
                    mode=TableFormerMode.FAST,
                    do_cell_matching=True,
                ),

                # Tudo que não precisamos: DESLIGADO
                do_picture_classification=False,
                do_picture_description=False,
                do_code_enrichment=False,
                do_formula_enrichment=False,
                generate_page_images=False,
                generate_picture_images=False,
                generate_table_images=False,
            )

            _converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pdf_options,
                    ),
                },
            )
            logger.info("Docling: converter inicializado (OCR=off, tables=FAST)")

        except ImportError:
            logger.warning("Docling não disponível")
            _converter = None

        return _converter


# ---------------------------------------------------------------------------
# Fast-path: pypdf para PDFs com texto embutido
# ---------------------------------------------------------------------------
def _extract_pdf_fast(file_path: str) -> dict | None:
    """
    Extração rápida com pypdf (< 3s mesmo para PDFs grandes).
    Retorna dict com text/metadata ou None se não extraiu texto suficiente.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        num_pages = len(reader.pages)

        if num_pages > MAX_NUM_PAGES:
            logger.warning(f"pypdf: PDF com {num_pages} páginas, limitando a {MAX_NUM_PAGES}")

        pages_to_read = min(num_pages, MAX_NUM_PAGES)
        text_parts = []
        for i in range(pages_to_read):
            page_text = reader.pages[i].extract_text() or ""
            text_parts.append(page_text)

        text = "\n\n".join(text_parts).strip()

        # Verificar se extraiu texto suficiente
        if len(text) < MIN_TEXT_RATIO * pages_to_read:
            logger.info(
                f"pypdf: pouco texto ({len(text)} chars / {pages_to_read} pgs) "
                f"— provavelmente escaneado, passando para Docling"
            )
            return None

        logger.info(f"pypdf: extraiu {len(text)} chars de {pages_to_read} páginas em < 3s")
        return {
            "text": text,
            "metadata": {
                "pages": num_pages,
                "format": ".pdf",
                "engine": "pypdf",
            },
        }

    except Exception as e:
        logger.warning(f"pypdf falhou: {e}")
        return None


# ---------------------------------------------------------------------------
# Docling extraction com hard timeout via ThreadPoolExecutor
# ---------------------------------------------------------------------------
def _extract_with_docling(file_path: str) -> dict | None:
    """Extrai com Docling, respeitando EXTRACTION_TIMEOUT via futures."""
    converter = _get_converter()
    if converter is None:
        return None

    def _do_convert():
        result = converter.convert(
            file_path,
            max_num_pages=MAX_NUM_PAGES,
            max_file_size=MAX_FILE_SIZE,
        )
        text = result.document.export_to_markdown()
        try:
            pages = result.document.num_pages()
        except Exception:
            pages = None
        return text, pages

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_convert)
            text, pages = future.result(timeout=EXTRACTION_TIMEOUT)

        if not text or not text.strip():
            return None

        logger.info(f"Docling: extraiu {len(text)} chars")
        return {
            "text": text,
            "metadata": {
                "pages": pages,
                "format": os.path.splitext(file_path)[1].lower(),
                "engine": "docling",
            },
        }

    except FuturesTimeout:
        logger.error(f"Docling: TIMEOUT ({EXTRACTION_TIMEOUT}s) — abortando extração")
        return None
    except Exception as e:
        logger.error(f"Docling: erro — {e}")
        return None


# ---------------------------------------------------------------------------
# Fallback: leitura como texto puro
# ---------------------------------------------------------------------------
def _extract_plaintext(file_path: str) -> dict | None:
    """Última tentativa: ler como arquivo de texto."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        if text.strip():
            return {
                "text": text,
                "metadata": {
                    "format": os.path.splitext(file_path)[1].lower(),
                    "engine": "plaintext",
                },
            }
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def parse_document(file_path: str) -> dict:
    """
    Extrai texto de qualquer documento em < 60 segundos.

    Estratégia em cascata:
    1. PDF → pypdf (rápido, < 3s)
    2. Se pypdf falhou ou não é PDF → Docling com timeout de 45s
    3. Último fallback → leitura como texto puro

    Args:
        file_path: Caminho absoluto para o arquivo

    Returns:
        dict com 'text', 'metadata', e opcionalmente 'error'
    """
    ext = os.path.splitext(file_path)[1].lower()
    logger.info(f"parse_document: {os.path.basename(file_path)} ({ext})")

    # --- Fast path: pypdf para PDFs ---
    if ext == ".pdf":
        result = _extract_pdf_fast(file_path)
        if result:
            return result
        logger.info("pypdf insuficiente — tentando Docling...")

    # --- Docling para todos os formatos (com timeout) ---
    result = _extract_with_docling(file_path)
    if result:
        return result

    # --- Último fallback: texto puro ---
    result = _extract_plaintext(file_path)
    if result:
        return result

    return {"text": "", "metadata": {}, "error": "Não foi possível extrair texto do documento"}
