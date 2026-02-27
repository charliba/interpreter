"""
Joel Chart Generator — Gera gráficos profissionais para enriquecer relatórios.

Capacidades:
- Gráficos de barras, linhas, pizza, gauge (indicadores)
- Paleta de cores corporativa consistente
- Export como PNG base64 (para embed em HTML/PDF) ou SVG
- Detecção automática de dados numéricos no texto do relatório
- Geração de gráficos de resumo (waterfall, treemap, etc.)

Inspirado em relatórios de RI (Relação com Investidores) de empresas listadas em bolsa.
"""

import io
import base64
import logging
import re
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (server-safe)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np

logger = logging.getLogger(__name__)

# === PALETA CORPORATIVA (Inspirada em relatórios de RI) ===
CORPORATE_COLORS = {
    "primary": "#1e3a5f",      # Navy blue
    "secondary": "#2563eb",    # Bright blue
    "accent": "#7c3aed",       # Purple
    "success": "#059669",      # Green
    "warning": "#d97706",      # Amber
    "danger": "#dc2626",       # Red
    "neutral": "#6b7280",      # Gray
    "light": "#f3f4f6",        # Light gray
    "bg": "#ffffff",           # White
}

PALETTE = [
    "#1e3a5f", "#2563eb", "#7c3aed", "#059669", "#d97706",
    "#dc2626", "#0891b2", "#4f46e5", "#ea580c", "#16a34a",
]

# Seaborn/Matplotlib global config
sns.set_theme(style="whitegrid", palette=PALETTE, font="sans-serif")
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.3,
})


def _fig_to_base64(fig: plt.Figure, fmt: str = "png") -> str:
    """Convert matplotlib figure to base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _fig_to_bytes(fig: plt.Figure, fmt: str = "png") -> bytes:
    """Convert matplotlib figure to bytes (for embedding in PDF/DOCX)."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ============================================================
# CHART TYPES
# ============================================================

def bar_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    horizontal: bool = False,
    color: str | None = None,
    highlight_max: bool = True,
    figsize: tuple = (8, 4.5),
) -> str:
    """Generate a corporate bar chart. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize)
    
    colors = [CORPORATE_COLORS["secondary"]] * len(values)
    if highlight_max and values:
        max_idx = values.index(max(values))
        colors[max_idx] = CORPORATE_COLORS["primary"]
    
    if color:
        colors = [color] * len(values)
    
    if horizontal:
        bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    f"{val:,.1f}", va="center", fontsize=9, color=CORPORATE_COLORS["primary"])
    else:
        bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5, width=0.6)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        # Add value labels on top
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    f"{val:,.1f}", ha="center", fontsize=9, color=CORPORATE_COLORS["primary"])
    
    if title:
        ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"], pad=15)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", which="major", labelsize=9)
    
    fig.tight_layout()
    return _fig_to_base64(fig)


def line_chart(
    x_labels: list[str],
    series: dict[str, list[float]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    figsize: tuple = (9, 4.5),
    show_markers: bool = True,
    fill: bool = False,
) -> str:
    """Generate a multi-series line chart. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize)
    
    for idx, (name, values) in enumerate(series.items()):
        color = PALETTE[idx % len(PALETTE)]
        ax.plot(x_labels, values, label=name, color=color, linewidth=2,
                marker="o" if show_markers else None, markersize=5)
        if fill:
            ax.fill_between(x_labels, values, alpha=0.1, color=color)
    
    if title:
        ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"], pad=15)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=True, fancybox=True, shadow=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", which="major", labelsize=9)
    
    fig.tight_layout()
    return _fig_to_base64(fig)


def pie_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    figsize: tuple = (6, 6),
    donut: bool = True,
) -> str:
    """Generate a professional donut/pie chart. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize)
    
    colors = PALETTE[:len(values)]
    wedgeprops = {"linewidth": 2, "edgecolor": "white"}
    
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct="%1.1f%%", pctdistance=0.75 if donut else 0.6,
        wedgeprops=wedgeprops, startangle=90,
    )
    
    for t in autotexts:
        t.set_fontsize(9)
        t.set_color("white")
        t.set_fontweight("bold")
    for t in texts:
        t.set_fontsize(9)
    
    if donut:
        centre_circle = plt.Circle((0, 0), 0.55, fc="white")
        ax.add_patch(centre_circle)
    
    if title:
        ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"], pad=20)
    
    fig.tight_layout()
    return _fig_to_base64(fig)


def gauge_chart(
    value: float,
    max_value: float = 100,
    title: str = "",
    label: str = "",
    figsize: tuple = (4, 2.5),
) -> str:
    """Generate a semi-circular gauge/meter chart. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"projection": "polar"})
    
    # Configure as semi-circle
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    
    pct = min(value / max_value, 1.0)
    angle = np.pi * pct
    
    # Background arc
    theta_bg = np.linspace(0, np.pi, 100)
    ax.fill_between(theta_bg, 0.7, 1.0, color=CORPORATE_COLORS["light"], alpha=0.5)
    
    # Value arc
    if pct <= 0.33:
        color = CORPORATE_COLORS["danger"]
    elif pct <= 0.66:
        color = CORPORATE_COLORS["warning"]
    else:
        color = CORPORATE_COLORS["success"]
    
    theta_val = np.linspace(0, angle, 100)
    ax.fill_between(theta_val, 0.7, 1.0, color=color)
    
    # Center text
    ax.annotate(f"{value:,.1f}", xy=(np.pi / 2, 0), fontsize=20, fontweight="bold",
                ha="center", va="center", color=CORPORATE_COLORS["primary"])
    if label:
        ax.annotate(label, xy=(np.pi / 2, -0.3), fontsize=9,
                    ha="center", va="center", color=CORPORATE_COLORS["neutral"])
    
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines["polar"].set_visible(False)
    ax.grid(False)
    
    if title:
        ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"],
                     pad=15, fontsize=11, y=1.1)
    
    fig.tight_layout()
    return _fig_to_base64(fig)


def comparison_table_chart(
    categories: list[str],
    group_a_values: list[float],
    group_b_values: list[float],
    group_a_label: str = "Documento",
    group_b_label: str = "Mercado",
    title: str = "",
    figsize: tuple = (9, 5),
) -> str:
    """Generate grouped bar chart for comparisons (doc vs market). Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax.bar(x - width / 2, group_a_values, width, label=group_a_label,
                   color=CORPORATE_COLORS["primary"], edgecolor="white")
    bars2 = ax.bar(x + width / 2, group_b_values, width, label=group_b_label,
                   color=CORPORATE_COLORS["secondary"], edgecolor="white")
    
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.legend(frameon=True, fontsize=9)
    
    if title:
        ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"], pad=15)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    # Value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{bar.get_height():,.1f}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{bar.get_height():,.1f}", ha="center", va="bottom", fontsize=8)
    
    fig.tight_layout()
    return _fig_to_base64(fig)


def heatmap_chart(
    data: list[list[float]],
    row_labels: list[str],
    col_labels: list[str],
    title: str = "",
    figsize: tuple = (8, 5),
    annot: bool = True,
) -> str:
    """Generate a professional heatmap. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize)
    
    arr = np.array(data)
    sns.heatmap(
        arr, annot=annot, fmt=".1f", cmap="Blues",
        xticklabels=col_labels, yticklabels=row_labels,
        linewidths=0.5, linecolor="white",
        cbar_kws={"shrink": 0.8},
        ax=ax,
    )
    
    if title:
        ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"], pad=15)
    
    ax.tick_params(axis="both", which="major", labelsize=9)
    fig.tight_layout()
    return _fig_to_base64(fig)


# ============================================================
# SMART CHART EXTRACTOR — Analisa markdown e gera gráficos
# ============================================================

def extract_numeric_data_from_markdown(markdown_text: str) -> list[dict]:
    """
    Scaneia o markdown do relatório procurando dados numéricos que podem
    ser visualizados em gráficos. Retorna lista de datasets detectados.
    """
    datasets = []
    
    # Pattern 1: Markdown tables with numbers
    # | Header1 | Header2 | Header3 |
    # |---------|---------|---------|
    # | Label   | 100     | 200     |
    table_pattern = r'\|(.+)\|'
    lines = markdown_text.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect table start
        if line.startswith("|") and "|" in line[1:]:
            headers = [h.strip() for h in line.split("|") if h.strip()]
            
            # Skip separator line
            if i + 1 < len(lines) and re.match(r'\|[\s\-:|]+\|', lines[i + 1].strip()):
                i += 2
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [c.strip() for c in lines[i].strip().split("|") if c.strip()]
                    rows.append(cells)
                    i += 1
                
                if rows and len(headers) >= 2:
                    # Check if any column has numbers
                    has_numbers = False
                    for row in rows:
                        for cell in row[1:]:
                            cleaned = re.sub(r'[R$%,.\s]', '', cell).replace(',', '')
                            if re.match(r'^-?\d+\.?\d*$', cleaned):
                                has_numbers = True
                                break
                    
                    if has_numbers:
                        datasets.append({
                            "type": "table",
                            "headers": headers,
                            "rows": rows,
                        })
                continue
        
        # Pattern 2: Lists with numbers (- Item: 45%, - Item: R$ 100)
        if re.match(r'^[-*]\s+.+:\s*[R$%]?\s*[\d.,]+', line):
            list_data = []
            while i < len(lines):
                m = re.match(r'^[-*]\s+(.+?):\s*[R$]*\s*([\d.,]+)\s*(%)?', lines[i].strip())
                if m:
                    label = m.group(1).strip()
                    val_str = m.group(2).replace(",", ".")
                    try:
                        val = float(val_str)
                        list_data.append({"label": label, "value": val, "pct": bool(m.group(3))})
                    except ValueError:
                        pass
                    i += 1
                else:
                    break
            
            if len(list_data) >= 2:
                datasets.append({
                    "type": "list",
                    "items": list_data,
                })
            continue
        
        i += 1
    
    return datasets


def generate_charts_from_markdown(markdown_text: str, max_charts: int = 4) -> list[dict]:
    """
    Analisa o markdown e gera gráficos automaticamente para dados detectados.
    
    Returns: List of {"title": str, "base64": str, "chart_type": str}
    """
    charts = []
    datasets = extract_numeric_data_from_markdown(markdown_text)
    
    for ds in datasets[:max_charts]:
        try:
            if ds["type"] == "table":
                chart = _chart_from_table(ds)
                if chart:
                    charts.append(chart)
            elif ds["type"] == "list":
                chart = _chart_from_list(ds)
                if chart:
                    charts.append(chart)
        except Exception as e:
            logger.warning(f"Erro ao gerar gráfico: {e}")
    
    return charts


def _chart_from_table(ds: dict) -> Optional[dict]:
    """Generate chart from a detected table dataset."""
    headers = ds["headers"]
    rows = ds["rows"]
    
    if len(rows) < 2 or len(headers) < 2:
        return None
    
    labels = [row[0] for row in rows if row]
    
    # Try to extract numeric values from second column
    values = []
    for row in rows:
        if len(row) >= 2:
            cleaned = re.sub(r'[R$%,\s]', '', row[1]).replace(',', '.')
            try:
                values.append(float(cleaned))
            except ValueError:
                values.append(0)
    
    if not values or all(v == 0 for v in values):
        return None
    
    title = headers[1] if len(headers) >= 2 else "Dados"
    
    # Choose chart type based on data
    if len(labels) <= 6 and all(v >= 0 for v in values):
        # Donut chart for small datasets with positive values
        b64 = pie_chart(labels[:6], values[:6], title=title)
        return {"title": title, "base64": b64, "chart_type": "donut"}
    else:
        # Bar chart
        b64 = bar_chart(labels[:12], values[:12], title=title, horizontal=len(labels) > 6)
        return {"title": title, "base64": b64, "chart_type": "bar"}


def _chart_from_list(ds: dict) -> Optional[dict]:
    """Generate chart from a detected list dataset."""
    items = ds["items"]
    
    if len(items) < 2:
        return None
    
    labels = [item["label"] for item in items]
    values = [item["value"] for item in items]
    is_pct = any(item.get("pct") for item in items)
    
    if is_pct and len(items) <= 8:
        b64 = pie_chart(labels, values, title="Distribuição")
        return {"title": "Distribuição", "base64": b64, "chart_type": "donut"}
    else:
        b64 = bar_chart(labels, values, title="Comparativo", horizontal=len(items) > 5)
        return {"title": "Comparativo", "base64": b64, "chart_type": "bar"}


# ============================================================
# SUMMARY CHARTS — Gráficos padrão para todos os relatórios
# ============================================================

def generate_cover_chart(
    professional_area: str,
    report_type: str,
    document_name: str,
) -> str:
    """
    Generate a professional cover/header graphic for the report.
    Returns base64 PNG.
    """
    fig, ax = plt.subplots(figsize=(10, 2))
    
    # Gradient bar
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "corp", [CORPORATE_COLORS["primary"], CORPORATE_COLORS["secondary"], CORPORATE_COLORS["accent"]]
    )
    ax.imshow(gradient, aspect="auto", cmap=cmap, extent=[0, 10, 0, 2])
    
    # Overlay text
    ax.text(0.3, 1.1, document_name[:50], fontsize=14, fontweight="bold",
            color="white", va="center", ha="left")
    ax.text(0.3, 0.6, f"{professional_area} | {report_type}",
            fontsize=10, color="rgba(255,255,255,0.8)", va="center", ha="left")
    
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2)
    ax.axis("off")
    
    fig.tight_layout(pad=0)
    return _fig_to_base64(fig)


def generate_analysis_summary_chart(
    metrics: dict[str, float],
    title: str = "Resumo da Análise",
) -> str:
    """
    Generate horizontal bar chart showing analysis metrics/scores.
    metrics: {"Qualidade": 8.5, "Completude": 7.0, ...}
    """
    if not metrics:
        return ""
    
    labels = list(metrics.keys())
    values = list(metrics.values())
    
    fig, ax = plt.subplots(figsize=(8, max(2.5, len(labels) * 0.6)))
    
    # Color gradient based on value
    max_val = max(values) if values else 10
    colors = []
    for v in values:
        ratio = v / max_val if max_val > 0 else 0
        if ratio >= 0.75:
            colors.append(CORPORATE_COLORS["success"])
        elif ratio >= 0.50:
            colors.append(CORPORATE_COLORS["secondary"])
        elif ratio >= 0.25:
            colors.append(CORPORATE_COLORS["warning"])
        else:
            colors.append(CORPORATE_COLORS["danger"])
    
    bars = ax.barh(labels, values, color=colors, height=0.5, edgecolor="white")
    
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", fontsize=10, fontweight="bold",
                color=CORPORATE_COLORS["primary"])
    
    ax.set_xlim(0, max_val * 1.15)
    ax.set_title(title, fontweight="bold", color=CORPORATE_COLORS["primary"],
                 pad=15, loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
    ax.tick_params(axis="y", which="both", labelsize=10)
    ax.invert_yaxis()
    
    fig.tight_layout()
    return _fig_to_base64(fig)
