# 🧠 REMEMBER_PROJECT.md - Lessons Learned (Joel)

> **⚠️ AGENTE IA:** Este documento contém lições aprendidas **ESPECÍFICAS** do projeto Joel.
> Consulte **ANTES** de resolver problemas deste projeto.
> Após resolver um problema novo, adicione aqui.

---

## 📋 Informações do Projeto

| Item | Valor |
|------|-------|
| **Projeto** | Joel — Interpretador de Documentos com IA |
| **VPS** | N/A (desenvolvimento local) |
| **Domínio** | N/A (localhost:8004) |
| **Framework** | Django 5.1.5 |
| **Repositório** | github.com/charliba/interpreter (branch: `main`) |
| **Database** | SQLite (dev) / PostgreSQL (prod futuro) |
| **Porta** | 8004 |
| **IA** | Agno + OpenAI GPT-4o |
| **Parsing** | Docling |
| **Busca** | Tavily |

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

*Nenhuma entrada ainda — projeto em desenvolvimento local.*

---

## 🤖 Agente Joel

*Nenhuma entrada ainda.*

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
