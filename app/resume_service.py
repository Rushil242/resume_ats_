
import json
import uuid
import os
import re
from app.pdf_parser import extract_text, pdf_first_page_to_image
from app.llm_client import call_vision, call_text_json
from app.ats_scorer import score_resume
from app.latex_compiler import build_full_latex, compile_latex
from app.prompts import (
    SYSTEM_PROMPT,
    STYLE_EXTRACTION_PROMPT,
    CONTENT_EXTRACTION_PROMPT,
    TAILOR_EXPERIENCE_PROMPT,
    TAILOR_PROJECTS_PROMPT,
    TAILOR_SKILLS_PROMPT,
    TAILOR_SUMMARY_PROMPT,
)
from app.config import settings

RESUME_STORE: dict = {}


def _default_style(section_ids=None):
    return {
        "page_size": "A4",
        "margins": {"top": 1.5, "bottom": 1.5, "left": 1.8, "right": 1.8},
        "columns": 1,
        "fonts": {"base_family": "Times New Roman", "heading_family": "Arial", "base_size_pt": 10,
                  "name_size_pt": 22, "section_heading_size_pt": 11, "line_spacing": 1.1},
        "colors": {"primary": "#000000", "accent": "#000000", "section_heading": "#000000"},
        "sections_order": section_ids or ["EDUCATION", "TECHNICAL_SKILLS", "PROJECTS", "EXPERIENCE", "POSITIONS_OF_RESPONSIBILITY", "ACHIEVEMENTS", "CERTIFICATIONS"],
        "section_styles": {},
        "bullet_style": {"marker": "bullet", "indent_cm": 0.5},
        "raw_description": "Standard single-column resume."
    }


def _detect_name(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:6]:
        if len(line.split()) >= 2 and len(line) < 60 and not any(ch.isdigit() for ch in line):
            if '@' not in line and 'linkedin' not in line.lower() and 'github' not in line.lower():
                return line.title() if line.isupper() else line
    return "Candidate"


def _extract_contact(text: str) -> dict:
    email = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    phone = re.search(r'(\+?\d[\d\-\s]{8,}\d)', text)
    linkedin = re.search(r'(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+', text, re.I)
    github = re.search(r'(https?://)?(www\.)?github\.com/[A-Za-z0-9_-]+', text, re.I)
    loc = ""
    for city in ["Bengaluru", "Bangalore", "Karnataka", "Hyderabad", "Mumbai", "Delhi", "Chennai", "Pune"]:
        if city.lower() in text.lower():
            loc = city if city != "Bangalore" else "Bengaluru"
            break
    return {
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else "",
        "location": loc,
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
        "website": "",
    }


def _extract_section_block(text: str, heading_patterns: list[str]):
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if any(re.fullmatch(p, line, re.I) for p in heading_patterns):
            j = i + 1
            collected = []
            while j < len(lines):
                nxt = lines[j].strip()
                if nxt and re.fullmatch(r'[A-Z][A-Z\s&/]+', nxt) and len(nxt.split()) <= 5:
                    break
                collected.append(lines[j])
                j += 1
            blocks.append("\n".join(collected).strip())
            i = j
        else:
            i += 1
    return "\n".join([b for b in blocks if b]).strip()


def _fallback_content_extract(text: str) -> dict:
    name = _detect_name(text)
    contact = _extract_contact(text)
    lines = [l.rstrip() for l in text.splitlines()]

    sections = []

    edu_block = _extract_section_block(text, [r'EDUCATION', r'ACADEMIC DETAILS'])
    if edu_block:
        edu_lines = [l.strip() for l in edu_block.splitlines() if l.strip()]
        item = {
            "type": "education",
            "title": edu_lines[0] if edu_lines else "Education",
            "subtitle": edu_lines[1] if len(edu_lines) > 1 else "",
            "location": "",
            "start": "",
            "end": "",
            "bullets": edu_lines[2:6] if len(edu_lines) > 2 else []
        }
        sections.append({"id": "EDUCATION", "title": "Education", "items": [item]})

    skills_block = _extract_section_block(text, [r'TECHNICAL SKILLS', r'SKILLS', r'SKILLS'])
    if skills_block:
        cats = []
        for line in [l.strip(' •-').strip() for l in skills_block.splitlines() if l.strip()]:
            if ':' in line:
                cat, vals = line.split(':', 1)
                skills = [v.strip() for v in re.split(r',|\|', vals) if v.strip()]
                cats.append({"type": "skill_category", "category": cat.strip(), "skills": skills})
        if not cats:
            merged = re.split(r',|\n|\|', skills_block)
            vals = [v.strip(' •-').strip() for v in merged if v.strip()]
            cats = [{"type": "skill_category", "category": "Skills", "skills": vals[:25]}]
        sections.append({"id": "SKILLS", "title": "Skills", "items": cats})

    proj_block = _extract_section_block(text, [r'PROJECTS', r'ACADEMIC PROJECTS', r'PERSONAL PROJECTS'])
    if proj_block:
        proj_lines = [l.strip() for l in proj_block.splitlines() if l.strip()]
        projects = []
        current = None
        for line in proj_lines:
            if len(line) < 120 and not line.startswith(('•', '-', '*')):
                if current:
                    projects.append(current)
                current = {"type": "project", "title": line, "subtitle": "", "location": "", "start": "", "end": "", "bullets": []}
            else:
                if not current:
                    current = {"type": "project", "title": "Project", "subtitle": "", "location": "", "start": "", "end": "", "bullets": []}
                current["bullets"].append(line.lstrip('•-* ').strip())
        if current:
            projects.append(current)
        if projects:
            sections.append({"id": "PROJECTS", "title": "Projects", "items": projects[:4]})

    exp_block = _extract_section_block(text, [r'EXPERIENCE', r'WORK EXPERIENCE', r'INTERNSHIPS?', r'INTERNSHIP'])
    if exp_block:
        exp_lines = [l.strip() for l in exp_block.splitlines() if l.strip()]
        jobs = []
        current = None
        for line in exp_lines:
            if len(line) < 120 and not line.startswith(('•', '-', '*')):
                if current:
                    jobs.append(current)
                current = {"type": "job", "title": line, "subtitle": "", "location": "", "start": "", "end": "", "bullets": []}
            else:
                if not current:
                    current = {"type": "job", "title": "Experience", "subtitle": "", "location": "", "start": "", "end": "", "bullets": []}
                current["bullets"].append(line.lstrip('•-* ').strip())
        if current:
            jobs.append(current)
        if jobs:
            sections.append({"id": "EXPERIENCE", "title": "Experience", "items": jobs[:4]})

    por_block = _extract_section_block(text, [r'POSITIONS OF RESPONSIBILITY', r'LEADERSHIP', r'EXTRACURRICULARS?'])
    if por_block:
        bullets = [l.lstrip('•-* ').strip() for l in por_block.splitlines() if l.strip()]
        items = [{"type": "paragraph", "text": b} for b in bullets[:8]]
        sections.append({"id": "POSITIONS_OF_RESPONSIBILITY", "title": "Positions of Responsibility", "items": items})

    ach_block = _extract_section_block(text, [r'ACHIEVEMENTS?', r'AWARDS?'])
    if ach_block:
        bullets = [l.lstrip('•-* ').strip() for l in ach_block.splitlines() if l.strip()]
        items = [{"type": "paragraph", "text": b} for b in bullets[:8]]
        sections.append({"id": "ACHIEVEMENTS", "title": "Achievements", "items": items})

    cert_block = _extract_section_block(text, [r'CERTIFICATIONS?', r'COURSES'])
    if cert_block:
        bullets = [l.lstrip('•-* ').strip() for l in cert_block.splitlines() if l.strip()]
        items = [{"type": "paragraph", "text": b} for b in bullets[:8]]
        sections.append({"id": "CERTIFICATIONS", "title": "Certifications", "items": items})

    if not sections:
        bullets = [l.strip() for l in lines if l.strip()][:12]
        sections = [{"id": "SUMMARY", "title": "Summary", "items": [{"type": "paragraph", "text": " ".join(bullets[:5])}]}]

    return {"name": name, "contact": contact, "sections": sections}


def analyze_resume(pdf_path: str, image_bytes: bytes = b"") -> dict:
    resume_id = str(uuid.uuid4())
    text = extract_text(pdf_path)
    if not text.strip():
        raise ValueError("Could not extract text from uploaded file.")

    if not image_bytes:
        try:
            image_bytes = pdf_first_page_to_image(pdf_path)
        except Exception:
            image_bytes = b""

    style = None
    if image_bytes:
        try:
            style = call_vision(STYLE_EXTRACTION_PROMPT, image_bytes, resume_text=text[:3000])
        except Exception as e:
            print(f"[style] vision failed: {e}")
    if not style:
        try:
            style = call_text_json(SYSTEM_PROMPT, STYLE_EXTRACTION_PROMPT.format(resume_text=text[:3000]))
        except Exception as e:
            print(f"[style] text failed: {e}")
            style = _default_style()

    try:
        content = call_text_json(SYSTEM_PROMPT, CONTENT_EXTRACTION_PROMPT.format(resume_text=text))
    except Exception as e:
        print(f"[content] llm extraction failed: {e}")
        content = _fallback_content_extract(text)

    extracted_ids = [s['id'] for s in content.get('sections', [])]
    if not style.get('sections_order'):
        style['sections_order'] = extracted_ids or _default_style()['sections_order']
    for sid in extracted_ids:
        if sid not in style['sections_order']:
            style['sections_order'].append(sid)

    latex_code = build_full_latex(content, style)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    tex_path = os.path.join(settings.OUTPUT_DIR, f"{resume_id}.tex")
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(latex_code)

    roundtrip_url = None
    try:
        compile_latex(latex_code, resume_id, settings.OUTPUT_DIR)
        roundtrip_url = f"/output/{resume_id}.pdf"
    except Exception as e:
        print(f"[compile] non-fatal: {e}")

    RESUME_STORE[resume_id] = {
        'style': style,
        'content': content,
        'original_pdf': pdf_path,
        'original_text': text,
    }

    return {
        'resume_id': resume_id,
        'name': content.get('name', ''),
        'sections_found': [s['id'] for s in content.get('sections', [])],
        'style': style,
        'roundtrip_pdf_url': roundtrip_url,
    }


def tailor_resume(resume_id: str, jd_text: str) -> dict:
    if resume_id not in RESUME_STORE:
        raise KeyError(f"resume_id '{resume_id}' not found")

    data = RESUME_STORE[resume_id]
    style = data['style']
    content = data['content']
    resume_text = data['original_text']

    orig_score, matched, missing = score_resume(resume_text, jd_text)
    updated_content = json.loads(json.dumps(content))
    sections_by_id = {s['id']: s for s in updated_content.get('sections', [])}
    summary_ids = {'SUMMARY', 'OBJECTIVE', 'PROFILE', 'CAREER_SUMMARY', 'PROFESSIONAL_SUMMARY'}

    for sec_id, section in sections_by_id.items():
        items = section.get('items', [])
        if not items:
            continue
        first_type = items[0].get('type', '')
        prompt = None
        if first_type == 'job':
            prompt = TAILOR_EXPERIENCE_PROMPT.format(jd_text=jd_text[:2000], missing_keywords=', '.join(missing[:15]), section_json=json.dumps(section))
        elif first_type == 'project':
            prompt = TAILOR_PROJECTS_PROMPT.format(jd_text=jd_text[:2000], missing_keywords=', '.join(missing[:15]), section_json=json.dumps(section))
        elif first_type == 'skill_category':
            prompt = TAILOR_SKILLS_PROMPT.format(jd_text=jd_text[:2000], missing_keywords=', '.join(missing[:15]), section_json=json.dumps(section))
        elif first_type == 'paragraph' and sec_id in summary_ids:
            skills_sec = next((s for s in updated_content.get('sections', []) if s['id'] in {'SKILLS', 'TECHNICAL_SKILLS'}), {})
            prompt = TAILOR_SUMMARY_PROMPT.format(jd_text=jd_text[:2000], missing_keywords=', '.join(missing[:10]), section_json=json.dumps(section), skills_summary=json.dumps(skills_sec)[:1000])
        if prompt:
            try:
                updated = call_text_json(SYSTEM_PROMPT, prompt)
                updated['id'] = sec_id
                updated['title'] = section['title']
                sections_by_id[sec_id] = updated
            except Exception as e:
                print(f"[tailor] failed for {sec_id}: {e}")

    updated_content['sections'] = [sections_by_id.get(s['id'], s) for s in content.get('sections', [])]

    job_id = str(uuid.uuid4())
    latex_code = build_full_latex(updated_content, style)
    tex_path = os.path.join(settings.OUTPUT_DIR, f"{job_id}.tex")
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(latex_code)

    pdf_url = None
    try:
        compile_latex(latex_code, job_id, settings.OUTPUT_DIR)
        pdf_url = f"/output/{job_id}.pdf"
    except Exception as e:
        print(f"[tailor compile] non-fatal: {e}")

    tailored_pdf = os.path.join(settings.OUTPUT_DIR, f"{job_id}.pdf")
    if os.path.exists(tailored_pdf):
        tailored_text = extract_text(tailored_pdf)
        new_score, new_matched, new_missing = score_resume(tailored_text, jd_text)
    else:
        new_score, new_matched, new_missing = orig_score, matched, missing

    return {
        'job_id': job_id,
        'resume_id': resume_id,
        'original_ats_score': orig_score,
        'tailored_ats_score': new_score,
        'matched_keywords': new_matched[:20],
        'missing_keywords': new_missing[:20],
        'tailored_pdf_url': pdf_url,
        'tailored_tex_url': f"/output/{job_id}.tex",
    }
