"""
Query Optimizer — Camada intermediária inteligente do Joel.

Fica ENTRE o que o usuário envia e o que de fato vai para as ferramentas.
Transforma a intenção bruta do usuário em:

1. Tópicos-foco extraídos do objetivo + documento
2. Queries otimizadas para cada ferramenta (formato diferente por tool)
3. Ativação inteligente de ferramentas (baseada em conteúdo, não só área)
4. Plano de ação estruturado injetado no prompt do agente

Princípios:
- Zero latência extra (processamento local, sem chamada LLM adicional)
- Determinístico e rastreável (log completo para DB)
- Compartimentalizado (cada tool tem estratégia independente)
- Queries em inglês para PubMed/ArXiv (melhor cobertura)
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Trigger keywords: detectam necessidade de tools pelo CONTEÚDO ────

FINANCE_TRIGGERS = frozenset({
    "custo", "investimento", "roi", "receita", "lucro", "ação", "ações",
    "bolsa", "faturamento", "preço", "cotação", "capital", "dividendo",
    "balanço", "dre", "valuation", "budget", "orçamento",
    "margem", "ebitda", "fluxo de caixa", "câmbio", "dólar", "selic",
    "inflação", "juros", "rendimento", "rentabilidade", "payback",
    "fundo imobiliário", "cdi", "ipca", "pib", "nasdaq", "ibovespa",
    "ticker", "ativo", "passivo", "patrimônio",
})

MEDICAL_TRIGGERS = frozenset({
    "estudo clínico", "protocolo clínico", "tratamento", "procedimento",
    "paciente", "eficácia", "efeito colateral", "terapia", "diagnóstico",
    "suplemento", "nutriente", "colágeno", "ácido hialurônico", "botox",
    "laser", "microagulhamento", "micropigmentação", "microblading",
    "sobrancelha", "dermato", "biomedicina", "fisiologia", "anatomia",
    "pele", "capilar", "tricologia", "peeling", "bioestimulador",
    "preenchimento", "lifting", "rejuvenescimento", "antienvelhecimento",
    "cicatrização", "regeneração", "stem cell", "vitamina", "hormônio",
    "metabolismo", "inflamação", "imunologia", "oncologia", "cardiologia",
})

ACADEMIC_TRIGGERS = frozenset({
    "artigo", "paper", "pesquisa", "estudo acadêmico", "tese",
    "metodologia", "algoritmo", "machine learning", "inteligência artificial",
    "framework", "benchmark", "revisão bibliográfica", "estado da arte",
    "inovação", "patent", "sistema", "arquitetura", "rede neural",
    "deep learning", "nlp", "computer vision", "iot", "blockchain",
    "robótica", "automação", "simulação", "modelagem", "otimização",
})


# ── Tradução de termos-chave para buscas em inglês ──────────────────

AREA_EN_TERMS = {
    "financeiro": "finance investment market analysis",
    "juridico": "legal law regulation compliance",
    "saude": "healthcare medicine clinical protocol",
    "estetica": "aesthetics beauty cosmetic dermatology",
    "educacao": "education learning pedagogy methodology",
    "tecnologia": "technology software engineering digital",
    "treinamento": "fitness training performance exercise",
    "protocolo": "clinical protocol procedure treatment",
    "marketing": "marketing strategy digital advertising",
    "engenharia": "engineering design construction systems",
    "outro": "professional analysis report",
}

AREA_PT_CONTEXT = {
    "financeiro": "mercado financeiro investimentos",
    "juridico": "legislação direito normas",
    "saude": "saúde medicina protocolos",
    "estetica": "estética beleza procedimentos",
    "educacao": "educação ensino aprendizagem",
    "tecnologia": "tecnologia software sistemas",
    "treinamento": "fitness treinamento performance",
    "protocolo": "protocolo clínico método",
    "marketing": "marketing digital vendas",
    "engenharia": "engenharia projetos construção",
    "outro": "",
}


# ── Dataclasses ─────────────────────────────────────────────────────

@dataclass
class ToolStrategy:
    """Estratégia de uso de uma ferramenta específica."""
    tool_key: str          # "web_search", "pubmed", "arxiv", "yfinance"
    priority: int          # 1 = mais importante
    queries: list = field(default_factory=list)
    rationale: str = ""


@dataclass
class QueryPlan:
    """Plano de ação completo do otimizador."""
    focus_topics: list = field(default_factory=list)
    strategies: list = field(default_factory=list)       # List[ToolStrategy]
    tool_overrides: dict = field(default_factory=dict)   # tool_key → bool
    action_plan_md: str = ""                              # Markdown para prompt
    optimization_log: str = ""                            # Para DB/processing_log


# ── Funções internas ────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return text.lower().strip()


def _detect_triggers(text: str, trigger_set: frozenset) -> list:
    """Detecta quais triggers estão presentes no texto (longest match first)."""
    text_lower = _normalize(text)
    return [t for t in sorted(trigger_set, key=len, reverse=True) if t in text_lower]


def _extract_key_phrases(text: str, max_phrases: int = 5) -> list:
    """Extrai frases-chave (proper nouns, termos técnicos) de um texto."""
    if not text:
        return []

    phrases = []
    seen = set()

    # Multi-word capitalized phrases (nomes próprios, técnicas, marcas)
    pattern = r'\b[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ][a-záàâãéèêíïóôõúüç]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ][a-záàâãéèêíïóôõúüç]+){1,4}\b'
    for match in re.finditer(pattern, text[:3000]):
        phrase = match.group()
        key = phrase.lower()
        if key not in seen and len(phrase) > 5:
            seen.add(key)
            phrases.append(phrase)
            if len(phrases) >= max_phrases:
                break

    return phrases


def _extract_focus_topics(
    user_objective: str,
    extracted_text: str = "",
    professional_area: str = "",
) -> list:
    """
    Extrai 3-5 tópicos-foco buscáveis.
    Combina: objetivo do usuário + frases-chave do documento + área.
    """
    topics = []

    # 1. Objetivo do usuário (sempre o tópico principal)
    obj_clean = user_objective.strip()
    if obj_clean:
        topics.append(obj_clean[:150])

    # 2. Frases-chave do documento
    if extracted_text:
        key_phrases = _extract_key_phrases(extracted_text)
        for kp in key_phrases:
            if kp.lower() not in obj_clean.lower():
                topics.append(kp)
            if len(topics) >= 4:
                break

    # 3. Contexto da área (se tópicos insuficientes)
    if len(topics) < 2 and professional_area:
        area_ctx = AREA_PT_CONTEXT.get(professional_area, "")
        if area_ctx:
            topics.append(f"{obj_clean[:60]} {area_ctx}")

    return topics[:5]


def _build_web_queries(
    topics: list,
    professional_area: str,
    geolocation: str,
    language: str,
) -> list:
    """Queries otimizadas para busca web (Tavily/DuckDuckGo)."""
    queries = []
    area_ctx = AREA_PT_CONTEXT.get(professional_area, "")
    geo = geolocation or "Brasil"
    year = "2026"

    for topic in topics[:3]:
        # Query contextualizada com área + ano
        q1 = f"{topic} {area_ctx} {year}".strip()
        queries.append(q1[:200])

        # Query com foco geográfico + tendências
        q2 = f"{topic} {geo} tendências dados atuais"
        queries.append(q2[:200])

    return queries[:6]


def _build_pubmed_queries(topics: list, professional_area: str) -> list:
    """Queries otimizadas para PubMed (preferencialmente em inglês)."""
    queries = []
    en_ctx = AREA_EN_TERMS.get(professional_area, "")

    for topic in topics[:2]:
        # Tentar manter termos técnicos + contexto em inglês
        q = f"{topic} {en_ctx} clinical study".strip()
        queries.append(q[:150])

    return queries


def _build_arxiv_queries(topics: list, professional_area: str) -> list:
    """Queries otimizadas para ArXiv papers."""
    queries = []
    en_ctx = AREA_EN_TERMS.get(professional_area, "")

    for topic in topics[:2]:
        q = f"{topic} {en_ctx} research".strip()
        queries.append(q[:150])

    return queries


def _build_finance_queries(topics: list, extracted_text: str) -> list:
    """Queries para YFinance — tickers, empresas, indicadores."""
    queries = []
    all_text = " ".join(topics) + " " + extracted_text[:2000]

    # Tickers americanos ($AAPL)
    us_tickers = re.findall(r'\$([A-Z]{2,5})\b', all_text)
    # Tickers brasileiros (PETR4, VALE3)
    br_tickers = re.findall(r'\b([A-Z]{4}[0-9]{1,2})\b', all_text)

    for t in us_tickers + br_tickers:
        queries.append(t)

    # Termos genéricos se nenhum ticker encontrado
    if not queries:
        for topic in topics[:2]:
            queries.append(f"{topic} stock market")

    return queries[:5]


# ── Função principal ────────────────────────────────────────────────

def optimize_query(
    user_objective: str,
    professional_area: str = "",
    analysis_mode: str = "document",
    extracted_text: str = "",
    geolocation: str = "",
    language: str = "pt-BR",
    source_count: int = 5,
    include_search: bool = True,
) -> QueryPlan:
    """
    Otimiza a query do usuário para máxima assertividade.

    Analisa objetivo + documento + área para:
    1. Extrair tópicos-foco (o que realmente importa)
    2. Detectar necessidade de tools pelo conteúdo (não só pela área)
    3. Gerar queries otimizadas por ferramenta (formato diferente por tool)
    4. Montar plano de ação estruturado para injeção no prompt

    Returns:
        QueryPlan com strategies, overrides e action_plan_md prontos.
    """
    plan = QueryPlan()
    log_lines = []

    # ── 1. Extrair tópicos-foco ──────────────────────────────────────
    plan.focus_topics = _extract_focus_topics(
        user_objective, extracted_text, professional_area
    )
    log_lines.append(f"[Optimizer] Tópicos: {[t[:60] for t in plan.focus_topics]}")

    # ── 2. Detecção inteligente de tools por conteúdo ────────────────
    combined_text = f"{user_objective} {extracted_text[:3000]}"

    finance_hits = _detect_triggers(combined_text, FINANCE_TRIGGERS)
    medical_hits = _detect_triggers(combined_text, MEDICAL_TRIGGERS)
    academic_hits = _detect_triggers(combined_text, ACADEMIC_TRIGGERS)

    # Ativar por conteúdo (mesmo que área não peça)
    if finance_hits:
        plan.tool_overrides["yfinance"] = True
        log_lines.append(f"[Optimizer] YFinance ativado: {finance_hits[:3]}")

    if medical_hits:
        plan.tool_overrides["pubmed"] = True
        log_lines.append(f"[Optimizer] PubMed ativado: {medical_hits[:3]}")

    if academic_hits:
        plan.tool_overrides["arxiv"] = True
        log_lines.append(f"[Optimizer] ArXiv ativado: {academic_hits[:3]}")

    # Desativar se irrelevante (economiza tempo e tokens)
    if not finance_hits and professional_area != "financeiro":
        plan.tool_overrides.setdefault("yfinance", False)
    if not medical_hits and professional_area not in (
        "saude", "estetica", "treinamento", "protocolo"
    ):
        plan.tool_overrides.setdefault("pubmed", False)
    if not academic_hits and professional_area not in (
        "tecnologia", "engenharia", "educacao"
    ):
        plan.tool_overrides.setdefault("arxiv", False)

    # ── 3. Gerar queries otimizadas por ferramenta ───────────────────
    priority = 1
    needs_search = include_search or analysis_mode == "free_form"

    # Web search
    if needs_search:
        web_q = _build_web_queries(
            plan.focus_topics, professional_area, geolocation, language
        )
        plan.strategies.append(ToolStrategy(
            tool_key="web_search",
            priority=priority,
            queries=web_q,
            rationale="Dados atuais, referências de mercado, tendências",
        ))
        priority += 1

    # PubMed
    if plan.tool_overrides.get("pubmed", False):
        pm_q = _build_pubmed_queries(plan.focus_topics, professional_area)
        plan.strategies.append(ToolStrategy(
            tool_key="pubmed",
            priority=priority,
            queries=pm_q,
            rationale="Artigos científicos médicos para embasamento clínico",
        ))
        priority += 1

    # ArXiv
    if plan.tool_overrides.get("arxiv", False):
        ax_q = _build_arxiv_queries(plan.focus_topics, professional_area)
        plan.strategies.append(ToolStrategy(
            tool_key="arxiv",
            priority=priority,
            queries=ax_q,
            rationale="Papers acadêmicos para fundamentação técnica",
        ))
        priority += 1

    # YFinance
    if plan.tool_overrides.get("yfinance", False):
        fin_q = _build_finance_queries(plan.focus_topics, extracted_text)
        plan.strategies.append(ToolStrategy(
            tool_key="yfinance",
            priority=priority,
            queries=fin_q,
            rationale="Dados financeiros em tempo real (cotações, balanços)",
        ))
        priority += 1

    # ── 4. Montar plano de ação markdown ─────────────────────────────
    plan.action_plan_md = _format_action_plan(plan, source_count)
    plan.optimization_log = "\n".join(log_lines)

    logger.info(
        f"QueryOptimizer: {len(plan.strategies)} estratégias, "
        f"{len(plan.focus_topics)} tópicos, "
        f"overrides={plan.tool_overrides}"
    )

    return plan


# ── Formatação do plano de ação ──────────────────────────────────────

TOOL_LABELS = {
    "web_search": "🔍 Busca Web (Tavily + DuckDuckGo)",
    "pubmed": "🏥 PubMed (artigos médicos/científicos)",
    "arxiv": "📚 ArXiv (papers acadêmicos)",
    "yfinance": "📊 YFinance (dados financeiros em tempo real)",
}


def _format_action_plan(plan: QueryPlan, source_count: int) -> str:
    """Formata plano de ação como markdown para injeção no prompt do agente."""
    if not plan.strategies:
        return ""

    lines = [
        "## PLANO DE AÇÃO (otimizado automaticamente)",
        "",
        f"**Meta:** {source_count} fontes/referências distintas",
        f"**Tópicos-foco:** {', '.join(t[:60] for t in plan.focus_topics[:3])}",
        "",
    ]

    for strat in sorted(plan.strategies, key=lambda s: s.priority):
        label = TOOL_LABELS.get(strat.tool_key, strat.tool_key)
        lines.append(f"### PRIORIDADE {strat.priority}: {label}")
        lines.append(f"*{strat.rationale}*")

        if strat.queries:
            lines.append("**Queries otimizadas:**")
            for i, q in enumerate(strat.queries, 1):
                lines.append(f'{i}. "{q[:120]}"')

        lines.append("")

    lines.append(
        "**INSTRUÇÕES DE EXECUÇÃO:**\n"
        "- Execute buscas na ORDEM DE PRIORIDADE acima\n"
        "- Use as queries otimizadas como ponto de partida\n"
        "- Refine conforme resultados — se uma query não trouxer bons resultados, reformule\n"
        "- Pare de buscar quando atingir a meta de fontes\n"
        "- Após cada busca relevante, use Newspaper4k/Website para ler artigos completos\n"
        "- Use Calculator para validar números e cálculos do relatório"
    )

    return "\n".join(lines)
