# Dependências — Joel

Explicação de cada pacote em `requirements.txt`.

## Framework Web

| Pacote | Versão | Uso |
|--------|--------|-----|
| `Django` | 5.1.5 | Framework web principal |
| `gunicorn` | 23.0.0 | Servidor WSGI para produção |

## IA / Agente

| Pacote | Versão | Uso |
|--------|--------|-----|
| `agno` | ≥1.0.0 | Framework de agentes IA (orquestra Joel) |
| `openai` | ≥1.50.0 | Client da API OpenAI (GPT-4.1-mini) |

## Processamento de Documentos

| Pacote | Versão | Uso |
|--------|--------|-----|
| `pypdf` | ≥6.0 | Extração rápida de texto de PDF (<3s, primeiro na cascata) |
| `docling` | ≥2.0.0 | Parsing avançado de documentos (fallback com OCR desligado) |

## Busca na Internet

| Pacote | Versão | Uso |
|--------|--------|-----|
| `tavily-python` | ≥0.5.0 | API de busca profunda (referências de mercado, dados complementares) |

## Geração de Relatórios

| Pacote | Versão | Uso |
|--------|--------|-----|
| `reportlab` | ≥4.0 | Geração de PDF com estilos customizados |
| `python-docx` | ≥1.0.0 | Geração de DOCX (Word) |
| `openpyxl` | ≥3.1.0 | Geração de XLSX (Excel) com estilos |
| `markdown` | ≥3.5 | Conversão Markdown → HTML |
| `bleach` | ≥6.0 | Sanitização de HTML (segurança XSS) |

## Utilitários

| Pacote | Versão | Uso |
|--------|--------|-----|
| `Pillow` | ≥10.0 | Processamento de imagens |
| `requests` | ≥2.31.0 | Requisições HTTP |
| `python-dotenv` | 1.2.1 | Carregamento de `.env` |

## Database (Produção)

| Pacote | Versão | Uso |
|--------|--------|-----|
| `psycopg2-binary` | ≥2.9.9 | Driver PostgreSQL para produção |

## Instalação

```bash
pip install -r requirements.txt
```

## Notas

- **pypdf** é extremamente rápido (~1–3s) para PDFs com texto embutido. Cobre 90%+ dos casos.
- **Docling** é o fallback (OCR desligado, timeout 45s). Exige ~1GB+ de dependências ML.
- **Tavily** requer API key separada (gratuito até 1000 buscas/mês).
- **Agno** usa OpenAI como provider padrão; suporta outros (Anthropic, Groq) se necessário no futuro.
- **psycopg2-binary** só é necessário em produção (PostgreSQL). Dev usa SQLite.
