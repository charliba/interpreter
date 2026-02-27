"""Quick VPS debug script."""
import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('31.97.171.87', username='root', password=os.getenv('VPS_PASSWORD'), timeout=30)

cmds = [
    'find /root/askjoel_project -name "*.log" -type f 2>/dev/null',
    'ls -la /root/askjoel_project/nohup.out 2>/dev/null; echo "---"',
    'tail -100 /root/askjoel_project/nohup.out 2>/dev/null || echo "no nohup"',
    # Get processing_log from latest analysis
    """cd /root/askjoel_project && source venv/bin/activate && python -c "
import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
import django; django.setup()
from core.models import AnalysisRequest
for a in AnalysisRequest.objects.order_by('-pk')[:3]:
    print(f'=== Analysis #{a.pk}: status={a.status}, error={a.error_message[:200] if a.error_message else None}')
    if a.processing_log:
        print(a.processing_log[-1500:])
    print()
" 2>&1""",
]

for cmd in cmds:
    print(f'\n>>> {cmd[:80]}...')
    si, so, se = c.exec_command(cmd, timeout=30)
    out = so.read().decode('utf-8', 'ignore').strip()
    err = se.read().decode('utf-8', 'ignore').strip()
    if out:
        print(out[-3000:])
    if err:
        print(f'STDERR: {err[-500:]}')

c.close()
