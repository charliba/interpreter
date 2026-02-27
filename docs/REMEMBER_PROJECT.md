# 🧠 REMEMBER_PROJECT.md - Lessons Learned (Joel)

> **⚠️ AGENTE IA:** Este documento contém lições aprendidas **ESPECÍFICAS** do projeto Joel.
> Consulte **ANTES** de resolver problemas deste projeto.
> Após resolver um problema novo, adicione aqui.

---

## 📋 Informações do Projeto

| Item | Valor |
|------|-------|
| **Projeto** | Joel — Interpretador de Documentos com IA |
| **VPS** | Hostinger 2.57.91.91 |
| **Domínio** | askjoel.cloud |
| **Framework** | Django 5.1.5 |
| **Repositório** | github.com/charliba/interpreter (branch: `main`) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Porta** | 8004 (Gunicorn) |
| **IA** | Agno + OpenAI gpt-4.1-mini |
| **Parsing** | pypdf (fast) + Docling (fallback, OCR off) |
| **Busca** | Tavily |
| **Email** | admin@askjoel.cloud, contato@askjoel.cloud |

---

## 📋 Índice

1. [Arquitetura](#-arquitetura)
2. [Deploy e Servidor](#-deploy-e-servidor)
3. [Agente Joel](#-agente-joel)
4. [Docling (Parsing)](#-docling-parsing)
5. [Banco de Dados](#-banco-de-dados)
6. [Frontend](#-frontend)

---

## 🏗️ Arquitetura

### ✅ Fluxo de processamento
```
Upload → Document + AnalysisRequest criados
  → Thread: process_analysis()
    → Docling extrai texto
    → Joel (Agno+GPT-4o) analisa
    → Tavily busca referências (opcional)
    → report_generator gera PDF/DOCX/XLSX/TXT
    → Report salvo, status = completed
```

### ⚠️ NOTA: Threading vs Celery
**Situação atual:** Processamento usa `threading.Thread` (solução temporária).
**Futuro:** Migrar para Celery + Redis para produção.
**Risco:** Thread pode falhar silenciosamente se o processo Django reiniciar durante análise.

---

## 🚀 Deploy e Servidor

### ✅ Mapa de portas na VPS
| Porta | Projeto | Domínio |
|-------|---------|--------|
| 8001 | buzzgear | beezle.io |
| 8002 | aresdev | aresdev.cloud |
| 8003 | waLink | walinkhub.cloud |
| 8004 | **Joel** | **askjoel.cloud** |

### ✅ Arquivos de deploy
- `config/systemd/askjoel.service` → Gunicorn systemd unit
- `config/nginx/askjoel.cloud.conf` → Nginx reverse proxy + SSL
- `.env.production` → Template do .env de produção
- `deploy.sh` → Script completo de deploy (8 etapas)

### ⚠️ NOTA: Docling na VPS
Docling exige ~1GB+ de dependências ML. Se a VPS tiver pouca RAM, pypdf será o extrator primário (funciona para 90%+ dos PDFs com texto embutido).

### ⚠️ NOTA: Timeout
`JOEL_TIMEOUT=120` (2 min). O processamento completo (extração + IA + relatório) DEVE completar em 2 minutos ou será cancelado.

---

## 🤖 Agente Joel

### ✅ Modelo atual: gpt-4.1-mini
Modelo otimizado para custo/velocidade. Mudamos de gpt-4o → gpt-4o-mini → gpt-4.1-mini.

### ✅ Extração de texto: pypdf primeiro
Estratégia em cascata:
1. pypdf (< 3s) para PDFs com texto embutido
2. Docling sem OCR (< 45s) como fallback
3. Leitura plain text como último recurso

---

## 📄 Docling (Parsing)

### ⚠️ NOTA: Docling é pesado
**Problema:** Docling instala ~1GB+ de dependências (ML, OCR).
**Solução:** Em ambientes limitados, usar fallback de leitura plain text.
**Código:** `core/joel/tools.py` → `parse_document()` tem fallback automático.

---

## 🗄️ Banco de Dados

*Nenhuma entrada ainda.*

---

## 🎨 Frontend

### ✅ Layout padrão waLink
- Sidebar fixa escura (#111827)
- Tailwind CSS CDN + HTMX + Alpine.js
- Cores: azul primário (#2563eb), roxo accent (#7c3aed)
- Polling HTMX a cada 3s para status de análise

---

## 📝 Template para Nova Entrada

```markdown
### ❌ ERRO: [Título descritivo]
**Data:** [Mês/Ano]
**Problema:** [Descrição]
**Solução:**
\```[linguagem]
[código]
\```
**Prevenção:** [Como evitar]
```

---

## 🔄 Histórico

| Data | Descrição |
|------|-----------|
| Jun/2025 | Criação do projeto |
