# Variáveis de Ambiente — Joel

Este documento descreve todas as variáveis de ambiente utilizadas no projeto.

## Django

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `SECRET_KEY` | ✅ | — | Chave secreta do Django (gerar com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DEBUG` | ❌ | `True` | Modo debug (`True`/`False`) |
| `ALLOWED_HOSTS` | ❌ | `localhost,127.0.0.1` | Hosts permitidos (separados por vírgula) |

## Banco de Dados

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `DATABASE_URL` | ❌ | SQLite local | URL do banco PostgreSQL para produção |

## OpenAI (Joel Agent)

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `OPENAI_API_KEY` | ✅ | — | API key da OpenAI |
| `OPENAI_MODEL` | ❌ | `gpt-4o` | Modelo para o agente Joel |

## Tavily (Busca na Internet)

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `TAVILY_API_KEY` | ❌* | — | API key do Tavily. *Necessário se "incluir referências de mercado" estiver ativado |

## Joel (Configuração do Agente)

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `JOEL_DEFAULT_LANGUAGE` | ❌ | `pt-BR` | Idioma padrão (`pt-BR`, `en`, `es`) |
| `JOEL_MAX_SEARCH_RESULTS` | ❌ | `10` | Número máximo de resultados Tavily |
| `JOEL_SEARCH_DEPTH` | ❌ | `advanced` | Profundidade de busca (`basic`/`advanced`) |

## Celery / Redis (futuro)

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `CELERY_BROKER_URL` | ❌ | — | URL do broker Redis |
| `CELERY_RESULT_BACKEND` | ❌ | — | URL do result backend |

## VPS / Deploy (futuro)

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `VPS_HOST` | ❌ | — | IP/hostname do VPS |
| `VPS_USER` | ❌ | — | Usuário SSH |
| `VPS_SSH_KEY_PATH` | ❌ | — | Caminho da chave SSH |

## Arquivo de Referência

Copie `.env.example` para `.env` e preencha os valores:

```bash
cp .env.example .env
```
