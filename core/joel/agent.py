"""
Joel Agent — Agente superinteligente de análise de documentos.

Equipado com arsenal completo de ferramentas Agno:
- Busca web: TavilyTools + DuckDuckGoTools (fallback gratuito)
- Dados financeiros: YFinanceTools (bolsa, ações, fundos)
- Papers científicos: ArxivTools (artigos acadêmicos)
- Artigos médicos: PubmedTools (saúde, medicina, estética)
- Leitura de sites: Newspaper4kTools (conteúdo de artigos)
- Scraping: WebsiteTools (leitura de URLs)
- Cálculos: CalculatorTools (matemática, financeiro)
- Modelo gpt-4.1-mini (rápido e barato)
"""

import logging
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.conf import settings

from .prompts import get_system_prompt

logger = logging.getLogger(__name__)

# Mapeamento: área profissional → tools extras relevantes
AREA_TOOLS_MAP = {
    "financeiro": ["yfinance"],
    "juridico": [],
    "saude": ["pubmed"],
    "estetica": ["pubmed"],
    "educacao": ["arxiv"],
    "tecnologia": ["arxiv"],
    "treinamento": ["pubmed"],
    "protocolo": ["pubmed"],
    "marketing": [],
    "engenharia": ["arxiv"],
    "outro": [],
}


def _build_tools(
    include_search: bool,
    professional_area: str = "",
    analysis_mode: str = "document",
) -> list:
    """
    Monta arsenal de ferramentas do Joel.
    
    Sempre ativas:
    - CalculatorTools (cálculos)
    - WebsiteTools (leitura de URLs)
    
    Condicionais (se busca habilitada ou free_form):
    - TavilyTools (busca principal — lê TAVILY_API_KEY do env)
    - DuckDuckGoTools (busca fallback — gratuito, sem API key)
    - Newspaper4kTools (leitura de artigos completos)
    
    Por área:
    - YFinanceTools → financeiro
    - PubmedTools → saúde, estética, treinamento, protocolo
    - ArxivTools → tecnologia, engenharia, educação
    """
    tools = []
    tool_names = []
    
    # === SEMPRE ATIVAS ===
    try:
        from agno.tools.calculator import CalculatorTools
        tools.append(CalculatorTools())
        tool_names.append("Calculator")
    except Exception as e:
        logger.warning(f"CalculatorTools indisponível: {e}")
    
    try:
        from agno.tools.website import WebsiteTools
        tools.append(WebsiteTools())
        tool_names.append("Website")
    except Exception as e:
        logger.warning(f"WebsiteTools indisponível: {e}")
    
    # === BUSCA (se habilitada ou free_form) ===
    needs_search = include_search or analysis_mode == "free_form"
    
    if needs_search:
        # Tavily — busca principal
        try:
            from agno.tools.tavily import TavilyTools
            tools.append(TavilyTools())
            tool_names.append("Tavily")
        except Exception as e:
            logger.warning(f"TavilyTools indisponível: {e}")
        
        # DuckDuckGo — busca fallback gratuita
        try:
            from agno.tools.duckduckgo import DuckDuckGoTools
            tools.append(DuckDuckGoTools(fixed_max_results=5))
            tool_names.append("DuckDuckGo")
        except Exception as e:
            logger.warning(f"DuckDuckGoTools indisponível: {e}")
        
        # Newspaper4k — leitura de artigos
        try:
            from agno.tools.newspaper4k import Newspaper4kTools
            tools.append(Newspaper4kTools())
            tool_names.append("Newspaper4k")
        except Exception as e:
            logger.warning(f"Newspaper4kTools indisponível: {e}")
    
    # === POR ÁREA PROFISSIONAL ===
    area_extras = AREA_TOOLS_MAP.get(professional_area, [])
    
    if "yfinance" in area_extras:
        try:
            from agno.tools.yfinance import YFinanceTools
            tools.append(YFinanceTools())
            tool_names.append("YFinance")
        except Exception as e:
            logger.warning(f"YFinanceTools indisponível: {e}")
    
    if "pubmed" in area_extras:
        try:
            from agno.tools.pubmed import PubmedTools
            tools.append(PubmedTools())
            tool_names.append("Pubmed")
        except Exception as e:
            logger.warning(f"PubmedTools indisponível: {e}")
    
    if "arxiv" in area_extras:
        try:
            from agno.tools.arxiv import ArxivTools
            tools.append(ArxivTools())
            tool_names.append("Arxiv")
        except Exception as e:
            logger.warning(f"ArxivTools indisponível: {e}")
    
    logger.info(f"Joel tools: [{', '.join(tool_names)}] ({len(tools)} ferramentas)")
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
    analysis_mode: str = "document",
    source_count: int = 5,
    include_images: bool = False,
) -> dict:
    """
    Executa a análise completa de um documento (ou análise livre).
    O agente recebe o texto + objetivo e gera o relatório direto.
    Se TavilyTools estiver disponível, o próprio agente busca referências quando precisar.
    
    Modos:
    - document / multi_document: análise de conteúdo
    - enhancement: aprimorar o documento
    - free_form: pesquisa e relatório do zero
    """
    config = settings.JOEL_CONFIG
    area_desc = professional_area_detail or professional_area or "Geral"

    logger.info(f"Joel: area={area_desc}, tipo={report_type}, modo={analysis_mode}, modelo={config['OPENAI_MODEL']}")

    # --- System prompt ---
    instructions = get_system_prompt(
        language=language,
        professional_area=professional_area,
        report_type=report_type,
        geolocation=geolocation,
        include_market_references=include_market_references,
        analysis_mode=analysis_mode,
        source_count=source_count,
        include_images=include_images,
    )

    # --- Tools ---
    tools = _build_tools(
        include_search=include_market_references,
        professional_area=professional_area,
        analysis_mode=analysis_mode,
    )

    # Build tool awareness string for user prompt
    tool_hints = []
    for t in tools:
        cls_name = type(t).__name__
        if "Tavily" in cls_name or "DuckDuckGo" in cls_name:
            tool_hints.append("busca web")
        elif "YFinance" in cls_name:
            tool_hints.append("dados financeiros (ações, indicadores, balanços)")
        elif "Pubmed" in cls_name:
            tool_hints.append("artigos científicos médicos (PubMed)")
        elif "Arxiv" in cls_name:
            tool_hints.append("papers acadêmicos (arXiv)")
        elif "Newspaper" in cls_name:
            tool_hints.append("leitura de artigos completos")
        elif "Website" in cls_name:
            tool_hints.append("leitura de websites")
        elif "Calculator" in cls_name:
            tool_hints.append("cálculos matemáticos")
    tool_hints_str = ", ".join(dict.fromkeys(tool_hints))  # unique, preserving order

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

    # --- Build user prompt based on mode ---
    tools_note = f"\n**Ferramentas disponíveis:** {tool_hints_str}\nUse TODAS as ferramentas relevantes para enriquecer sua análise.\n\n" if tool_hints_str else ""
    
    if analysis_mode == "free_form":
        user_prompt = (
            f"## SOLICITAÇÃO DE ANÁLISE LIVRE\n\n"
            f"**Objetivo:** {user_objective}\n\n"
            f"**Área:** {area_desc}\n\n"
            f"**Tipo de relatório:** {report_type}\n\n"
            f"**Região:** {geolocation or 'Global'}\n\n"
            f"**Fontes desejadas:** {source_count}\n\n"
            f"{tools_note}"
        )
        if search_scope:
            user_prompt += f"**Escopo de busca:** {search_scope}\n\n"
        user_prompt += (
            "NÃO há documento. Pesquise extensivamente na internet usando TODAS as suas "
            "ferramentas de busca disponíveis e produza um relatório profissional completo "
            "baseado em dados públicos e referências confiáveis."
        )
    elif analysis_mode == "enhancement":
        text_preview = extracted_text[:12000]
        truncated_note = "\n[... documento truncado ...]" if len(extracted_text) > 12000 else ""
        
        user_prompt = (
            f"## DOCUMENTO PARA APRIMORAMENTO\n\n{text_preview}{truncated_note}\n\n---\n\n"
            f"## SOLICITAÇÃO DE APRIMORAMENTO\n\n"
            f"**Instruções:** {user_objective}\n\n"
            f"**Área:** {area_desc}\n\n"
            f"**Região:** {geolocation or 'Global'}\n\n"
            f"**Fontes desejadas:** {source_count}\n\n"
            f"{tools_note}"
        )
        if search_scope:
            user_prompt += f"**Escopo de busca:** {search_scope}\n\n"
        user_prompt += (
            "Aprimore este documento: melhore a estrutura, enriqueça com dados de mercado "
            "usando TODAS as suas ferramentas, adicione análises complementares e produza "
            "uma versão premium do material."
        )
    else:
        # document / multi_document
        text_preview = extracted_text[:8000]
        truncated_note = "\n[... documento truncado ...]" if len(extracted_text) > 8000 else ""
        
        is_multi = analysis_mode == "multi_document"
        header = "## DOCUMENTOS" if is_multi else "## DOCUMENTO"
        
        user_prompt = (
            f"{header}\n\n{text_preview}{truncated_note}\n\n---\n\n"
            f"## SOLICITAÇÃO\n\n"
            f"**Objetivo:** {user_objective}\n\n"
            f"**Área:** {area_desc}\n\n"
            f"**Tipo de relatório:** {report_type}\n\n"
            f"**Região:** {geolocation or 'Global'}\n\n"
            f"**Fontes desejadas:** {source_count}\n\n"
            f"{tools_note}"
        )
        if search_scope:
            user_prompt += f"**Escopo de busca adicional:** {search_scope}\n\n"
        if include_market_references and tools:
            user_prompt += "Use suas ferramentas de busca para encontrar referências de mercado atuais.\n\n"
        if is_multi:
            user_prompt += (
                "NOTA: Múltiplos documentos foram enviados. Analise TODOS em conjunto, "
                "identifique conexões, divergências e produza uma análise cruzada integrada.\n\n"
            )

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
