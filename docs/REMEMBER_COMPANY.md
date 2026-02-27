# 🧠 REMEMBER_COMPANY.md - Lessons Learned (Genéricos)

> **⚠️ AGENTE IA:** Este documento contém lições aprendidas **REUTILIZÁVEIS** entre projetos.
> Consulte **ANTES** de resolver qualquer problema.
> Após resolver um problema novo **GENÉRICO**, adicione aqui.

---

## 🔴 REGRA FUNDAMENTAL - WORKFLOW DE DESENVOLVIMENTO

```
┌─────────────────┐     git push     ┌─────────────┐    deploy.py    ┌─────────────┐
│  LOCAL (venv)   │ ───────────────► │   GitHub    │ ───────────────► │  VPS (prod) │
└─────────────────┘                  └─────────────┘                  └─────────────┘
```

### OBRIGATÓRIO:
1. **SEMPRE desenvolver localmente** dentro do `venv`
2. **NUNCA editar código diretamente na VPS**
3. **SEMPRE commitar no GitHub antes de deploy**
4. **SEMPRE usar `python deploy.py`** para deploy

### Ativar venv (Windows):
```powershell
cd "interpretador de documentos"
.\venv\Scripts\Activate.ps1
```

### Ativar venv (Linux/Mac):
```bash
cd "interpretador de documentos"
source venv/bin/activate
```

---

## 📋 Índice

1. [Segurança](#-segurança)
2. [Git e Versionamento](#-git-e-versionamento)
3. [Deploy Genérico](#-deploy-genérico)
4. [Django - Boas Práticas](#-django---boas-práticas)
5. [Frontend - Padrões](#-frontend---padrões)
6. [APIs - Padrões](#-apis---padrões)

---

## 🔒 Segurança

### ❌ ERRO: Credenciais expostas no repositório
**Solução:**
```python
from dotenv import load_dotenv
import os
load_dotenv()
PASSWORD = os.getenv("PASSWORD", "")
```

**Prevenção:**
- NUNCA colocar senhas em código
- Sempre usar variáveis de ambiente
- Usar `.env.example` como template

---

### ❌ ERRO: XSS em campo de texto
**Solução:**
```python
# No template - NUNCA use |safe em input do usuário
{{ campo }}  # Auto-escaped
```

---

## 🔀 Git e Versionamento

### ✅ Convenção de Commits
```bash
feat:     Nova funcionalidade
fix:      Correção de bug
docs:     Documentação
style:    Formatação
refactor: Refatoração
test:     Testes
chore:    Manutenção
security: Correção de segurança
```

---

## 🚀 Deploy Genérico

### ❌ ERRO: SSH trava pedindo senha
**Solução:** Usar Paramiko:
```python
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password)
```

### ❌ ERRO: 502 Bad Gateway
**Causa:** Backend (Gunicorn) não está rodando.
```bash
ps aux | grep gunicorn
pkill -9 -f gunicorn
gunicorn config.wsgi:application --bind=127.0.0.1:PORT --daemon
```

### ❌ ERRO: Static files não carregam
```bash
python manage.py collectstatic --noinput
```

---

## 🐍 Django - Boas Práticas

### ✅ Sempre usar get_or_create
```python
obj, created = Model.objects.get_or_create(email=email, defaults={'name': name})
```

### ✅ Sempre usar select_related
```python
items = Item.objects.select_related('category', 'owner').all()
```

### ✅ CSRF obrigatório
```html
<form method="post">{% csrf_token %}{{ form.as_p }}<button type="submit">Enviar</button></form>
```

---

## 🎨 Frontend - Padrões

### ✅ Sidebar fixa + Conteúdo flexível
```css
.sidebar { position: fixed; width: 250px; height: 100vh; }
.main-content { margin-left: 250px; flex: 1; }
```

---

## 🔌 APIs - Padrões

### ✅ Sempre retornar JSON
```python
from django.http import JsonResponse
def my_api(request):
    try:
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
```

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

*Documento genérico - Reutilizável entre projetos*
