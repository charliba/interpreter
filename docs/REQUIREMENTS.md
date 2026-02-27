# Dependências — Joel

Explicação de cada pacote em `requirements.txt`.

## Framework Web

| Pacote | Versão | Uso |
|--------|--------|-----|
| `Django` | 5.1.5 | Framework web principal |
| `gunicorn` | — | Servidor WSGI para produção |

## IA / Agente

| Pacote | Versão | Uso |
|--------|--------|-----|
| `agno` | — | Framework de agentes IA (orquestra Joel) |
| `openai` | — | Client da API OpenAI (GPT-4o) |

## Processamento de Documentos

| Pacote | Versão | Uso |
|--------|--------|-----|
| `docling` | — | Parsing avançado de documentos (PDF, DOCX, XLSX, PPTX, imagens/OCR, etc.) |

## Busca na Internet

| Pacote | Versão | Uso |
|--------|--------|-----|
| `tavily-python` | — | API de busca profunda (referências de mercado, dados complementares) |

## Geração de Relatórios

| Pacote | Versão | Uso |
|--------|--------|-----|
| `reportlab` | — | Geração de PDF com estilos customizados |
| `python-docx` | — | Geração de DOCX (Word) |
| `openpyxl` | — | Geração de XLSX (Excel) com estilos |
| `markdown` | — | Conversão Markdown → HTML |
| `bleach` | — | Sanitização de HTML |

## Utilitários

| Pacote | Versão | Uso |
|--------|--------|-----|
| `Pillow` | — | Processamento de imagens |
| `requests` | — | Requisições HTTP |
| `python-dotenv` | — | Carregamento de `.env` |

## Instalação

```bash
pip install -r requirements.txt
```

## Notas

- **Docling** pode ser pesado na instalação (~1GB+ com dependências de ML/OCR). Em ambientes limitados, considere instalar apenas os extras necessários.
- **Tavily** requer API key separada (gratuito até 1000 buscas/mês).
- **Agno** usa OpenAI como provider padrão; suporta outros (Anthropic, Groq) se necessário no futuro.
