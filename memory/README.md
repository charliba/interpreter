# Memory — Joel

Leia este arquivo no início de cada sessão.

## Projeto
- **Nome:** Joel — Interpretador de Documentos com IA
- **Versão:** 1.1.0
- **Porta:** 8004
- **Domínio:** askjoel.cloud (VPS 31.97.171.87)
- **Repo:** github.com/charliba/interpreter (branch: main)
- **Stack:** Django 5.1.5 + Agno + OpenAI GPT-4.1-mini + pypdf + Docling + Tavily
- **Database:** SQLite (dev) / PostgreSQL askjoel_db (prod)

## Models (4)
- `Document` — arquivo + texto extraído
- `AnalysisRequest` — configuração da análise (7 status)
- `Report` — relatório gerado (1:1 com análise)
- `Suggestion` — sugestões de melhoria dos usuários (UUID pk)

## Docs Importantes
- `docs/BOOTSTRAP.md` — Quick Start
- `docs/REMEMBER_COMPANY.md` — Lições genéricas
- `docs/REMEMBER_PROJECT.md` — Lições do Joel (ERROS SSL, PostgreSQL, deploy)
- `docs/SCHEMA.md` — Diagramas do banco (4 tabelas)
- `docs/ENV.md` — Variáveis de ambiente (incluindo VPS, JOEL_TIMEOUT, DB_*)

## Regras
1. Desenvolver **localmente no venv**, nunca na VPS
2. **Nunca** hardcode credenciais — usar `.env`
3. Git commit antes de deploy
4. Testar localmente antes do deploy
5. Documentar erros em `docs/REMEMBER_PROJECT.md`
6. Deploy automatizado: `python deploy_vps.py`
