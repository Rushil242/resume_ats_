
SYSTEM_PROMPT = (
    "You are a professional resume parser and resume writer.\n"
    "CRITICAL RULES:\n"
    "1. Output ONLY raw JSON. No markdown fences. No triple backticks.\n"
    "2. In JSON string values, NEVER use LaTeX escaping like \\& or \\_ or \\#.\n"
    "   Use plain characters: & _ # % $ { } instead.\n"
    "3. Do not invent resume facts.\n"
    "4. For tailoring, keep the same candidate facts and only rewrite wording.\n"
)

STYLE_EXTRACTION_PROMPT = (
    "Analyze this resume and return ONLY a JSON object describing its visual style.\n"
    "Use plain JSON string values, not LaTeX escapes.\n\n"
    "Return this schema filled with real values:\n"
    '{\n'
    '  "page_size": "A4",\n'
    '  "margins": {"top": 1.5, "bottom": 1.5, "left": 1.8, "right": 1.8},\n'
    '  "columns": 1,\n'
    '  "fonts": {\n'
    '    "base_family": "Times New Roman",\n'
    '    "heading_family": "Arial",\n'
    '    "base_size_pt": 10,\n'
    '    "name_size_pt": 22,\n'
    '    "section_heading_size_pt": 11,\n'
    '    "line_spacing": 1.1\n'
    '  },\n'
    '  "colors": {"primary": "#000000", "accent": "#000000", "section_heading": "#000000"},\n'
    '  "sections_order": ["EDUCATION", "TECHNICAL_SKILLS", "PROJECTS", "EXPERIENCE", "ACHIEVEMENTS", "CERTIFICATIONS"],\n'
    '  "section_styles": {},\n'
    '  "bullet_style": {"marker": "bullet", "indent_cm": 0.5},\n'
    '  "raw_description": "Single column, serif font, bold section headings."\n'
    '}\n\n'
    "Resume text:\n{resume_text}"
)

CONTENT_EXTRACTION_PROMPT = (
    "Extract all resume content and return ONLY a JSON object.\n"
    "IMPORTANT: Use plain characters in all JSON strings.\n"
    "Example: write 'Artificial Intelligence & Machine Learning',\n"
    "NOT 'Artificial Intelligence \\& Machine Learning'.\n\n"
    "Use this schema:\n"
    '{\n'
    '  "name": "Full Name",\n'
    '  "contact": {\n'
    '    "email": "", "phone": "", "location": "", "linkedin": "", "github": "", "website": ""\n'
    '  },\n'
    '  "sections": [\n'
    '    {\n'
    '      "id": "EDUCATION", "title": "Education",\n'
    '      "items": [{\n'
    '        "type": "education",\n'
    '        "title": "Degree name",\n'
    '        "subtitle": "University name",\n'
    '        "location": "City",\n'
    '        "start": "2023", "end": "2027",\n'
    '        "bullets": []\n'
    '      }]\n'
    '    },\n'
    '    {\n'
    '      "id": "EXPERIENCE", "title": "Experience",\n'
    '      "items": [{\n'
    '        "type": "job",\n'
    '        "title": "Job Title", "subtitle": "Company",\n'
    '        "location": "City", "start": "Jan 2024", "end": "Present",\n'
    '        "bullets": ["Bullet 1", "Bullet 2"]\n'
    '      }]\n'
    '    },\n'
    '    {\n'
    '      "id": "PROJECTS", "title": "Projects",\n'
    '      "items": [{\n'
    '        "type": "project",\n'
    '        "title": "Project Name",\n'
    '        "subtitle": "", "location": "", "start": "2025", "end": "",\n'
    '        "bullets": ["Description"]\n'
    '      }]\n'
    '    },\n'
    '    {\n'
    '      "id": "SKILLS", "title": "Skills",\n'
    '      "items": [{"type": "skill_category", "category": "Languages", "skills": ["Python"]}]\n'
    '    }\n'
    '  ]\n'
    '}\n\n'
    "Rules:\n"
    "- Include ALL sections found in the resume.\n"
    "- Use UPPER_SNAKE_CASE for section ids.\n"
    "- Preserve bullets verbatim.\n"
    "- Output only one JSON object.\n\n"
    "Resume text:\n{resume_text}"
)

TAILOR_EXPERIENCE_PROMPT = (
    "Rewrite this experience section to better match the job description.\n"
    "Return ONLY one JSON object for the updated section. No markdown fences.\n"
    "Keep the same companies and dates. Use plain JSON strings.\n"
    "Incorporate these missing keywords where honest: {missing_keywords}\n\n"
    "Job description:\n{jd_text}\n\n"
    "Current section:\n{section_json}"
)

TAILOR_PROJECTS_PROMPT = (
    "Rewrite this projects section to better match the job description.\n"
    "Return ONLY one JSON object for the updated section. No markdown fences.\n"
    "Keep the same projects. Use plain JSON strings.\n"
    "Incorporate these missing keywords where honest: {missing_keywords}\n\n"
    "Job description:\n{jd_text}\n\n"
    "Current section:\n{section_json}"
)

TAILOR_SKILLS_PROMPT = (
    "Reorder this skills section to better match the job description.\n"
    "Return ONLY one JSON object for the updated section. No markdown fences.\n"
    "Do not add skills the candidate does not have. Use plain JSON strings.\n"
    "Missing keywords to add if candidate has them: {missing_keywords}\n\n"
    "Job description:\n{jd_text}\n\n"
    "Current section:\n{section_json}"
)

TAILOR_SUMMARY_PROMPT = (
    "Rewrite this summary to better match the job description.\n"
    "Return ONLY one JSON object for the updated section. No markdown fences.\n"
    "2-3 sentences. Use only candidate facts. Use plain JSON strings.\n"
    "Missing keywords to add if honest: {missing_keywords}\n\n"
    "Job description:\n{jd_text}\n\n"
    "Candidate skills:\n{skills_summary}\n\n"
    "Current section:\n{section_json}"
)
