# Joel — Lembrar (Erros e Soluções)

> Documentar TUDO aqui. Cada erro é uma lição.
> Formato: ## N. Título | O que aconteceu | Solução | Regra

---

## Regras Universais (herdadas do ecossistema)

### Da Aeresdev.cloud
0. **UM reverse proxy por VPS** — Nginx é o único. NUNCA instalar Traefik junto.
1. **Todos os registros DNS** → mesmo IP (31.97.171.87)
2. **UM certificado wildcard** por domínio base, OU certificado individual
3. **Configs Nginx** em `/etc/nginx/conf.d/` — um arquivo por domínio
4. **`nginx -t` ANTES** de qualquer reload
5. **Usar `reload`, NUNCA `restart`** para Nginx
6. Documentar tudo localmente — pasta local é fonte de verdade

### Da Beezle.io
7. **NUNCA hardcode credenciais** — sempre `.env` + `os.getenv()` / `process.env`
8. **Deploy SEMPRE via script** — nunca manualmente
9. **Backup ANTES de qualquer migration**
10. **Testar localmente ANTES do deploy**

---

## Informações Rápidas — Joel

| Item | Valor |
|------|-------|
| Porta | 8004 |
| Framework | Django 5.1.5 |
| Python | 3.14.3 (local) / 3.12 (VPS) |
| IA | Agno + GPT-4.1-mini |
| Parsing | pypdf (fast) → Docling (fallback) |
| Busca | Tavily |
| Repo | github.com/charliba/interpreter |
| Branch | main |
| Domínio | askjoel.cloud |
| VPS | 31.97.171.87 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Models | Document, AnalysisRequest, Report, Suggestion |

---

## Lições do Joel

### 1. SSL — Gerar certificado ANTES de configurar HTTPS no Nginx
**Jun/2025** — Sem cert, Nginx servia o cert default da VPS (aresdev.cloud → ERR_CERT_COMMON_NAME_INVALID).
Solução: deploy_vps.py já automatiza: HTTP temp → certbot → HTTPS.

### 2. PostgreSQL — Nunca combinar CREATE DATABASE com outros SQL em -c
**Jun/2025** — `CREATE DATABASE` não roda em transaction block.
Solução: Usar `createdb` como comando separado.

### 3. PostgreSQL — CREATE USER antes de createdb
**Jun/2025** — `createdb -O user db` falha se user não existe ainda.

### 4. Docling — Pesado demais para ser primário
**Jun/2025** — pypdf resolve 90%+ dos PDFs em <3s. Docling com OCR off como fallback com timeout 45s.

### 5. GPT-4.1-mini — Melhor custo/velocidade
**Jun/2025** — Evolução: gpt-4o → gpt-4o-mini → gpt-4.1-mini. Qualidade suficiente para relatórios.

### 6. Suggestion box — Baseado no buzzgear/ImprovementRequest
**Fev/2026** — Model Suggestion com UUID, gestão interna via admin (priority + status + admin_notes).

---

## Referência Rápida de Comandos

| Ação | Comando |
|------|---------|
| Ativar venv | `.\venv\Scripts\Activate.ps1` |
| Rodar servidor | `python manage.py runserver 8004` |
| Migrations | `python manage.py makemigrations; python manage.py migrate` |
| Criar admin | `python manage.py createsuperuser` |
| Testar Joel | `python scripts/test_joel.py` |
| Django check | `python manage.py check` |
| Collectstatic | `python manage.py collectstatic --noinput` |
