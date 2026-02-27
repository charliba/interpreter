# Joel — Referência Completa

## Visão Geral

Joel é uma plataforma Django com inteligência artificial para interpretação de documentos e geração de relatórios profissionais. O agente Joel (Agno + GPT-4o) atua como intermediário inteligente entre o usuário e a produção do relatório.

## URLs

| URL | View | Descrição |
|-----|------|-----------|
| `/` | `upload_view` | Tela principal (upload + configuração) |
| `/analysis/<id>/` | `analysis_status_view` | Progresso da análise |
| `/analysis/<id>/poll/` | `analysis_poll_view` | API polling (HTMX) |
| `/report/<id>/` | `report_view` | Relatório na tela |
| `/report/<id>/download/<fmt>/` | `download_view` | Download (pdf/docx/xlsx/txt) |
| `/history/` | `history_view` | Histórico de análises |
| `/accounts/` | `auth_page` | Login/registro |
| `/accounts/login/` | `login_view` | POST login |
| `/accounts/register/` | `register_view` | POST registro |
| `/accounts/logout/` | `logout_view` | POST logout |
| `/admin/` | Django Admin | Admin |

## Fluxo de Análise

```
1. Upload (POST multipart)
   └─> Document + AnalysisRequest criados
       └─> Thread: process_analysis()
           ├─> Docling: parse_document(file_path)
           │   └─> extracted_text salvo no Document
           ├─> Joel: run_analysis(text, config)
           │   ├─> Agno Agent com GPT-4o
           │   └─> Tavily search (se incluir referências)
           └─> report_generator: markdown → HTML/PDF/DOCX/XLSX/TXT
               └─> Report criado, Analysis marcada completed
```

## Models

- **Document**: arquivo + texto extraído
- **AnalysisRequest**: configuração da análise (objetivo, área, geo, idioma, tipo)
- **Report**: relatório gerado (HTML, markdown, referências, arquivos)

## Agente Joel

- **Framework**: Agno
- **LLM**: OpenAI GPT-4o
- **Tools**: Tavily (busca), Docling (parsing)
- **Prompts**: configuráveis por tipo de relatório e idioma

## Frontend Stack

- Tailwind CSS (CDN)
- HTMX (polling, interações)
- Alpine.js (estado local, modais)
- Layout: sidebar fixa escura + conteúdo principal (padrão waLink)
