"""Deploy + reset analysis #3 on VPS."""
import paramiko, os, time
from dotenv import load_dotenv
load_dotenv()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    os.getenv("VPS_HOST", "31.97.171.87"),
    username=os.getenv("VPS_USER", "root"),
    password=os.getenv("VPS_PASSWORD", ""),
    timeout=30,
)
print("Connected")

def run(cmd, t=60):
    si, so, se = c.exec_command(cmd, timeout=t)
    return so.read().decode("utf-8", "ignore").strip(), se.read().decode("utf-8", "ignore").strip()

# 1. Git pull
print("1. Git pull...")
o, e = run("cd /root/askjoel_project && git fetch origin && git reset --hard origin/main 2>&1")
print(o[-200:])

# 2. Restart gunicorn
print("2. Restart gunicorn...")
run("pkill -f gunicorn")
time.sleep(2)
o, e = run(
    "cd /root/askjoel_project && source venv/bin/activate && "
    "gunicorn config.wsgi:application --bind 0.0.0.0:8004 --workers 3 --timeout 300 --daemon 2>&1"
)
print(o or "Restarted")
time.sleep(3)

# 3. Reset analysis #3
print("3. Reset analysis #3...")
reset_script = """
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from core.models import AnalysisRequest
a = AnalysisRequest.objects.get(pk=3)
print(f"Before: status={a.status}, error={a.error_message[:80]}")
a.status = "pending"
a.error_message = ""
a.processing_log = ""
a.started_at = None
a.completed_at = None
a.save()
print(f"After: status={a.status} — RESET OK")
"""
sftp = c.open_sftp()
with sftp.open("/root/askjoel_project/_reset.py", "w") as f:
    f.write(reset_script)
sftp.close()
o, e = run("cd /root/askjoel_project && source venv/bin/activate && python _reset.py 2>&1")
print(o)

# 4. Verify
print("4. Verify...")
o, e = run("pgrep -c gunicorn")
print(f"Gunicorn workers: {o}")

c.close()
print("DONE")
