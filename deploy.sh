#!/bin/bash
# =============================================================================
# Deploy askjoel.cloud — VPS Hostinger (2.57.91.91)
# Execute no VPS como root: bash deploy.sh
#
# Portas em uso:
#   8001 = buzzgear (beezle.io)
#   8002 = aresdev.cloud
#   8003 = waLink (walinkhub.cloud)
#   8004 = Joel (askjoel.cloud)  ← ESTE PROJETO
# =============================================================================

set -e  # Para ao primeiro erro

PROJECT_DIR="/root/askjoel_project"
REPO_URL="https://github.com/charliba/interpreter.git"
BRANCH="main"
DOMAIN="askjoel.cloud"
DB_NAME="askjoel_db"
DB_USER="askjoel_user"

echo "================================================"
echo "  Deploy askjoel.cloud"
echo "================================================"

# --------------------------------------------------
# 1. Clonar repositório (ou atualizar)
# --------------------------------------------------
echo ""
echo "[1/8] Repositório..."
if [ -d "$PROJECT_DIR" ]; then
    echo "  → Atualizando..."
    cd "$PROJECT_DIR"
    git fetch origin
    git reset --hard origin/$BRANCH
else
    echo "  → Clonando..."
    git clone -b $BRANCH $REPO_URL "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# --------------------------------------------------
# 2. Python venv + dependências
# --------------------------------------------------
echo ""
echo "[2/8] Python venv + dependências..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# --------------------------------------------------
# 3. .env de produção
# --------------------------------------------------
echo ""
echo "[3/8] Verificando .env..."
if [ ! -f ".env" ]; then
    echo "  ⚠️  ATENÇÃO: Copie .env.production para .env e preencha as chaves!"
    echo "  cp .env.production .env"
    echo "  nano .env"
    echo ""
    echo "  Depois execute este script novamente."
    exit 1
fi
echo "  → .env encontrado ✓"

# --------------------------------------------------
# 4. PostgreSQL
# --------------------------------------------------
echo ""
echo "[4/8] PostgreSQL..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "  → Database '$DB_NAME' já existe ✓"
else
    echo "  → Criando database e user..."
    DB_PASS=$(grep DB_PASSWORD .env | cut -d= -f2)
    sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    echo "  → Database criado ✓"
fi

# --------------------------------------------------
# 5. Django setup
# --------------------------------------------------
echo ""
echo "[5/8] Django migrate + collectstatic..."
mkdir -p logs media
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Criar superuser se não existe
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@askjoel.cloud', 'TROCAR_SENHA')
    print('  → Superuser admin criado (TROCAR SENHA!)')
else:
    print('  → Superuser já existe ✓')
"

# --------------------------------------------------
# 6. Systemd service
# --------------------------------------------------
echo ""
echo "[6/8] Systemd service..."
cp config/systemd/askjoel.service /etc/systemd/system/askjoel.service
systemctl daemon-reload
systemctl enable askjoel
systemctl restart askjoel
echo "  → askjoel.service ativo ✓"
sleep 2
systemctl status askjoel --no-pager -l | head -15

# --------------------------------------------------
# 7. Nginx
# --------------------------------------------------
echo ""
echo "[7/8] Nginx..."
cp config/nginx/askjoel.cloud.conf /etc/nginx/conf.d/askjoel.conf
nginx -t
systemctl reload nginx
echo "  → Nginx recarregado ✓"

# --------------------------------------------------
# 8. SSL (Let's Encrypt)
# --------------------------------------------------
echo ""
echo "[8/8] SSL..."
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "  → Certificado SSL já existe ✓"
else
    echo "  → Gerando certificado SSL..."
    mkdir -p /var/www/certbot
    certbot certonly --webroot -w /var/www/certbot \
        -d $DOMAIN -d www.$DOMAIN \
        --non-interactive --agree-tos \
        --email admin@askjoel.cloud
    systemctl reload nginx
    echo "  → SSL gerado ✓"
fi

echo ""
echo "================================================"
echo "  ✅ Deploy concluído!"
echo ""
echo "  Site:    https://$DOMAIN"
echo "  Admin:   https://$DOMAIN/admin/"
echo "  Status:  systemctl status askjoel"
echo "  Logs:    journalctl -u askjoel -f"
echo "================================================"
