"""
Joel Agent — Agente de análise de documentos.

Pipeline otimizado para velocidade (meta: <2min total):
1. QueryOptimizer analisa intenção → plano focado + tool overrides
2. _build_tools monta APENAS as ferramentas necessárias
3. Plano de ação injetado no prompt → Joel sabe O QUE buscar
4. Agente executa com timeout estrito de 90s

CLOCK BUDGET (total = 120s):
- Extração: ~3s (pypdf)
- Optimizer: ~0s (local, sem LLM)
- Agente Joel: máx 90s (timeout no Thread)
- Formatação: ~10s (gráficos + PDF)
- Margem: ~17s
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.conf import settings

from .prompts import get_system_prompt
from .query_optimizer import optimize_query

logger = logging.getLogger(__name__)

# Timeout estrito para joel.run() — em segundos
AGENT_TIMEOUT = 90

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
    tool_overrides: dict | None = None,
) -> list:
    """
    Monta arsenal MÍNIMO NECESSÁRIO de ferramentas.

    Prioridade: velocidade. Cada tool extra = mais latência.
    Só carrega o que o optimizer decidiu ser relevante.

    Removidos por lentidão:
    - Newspaper4kTools (lê artigos inteiros, 5-15s por URL)
    - WebsiteTools (scraping genérico, lento e instável)
    - DuckDuckGo (redundante com Tavily, só como fallback)
    """
    tools = []
    tool_names = []
    overrides = tool_overrides or {}

    # === SEMPRE ATIVA: Calculator (leve, sem rede) ===
    try:
        from agno.tools.calculator import CalculatorTools
        tools.append(CalculatorTools())
        tool_names.append("Calculator")
    except Exception as e:
        logger.warning(f"CalculatorTools: {e}")

    # === BUSCA WEB (se habilitada) ===
    needs_search = include_search or analysis_mode == "free_form"

    if needs_search:
        # Tavily — busca principal (rápida, ~1-2s por query)
        tavily_ok = False
        try:
            from agno.tools.tavily import TavilyTools
            tools.append(TavilyTools())
            tool_names.append("Tavily")
            tavily_ok = True
        except Exception as e:
            logger.warning(f"TavilyTools: {e}")

        # DuckDuckGo APENAS se Tavily falhou (evita duplicidade)
        if not tavily_ok:
            try:
                from agno.tools.duckduckgo import DuckDuckGoTools
                tools.append(DuckDuckGoTools(fixed_max_results=3))
                tool_names.append("DuckDuckGo")
            except Exception as e2:
                logger.warning(f"DuckDuckGoTools: {e2}")

    # === POR ÁREA + OVERRIDES DO OPTIMIZER ===
    area_extras = AREA_TOOLS_MAP.get(professional_area, [])

    if overrides.get("yfinance", "yfinance" in area_extras):
        try:
            from agno.tools.yfinance import YFinanceTools
            tools.append(YFinanceTools())
            tool_names.append("YFinance")
        except Exception as e:
            logger.warning(f"YFinanceTools: {e}")

    if overrides.get("pubmed", "pubmed" in area_extras):
        try:
            from agno.tools.pubmed import PubmedTools
            tools.append(PubmedTools())
            tool_names.append("Pubmed")
        except Exception as e:
            logger.warning(f"PubmedTools: {e}")

    if overrides.get("arxiv", "arxiv" in area_extras):
        try:
            from agno.tools.arxiv import ArxivTools
            tools.append(ArxivTools())
            tool_names.append("Arxiv")
        except Exception as e:
            logger.warning(f"ArxivTools: {e}")

    logger.info(f"Joel tools: [{', '.join(tool_names)}] ({len(tools)})")
    return tools


def _run_agent_with_timeout(joel: Agent, prompt: str, timeout: int) -> str:
    """
    Executa joel.run() com timeout estrito.
    Se exceder o tempo, retorna TimeoutError.
    """
    start = time.time()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(joel.run, prompt)
        try:
            response = future.result(timeout=timeout)
            elapsed = time.time() - start
            logger.info(f"Joel respondeu em {elapsed:.1f}s")
            return response.content or ""
        except FuturesTimeout:
            elapsed = time.time() - start
            logger.warning(f"Joel TIMEOUT após {elapsed:.1f}s (limite: {timeout}s)")
            future.cancel()
            raise TimeoutError(
                f"Joel excedeu o limite de {timeout}s. "
                f"Tente com um objetivo mais específico ou menos fontes."
            )


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
    Executa análise com pipeline otimizado para velocidade.

    Clock budget: máx 90s para o agente Joel.

    1. QueryOptimizer (local, 0s) → plano focado + tool overrides
    2. _build_tools → mínimo necessário
    3. Prompt com plano de ação injetado → Joel sabe o que buscar
    4. joel.run() com timeout estrito
    """
    config = settings.JOEL_CONFIG
    area_desc = professional_area_detail or professional_area or "Geral"

    logger.info(
        f"Joel: area={area_desc}, tipo={report_type}, "
        f"modo={analysis_mode}, modelo={config['OPENAI_MODEL']}"
    )

    # ── 1. QUERY OPTIMIZER (local, ~0ms) ─────────────────────────────
    query_plan = optimize_query(
        user_objective=user_objective,
        professional_area=professional_area,
        analysis_mode=analysis_mode,
        extracted_text=extracted_text[:3000],
        geolocation=geolocation,
        language=language,
        source_count=source_count,
        include_search=include_market_references,
    )

    if query_plan.optimization_log:
        logger.info(query_plan.optimization_log)

    # ── 2. SYSTEM PROMPT ─────────────────────────────────────────────
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

    # ── 3. TOOLS (mínimo necessário) ─────────────────────────────────
    tools = _build_tools(
        include_search=include_market_references,
        professional_area=professional_area,
        analysis_mode=analysis_mode,
        tool_overrides=query_plan.tool_overrides,
    )

    # ── 4. AGENTE ────────────────────────────────────────────────────
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

    # ── 5. USER PROMPT focado ────────────────────────────────────────
    action_plan = query_plan.action_plan_md
    effective_sources = min(source_count, 5)

    if analysis_mode == "free_form":
        user_prompt = (
            f"## ANÁLISE LIVRE\n\n"
            f"**Objetivo:** {user_objective}\n\n"
            f"**Área:** {area_desc}\n"
            f"**Relatório:** {report_type}\n"
            f"**Região:** {geolocation or 'Global'}\n"
            f"**Fontes:** {effective_sources}\n\n"
        )
        if search_scope:
            user_prompt += f"**Escopo:** {search_scope}\n\n"
        if action_plan:
            user_prompt += f"---\n\n{action_plan}\n\n---\n\n"
        user_prompt += (
            "Sem documento. Execute o plano acima de forma RÁPIDA e OBJETIVA. "
            "Faça no máximo 3-4 buscas focadas, leia apenas os resultados mais "
            "relevantes e produza o relatório completo."
        )

    elif analysis_mode == "enhancement":
        text_preview = extracted_text[:10000]
        truncated = "\n[... truncado ...]" if len(extracted_text) > 10000 else ""

        user_prompt = (
            f"## DOCUMENTO PARA APRIMORAMENTO\n\n"
            f"{text_preview}{truncated}\n\n---\n\n"
            f"**Instruções:** {user_objective}\n"
            f"**Área:** {area_desc}\n"
            f"**Fontes:** {effective_sources}\n\n"
        )
        if action_plan:
            user_prompt += f"---\n\n{action_plan}\n\n---\n\n"
        user_prompt += (
            "Aprimore o documento: faça 2-3 buscas focadas para enriquecer, "
            "melhore estrutura e produza versão premium. Seja RÁPIDO e OBJETIVO."
        )

    else:
        # document / multi_document
        text_preview = extracted_text[:8000]
        truncated = "\n[... truncado ...]" if len(extracted_text) > 8000 else ""
        is_multi = analysis_mode == "multi_document"
        header = "## DOCUMENTOS" if is_multi else "## DOCUMENTO"

        user_prompt = (
            f"{header}\n\n{text_preview}{truncated}\n\n---\n\n"
            f"**Objetivo:** {user_objective}\n"
            f"**Área:** {area_desc}\n"
            f"**Relatório:** {report_type}\n"
            f"**Região:** {geolocation or 'Global'}\n"
            f"**Fontes:** {effective_sources}\n\n"
        )
        if search_scope:
            user_prompt += f"**Escopo:** {search_scope}\n\n"
        if action_plan:
            user_prompt += f"---\n\n{action_plan}\n\n---\n\n"
        if is_multi:
            user_prompt += "Múltiplos docs — análise cruzada integrada.\n\n"
        user_prompt += (
            "Execute o plano de forma RÁPIDA: faça 2-4 buscas focadas "
            "(se busca habilitada), analise o documento e gere o relatório completo. "
            "Priorize QUALIDADE sobre QUANTIDADE de buscas."
        )

    # ── 6. EXECUTAR COM TIMEOUT ESTRITO ──────────────────────────────
    try:
        content = _run_agent_with_timeout(joel, user_prompt, AGENT_TIMEOUT)

        reasoning = (
            f"Tipo: {report_type}, Área: {area_desc}, "
            f"Modelo: {config['OPENAI_MODEL']}, "
            f"Estratégias: {len(query_plan.strategies)}, "
            f"Tópicos: {[t[:40] for t in query_plan.focus_topics[:3]]}"
        )

        return {
            "content_markdown": content,
            "references": [],
            "search_results_raw": [],
            "joel_reasoning": reasoning,
            "optimization_log": query_plan.optimization_log,
        }
    except Exception as e:
        logger.error(f"Erro no Joel: {e}")
        raise
