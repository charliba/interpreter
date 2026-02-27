"""Diagnose analysis #3 error on VPS."""
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

# Upload a quick diagnostic script
diag_script = r'''
import django, os, sys, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import AnalysisRequest

a = AnalysisRequest.objects.get(pk=3)
print(f"Analysis mode: {a.analysis_mode}")
print(f"Source count: {a.source_count}")
print(f"Include images: {a.include_images}")
print(f"Document ID: {a.document_id}")
print(f"Status: {a.status}")

# Try imports
try:
    from core.joel.agent import run_analysis
    print("agent import OK")
except Exception as e:
    print(f"agent IMPORT ERROR: {e}")
    traceback.print_exc()

try:
    from core.joel.ai_images import generate_report_images
    print("ai_images import OK")
except Exception as e:
    print(f"ai_images IMPORT ERROR: {e}")
    traceback.print_exc()

# Try to extract text (the step that likely failed)
try:
    doc = a.document
    if doc:
        print(f"Document file: {doc.file.name}")
        print(f"Extracted text length: {len(doc.extracted_text)}")
        if not doc.extracted_text:
            print("NO TEXT EXTRACTED - trying extraction...")
            from core.views import _extract_text
            text = _extract_text(doc)
            print(f"Extracted {len(text)} chars")
        else:
            print(f"Text preview: {doc.extracted_text[:200]}")
except Exception as e:
    print(f"EXTRACTION ERROR: {e}")
    traceback.print_exc()

# Try to run the agent (dry run check)
try:
    from core.joel.prompts import get_system_prompt
    prompt = get_system_prompt(
        report_type=a.report_type,
        language=a.language,
        professional_area=a.professional_area,
        include_market_references=a.include_market_references,
        analysis_mode=a.analysis_mode,
        source_count=a.source_count,
        include_images=a.include_images,
    )
    print(f"System prompt generated OK ({len(prompt)} chars)")
except Exception as e:
    print(f"PROMPT ERROR: {e}")
    traceback.print_exc()
'''

# Write script to VPS
sftp = c.open_sftp()
with sftp.open("/root/askjoel_project/_diag.py", "w") as f:
    f.write(diag_script)
sftp.close()

# Run it
cmd = "cd /root/askjoel_project && source venv/bin/activate && python _diag.py 2>&1"
si, so, se = c.exec_command(cmd, timeout=60)
print(so.read().decode("utf-8", "ignore"))
print(se.read().decode("utf-8", "ignore"))

c.close()
