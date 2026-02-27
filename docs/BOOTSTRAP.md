# 🚀 BOOTSTRAP.md - Guia de Inicialização — Joel

> **COPILOT:** Este é o arquivo principal. Leia-o INTEIRO antes de qualquer ação.

---

## 📋 O que esta documentação contém

| Arquivo | Propósito |
|---------|-----------|
| `BOOTSTRAP.md` | **ESTE ARQUIVO** - Ponto de entrada |
| `README.md` | Referência completa do projeto |
| `ENV.md` | Referência de variáveis de ambiente |
| `REQUIREMENTS.md` | Dependências e versões |
| `SCHEMA.md` | Estrutura do banco de dados (Mermaid) |
| `REMEMBER_COMPANY.md` | Lessons learned **GENÉRICOS** (reutilizáveis) |
| `REMEMBER_PROJECT.md` | Lessons learned **DO PROJETO** (específicos) |
| `INDEX.md` | Índice geral da documentação |

---

## 🏁 Quick Start (Novo Desenvolvedor)

### 1. Clonar repositório
```powershell
git clone https://github.com/charliba/interpreter.git "interpretador de documentos"
cd "interpretador de documentos"
```

### 2. Criar e ativar venv
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar dependências
```powershell
pip install -r requirements.txt
```

### 4. Configurar .env
```powershell
cp .env.example .env
# Editar .env com suas chaves (OpenAI obrigatória, Tavily opcional)
```

### 5. Rodar migrations
```powershell
python manage.py migrate
```

### 6. Criar superusuário
```powershell
python manage.py createsuperuser
```

### 7. Rodar servidor
```powershell
python manage.py runserver 8004
# Abrir http://localhost:8004
```

---

## 📂 Estrutura do Projeto

```
interpretador de documentos/
├── config/          # Django settings, urls, wsgi
├── core/            # App principal
│   ├── joel/        # Agente IA (agent, tools, prompts, reports)
│   ├── models.py    # Document, AnalysisRequest, Report
│   ├── views.py     # Upload, análise, relatórios, histórico
│   └── forms.py     # Upload + configuração de análise
├── accounts/        # Auth (login, registro, logout)
├── templates/       # HTML (base, pages, components)
├── static/          # CSS, JS
├── media/           # Uploads e relatórios gerados
├── scripts/         # Scripts de teste e utilitários
├── docs/            # Documentação
└── memory/          # Memória rápida do projeto
```

---

## 🔑 Chaves API Necessárias

| Serviço | Variável | Obrigatório | Onde obter |
|---------|----------|-------------|------------|
| OpenAI | `OPENAI_API_KEY` | ✅ | https://platform.openai.com/api-keys |
| Tavily | `TAVILY_API_KEY` | ❌* | https://tavily.com (1000 buscas/mês grátis) |

*Tavily é necessário apenas se ativar "referências de mercado" na análise.

**Modelo IA atual:** `gpt-4.1-mini` (otimizado custo/velocidade).

---

## ⚠️ Ao Criar Novo Projeto (Reutilizar Docs)

### Arquivos para MANTER (genéricos):
- ✅ `REMEMBER_COMPANY.md`
- ✅ `BOOTSTRAP.md`

### Arquivos para RESETAR (específicos):
- 🔄 `REMEMBER_PROJECT.md` — Limpar e reiniciar
- 🔄 `SCHEMA.md` — Novo schema
- 🔄 `ENV.md` — Novas variáveis
- 🔄 `REQUIREMENTS.md` — Novas dependências
- 🔄 `README.md` — Reescrever

---

## 🔄 Portas do Ecossistema

| Projeto | Porta | Status |
|---------|-------|--------|
| Beezle | 8001 | Produção |
| AresDev | 8002 | Produção |
| waLink | 8003 | Produção |
| **Joel** | **8004** | **Desenvolvimento** |
