"""Reproduce analysis #3 error step by step on VPS."""
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

diag = r'''
import django, os, sys, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import AnalysisRequest

a = AnalysisRequest.objects.get(pk=3)
doc = a.document
text = doc.extracted_text

print(f"=== Step 1: Text extraction OK ({len(text)} chars) ===")

# Step 2: Run analysis
print("=== Step 2: Running analysis... ===")
try:
    from core.joel.agent import run_analysis
    result = run_analysis(
        extracted_text=text[:6000],
        user_objective=a.user_objective,
        professional_area=a.professional_area,
        professional_area_detail=a.professional_area_detail,
        geolocation=a.geolocation,
        language=a.language,
        include_market_references=a.include_market_references,
        search_scope=a.search_scope,
        report_type=a.report_type,
        analysis_mode=a.analysis_mode,
        source_count=a.source_count,
        include_images=a.include_images,
    )
    md = result.get("content_markdown", "")
    refs = result.get("references", [])
    print(f"Analysis OK: {len(md)} chars markdown, {len(refs)} refs")
    
    if not md:
        print("WARNING: Empty markdown content!")
        print(f"Full result keys: {result.keys()}")
        print(f"Result: {str(result)[:500]}")
    
except Exception as e:
    print(f"ANALYSIS ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Charts
print("=== Step 3: Charts ===")
try:
    from core.joel.charts import generate_charts_from_markdown
    charts = generate_charts_from_markdown(md, max_charts=4)
    print(f"Charts: {len(charts)}")
except Exception as e:
    print(f"CHARTS ERROR: {e}")
    traceback.print_exc()

# Step 4: AI Images
print("=== Step 4: AI Images ===")
if a.include_images:
    try:
        from core.joel.ai_images import generate_report_images
        imgs = generate_report_images(
            content_markdown=md,
            professional_area=a.professional_area,
            analysis_mode=a.analysis_mode,
            max_images=2,
        )
        print(f"Images: {len(imgs)}")
    except Exception as e:
        print(f"IMAGES ERROR: {e}")
        traceback.print_exc()
else:
    print("Skipped (include_images=False)")

# Step 5: Report generation
print("=== Step 5: Report generation ===")
try:
    from core.joel.report_generator import markdown_to_html, generate_pdf
    html = markdown_to_html(md)
    print(f"HTML OK: {len(html)} chars")
except Exception as e:
    print(f"REPORT ERROR: {e}")
    traceback.print_exc()

print("=== ALL STEPS COMPLETE ===")
'''

sftp = c.open_sftp()
with sftp.open("/root/askjoel_project/_repro.py", "w") as f:
    f.write(diag)
sftp.close()

cmd = "cd /root/askjoel_project && source venv/bin/activate && timeout 180 python _repro.py 2>&1"
si, so, se = c.exec_command(cmd, timeout=200)
print(so.read().decode("utf-8", "ignore"))
err = se.read().decode("utf-8", "ignore")
if err:
    print("STDERR:", err[-2000:])

c.close()
