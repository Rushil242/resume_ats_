"""
Manual test script — run this to verify the full pipeline works.
Usage:
    python test_manual.py --resume path/to/resume.pdf --jd path/to/jd.txt
    python test_manual.py --resume path/to/resume.pdf --jd "Software Engineer at Google..."
"""
import argparse
import json
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from app.pdf_parser import extract_text, pdf_first_page_to_image
from app.resume_service import analyze_resume, tailor_resume

def main():
    parser = argparse.ArgumentParser(description="ResumeATS manual test")
    parser.add_argument("--resume", required=True, help="Path to resume PDF")
    parser.add_argument("--jd", required=True, help="Path to JD file OR JD text string")
    parser.add_argument("--screenshot", default=None, help="Path to resume screenshot (optional)")
    args = parser.parse_args()

    if not os.path.exists(args.resume):
        print(f"❌ Resume file not found: {args.resume}")
        sys.exit(1)

    # Load screenshot
    image_bytes = b""
    if args.screenshot and os.path.exists(args.screenshot):
        with open(args.screenshot,"rb") as f:
            image_bytes = f.read()
        print(f"📸 Using screenshot: {args.screenshot}")

    # Load JD
    if os.path.exists(args.jd):
        if args.jd.endswith(".pdf"):
            jd_text = extract_text(args.jd)
        else:
            with open(args.jd) as f:
                jd_text = f.read()
    else:
        jd_text = args.jd  # treat as raw text

    print("\n🔍 Step 1: Analyzing resume...")
    result = analyze_resume(args.resume, image_bytes=image_bytes)
    resume_id = result["resume_id"]

    print(f"  ✅ Resume ID: {resume_id}")
    print(f"  📄 Sections found: {[s['id'] for s in result['content']['sections']]}")
    print(f"  🎨 Style: {result['style'].get('raw_description','')[:120]}...")
    if result.get("roundtrip_pdf_url"):
        print(f"  📥 Round-trip PDF: output/{resume_id}.pdf")

    print("\n🎯 Step 2: Tailoring to job description...")
    tailor = tailor_resume(resume_id, jd_text)

    print(f"  📊 ATS Score: {tailor['original_ats_score']}% → {tailor['tailored_ats_score']}%")
    print(f"  ✅ Matched keywords ({len(tailor['matched_keywords'])}): {tailor['matched_keywords'][:10]}")
    print(f"  ⚠️  Still missing ({len(tailor['missing_keywords'])}): {tailor['missing_keywords'][:10]}")
    if tailor.get("tailored_pdf_url"):
        print(f"  📥 Tailored PDF: output/{tailor['job_id']}.pdf")
    print(f"  📝 LaTeX: output/{tailor['job_id']}.tex")

    print("\n🎉 Done! Check the output/ folder for your PDFs.")

if __name__ == "__main__":
    main()
