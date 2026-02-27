"""
Joel Agent — Agente de análise de documentos.

Simplificado seguindo boas práticas do Agno:
- TavilyTools nativo como tool do agente (o agente decide quando buscar)
- Prompt enxuto, sem busca manual pré-agente
- Modelo gpt-4.1-mini (rápido e barato)
"""

import logging
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.conf import settings

from .prompts import get_system_prompt

logger = logging.getLogger(__name__)


def _build_tools(include_market_references: bool) -> list:
    """Monta lista de tools. TavilyTools só se tiver API key e usuário pediu referências."""
    tools = []
    if include_market_references:
        tavily_key = settings.JOEL_CONFIG.get("TAVILY_API_KEY", "")
        if tavily_key and not tavily_key.startswith("tvly-COLE"):
            try:
                from agno.tools.tavily import TavilyTools
                tools.append(TavilyTools(api_key=tavily_key, max_results=3))
                logger.info("TavilyTools adicionado ao agente")
            except Exception as e:
                logger.warning(f"TavilyTools indisponível: {e}")
    return tools


def run_analysis(
    extracted_text: str,
    user_objective: str,
    professional_area: str = "",
    professional_area_detail: str = "",
    geolocation: str = "",
    language: str = "pt-BR",
    include_market_references: bool = True,
    search_scope: str = "",
    report_type: str = "analitico",
) -> dict:
    """
    Executa a análise completa de um documento.
    O agente recebe o texto + objetivo e gera o relatório direto.
    Se TavilyTools estiver disponível, o próprio agente busca referências quando precisar.
    """
    config = settings.JOEL_CONFIG
    area_desc = professional_area_detail or professional_area or "Geral"

    logger.info(f"Joel: area={area_desc}, tipo={report_type}, modelo={config['OPENAI_MODEL']}")

    # --- System prompt ---
    instructions = get_system_prompt(
        language=language,
        professional_area=professional_area,
        report_type=report_type,
        geolocation=geolocation,
        include_market_references=include_market_references,
    )

    # --- Tools ---
    tools = _build_tools(include_market_references)

    # --- Agente (padrão curso Agno: simples e direto) ---
    joel = Agent(
        name="Joel",
        model=OpenAIChat(
            id=config["OPENAI_MODEL"],
            api_key=config["OPENAI_API_KEY"],
        ),
        tools=tools if tools else None,
        instructions=instructions,
        markdown=True,
    )

    # --- Prompt do usuário (enxuto) ---
    text_preview = extracted_text[:8000]
    truncated_note = "\n[... documento truncado ...]" if len(extracted_text) > 8000 else ""

    user_prompt = (
        f"## DOCUMENTO\n\n{text_preview}{truncated_note}\n\n---\n\n"
        f"## SOLICITAÇÃO\n\n"
        f"**Objetivo:** {user_objective}\n\n"
        f"**Área:** {area_desc}\n\n"
        f"**Tipo de relatório:** {report_type}\n\n"
        f"**Região:** {geolocation or 'Global'}\n\n"
    )
    if search_scope:
        user_prompt += f"**Escopo de busca adicional:** {search_scope}\n\n"
    if include_market_references and tools:
        user_prompt += "Use suas ferramentas de busca para encontrar referências de mercado atuais.\n\n"

    user_prompt += "Gere o relatório profissional completo conforme as instruções."

    # --- Executar ---
    try:
        response = joel.run(user_prompt)
        content = response.content or ""

        return {
            "content_markdown": content,
            "references": [],
            "search_results_raw": [],
            "joel_reasoning": f"Tipo: {report_type}, Área: {area_desc}, Modelo: {config['OPENAI_MODEL']}",
        }
    except Exception as e:
        logger.error(f"Erro no Joel: {e}")
        raise
