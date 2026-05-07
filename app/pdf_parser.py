"""
PDF text and image extraction.
Uses pdfplumber for text, pdf2image for first-page screenshot.
"""
import pdfplumber
import io
from pathlib import Path
from PIL import Image


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def pdf_first_page_to_image(pdf_path: str, dpi: int = 150) -> bytes:
    """
    Returns the first page of the PDF as JPEG bytes.
    Falls back gracefully if pdf2image / poppler is not installed.
    """
    try:
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)
        if pages:
            buf = io.BytesIO()
            pages[0].save(buf, format="JPEG", quality=85)
            return buf.getvalue()
    except Exception as e:
        print(f"[pdf_parser] pdf2image failed ({e}), skipping screenshot")
    return b""


def extract_docx_text(docx_path: str) -> str:
    from docx import Document
    doc = Document(docx_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
