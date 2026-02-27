"""
Joel Image Service — Busca imagens profissionais para enriquecer relatórios.

Usa Pixabay API (gratuita, sem OAuth, royalty-free).
Fallback: gera imagens decorativas via matplotlib se API indisponível.

PIXABAY_API_KEY deve estar no .env
"""

import os
import io
import logging
import hashlib
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
PIXABAY_ENDPOINT = "https://pixabay.com/api/"

# Mapeamento de áreas profissionais para termos de busca
AREA_KEYWORDS = {
    "financeiro": "finance business chart investment",
    "juridico": "law justice legal court",
    "saude": "health medical healthcare",
    "estetica": "beauty spa aesthetics",
    "educacao": "education learning school",
    "tecnologia": "technology digital software",
    "treinamento": "training coaching professional",
    "protocolo": "protocol compliance standards",
    "marketing": "marketing strategy branding",
    "engenharia": "engineering architecture blueprint",
    "outro": "business professional report",
}

# Cache simples em memória (evita requests duplicados na mesma sessão)
_image_cache: dict[str, bytes] = {}


def search_images(
    query: str,
    professional_area: str = "outro",
    count: int = 3,
    image_type: str = "photo",
    orientation: str = "horizontal",
    min_width: int = 800,
) -> list[dict]:
    """
    Busca imagens no Pixabay API.
    
    Returns: Lista de dicts com {url, preview_url, width, height, tags, source}
    """
    if not PIXABAY_API_KEY:
        logger.warning("PIXABAY_API_KEY não configurada. Imagens indisponíveis.")
        return []
    
    # Enriquecer query com termos da área profissional
    area_terms = AREA_KEYWORDS.get(professional_area, "business professional")
    full_query = f"{query} {area_terms}"
    
    try:
        params = {
            "key": PIXABAY_API_KEY,
            "q": full_query[:100],  # Pixabay limita query a 100 chars
            "image_type": image_type,
            "orientation": orientation,
            "min_width": min_width,
            "per_page": min(count, 10),
            "safesearch": "true",
            "category": "business",
            "lang": "pt",
        }
        
        resp = requests.get(PIXABAY_ENDPOINT, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        images = []
        for hit in data.get("hits", [])[:count]:
            images.append({
                "url": hit.get("webformatURL", ""),
                "large_url": hit.get("largeImageURL", ""),
                "preview_url": hit.get("previewURL", ""),
                "width": hit.get("webformatWidth", 0),
                "height": hit.get("webformatHeight", 0),
                "tags": hit.get("tags", ""),
                "source": f"Pixabay (ID: {hit.get('id', '')})",
                "user": hit.get("user", ""),
            })
        
        return images
    
    except requests.RequestException as e:
        logger.warning(f"Erro ao buscar imagens no Pixabay: {e}")
        return []


def download_image(url: str, max_size_kb: int = 500) -> Optional[bytes]:
    """
    Download de uma imagem para bytes.
    Usa cache em memória para evitar downloads duplicados.
    """
    cache_key = hashlib.md5(url.encode()).hexdigest()
    
    if cache_key in _image_cache:
        return _image_cache[cache_key]
    
    try:
        resp = requests.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        
        content = resp.content
        
        # Verificar tamanho
        if len(content) > max_size_kb * 1024:
            logger.warning(f"Imagem muito grande ({len(content) / 1024:.0f}KB), ignorando.")
            return None
        
        _image_cache[cache_key] = content
        return content
    
    except requests.RequestException as e:
        logger.warning(f"Erro ao baixar imagem: {e}")
        return None


def get_header_image(professional_area: str = "outro") -> Optional[bytes]:
    """
    Busca uma imagem de cabeçalho adequada à área profissional.
    Retorna bytes da imagem ou None se indisponível.
    """
    images = search_images(
        query="corporate header banner",
        professional_area=professional_area,
        count=1,
        orientation="horizontal",
        min_width=1200,
    )
    
    if images:
        return download_image(images[0]["url"])
    return None


def generate_decorative_header(
    title: str = "",
    subtitle: str = "",
    width: int = 800,
    height: int = 200,
) -> bytes:
    """
    Fallback: gera header decorativo via matplotlib quando API não disponível.
    Returns: bytes PNG.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    
    # Gradient background
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "corp", ["#1e3a5f", "#2563eb", "#7c3aed"]
    )
    ax.imshow(gradient, aspect="auto", cmap=cmap, extent=[0, width, 0, height])
    
    # Add geometric decorative elements
    for i in range(5):
        circle = plt.Circle(
            (width * (0.1 + i * 0.2), height * 0.5),
            height * 0.15,
            fill=False,
            color="white",
            alpha=0.15,
            linewidth=2,
        )
        ax.add_patch(circle)
    
    # Title text
    if title:
        ax.text(
            width * 0.05, height * 0.6,
            title[:60],
            fontsize=18, fontweight="bold", color="white",
            va="center", ha="left",
        )
    if subtitle:
        ax.text(
            width * 0.05, height * 0.3,
            subtitle[:80],
            fontsize=11, color="rgba(255,255,255,0.8)",
            va="center", ha="left",
        )
    
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    fig.tight_layout(pad=0)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_section_divider(color: str = "#2563eb") -> bytes:
    """Generate a thin decorative divider bar. Returns bytes PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    
    fig, ax = plt.subplots(figsize=(6, 0.15), dpi=150)
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "div", [color, "#ffffff"]
    )
    ax.imshow(gradient, aspect="auto", cmap=cmap)
    ax.axis("off")
    fig.tight_layout(pad=0)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
