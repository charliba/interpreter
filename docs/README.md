# Joel — Referência Completa

## Visão Geral

Joel é uma plataforma Django com inteligência artificial para interpretação de documentos e geração de relatórios profissionais. O agente Joel (Agno + GPT-4.1-mini) atua como intermediário inteligente entre o usuário e a produção do relatório.

- **Domínio**: askjoel.cloud
- **VPS**: Hostinger 31.97.171.87 (porta 8004)
- **SSL**: Let's Encrypt (válido até mai/2026)
- **Repositório**: github.com/charliba/interpreter (branch: main)

## URLs

| URL | View | Descrição |
|-----|------|-----------|
| `/` | `upload_view` | Tela principal (upload + configuração) |
| `/analysis/<id>/` | `analysis_status_view` | Progresso da análise |
| `/analysis/<id>/poll/` | `analysis_poll_view` | API polling (HTMX) |
| `/analysis/<id>/retry/` | `retry_view` | Reprocessar análise com erro |
| `/analysis/<id>/edit/` | `edit_analysis_view` | Editar parâmetros e reanalisar |
| `/report/<id>/` | `report_view` | Relatório na tela |
| `/report/<id>/download/<fmt>/` | `download_view` | Download (pdf/docx/xlsx/txt) |
| `/history/` | `history_view` | Histórico de análises + caixa de sugestão |
| `/sugestao/` | `submit_suggestion` | POST sugestão de melhoria |
| `/accounts/` | `auth_page` | Login/registro |
| `/accounts/login/` | `login_view` | POST login |
| `/accounts/register/` | `register_view` | POST registro |
| `/accounts/logout/` | `logout_view` | POST logout |
| `/admin/` | Django Admin | Admin (gestão de sugestões, docs, etc) |

## Fluxo de Análise

```
1. Upload (POST multipart)
   └─> Document + AnalysisRequest criados
       └─> Thread: process_analysis()
           ├─> pypdf (fast, <3s) → Docling fallback → plaintext
           │   └─> extracted_text salvo no Document
           ├─> Joel: run_analysis(text, config)
           │   ├─> Agno Agent com GPT-4.1-mini
           │   └─> Tavily search (se incluir referências)
           └─> report_generator: markdown → HTML/PDF/DOCX/XLSX/TXT
               └─> Report criado, Analysis marcada completed
   HTMX polling a cada 3s → auto-redirect ao report
```

## Models (4)

- **Document**: arquivo + texto extraído (pypdf/Docling)
- **AnalysisRequest**: configuração da análise (objetivo, área, geo, idioma, tipo) — 7 status
- **Report**: relatório gerado (HTML, markdown, referências, 4 formatos de arquivo)
- **Suggestion**: sugestões de melhoria enviadas por usuários (categoria, prioridade, status interno)

## Agente Joel

- **Framework**: Agno
- **LLM**: OpenAI GPT-4.1-mini (otimizado custo/velocidade)
- **Parsing**: pypdf (rápido) → Docling sem OCR (fallback) → plaintext
- **Tools**: Tavily (busca de referências, controlada pelo agente)
- **Prompts**: configuráveis por tipo de relatório × idioma
- **Timeout**: 120s (JOEL_TIMEOUT)

## Frontend Stack

- Tailwind CSS (CDN)
- HTMX (polling a cada 3s, interações)
- Alpine.js (estado local, modais, sidebar)
- Layout: sidebar fixa escura (#111827) + conteúdo principal (padrão waLink)

## Deploy

- **Local**: `python manage.py runserver 8004` (SQLite)
- **Produção**: `python deploy_vps.py` (Paramiko SSH → VPS)
- **Infra**: Nginx reverse proxy → Gunicorn (systemd) → Django
- **Arquivos**: `config/systemd/askjoel.service`, `config/nginx/askjoel.cloud.conf`
