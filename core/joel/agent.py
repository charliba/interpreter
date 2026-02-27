"""
Joel Agent — Intermediário inteligente entre o usuário e a análise de documentos.

Joel utiliza:
- Docling para parsear qualquer tipo de documento
- Tavily para busca profunda na internet
- OpenAI GPT-4o (via Agno) para gerar relatórios profissionais

Joel age como intermediário: traduz o que o usuário quer em prompts otimizados
para busca e análise, garantindo resultados profissionais e assertivos.
"""

import os
import logging
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.conf import settings

from .tools import TavilySearchTool, parse_document
from .prompts import get_system_prompt

logger = logging.getLogger(__name__)


def create_joel_agent(
    language: str = "pt-BR",
    professional_area: str = "",
    report_type: str = "analitico",
    geolocation: str = "",
    include_market_references: bool = True,
) -> Agent:
    """
    Cria uma instância do agente Joel configurada para a análise específica.
    
    Args:
        language: Idioma do relatório (pt-BR, en, es)
        professional_area: Área profissional da análise
        report_type: Tipo de relatório (analitico, comparativo, resumo_executivo, tecnico, parecer)
        geolocation: Localização para referências de mercado
        include_market_references: Se deve incluir referências de mercado
    """
    config = settings.JOEL_CONFIG
    
    system_prompt = get_system_prompt(
        language=language,
        professional_area=professional_area,
        report_type=report_type,
        geolocation=geolocation,
        include_market_references=include_market_references,
    )
    
    # Ferramentas disponíveis para o Joel
    tools = [TavilySearchTool()]
    
    joel = Agent(
        name="Joel",
        model=OpenAIChat(
            id=config["OPENAI_MODEL"],
            api_key=config["OPENAI_API_KEY"],
        ),
        description=(
            "Joel é um agente especialista em análise de documentos. "
            "Ele interpreta documentos, pesquisa referências na internet, "
            "e gera relatórios profissionais completos."
        ),
        instructions=system_prompt,
        tools=tools,
        markdown=True,
        show_tool_calls=False,
    )
    
    return joel


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
    
    Returns:
        dict com 'content_markdown', 'references', 'search_results_raw', 'joel_reasoning'
    """
    logger.info(f"Joel iniciando análise: area={professional_area}, tipo={report_type}, idioma={language}")
    
    # Criar o agente Joel
    joel = create_joel_agent(
        language=language,
        professional_area=professional_area,
        report_type=report_type,
        geolocation=geolocation,
        include_market_references=include_market_references,
    )
    
    # Montar o prompt do usuário com todo o contexto
    area_desc = professional_area_detail if professional_area_detail else professional_area
    
    user_prompt = f"""
## DOCUMENTO PARA ANÁLISE

{extracted_text[:15000]}

{"[... documento truncado por tamanho ...]" if len(extracted_text) > 15000 else ""}

---

## SOLICITAÇÃO DO USUÁRIO

**Objetivo da análise:** {user_objective}

**Área profissional:** {area_desc}

**Tipo de relatório solicitado:** {report_type}

**Geolocalização para referências:** {geolocation if geolocation else "Global"}

**Escopo adicional de busca:** {search_scope if search_scope else "Nenhum especificado"}

**Incluir referências de mercado:** {"Sim" if include_market_references else "Não"}

---

Por favor, analise este documento e gere o relatório profissional completo conforme as instruções do sistema.
{"Utilize a ferramenta de busca na internet para encontrar referências de mercado relevantes." if include_market_references else ""}
"""
    
    try:
        # Executar o agente
        response = joel.run(user_prompt)
        
        content_markdown = response.content if response.content else ""
        
        return {
            "content_markdown": content_markdown,
            "references": [],
            "search_results_raw": [],
            "joel_reasoning": f"Análise concluída com sucesso. Tipo: {report_type}, Área: {area_desc}, Idioma: {language}",
        }
        
    except Exception as e:
        logger.error(f"Erro na análise do Joel: {e}")
        raise
