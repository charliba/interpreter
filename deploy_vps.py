#!/usr/bin/env python3
"""
Deploy askjoel.cloud — VPS Hostinger (31.97.171.87)
Baseado no padrão buzzgear/deploy.py

Etapas:
1. Conectar via SSH
2. Clonar/atualizar repositório
3. Python venv + dependências
4. .env de produção
5. PostgreSQL
6. Django migrate + collectstatic
7. Gunicorn (systemd)
8. Nginx (temporário HTTP → certbot → HTTPS completo)
9. SSL (Let's Encrypt)
10. Verificação final
"""

import paramiko
import os
import sys
import time
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

load_dotenv()

# === Configuração (lido do .env) ===
VPS_HOST = os.getenv("VPS_HOST", "31.97.171.87")
VPS_USER = os.getenv("VPS_USER", "root")
VPS_PASSWORD = os.getenv("VPS_PASSWORD", "")

PROJECT_DIR = os.getenv("VPS_PROJECT_PATH", "/root/askjoel_project")
REPO_URL = os.getenv("GITHUB_CLONE_URL", "https://github.com/charliba/interpreter.git")
BRANCH = os.getenv("GITHUB_BRANCH", "main")
DOMAIN = os.getenv("VPS_DOMAIN", "askjoel.cloud")
DB_NAME = "askjoel_db"
DB_USER = "askjoel_user"
DB_PASSWORD = None  # Será gerado automaticamente

# Chaves que precisamos copiar do .env local
LOCAL_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def run(client, cmd, timeout=60):
    """Executa comando SSH com timeout."""
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore").strip()
        err = stderr.read().decode("utf-8", errors="ignore").strip()
        return out, err
    except Exception as e:
        return "", str(e)


def step(num, total, msg):
    print(f"\n[{num}/{total}] {msg}")
    sys.stdout.flush()


def main():
    total_steps = 10

    print("=" * 60)
    print("  DEPLOY ASKJOEL.CLOUD")
    print("  VPS: 31.97.171.87 | Porta: 8004")
    print("=" * 60)
    sys.stdout.flush()

    # ── 1. Conectar ──
    step(1, total_steps, "Conectando via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
    except Exception as e:
        print(f"  ERRO: {e}")
        return
    print("  OK — conectado")
    sys.stdout.flush()

    # ── 2. Clonar/Atualizar repositório ──
    step(2, total_steps, "Repositório...")
    out, _ = run(client, f"test -d {PROJECT_DIR}/.git && echo 'exists'")
    if "exists" in out:
        print("  → Atualizando...")
        out, err = run(client, f"cd {PROJECT_DIR} && git fetch origin && git reset --hard origin/{BRANCH} 2>&1")
        print(f"  {out[-200:]}" if out else f"  {err[-200:]}")
    else:
        print("  → Clonando...")
        out, err = run(client, f"git clone -b {BRANCH} {REPO_URL} {PROJECT_DIR} 2>&1", timeout=120)
        print(f"  {out[-200:]}" if out else f"  {err[-200:]}")
    sys.stdout.flush()

    # ── 3. Python venv + dependências ──
    step(3, total_steps, "Python venv + dependências...")
    out, _ = run(client, f"test -d {PROJECT_DIR}/venv && echo 'exists'")
    if "exists" not in out:
        print("  → Criando venv...")
        run(client, f"python3 -m venv {PROJECT_DIR}/venv", timeout=60)

    print("  → Instalando dependências (pode demorar ~2min)...")
    sys.stdout.flush()
    out, err = run(
        client,
        f"cd {PROJECT_DIR} && source venv/bin/activate && "
        f"pip install --upgrade pip && "
        f"pip install -r requirements.txt gunicorn 2>&1 | tail -5",
        timeout=600,
    )
    print(f"  {out}" if out else "  OK")
    sys.stdout.flush()

    # ── 4. .env de produção ──
    step(4, total_steps, "Configurando .env de produção...")

    # Ler OPENAI_API_KEY do .env local
    openai_key = ""
    if os.path.exists(LOCAL_ENV):
        with open(LOCAL_ENV) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    openai_key = line.strip().split("=", 1)[1]

    # Gerar SECRET_KEY e DB_PASSWORD no servidor
    out_secret, _ = run(client, "python3 -c \"import secrets; print(secrets.token_urlsafe(50))\"")
    secret_key = out_secret.strip()

    out_dbpass, _ = run(client, "python3 -c \"import secrets; print(secrets.token_urlsafe(24))\"")
    global DB_PASSWORD
    DB_PASSWORD = out_dbpass.strip()

    env_content = f"""# =============================================================================
# ASKJOEL.CLOUD — Joel Agent — PRODUÇÃO
# =============================================================================

# === DJANGO ===
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS=askjoel.cloud,www.askjoel.cloud

# === DATABASE (PostgreSQL) ===
DB_ENGINE=postgresql
DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASSWORD={DB_PASSWORD}
DB_HOST=localhost
DB_PORT=5432

# === OPENAI ===
OPENAI_API_KEY={openai_key}
OPENAI_MODEL=gpt-4.1-mini

# === TAVILY ===
TAVILY_API_KEY=

# === JOEL AGENT ===
JOEL_TIMEOUT=120
JOEL_DEFAULT_LANGUAGE=pt-BR
JOEL_MAX_SEARCH_RESULTS=10
JOEL_SEARCH_DEPTH=advanced
"""

    # Verificar se já tem .env (não sobrescrever se existir)
    out, _ = run(client, f"test -f {PROJECT_DIR}/.env && echo 'exists'")
    if "exists" in out:
        print("  → .env já existe — atualizando OPENAI_API_KEY apenas...")
        if openai_key:
            run(client, f"sed -i 's|^OPENAI_API_KEY=.*|OPENAI_API_KEY={openai_key}|' {PROJECT_DIR}/.env")
    else:
        print("  → Criando .env de produção...")
        # Escapar para bash
        escaped = env_content.replace("'", "'\\''")
        run(client, f"cat > {PROJECT_DIR}/.env << 'ENVEOF'\n{env_content}\nENVEOF")
    print("  OK")
    sys.stdout.flush()

    # ── 5. PostgreSQL ──
    step(5, total_steps, "PostgreSQL...")
    out, _ = run(client, f"sudo -u postgres psql -lqt 2>/dev/null | grep {DB_NAME} | wc -l")
    if out.strip() and int(out.strip()) > 0:
        print(f"  → Database '{DB_NAME}' já existe ✓")
    else:
        print(f"  → Criando database '{DB_NAME}'...")
        # Ler a senha atual do .env no servidor
        db_pass_out, _ = run(client, f"grep -oP '(?<=DB_PASSWORD=).*' {PROJECT_DIR}/.env")
        db_pass = db_pass_out.strip() or DB_PASSWORD

        sql = (
            f"CREATE USER {DB_USER} WITH PASSWORD '{db_pass}';"
            f"CREATE DATABASE {DB_NAME} OWNER {DB_USER};"
            f"ALTER ROLE {DB_USER} SET client_encoding TO 'utf8';"
            f"ALTER ROLE {DB_USER} SET default_transaction_isolation TO 'read committed';"
            f"ALTER ROLE {DB_USER} SET timezone TO 'America/Sao_Paulo';"
            f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};"
        )
        out, err = run(client, f'sudo -u postgres psql -c "{sql}" 2>&1')
        if "already exists" in (out + err):
            print("  → User/DB já existiam, OK")
        else:
            print(f"  {out[:200]}" if out else "  OK")
    sys.stdout.flush()

    # ── 6. Django migrate + collectstatic ──
    step(6, total_steps, "Django migrate + collectstatic...")
    run(client, f"mkdir -p {PROJECT_DIR}/logs {PROJECT_DIR}/media")

    out, err = run(
        client,
        f"cd {PROJECT_DIR} && source venv/bin/activate && python manage.py migrate --noinput 2>&1 | tail -10",
        timeout=120,
    )
    print(f"  migrate: {out[-300:]}" if out else f"  migrate: {err[-200:]}")

    out, _ = run(
        client,
        f"cd {PROJECT_DIR} && source venv/bin/activate && python manage.py collectstatic --noinput 2>&1 | tail -3",
        timeout=60,
    )
    print(f"  static: {out}" if out else "  static: OK")

    # Criar superuser
    out, _ = run(
        client,
        f"cd {PROJECT_DIR} && source venv/bin/activate && python manage.py shell -c \""
        f"from django.contrib.auth import get_user_model; User = get_user_model(); "
        f"print('exists' if User.objects.filter(is_superuser=True).exists() else 'none')\" 2>&1",
    )
    if "none" in out:
        run(
            client,
            f"cd {PROJECT_DIR} && source venv/bin/activate && "
            f"DJANGO_SUPERUSER_PASSWORD=AskJoel2026! python manage.py createsuperuser "
            f"--username admin --email admin@askjoel.cloud --noinput 2>&1",
        )
        print("  superuser: admin / AskJoel2026! (TROCAR!)")
    else:
        print("  superuser: já existe ✓")
    sys.stdout.flush()

    # ── 7. Gunicorn (systemd) ──
    step(7, total_steps, "Gunicorn (systemd)...")

    # Copiar service file
    run(client, f"cp {PROJECT_DIR}/config/systemd/askjoel.service /etc/systemd/system/askjoel.service")
    run(client, "systemctl daemon-reload")
    run(client, "systemctl enable askjoel 2>&1")
    run(client, "systemctl restart askjoel 2>&1")
    time.sleep(3)

    out, _ = run(client, "systemctl is-active askjoel")
    if "active" in out:
        print(f"  → askjoel.service: {out} ✓")
    else:
        print(f"  → askjoel.service: {out} ⚠")
        # Fallback: gunicorn manual
        print("  → Tentando gunicorn manual...")
        run(client, "pkill -f 'gunicorn.*config.wsgi.*8004' 2>/dev/null")
        time.sleep(1)
        run(
            client,
            f"cd {PROJECT_DIR} && source venv/bin/activate && "
            f"gunicorn config.wsgi:application --bind=127.0.0.1:8004 --workers=2 --threads=4 --timeout=180 --daemon "
            f"--access-logfile {PROJECT_DIR}/logs/access.log "
            f"--error-logfile {PROJECT_DIR}/logs/error.log",
        )
        time.sleep(3)

    # Verificar porta
    out, _ = run(client, "ss -tlnp | grep 8004")
    if "8004" in out:
        print("  → Porta 8004: OK ✓")
    else:
        print("  → Porta 8004: NÃO ATIVA ⚠")
        out2, _ = run(client, f"tail -20 {PROJECT_DIR}/logs/error.log 2>/dev/null")
        print(f"  Log: {out2[-300:]}")
    sys.stdout.flush()

    # ── 8. Nginx (temporário HTTP) ──
    step(8, total_steps, "Nginx (configurando HTTP temporário para certbot)...")

    # Primeiro: config HTTP only (sem SSL) para o certbot poder validar
    nginx_tmp = f"""upstream askjoel_app {{
    server 127.0.0.1:8004;
}}

server {{
    listen 80;
    server_name {DOMAIN} www.{DOMAIN};

    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}

    location /static/ {{
        alias {PROJECT_DIR}/staticfiles/;
        expires 30d;
    }}

    location /media/ {{
        alias {PROJECT_DIR}/media/;
        expires 7d;
    }}

    location / {{
        proxy_pass http://askjoel_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180;
        client_max_body_size 50M;
    }}
}}"""

    # Escapar e criar o arquivo
    run(client, f"cat > /etc/nginx/conf.d/askjoel.conf << 'NGINXEOF'\n{nginx_tmp}\nNGINXEOF")

    out, err = run(client, "nginx -t 2>&1")
    combined = f"{out} {err}"
    if "successful" in combined:
        run(client, "systemctl reload nginx")
        print("  → Nginx HTTP temporário: OK ✓")
    else:
        print(f"  → Nginx test FALHOU: {combined[:200]}")
    sys.stdout.flush()

    # Testar HTTP
    out, _ = run(client, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:8004/")
    print(f"  → Teste local (gunicorn): HTTP {out}")
    out, _ = run(client, f"curl -s -o /dev/null -w '%{{http_code}}' http://{DOMAIN}/")
    print(f"  → Teste HTTP externo: HTTP {out}")
    sys.stdout.flush()

    # ── 9. SSL (Let's Encrypt) ──
    step(9, total_steps, "SSL (Let's Encrypt)...")
    out, _ = run(client, f"test -f /etc/letsencrypt/live/{DOMAIN}/fullchain.pem && echo 'exists'")

    if "exists" in out:
        print("  → Certificado já existe ✓")
    else:
        print("  → Gerando certificado...")
        run(client, "mkdir -p /var/www/certbot")

        # Certbot certonly (webroot)
        out, err = run(
            client,
            f"certbot certonly --webroot -w /var/www/certbot "
            f"-d {DOMAIN} -d www.{DOMAIN} "
            f"--non-interactive --agree-tos "
            f"--email admin@{DOMAIN} 2>&1",
            timeout=120,
        )
        combined = f"{out}\n{err}"
        if "Successfully" in combined or "Congratulations" in combined:
            print("  → Certificado gerado ✓")
        else:
            print(f"  → Certbot output: {combined[-400:]}")
    sys.stdout.flush()

    # Instalar nginx HTTPS completo
    out, _ = run(client, f"test -f /etc/letsencrypt/live/{DOMAIN}/fullchain.pem && echo 'exists'")
    if "exists" in out:
        print("  → Instalando Nginx HTTPS completo...")
        run(client, f"cp {PROJECT_DIR}/config/nginx/askjoel.cloud.conf /etc/nginx/conf.d/askjoel.conf")
        out, err = run(client, "nginx -t 2>&1")
        combined = f"{out} {err}"
        if "successful" in combined:
            run(client, "systemctl reload nginx")
            print("  → Nginx HTTPS: OK ✓")
        else:
            print(f"  → Nginx HTTPS test FALHOU: {combined[:200]}")
            # Reverter para HTTP
            run(client, f"cat > /etc/nginx/conf.d/askjoel.conf << 'NGINXEOF'\n{nginx_tmp}\nNGINXEOF")
            run(client, "systemctl reload nginx")
            print("  → Revertido para HTTP")
    else:
        print("  → SSL não gerado — site funcionará em HTTP apenas ⚠")
    sys.stdout.flush()

    # ── 10. Verificação final ──
    step(10, total_steps, "Verificação final...")

    # Gunicorn
    out, _ = run(client, "ps aux | grep 'gunicorn.*config.wsgi' | grep -v grep | wc -l")
    print(f"  → Processos Gunicorn: {out}")

    # Porta
    out, _ = run(client, "ss -tlnp | grep 8004 | head -1")
    print(f"  → Porta 8004: {'OK ✓' if '8004' in out else 'NÃO ⚠'}")

    # HTTP local
    out, _ = run(client, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/")
    print(f"  → Gunicorn local: HTTP {out}")

    # HTTPS externo
    out, _ = run(client, f"curl -sk -o /dev/null -w '%{{http_code}}' https://{DOMAIN}/")
    print(f"  → HTTPS externo: HTTP {out}")

    # SSL info
    out, _ = run(client, f"certbot certificates 2>&1 | grep -A3 'askjoel'")
    if out:
        print(f"  → SSL: {out[:200]}")
    sys.stdout.flush()

    client.close()

    print("\n" + "=" * 60)
    print("  DEPLOY CONCLUÍDO!")
    print(f"  Site: https://{DOMAIN}")
    print(f"  Admin: https://{DOMAIN}/admin/")
    print("  Credenciais: admin / AskJoel2026! (TROCAR!)")
    print(f"  Logs: ssh root@{VPS_HOST} journalctl -u askjoel -f")
    print("=" * 60)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
