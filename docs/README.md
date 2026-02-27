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

## Modos de Análise (4)

Joel suporta 4 modos de análise, selecionados pelo usuário na tela principal:

| Modo | Campo `analysis_mode` | Descrição |
|------|----------------------|-----------|
| **Documento** | `document` | Análise tradicional de um documento enviado |
| **Multi-Documento** | `multi_document` | Análise conjunta de vários documentos (auto-ativado se >1 arquivo) |
| **Aprimorar** | `enhancement` | Melhoria/enriquecimento de um documento existente com pesquisa e imagens IA |
| **Análise Livre** | `free_form` | Análise sem documento — o usuário descreve o tema e Joel pesquisa na internet |

### Parâmetros configuráveis pelo usuário

- **Quantidade de fontes** (`source_count`, 1–20, padrão 5): slider na UI que controla quantas referências o Joel deve incluir
- **Incluir imagens** (`include_images`, bool): toggle que ativa geração de imagens profissionais via DALL-E 3 + Pixabay

## Fluxo de Análise

```
1. Upload (POST multipart — suporta múltiplos arquivos)
   └─> Document(s) + AnalysisRequest criados
       ├─> mode=document: 1 documento → extração + análise
       ├─> mode=multi_document: N documentos → extração de cada → análise conjunta
       ├─> mode=enhancement: 1 documento → extração → melhoria + imagens IA
       └─> mode=free_form: sem documento → pesquisa internet + análise
       └─> Thread: process_analysis()
           ├─> pypdf (fast, <3s) → Docling fallback → plaintext
           │   └─> extracted_text salvo no Document (skip se free_form)
           ├─> Joel: run_analysis(text, config, mode, source_count, include_images)
           │   ├─> Agno Agent com GPT-4.1-mini
           │   ├─> Tavily search (referências + free_form)
           │   └─> Source count target: N referências distintas
           ├─> [se include_images] ai_images: DALL-E 3 → Pixabay fallback
           └─> report_generator: markdown → HTML/PDF/DOCX/XLSX/TXT
               └─> Report criado, Analysis marcada completed
   HTMX polling a cada 3s → auto-redirect ao report
```

## Models (4)

- **Document**: arquivo + texto extraído (pypdf/Docling)
- **AnalysisRequest**: configuração da análise (modo, objetivo, área, geo, idioma, tipo, source_count, include_images) — 7 status
  - `document` FK (nullable — null em modo free_form)
  - `additional_documents` M2M (para multi-documento)
  - `analysis_mode` (4 modos: document, multi_document, enhancement, free_form)
  - `source_count` (1–20, padrão 5)
  - `include_images` (bool, padrão False)
- **Report**: relatório gerado (HTML, markdown, referências, 4 formatos de arquivo, charts + imagens IA)
- **Suggestion**: sugestões de melhoria enviadas por usuários (categoria, prioridade, status interno)

## Agente Joel

- **Framework**: Agno
- **LLM**: OpenAI GPT-4.1-mini (otimizado custo/velocidade)
- **Parsing**: pypdf (rápido) → Docling sem OCR (fallback) → plaintext
- **Tools**: Tavily (busca de referências, controlada pelo agente — forçado em free_form)
- **Prompts**: configuráveis por tipo de relatório × idioma × modo de análise
- **Source count**: meta de N referências distintas passada ao prompt
- **Timeout**: 120s (JOEL_TIMEOUT)

## Geração de Imagens (ai_images.py)

Módulo `core/joel/ai_images.py` — ativado quando `include_images=True`.

**Estratégia em camadas:**
1. **DALL-E 3** (OpenAI): imagens profissionais a partir de prompts contextuais (~$0.04/imagem, 1792×1024)
2. **Pixabay API**: fotos de stock como fallback (gratuito, requer `PIXABAY_API_KEY`)
3. **Matplotlib**: imagens decorativas como último recurso

**Fluxos:**
- **Relatórios normais** (`generate_report_images()`): extrai tópicos do markdown → gera 2-4 imagens temáticas
- **Modo enhancement** (`enhance_document_images()`): gera ilustrações profissionais com legendas contextuais

**Estilos por área**: mapeamento automático (financeiro→corporate blue, saúde→clinical white, etc.)

## Frontend Stack

- Tailwind CSS (CDN)
- HTMX (polling a cada 3s, interações)
- Alpine.js (estado local, modais, sidebar, multi-arquivo, modos de análise)
- Layout: sidebar fixa escura (#111827) + conteúdo principal (padrão waLink)
- Upload: 4 abas de modo com gradientes por tipo, drag-and-drop, multi-arquivo com remoção individual
- Slider: source_count range 1–20 com display dinâmico
- Toggle: include_images com descrição contextual

## Migrations

| Migration | Operações |
|-----------|-----------|
| 0001 | Criação inicial: Document, AnalysisRequest, Report |
| 0002 | Suggestion model |
| 0003 | Extraction metadata, file_type, report_type, search_scope |
| 0004 | Report fields: charts, executive_summary, etc. |
| 0005 | analysis_mode, additional_documents M2M, source_count, include_images, document nullable, ReportType.enhancement |

## Deploy

- **Local**: `python manage.py runserver 8004` (SQLite)
- **Produção**: `python deploy_vps.py` (Paramiko SSH → VPS)
- **Infra**: Nginx reverse proxy → Gunicorn (daemon) → Django
- **Restart**: `pkill -f gunicorn && source venv/bin/activate && gunicorn config.wsgi:application --bind 0.0.0.0:8004 --workers 3 --timeout 300 --daemon`

## ENV Keys

| Variável | Uso |
|----------|-----|
| `OPENAI_API_KEY` | GPT-4.1-mini (análise) + DALL-E 3 (imagens) |
| `TAVILY_API_KEY` | Pesquisa web via Agno |
| `PIXABAY_API_KEY` | Busca de fotos de stock (fallback imagens) |
| `VPS_HOST` | IP do servidor (31.97.171.87) |
| `VPS_USER` | Usuário SSH (root) |
| `VPS_PASSWORD` | Senha SSH |
