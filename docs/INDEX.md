# Joel — Índice de Documentação

> Interpretador Inteligente de Documentos v1.0.0
> Django 5.1.5 + Agno + OpenAI GPT-4o + Docling + Tavily
> Porta: 8004 | Localhost (dev)
> Repo: https://github.com/charliba/interpreter.git

## Documentos

| Arquivo | Descrição |
|---------|-----------|
| [README.md](README.md) | Referência completa do projeto |
| [ENV.md](ENV.md) | Variáveis de ambiente (.env) |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Explicação de cada pacote |
| [SCHEMA.md](SCHEMA.md) | Diagrama ER dos models |
| [REMEMBER_COMPANY.md](REMEMBER_COMPANY.md) | Lições genéricas (reusável entre projetos) |
| [REMEMBER_PROJECT.md](REMEMBER_PROJECT.md) | Lições específicas do Joel |
| [BOOTSTRAP.md](BOOTSTRAP.md) | Template para criar novos projetos |

## Onde Encontrar o Quê

| Eu quero... | Veja... |
|-------------|---------|
| Rodar o projeto local | [../README.md](../README.md) Quick Start |
| Entender as variáveis .env | [ENV.md](ENV.md) |
| Ver todos os pacotes | [REQUIREMENTS.md](REQUIREMENTS.md) |
| Ver o schema do banco | [SCHEMA.md](SCHEMA.md) |
| Relembrar erros resolvidos | [REMEMBER_PROJECT.md](REMEMBER_PROJECT.md) |
| Regras genéricas de projeto | [REMEMBER_COMPANY.md](REMEMBER_COMPANY.md) |
| Criar um projeto novo | [BOOTSTRAP.md](BOOTSTRAP.md) |

## Apps Django

| App | Função |
|-----|--------|
| `config/` | Settings, URLs, WSGI |
| `accounts/` | Login, registro, logout |
| `core/` | Upload, análise, Joel agent, relatórios, histórico |

## Agente Joel

Joel é o agente de IA intermediário. Ele:
1. Recebe o documento parseado pelo Docling
2. Entende o objetivo do usuário
3. Formula buscas inteligentes no Tavily
4. Gera relatório profissional com referências

Módulo: `core/joel/` (agent.py, tools.py, prompts.py, report_generator.py)
