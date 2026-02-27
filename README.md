# Joel — Interpretador Inteligente de Documentos

Plataforma Django com IA (GPT-4o) para análise de documentos e geração de relatórios profissionais.

## Stack

| Componente | Tecnologia |
|------------|------------|
| Framework | Django 5.1.5 |
| AI Agent | Agno + OpenAI GPT-4o |
| Document Parsing | Docling |
| Internet Search | Tavily |
| Report Formats | PDF (ReportLab), DOCX (python-docx), XLSX (openpyxl), TXT |
| Frontend | Tailwind CSS + HTMX + Alpine.js |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | Django Auth |
| Porta | 8004 |

## Quick Start

```powershell
# 1. Clonar
git clone https://github.com/charliba/interpreter.git "interpretador de documentos"
cd "interpretador de documentos"

# 2. Configurar
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 3. Credenciais
copy .env.example .env
# Editar .env com suas chaves (OPENAI_API_KEY, TAVILY_API_KEY)

# 4. Database
python manage.py migrate
python manage.py createsuperuser

# 5. Rodar
python manage.py runserver 8004
```

Acesse: http://localhost:8004

## Estrutura

```
interpretador de documentos/
├── config/              # Django project config (settings, urls, wsgi)
├── accounts/            # Auth (login, register, logout)
├── core/                # App principal
│   ├── models.py        # Document, AnalysisRequest, Report
│   ├── views.py         # Upload, análise, relatório, download, histórico
│   ├── forms.py         # Formulários de upload e configuração
│   ├── joel/            # Módulo do agente Joel
│   │   ├── agent.py     # Agno Agent (GPT-4o)
│   │   ├── tools.py     # Docling parse + Tavily search
│   │   ├── prompts.py   # System prompts por tipo de relatório
│   │   └── report_generator.py  # PDF, DOCX, XLSX, TXT
│   └── urls.py
├── templates/           # HTML (Tailwind + HTMX + Alpine.js)
├── static/              # CSS, JS
├── media/               # Uploads e relatórios gerados
├── docs/                # Documentação completa
├── memory/              # Lições aprendidas
├── scripts/             # Scripts utilitários
└── requirements.txt
```

## Fluxo

1. Usuário faz login
2. Upload de documento (qualquer formato suportado pelo Docling)
3. Descreve objetivo, área profissional, geolocalização, tipo de relatório
4. Joel (IA): extrai texto → analisa → pesquisa referências → gera relatório
5. Relatório exibido na tela + download (PDF/DOCX/XLSX/TXT)

## GitHub

- **Repo**: https://github.com/charliba/interpreter.git
- **Branch**: main

## Documentação

Veja [docs/INDEX.md](docs/INDEX.md) para o índice completo.
