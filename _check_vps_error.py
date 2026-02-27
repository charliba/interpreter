"""Quick script to check analysis #3 error on VPS."""
import paramiko, os
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
print("Connected to VPS")

commands = [
    # 1. Check analysis #3 in DB
    (
        "cd /root/askjoel_project && source venv/bin/activate && "
        'python manage.py shell -c "'
        "from core.models import AnalysisRequest;"
        "a=AnalysisRequest.objects.get(pk=3);"
        "print('STATUS:', a.status);"
        "print('ERROR:', a.error_message);"
        "print('MODE:', a.analysis_mode);"
        "print('DOC:', a.document);"
        "print('OBJECTIVE:', a.user_objective[:200]);"
        '"'
    ),
    # 2. Find logs
    "find /root/askjoel_project -name '*.log' -type f 2>/dev/null; ls -la /root/askjoel_project/logs/ 2>/dev/null || echo NO_LOGS_DIR",
    # 3. Check gunicorn stderr
    "cat /tmp/gunicorn_error.log 2>/dev/null | tail -50 || echo NO_TMP_LOG",
    # 4. Check syslog for python errors  
    "grep -i 'traceback\\|error\\|exception' /var/log/syslog 2>/dev/null | grep -i 'askjoel\\|gunicorn\\|django' | tail -20 || echo NO_SYSLOG",
    # 5. Try checking nohup or daemon output
    "cat /root/nohup.out 2>/dev/null | tail -50 || echo NO_NOHUP",
]

for cmd in commands:
    print(f"\n{'='*60}")
    print(f"CMD: {cmd[:80]}...")
    si, so, se = c.exec_command(cmd, timeout=30)
    out = so.read().decode("utf-8", "ignore").strip()
    err = se.read().decode("utf-8", "ignore").strip()
    if out:
        print(f"OUT:\n{out[-2000:]}")
    if err:
        print(f"ERR:\n{err[-1000:]}")

c.close()
print("\nDone")
