"""Deploy supercharged Joel to VPS."""
import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('31.97.171.87', username='root', password=os.getenv('VPS_PASSWORD'), timeout=30)

cmds = [
    'cd /root/askjoel_project && git pull origin main 2>&1',
    'cd /root/askjoel_project && source venv/bin/activate && pip install ddgs newspaper4k lxml_html_clean beautifulsoup4 arxiv yfinance --quiet 2>&1 | tail -10',
    'pkill -f "gunicorn config.wsgi" || true',
    'sleep 2',
    'cd /root/askjoel_project && source venv/bin/activate && gunicorn config.wsgi:application --bind 0.0.0.0:8004 --workers 3 --timeout 300 --daemon && echo GUNICORN_STARTED',
    'sleep 2',
    'ps aux | grep gunicorn | grep -v grep | wc -l',
    'curl -s -o /dev/null -w "%{http_code}" https://askjoel.cloud/',
]

for cmd in cmds:
    print(f'\n>>> {cmd[:70]}...')
    si, so, se = c.exec_command(cmd, timeout=120)
    out = so.read().decode('utf-8', 'ignore').strip()
    err = se.read().decode('utf-8', 'ignore').strip()
    if out:
        print(out[-600:])
    if err:
        print(f'STDERR: {err[-400:]}')

c.close()
print('\n=== DEPLOY COMPLETE ===')
