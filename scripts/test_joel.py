"""
scripts/test_joel.py — Teste isolado do agente Joel (sem Django)

Uso:
    cd "interpretador de documentos"
    venv\Scripts\activate
    python scripts/test_joel.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Simular settings.JOEL_CONFIG
class MockSettings:
    JOEL_CONFIG = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        "DEFAULT_LANGUAGE": os.getenv("JOEL_DEFAULT_LANGUAGE", "pt-BR"),
        "MAX_SEARCH_RESULTS": int(os.getenv("JOEL_MAX_SEARCH_RESULTS", "10")),
        "SEARCH_DEPTH": os.getenv("JOEL_SEARCH_DEPTH", "advanced"),
    }

# Monkey-patch django.conf.settings
sys.modules['django'] = type(sys)('django')
sys.modules['django.conf'] = type(sys)('django.conf')
sys.modules['django.conf'].settings = MockSettings()


def test_openai_connection():
    """Testa conexão com OpenAI."""
    print("=" * 50)
    print("TESTE 1: Conexão OpenAI")
    print("=" * 50)
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-COLE"):
        print("ERRO: Configure OPENAI_API_KEY no .env")
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Diga apenas 'Joel online!' em uma linha."}],
            max_tokens=20,
        )
        print(f"OK: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        return False


def test_tavily_connection():
    """Testa conexão com Tavily."""
    print("\n" + "=" * 50)
    print("TESTE 2: Conexão Tavily")
    print("=" * 50)
    
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.startswith("tvly-COLE"):
        print("AVISO: TAVILY_API_KEY não configurada (busca desabilitada)")
        return False
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        result = client.search("Python Django web development", max_results=2)
        print(f"OK: {len(result.get('results', []))} resultados encontrados")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        return False


def test_docling():
    """Testa se Docling está instalado."""
    print("\n" + "=" * 50)
    print("TESTE 3: Docling instalado")
    print("=" * 50)
    
    try:
        from docling.document_converter import DocumentConverter
        print("OK: Docling disponível")
        return True
    except ImportError as e:
        print(f"AVISO: Docling não disponível ({e})")
        return False


def test_report_generation():
    """Testa geração de relatório."""
    print("\n" + "=" * 50)
    print("TESTE 4: Geração de relatórios")
    print("=" * 50)
    
    # Add project root to path
    sys.path.insert(0, str(BASE_DIR))
    
    try:
        from core.joel.report_generator import generate_pdf, generate_docx, generate_xlsx, generate_txt
        
        test_markdown = """# Relatório de Teste

## Resumo Executivo

Este é um relatório de teste gerado pelo Joel.

## Análise

- Ponto 1: Tudo funcionando
- Ponto 2: Geração de formatos OK
- Ponto 3: Sistema operacional

## Referências

1. [Python](https://python.org) — Linguagem principal
2. [Django](https://djangoproject.com) — Framework web
"""
        
        pdf = generate_pdf(test_markdown, "Teste Joel")
        print(f"  PDF: {len(pdf.read())} bytes")
        
        docx = generate_docx(test_markdown, "Teste Joel")
        print(f"  DOCX: {len(docx.read())} bytes")
        
        xlsx = generate_xlsx(test_markdown, [], "Teste Joel")
        print(f"  XLSX: {len(xlsx.read())} bytes")
        
        txt = generate_txt(test_markdown, "Teste Joel")
        print(f"  TXT: {len(txt.read())} bytes")
        
        print("OK: Todos os formatos gerados")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Joel — Teste do Agente")
    print("=" * 50)
    
    results = {
        "OpenAI": test_openai_connection(),
        "Tavily": test_tavily_connection(),
        "Docling": test_docling(),
        "Relatórios": test_report_generation(),
    }
    
    print("\n" + "=" * 50)
    print("RESUMO")
    print("=" * 50)
    for name, ok in results.items():
        status = "OK" if ok else "FALHA/AVISO"
        print(f"  {name}: {status}")
    
    all_ok = all(results.values())
    print(f"\n{'TUDO OK!' if all_ok else 'Alguns testes falharam — verifique o .env'}")
