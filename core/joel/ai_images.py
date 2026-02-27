"""
Joel AI Image Generation — Cria imagens profissionais para relatórios.

Estratégia em camadas:
1. DALL-E 3 (OpenAI) — geração de imagens profissionais a partir de prompts
2. Pixabay API — busca de fotos de stock como fallback
3. Matplotlib — gráficos/imagens decorativas como último recurso

Custo DALL-E 3: ~$0.04/imagem (1024x1024, standard quality)
"""

import io
import re
import base64
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Mapeamento de áreas para estilos visuais
AREA_VISUAL_STYLES = {
    "financeiro": "corporate finance, charts, business graphs, blue and navy theme",
    "juridico": "legal, scales of justice, formal documents, dark wood tones",
    "saude": "medical, healthcare, clean white and blue, clinical",
    "estetica": "beauty, spa, soft pastels, elegant and luxurious",
    "educacao": "education, books, learning, warm and inviting",
    "tecnologia": "technology, digital, futuristic, blue neon accents",
    "treinamento": "fitness, training, dynamic, energetic colors",
    "protocolo": "protocol, clinical procedures, organized, clean",
    "marketing": "marketing, creative, colorful, modern advertising",
    "engenharia": "engineering, blueprints, technical, precise",
    "outro": "professional, corporate, clean modern design",
}


def _generate_image_prompt(
    topic: str,
    professional_area: str = "",
    style: str = "professional illustration",
) -> str:
    """Gera prompt otimizado para DALL-E 3 baseado no conteúdo."""
    area_style = AREA_VISUAL_STYLES.get(professional_area, AREA_VISUAL_STYLES["outro"])
    
    prompt = (
        f"Professional {style} for a business report about: {topic}. "
        f"Style: {area_style}. "
        f"Clean, modern design suitable for executive presentations. "
        f"High quality, photorealistic or high-end illustration. "
        f"No text, no watermarks, no logos. "
        f"16:9 aspect ratio composition."
    )
    return prompt


def _extract_topics_from_markdown(content_markdown: str, max_topics: int = 3) -> list[str]:
    """Extrai tópicos principais do markdown para gerar imagens relevantes."""
    topics = []
    
    # Extract from H2 headers
    headers = re.findall(r'^##\s+(.+)$', content_markdown, re.MULTILINE)
    for h in headers:
        clean = re.sub(r'[*_#\d.]+', '', h).strip()
        if clean and len(clean) > 5 and 'referência' not in clean.lower() and 'conclus' not in clean.lower():
            topics.append(clean)
    
    # If not enough, try first paragraph after each header
    if len(topics) < max_topics:
        sections = re.split(r'^##\s+', content_markdown, flags=re.MULTILINE)
        for section in sections[1:]:  # Skip content before first header
            lines = section.strip().split('\n')
            for line in lines[1:]:  # Skip header itself
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('|') and not line.startswith('-'):
                    topics.append(line[:100])
                    break
    
    # Deduplicate and limit
    seen = set()
    unique = []
    for t in topics:
        key = t.lower()[:30]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    
    return unique[:max_topics]


def generate_dalle_image(
    prompt: str,
    size: str = "1792x1024",
    quality: str = "standard",
) -> Optional[str]:
    """
    Gera uma imagem com DALL-E 3 e retorna como base64.
    
    Retorna None se não houver API key ou ocorrer erro.
    Custo: ~$0.04 (standard), ~$0.08 (hd)
    """
    config = getattr(settings, 'JOEL_CONFIG', {})
    api_key = config.get("OPENAI_API_KEY", "")
    
    if not api_key or api_key.startswith("sk-COLE"):
        logger.info("DALL-E: API key não configurada, pulando geração.")
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            response_format="b64_json",
            n=1,
        )
        
        image_b64 = response.data[0].b64_json
        logger.info(f"DALL-E: Imagem gerada com sucesso ({len(image_b64)} bytes b64)")
        return image_b64
        
    except Exception as e:
        logger.warning(f"DALL-E: Erro ao gerar imagem: {e}")
        return None


def generate_report_images(
    content_markdown: str,
    professional_area: str = "",
    analysis_mode: str = "document",
    max_images: int = 3,
) -> list[str]:
    """
    Gera imagens profissionais para o relatório.
    
    Estratégia:
    1. Tenta DALL-E 3 para até max_images
    2. Se DALL-E indisponível, busca no Pixabay
    3. Se nenhum disponível, retorna lista vazia (charts.py já gera gráficos)
    
    Returns:
        Lista de strings base64 PNG/JPEG
    """
    images = []
    
    # Extract key topics from the report content
    topics = _extract_topics_from_markdown(content_markdown, max_topics=max_images)
    
    if not topics:
        logger.info("AI Images: Nenhum tópico relevante encontrado para gerar imagens.")
        return images
    
    # --- Try DALL-E 3 first ---
    for i, topic in enumerate(topics[:max_images]):
        if len(images) >= max_images:
            break
        
        style = "professional infographic" if i == 0 else "professional illustration"
        prompt = _generate_image_prompt(topic, professional_area, style)
        
        image_b64 = generate_dalle_image(prompt, quality="standard")
        if image_b64:
            images.append(image_b64)
            logger.info(f"AI Images: DALL-E imagem {i+1}/{max_images} gerada para: {topic[:50]}")
    
    # --- Fallback to Pixabay if DALL-E didn't work ---
    if not images:
        try:
            from .images import search_images, download_image
            
            for topic in topics[:max_images]:
                results = search_images(topic, professional_area, per_page=1)
                if results:
                    img_data = download_image(results[0]["webformatURL"])
                    if img_data:
                        images.append(base64.b64encode(img_data).decode())
                        logger.info(f"AI Images: Pixabay imagem obtida para: {topic[:50]}")
        except Exception as e:
            logger.warning(f"AI Images: Pixabay fallback falhou: {e}")
    
    logger.info(f"AI Images: Total de {len(images)} imagens geradas para o relatório.")
    return images


def enhance_document_images(
    extracted_text: str,
    professional_area: str = "",
    max_images: int = 3,
) -> list[dict]:
    """
    Para o modo 'enhancement': gera imagens que complementam o conteúdo
    do documento original, criando uma versão visualmente enriquecida.
    
    Returns:
        Lista de dicts: [{"image_b64": str, "caption": str, "placement": str}]
    """
    enhanced_images = []
    
    topics = _extract_topics_from_markdown(extracted_text, max_topics=max_images)
    
    for topic in topics:
        prompt = _generate_image_prompt(
            topic, professional_area,
            style="high-end professional photograph or detailed illustration"
        )
        
        image_b64 = generate_dalle_image(prompt, quality="standard")
        if image_b64:
            enhanced_images.append({
                "image_b64": image_b64,
                "caption": f"Ilustração: {topic[:80]}",
                "placement": "after_section",
            })
    
    return enhanced_images
