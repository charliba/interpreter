"""
Joel Tools — Ferramentas de parsing para o agente Joel.

Docling best-practices (v2.75+):
- PdfPipelineOptions com document_timeout, TableFormerMode.FAST
- Singleton converter (evita recarregar modelos a cada chamada)
- max_num_pages / max_file_size para proteger contra docs enormes
- Busca via Tavily agora é nativa do Agno (TavilyTools) — não precisa mais de classe aqui
"""

import os
import logging
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Converter singleton — Docling carrega modelos pesados na primeira chamada.
# Reutilizar a instância evita reload a cada documento.
# ---------------------------------------------------------------------------
_converter = None
_converter_lock = threading.Lock()

# Limites de segurança para documentos
MAX_NUM_PAGES = 200          # máximo de páginas por documento
MAX_FILE_SIZE = 50_000_000   # 50 MB


def _get_converter():
    """Retorna (ou cria) o DocumentConverter singleton com pipeline otimizado."""
    global _converter
    if _converter is not None:
        return _converter

    with _converter_lock:
        # Double-check após adquirir lock
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

            # --- PDF pipeline otimizado ---
            pdf_options = PdfPipelineOptions(
                # Timeout: docs recomendam 90-120s para produção
                document_timeout=120,

                # OCR (necessário para PDFs escaneados)
                do_ocr=True,

                # Tabelas: FAST é ~2x mais rápido que ACCURATE
                do_table_structure=True,
                table_structure_options=TableStructureOptions(
                    mode=TableFormerMode.FAST,
                    do_cell_matching=True,
                ),

                # Desabilitar features que não usamos (economia de tempo)
                do_picture_classification=False,
                do_picture_description=False,
                do_code_enrichment=False,
                do_formula_enrichment=False,

                # Não gerar imagens (não precisamos)
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
            logger.info("Docling: DocumentConverter inicializado com pipeline otimizado")

        except ImportError:
            logger.warning("Docling não instalado — usando DocumentConverter padrão")
            from docling.document_converter import DocumentConverter
            _converter = DocumentConverter()

        return _converter


def parse_document(file_path: str) -> dict:
    """
    Extrai texto e estrutura de qualquer documento usando Docling.

    Suporta: PDF, DOCX, XLSX, PPTX, HTML, imagens (OCR), TXT, CSV, MD

    Best practices aplicadas (Docling v2.75+):
    - Singleton converter (reaproveita modelos carregados)
    - PdfPipelineOptions: document_timeout=120s, TableFormerMode.FAST
    - Features desnecessárias desligadas (picture desc, code/formula)
    - Limites: max_num_pages=200, max_file_size=50MB

    Args:
        file_path: Caminho absoluto para o arquivo

    Returns:
        dict com 'text' (texto extraído), 'metadata' (metadados)
    """
    try:
        converter = _get_converter()

        logger.info(f"Docling: parseando {file_path}")

        result = converter.convert(
            file_path,
            max_num_pages=MAX_NUM_PAGES,
            max_file_size=MAX_FILE_SIZE,
        )

        # Extrair texto do resultado
        text = result.document.export_to_markdown()

        # num_pages() é um método, não propriedade
        try:
            pages = result.document.num_pages()
        except Exception:
            pages = None

        metadata = {
            "pages": pages,
            "format": os.path.splitext(file_path)[1].lower(),
        }

        logger.info(f"Docling: extraiu {len(text)} caracteres de {file_path}")

        return {
            "text": text,
            "metadata": metadata,
        }

    except ImportError:
        logger.error("docling não instalado. Execute: pip install docling")
        return {"text": "", "metadata": {}, "error": "docling não instalado"}
    except Exception as e:
        logger.error(f"Erro no parsing Docling: {e}")
        # Fallback: tentar ler como texto puro
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return {
                "text": text,
                "metadata": {"format": os.path.splitext(file_path)[1].lower(), "fallback": True},
            }
        except Exception:
            return {"text": "", "metadata": {}, "error": str(e)}
