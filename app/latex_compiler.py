"""
LaTeX → PDF compilation.
Requires pdflatex to be installed (sudo apt-get install texlive-full).
For Codespaces: install via the setup script provided.
"""
import subprocess
import os
import shutil
from pathlib import Path


LATEX_TEMPLATE = r"""
\documentclass[letterpaper,11pt]{{article}}

%% Packages
\usepackage[empty]{{fullpage}}
\usepackage{{titlesec}}
\usepackage{{marvosym}}
\usepackage[usenames,dvipsnames]{{color}}
\usepackage{{enumitem}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{fancyhdr}}
\usepackage[english]{{babel}}
\usepackage{{tabularx}}
\usepackage{{setspace}}

%% Page setup
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot{{}}
\renewcommand{{\headrulewidth}}{{0pt}}
\renewcommand{{\footrulewidth}}{{0pt}}
\addtolength{{\oddsidemargin}}{{-0.5in}}
\addtolength{{\evensidemargin}}{{-0.5in}}
\addtolength{{\textwidth}}{{1in}}
\addtolength{{\topmargin}}{{-0.5in}}
\addtolength{{\textheight}}{{1.0in}}
\setlength{{\footskip}}{{5pt}}
\urlstyle{{same}}
\raggedbottom
\raggedright
\setlength{{\tabcolsep}}{{0in}}

%% Section formatting
\titleformat{{\section}}{{
  \vspace{{-4pt}}\scshape\raggedright\large\bfseries
}}{{}}{{0em}}{{}}[\color{{black}}\titlerule \vspace{{-5pt}}]

%% Custom commands (from Resume-Builder-TeX template)
\newcommand{{\resumeItem}}[1]{{
  \item\small{{#1 \vspace{{-2pt}}}}
}}
\newcommand{{\resumeSubheading}}[4]{{
  \vspace{{-2pt}}\item
  \begin{{tabular*}}{{0.97\textwidth}}[t]{{l@{{\extracolsep{{\fill}}}}r}}
    \textbf{{#1}} & #2 \\
    \textit{{\small#3}} & \textit{{\small #4}} \\
  \end{{tabular*}}\vspace{{-7pt}}
}}
\newcommand{{\resumeProjectHeading}}[2]{{
  \item
  \begin{{tabular*}}{{0.97\textwidth}}{{l@{{\extracolsep{{\fill}}}}r}}
    \small#1 & #2 \\
  \end{{tabular*}}\vspace{{-7pt}}
}}
\newcommand{{\resumeSkillHeading}}[2]{{
  \vspace{{-2pt}}\item
  {{\textbf{{\small#1}}}}{{: \small#2}}
}}
\newcommand{{\resumeSubItem}}[1]{{\resumeItem{{#1}}\vspace{{-4pt}}}}
\newcommand{{\resumeSubHeadingListStart}}{{\begin{{itemize}}[leftmargin=0.15in, label={{}}]}}
\newcommand{{\resumeSubHeadingListEnd}}{{\end{{itemize}}}}
\newcommand{{\resumeItemListStart}}{{\begin{{itemize}}}}
\newcommand{{\resumeItemListEnd}}{{\end{{itemize}}\vspace{{-5pt}}}}

\begin{{document}}

%% Header
\begin{{center}}
  {{\Huge \textbf{{{name}}}}} \\[4pt]
  \small {contact_line}
\end{{center}}

%% Sections
{sections_latex}

\end{{document}}
"""


def build_contact_line(contact: dict) -> str:
    parts = []
    if contact.get("phone"):
        parts.append(contact["phone"])
    if contact.get("email"):
        parts.append(f"\href{{mailto:{contact['email']}}}{{{contact['email']}}}")
    if contact.get("linkedin"):
        lnk = contact["linkedin"].replace("https://","").replace("http://","")
        parts.append(f"\href{{{contact['linkedin']}}}{{{lnk}}}")
    if contact.get("github"):
        ghk = contact["github"].replace("https://","").replace("http://","")
        parts.append(f"\href{{{contact['github']}}}{{{ghk}}}")
    if contact.get("location"):
        parts.append(contact["location"])
    return " $|$ ".join(parts)


def content_to_latex_sections(content: dict, style: dict) -> str:
    """
    Converts content JSON → raw LaTeX section blocks.
    Uses sections_order from style when available.
    """
    sections_by_id = {s["id"]: s for s in content.get("sections", [])}
    order = style.get("sections_order") or list(sections_by_id.keys())

    out = []
    for sec_id in order:
        sec = sections_by_id.get(sec_id)
        if not sec:
            continue
        out.append(_render_section(sec))
    return "\n\n".join(out)


def _escape(text: str) -> str:
    """Escape LaTeX special characters."""
    if not text:
        return ""
    replacements = [
        ("\\", "\\textbackslash{}"),
        ("&",  "\\&"),
        ("%",  "\\%"),
        ("$",  "\\$"),
        ("#",  "\\#"),
        ("_",  "\\_"),
        ("{",  "\\{"),
        ("}",  "\\}"),
        ("~",  "\\textasciitilde{}"),
        ("^",  "\\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _render_section(sec: dict) -> str:
    title = _escape(sec.get("title", sec["id"].title()))
    lines = [f"\\section{{{title}}}"]

    items = sec.get("items", [])
    item_type = items[0]["type"] if items else "paragraph"

    if item_type == "skill_category":
        lines.append("\\resumeSubHeadingListStart")
        for item in items:
            cat = _escape(item.get("category",""))
            skills_str = ", ".join(_escape(s) for s in item.get("skills",[]))
            lines.append(f"  \\resumeSkillHeading{{{cat}}}{{{skills_str}}}")
        lines.append("\\resumeSubHeadingListEnd")

    elif item_type in ("job", "education"):
        lines.append("\\resumeSubHeadingListStart")
        for item in items:
            t  = _escape(item.get("title",""))
            st = _escape(item.get("subtitle",""))
            lo = _escape(item.get("location",""))
            start = _escape(item.get("start",""))
            end   = _escape(item.get("end",""))
            date_str = f"{start} -- {end}" if end else start
            lines.append(f"  \\resumeSubheading{{{t}}}{{{date_str}}}{{{st}}}{{{lo}}}")
            bullets = item.get("bullets",[])
            if bullets:
                lines.append("  \\resumeItemListStart")
                for b in bullets:
                    lines.append(f"    \\resumeItem{{{_escape(b)}}}")
                lines.append("  \\resumeItemListEnd")
        lines.append("\\resumeSubHeadingListEnd")

    elif item_type == "project":
        lines.append("\\resumeSubHeadingListStart")
        for item in items:
            t    = _escape(item.get("title",""))
            start = _escape(item.get("start",""))
            lines.append(f"  \\resumeProjectHeading{{\\textbf{{{t}}}}}{{{start}}}")
            bullets = item.get("bullets",[])
            if bullets:
                lines.append("  \\resumeItemListStart")
                for b in bullets:
                    lines.append(f"    \\resumeItem{{{_escape(b)}}}")
                lines.append("  \\resumeItemListEnd")
        lines.append("\\resumeSubHeadingListEnd")

    else:  # paragraph / summary
        for item in items:
            lines.append(_escape(item.get("text","")))

    return "\n".join(lines)


def compile_latex(latex_code: str, output_id: str, output_dir: str = "output") -> str:
    """
    Writes .tex file, runs pdflatex twice (for references), returns PDF path.
    """
    os.makedirs(output_dir, exist_ok=True)
    tex_path = os.path.join(output_dir, f"{output_id}.tex")
    pdf_path = os.path.join(output_dir, f"{output_id}.pdf")

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_code)

    for _ in range(2):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"{output_id}.tex"],
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log_path = os.path.join(output_dir, f"{output_id}.log")
            err_msg = result.stdout[-3000:] if result.stdout else result.stderr
            raise RuntimeError(f"pdflatex failed.\nLog:\n{err_msg}")

    return pdf_path


def build_full_latex(content: dict, style: dict) -> str:
    contact = content.get("contact", {})
    contact_line = build_contact_line(contact)
    sections_latex = content_to_latex_sections(content, style)
    return LATEX_TEMPLATE.format(
        name=_escape(content.get("name","")),
        contact_line=contact_line,
        sections_latex=sections_latex,
    )
