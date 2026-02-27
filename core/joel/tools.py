"""
Joel Tools — Ferramentas de busca e parsing para o agente Joel.

- TavilySearchTool: busca profunda na internet via Tavily API
- DoclingParseTool: extrai texto/estrutura de documentos via Docling
"""

import os
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class TavilySearchTool:
    """
    Ferramenta de busca profunda na internet via Tavily API.
    Usada pelo Joel para encontrar referências de mercado e contexto.
    """
    
    def __init__(self):
        config = settings.JOEL_CONFIG
        self.api_key = config.get("TAVILY_API_KEY", "")
        self.max_results = config.get("MAX_SEARCH_RESULTS", 10)
        self.search_depth = config.get("SEARCH_DEPTH", "advanced")
    
    def search(
        self,
        query: str,
        geolocation: str = "",
        max_results: Optional[int] = None,
        search_depth: Optional[str] = None,
    ) -> dict:
        """
        Executa busca profunda na internet.
        
        Args:
            query: Termo de busca
            geolocation: Filtro de localização (ex: 'Brazil', 'São Paulo')
            max_results: Número máximo de resultados
            search_depth: 'basic' ou 'advanced'
        
        Returns:
            dict com 'results' (lista de {title, url, content}) e 'query'
        """
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=self.api_key)
            
            # Adicionar geolocalização à query se especificada
            search_query = query
            if geolocation:
                search_query = f"{query} {geolocation}"
            
            response = client.search(
                query=search_query,
                max_results=max_results or self.max_results,
                search_depth=search_depth or self.search_depth,
            )
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                })
            
            logger.info(f"Tavily: {len(results)} resultados para '{search_query}'")
            
            return {
                "query": search_query,
                "results": results,
                "answer": response.get("answer", ""),
            }
            
        except ImportError:
            logger.error("tavily-python não instalado. Execute: pip install tavily-python")
            return {"query": query, "results": [], "answer": "", "error": "tavily não instalado"}
        except Exception as e:
            logger.error(f"Erro na busca Tavily: {e}")
            return {"query": query, "results": [], "answer": "", "error": str(e)}

    def search_market_references(
        self,
        topic: str,
        professional_area: str,
        geolocation: str = "",
    ) -> dict:
        """
        Busca especializada por referências de mercado.
        Uma única busca otimizada (em vez de múltiplas queries lentas).
        """
        query = f"{topic} {professional_area} market analysis trends {geolocation}".strip()
        result = self.search(query, max_results=5, search_depth="basic")
        
        return {
            "topic": topic,
            "area": professional_area,
            "results": result.get("results", []),
        }


def parse_document(file_path: str) -> dict:
    """
    Extrai texto e estrutura de qualquer documento usando Docling.
    
    Suporta: PDF, DOCX, XLSX, PPTX, HTML, imagens (OCR), TXT, CSV, MD
    
    Args:
        file_path: Caminho absoluto para o arquivo
    
    Returns:
        dict com 'text' (texto extraído), 'metadata' (metadados)
    """
    try:
        from docling.document_converter import DocumentConverter
        
        logger.info(f"Docling: parseando {file_path}")
        
        converter = DocumentConverter()
        result = converter.convert(file_path)
        
        # Extrair texto do resultado
        text = result.document.export_to_markdown()
        
        # num_pages() é um método, não propriedade — precisa chamar()
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
