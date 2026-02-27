"""
Joel Report Generator — Converte relatórios para múltiplos formatos.

Formatos suportados:
- PDF (via ReportLab)
- DOCX (via python-docx)
- XLSX (via openpyxl — dados tabulares e referências)
- TXT (plain text)
"""

import os
import io
import logging
from datetime import datetime

import markdown as md
import bleach
from django.conf import settings

logger = logging.getLogger(__name__)

ALLOWED_TAGS = bleach.ALLOWED_TAGS | {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "strong", "em", "a", "code", "pre", "blockquote",
    "img", "div", "span",
}
ALLOWED_ATTRS = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}


def markdown_to_html(markdown_text: str) -> str:
    """Converte Markdown para HTML sanitizado."""
    html = md.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)


def generate_pdf(markdown_text: str, title: str = "Relatório") -> io.BytesIO:
    """
    Gera PDF profissional a partir de Markdown.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=HexColor("#1e3a5f"),
        spaceAfter=20,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="ReportH2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HexColor("#2563eb"),
        spaceBefore=16,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="ReportH3",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=HexColor("#1e40af"),
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ReportBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ReportFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=HexColor("#6b7280"),
        alignment=TA_CENTER,
    ))
    
    story = []
    
    # Cover / Title
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(title, styles["ReportTitle"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="80%", color=HexColor("#2563eb"), thickness=2))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Gerado por Joel — Agente de Análise de Documentos<br/>Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["ReportFooter"],
    ))
    story.append(PageBreak())
    
    # Parse markdown content into paragraphs
    lines = markdown_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.3 * cm))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], styles["ReportH3"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["ReportH2"]))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], styles["ReportTitle"]))
        elif line.startswith("---"):
            story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb"), thickness=1))
        elif line.startswith("- ") or line.startswith("* "):
            bullet_text = f"• {line[2:]}"
            story.append(Paragraph(bullet_text, styles["ReportBody"]))
        else:
            # Handle bold and italic
            line = line.replace("**", "<b>").replace("*", "<i>")
            # Simple fix for unmatched tags
            if line.count("<b>") % 2 != 0:
                line += "</b>"
            if line.count("<i>") % 2 != 0:
                line += "</i>"
            try:
                story.append(Paragraph(line, styles["ReportBody"]))
            except Exception:
                story.append(Paragraph(bleach.clean(line, tags=set(), strip=True), styles["ReportBody"]))
    
    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        # Fallback: PDF simples
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = [Paragraph(title, styles["Title"]), Spacer(1, 1 * cm)]
        for line in markdown_text.split("\n"):
            if line.strip():
                try:
                    story.append(Paragraph(bleach.clean(line.strip(), tags=set(), strip=True), styles["Normal"]))
                except Exception:
                    pass
        doc.build(story)
    
    buffer.seek(0)
    return buffer


def generate_docx(markdown_text: str, title: str = "Relatório") -> io.BytesIO:
    """
    Gera DOCX profissional a partir de Markdown.
    """
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    doc = Document()
    
    # Estilos
    style = doc.styles["Normal"]
    style.font.size = Pt(11)
    style.font.name = "Calibri"
    
    # Título
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title_para.runs:
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x5F)
    
    doc.add_paragraph(f"Gerado por Joel — Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_page_break()
    
    # Parse markdown
    lines = markdown_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("---"):
            doc.add_paragraph("_" * 60)
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. "):
            doc.add_paragraph(line[3:], style="List Number")
        else:
            # Clean markdown formatting
            clean = line.replace("**", "").replace("*", "")
            doc.add_paragraph(clean)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def generate_xlsx(markdown_text: str, references: list = None, title: str = "Relatório") -> io.BytesIO:
    """
    Gera XLSX com dados estruturados do relatório e referências.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    wb = Workbook()
    
    # Sheet 1: Conteúdo do Relatório
    ws = wb.active
    ws.title = "Relatório"
    
    # Header
    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=12)
    
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=16, color="1E3A5F")
    ws["A2"] = f"Gerado por Joel — {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws["A2"].font = Font(italic=True, size=10, color="6B7280")
    
    row = 4
    for line in markdown_text.split("\n"):
        line = line.strip()
        if not line:
            row += 1
            continue
        
        cell = ws.cell(row=row, column=1, value=line.replace("**", "").replace("*", "").replace("#", "").strip())
        
        if line.startswith("# "):
            cell.font = Font(bold=True, size=14, color="1E3A5F")
        elif line.startswith("## "):
            cell.font = Font(bold=True, size=12, color="2563EB")
        elif line.startswith("### "):
            cell.font = Font(bold=True, size=11, color="1E40AF")
        else:
            cell.font = Font(size=10)
        
        row += 1
    
    ws.column_dimensions["A"].width = 100
    
    # Sheet 2: Referências
    if references:
        ws_ref = wb.create_sheet("Referências")
        headers = ["#", "Título", "URL", "Resumo"]
        for col, header in enumerate(headers, 1):
            cell = ws_ref.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for idx, ref in enumerate(references, 1):
            ws_ref.cell(row=idx + 1, column=1, value=idx)
            ws_ref.cell(row=idx + 1, column=2, value=ref.get("title", ""))
            ws_ref.cell(row=idx + 1, column=3, value=ref.get("url", ""))
            ws_ref.cell(row=idx + 1, column=4, value=ref.get("content", "")[:500])
        
        ws_ref.column_dimensions["A"].width = 5
        ws_ref.column_dimensions["B"].width = 40
        ws_ref.column_dimensions["C"].width = 60
        ws_ref.column_dimensions["D"].width = 80
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def generate_txt(markdown_text: str, title: str = "Relatório") -> io.BytesIO:
    """
    Gera versão plain text do relatório.
    """
    lines = [
        "=" * 70,
        title.upper().center(70),
        "=" * 70,
        f"Gerado por Joel — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "-" * 70,
        "",
    ]
    
    for line in markdown_text.split("\n"):
        clean = line.replace("**", "").replace("*", "")
        if clean.strip().startswith("# "):
            lines.append("")
            lines.append("=" * 70)
            lines.append(clean.strip()[2:].upper())
            lines.append("=" * 70)
        elif clean.strip().startswith("## "):
            lines.append("")
            lines.append("-" * 50)
            lines.append(clean.strip()[3:].upper())
            lines.append("-" * 50)
        elif clean.strip().startswith("### "):
            lines.append("")
            lines.append(clean.strip()[4:])
            lines.append("~" * len(clean.strip()[4:]))
        elif clean.strip() == "---":
            lines.append("-" * 70)
        else:
            lines.append(clean)
    
    content = "\n".join(lines)
    buffer = io.BytesIO()
    buffer.write(content.encode("utf-8"))
    buffer.seek(0)
    return buffer
