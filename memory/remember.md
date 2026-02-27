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
| Python | 3.14.3 |
| IA | Agno + GPT-4o |
| Parsing | Docling |
| Busca | Tavily |
| Repo | github.com/charliba/interpreter |
| Branch | main |

---

## Lições do Joel

*Nenhuma entrada ainda — projeto recém-criado.*

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
