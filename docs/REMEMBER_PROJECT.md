# 🧠 REMEMBER_PROJECT.md - Lessons Learned (Joel)

> **⚠️ AGENTE IA:** Este documento contém lições aprendidas **ESPECÍFICAS** do projeto Joel.
> Consulte **ANTES** de resolver problemas deste projeto.
> Após resolver um problema novo, adicione aqui.

---

## 📋 Informações do Projeto

| Item | Valor |
|------|-------|
| **Projeto** | Joel — Interpretador de Documentos com IA |
| **VPS** | Hostinger 31.97.171.87 |
| **Domínio** | askjoel.cloud |
| **SSL** | Let's Encrypt (válido até mai/2026) |
| **Framework** | Django 5.1.5 |
| **Python** | 3.14.3 (local) / 3.12 (VPS) |
| **Repositório** | github.com/charliba/interpreter (branch: main) |
| **Database** | SQLite (dev) / PostgreSQL askjoel_db (prod) |
| **Porta** | 8004 (Gunicorn) |
| **IA** | Agno + OpenAI gpt-4.1-mini |
| **Parsing** | pypdf (fast) + Docling (fallback, OCR off) |
| **Busca** | Tavily (controlada pelo agente) |
| **Email** | admin@askjoel.cloud, contato@askjoel.cloud |
| **Admin prod** | admin / AskJoel2026! (trocar na primeira oportunidade) |

---

## 📋 Índice

1. [Arquitetura](#-arquitetura)
2. [Deploy e Servidor](#-deploy-e-servidor)
3. [Agente Joel](#-agente-joel)
4. [Docling (Parsing)](#-docling-parsing)
5. [Banco de Dados](#-banco-de-dados)
6. [Frontend](#-frontend)
7. [Segurança](#-segurança)
8. [Caixa de Sugestões](#-caixa-de-sugestões)

---

## 🏗️ Arquitetura

### ✅ Fluxo de processamento
```
Upload → Document + AnalysisRequest criados (status=pending)
  → Thread: process_analysis()
    → ETAPA 1: pypdf (<3s) → Docling fallback (45s) → plaintext
    → ETAPA 2: Joel (Agno + GPT-4.1-mini + TavilyTools)
    → ETAPA 3: report_generator → PDF/DOCX/XLSX/TXT
    → Report salvo, status = completed
  → HTMX polling /analysis/<id>/poll/ a cada 3s
  → Auto-redirect para /report/<id>/ ao completar
```

### ⚠️ NOTA: Threading vs Celery
**Situação atual:** Processamento usa threading.Thread (solução temporária).
**Futuro:** Migrar para Celery + Redis para produção.
**Risco:** Thread pode falhar silenciosamente se o processo Django reiniciar durante análise.

### ✅ Models (4 tabelas)
| Model | Função |
|-------|--------|
| Document | Arquivo + texto extraído |
| AnalysisRequest | Configuração da análise (7 status) |
| Report | Relatório gerado (1:1 com análise) |
| Suggestion | Sugestões de melhoria dos usuários |

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
- config/systemd/askjoel.service → Gunicorn: 2 workers, 4 threads, timeout 180
- config/nginx/askjoel.cloud.conf → Nginx reverse proxy + SSL + security headers
- .env.production → Template do .env de produção
- deploy.sh → Script completo de deploy (8 etapas)
- deploy_vps.py → Script automatizado via Paramiko SSH (10 etapas, roda localmente)

### ✅ Deploy automático
```powershell
.\venv\Scripts\python.exe deploy_vps.py
```
Faz: git pull → pip install → .env → PostgreSQL → migrate → collectstatic → Gunicorn → Nginx → SSL

### ❌ ERRO: SSL ERR_CERT_COMMON_NAME_INVALID
**Data:** Jun/2025
**Problema:** HTTPS retornava certificado do aresdev.cloud (CN errado).
**Causa:** Sem certificado SSL para askjoel.cloud, Nginx servia o cert default do VPS.
**Solução:** Gerar certificado com certbot antes de ativar HTTPS no Nginx:
```bash
# Primeiro: Nginx com HTTP only (sem SSL)
certbot certonly --webroot -w /var/www/html -d askjoel.cloud -d www.askjoel.cloud --non-interactive --agree-tos -m admin@askjoel.cloud
# Depois: Nginx com HTTPS + cert paths
nginx -t && systemctl reload nginx
```
**Prevenção:** Sempre gerar SSL antes de configurar HTTPS. Script deploy_vps.py já faz isso automaticamente.

### ❌ ERRO: PostgreSQL CREATE DATABASE in transaction block
**Data:** Jun/2025
**Problema:** CREATE DATABASE via psql -c "CREATE USER...; CREATE DATABASE..." falha.
**Causa:** CREATE DATABASE não pode rodar dentro de transaction block.
**Solução:** Usar createdb como comando separado:
```bash
sudo -u postgres psql -c "CREATE USER askjoel_user WITH PASSWORD '...';"
sudo -u postgres createdb -O askjoel_user askjoel_db
```
**Prevenção:** Nunca combinar CREATE DATABASE com outros SQL em um único -c.

### ❌ ERRO: PostgreSQL role doesn't exist
**Data:** Jun/2025
**Problema:** createdb -O askjoel_user askjoel_db falha: "role doesn't exist".
**Causa:** CREATE USER precisa rodar ANTES do createdb.
**Solução:** Sequência correta: CREATE USER → createdb → ALTER ROLE.

### ⚠️ NOTA: Gunicorn HTTP 400 em localhost
O curl http://127.0.0.1:8004/ retorna 400 Bad Request em produção.
**Isso é esperado** — ALLOWED_HOSTS não inclui localhost, apenas askjoel.cloud.
Testar com: curl -sIk https://askjoel.cloud/accounts/

### ⚠️ NOTA: Docling na VPS
Docling exige ~1GB+ de dependências ML. Se a VPS tiver pouca RAM, pypdf será o extrator primário (funciona para 90%+ dos PDFs com texto embutido).

### ⚠️ NOTA: Timeout
JOEL_TIMEOUT=120 (2 min). Processamento completo DEVE completar em 2 minutos ou será cancelado. Gunicorn timeout = 180s.

### ⚠️ NOTA: SSL Auto-Renewal
Certificado Let's Encrypt expira em mai/2026. Verificar renovação automática:
```bash
certbot renew --dry-run
```

---

## 🤖 Agente Joel

### ✅ Evolução do modelo
| Versão | Motivo da troca |
|--------|----------------|
| gpt-4o | Inicial, caro |
| gpt-4o-mini | Mais barato, suficiente |
| **gpt-4.1-mini** | Atual — melhor custo/velocidade, boa qualidade |

### ✅ Extração de texto: pypdf primeiro
Estratégia em cascata (core/joel/tools.py):
1. **pypdf** (< 3s) para PDFs com texto embutido — cobre 90%+ dos casos
2. **Docling sem OCR** (< 45s) como fallback para PDFs complexos
3. **Leitura plain text** como último recurso

### ✅ Tavily é controlada pelo agente
O agente Joel decide quando pesquisar via TavilyTools. O flag include_market_references do usuário apenas habilita/desabilita a tool — o agente decide se/quando usá-la.

---

## 📄 Docling (Parsing)

### ⚠️ NOTA: Docling é pesado
**Problema:** Docling instala ~1GB+ de dependências (ML, OCR).
**Solução:** OCR desligado (do_ocr=False). pypdf como caminho principal.
**Código:** core/joel/tools.py → parse_document() tem fallback automático.
**Timeout:** ThreadPoolExecutor com 45s hard limit para Docling.

---

## 🗄️ Banco de Dados

### ✅ Dev vs Prod
| Ambiente | Engine | Database |
|----------|--------|----------|
| Local | SQLite | db.sqlite3 |
| Produção | PostgreSQL | askjoel_db / askjoel_user |

### ✅ Migration da Suggestion (v1.1.0)
```bash
python manage.py makemigrations core  # 0003_suggestion.py
python manage.py migrate
```

### ⚠️ NOTA: Backup antes de migrate em produção
Sempre fazer backup do PostgreSQL antes de rodar migrations:
```bash
pg_dump -U askjoel_user askjoel_db > backup_$(date +%Y%m%d).sql
```

---

## 🎨 Frontend

### ✅ Layout padrão waLink
- Sidebar fixa escura (#111827)
- Tailwind CSS CDN + HTMX + Alpine.js
- Cores: azul primário (#2563eb), roxo accent (#7c3aed)
- Polling HTMX a cada 3s para status de análise

### ✅ Componentes
| Componente | Template | Descrição |
|------------|----------|-----------|
| Sidebar | components/sidebar.html | Menu lateral com links + user info |
| Upload | pages/upload.html | Drag-and-drop + config da análise |
| Análise | pages/analysis.html | Progresso 4 etapas + polling |
| Relatório | pages/report.html | Display + download (4 formatos) |
| Histórico | pages/history.html | Lista de análises + caixa de sugestão |
| Edição | pages/edit_analysis.html | Reanalisar com novos parâmetros |
| Auth | pages/auth.html | Login/registro split-screen |

---

## 🔒 Segurança

### ✅ Produção — Headers de segurança
Configurados em config/settings.py (bloco if not DEBUG):
- Strict-Transport-Security (HSTS 1 ano)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- CSRF_COOKIE_SECURE, SESSION_COOKIE_SECURE
- SECURE_SSL_REDIRECT
- SECURE_PROXY_SSL_HEADER

### ✅ CSRF em todas as forms
Toda form POST usa {% csrf_token %}. HTMX headers de CSRF no body tag.

### ✅ Sanitização de HTML
Relatórios usam bleach para sanitizar HTML antes de exibir ao usuário.

### ⚠️ NOTA: Credenciais
- NUNCA no repositório — sempre .env + .gitignore
- deploy_vps.py lê de .env local (VPS_HOST, VPS_USER, VPS_PASSWORD, VPS_DOMAIN)
- Produção: .env gerado no VPS pelo deploy script

---

## 💡 Caixa de Sugestões

### ✅ Implementação (v1.1.0, Fev/2026)
Modelo: Suggestion (inspirado no ImprovementRequest do buzzgear/beezle.io).

**Localização:**
- Model: core/models.py → Suggestion (UUID pk, 6 categorias, 3 prioridades, 5 status)
- Form: core/forms.py → SuggestionForm (ModelForm clean)
- View: core/views.py → submit_suggestion() (POST only, @login_required)
- URL: /sugestao/ (name: submit_suggestion)
- Template: Embutida em pages/history.html (card gradient no final da página)
- Link: components/sidebar.html → "Sugerir Melhoria" (ancora #sugestao)
- Admin: core/admin.py → SuggestionAdmin (list_editable para priority/status)

**Workflow de gestão:**
```
Usuário envia sugestão → status=pending
  → Admin revisa no /admin/ → status=reviewed
    → Planejada → status=planned
    → Implementada → status=implemented
    → Recusada → status=declined
```

**Campos internos (invisíveis ao usuário):**
- priority (low/medium/high) — definida pela equipe
- status (pending/reviewed/planned/implemented/declined) — gestão interna
- admin_notes — notas da equipe sobre a sugestão

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
| Jun/2025 | Criação do projeto (scaffolding completo, GPT-4o) |
| Jun/2025 | pypdf adicionado como extrator rápido (cascata pypdf -> Docling) |
| Jun/2025 | Modelo trocado para gpt-4.1-mini (custo/velocidade) |
| Jun/2025 | Hard timeout de 120s implementado (JOEL_TIMEOUT) |
| Jun/2025 | Deploy VPS automatizado via deploy_vps.py (Paramiko SSH) |
| Jun/2025 | SSL Let's Encrypt gerado (askjoel.cloud + www) |
| Jun/2025 | PostgreSQL configurado na produção (askjoel_db) |
| Jun/2025 | Security headers em produção (HSTS, X-Frame-Options, etc) |
| Fev/2026 | Caixa de Sugestões adicionada (model Suggestion + admin gestão) |
| Fev/2026 | Docs atualizados comprehensivamente (v1.1.0) |
