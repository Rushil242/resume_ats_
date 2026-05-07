import os
import shutil
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.resume_service import analyze_resume, tailor_resume

app = FastAPI(title="Resume ATS Tailor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=settings.OUTPUT_DIR), name="output")


@app.get("/")
def root():
    return {
        "status": "running",
        "analyze": "POST /api/resume/analyze",
        "tailor": "POST /api/resume/{resume_id}/tailor",
        "docs": "/docs",
    }


@app.post("/api/resume/analyze")
async def api_analyze_resume(
    resume_file: UploadFile = File(..., description="Resume PDF or DOCX"),
    screenshot: Optional[UploadFile] = File(default=None, description="Optional screenshot PNG/JPG"),
):
    ext = os.path.splitext(resume_file.filename or "")[-1].lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX are supported.")

    temp_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(resume_file.file, f)

    image_bytes = b""
    if screenshot and hasattr(screenshot, "read"):
        image_bytes = await screenshot.read()

    try:
        result = analyze_resume(temp_path, image_bytes)
        return result
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── TAILOR endpoint — jd_file intentionally removed from multipart.
# Swagger sends empty string "" for unused optional file fields, which crashes
# FastAPI's UploadFile validator regardless of Optional annotation (known FastAPI bug
# with multipart + empty binary fields). Solution: accept only jd_text as Form field.
# If you need file upload, use a separate dedicated endpoint below.
@app.post("/api/resume/{resume_id}/tailor")
async def api_tailor_resume(
    resume_id: str,
    jd_text: str = Form(default=""),
):
    text = jd_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="jd_text is required and cannot be empty.")

    try:
        return tailor_resume(resume_id, text)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Resume ID not found: {e}")
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Separate endpoint to upload a JD as a PDF/TXT file
@app.post("/api/resume/{resume_id}/tailor-file")
async def api_tailor_resume_file(
    resume_id: str,
    jd_file: UploadFile = File(..., description="Job description as PDF or TXT file"),
):
    raw = await jd_file.read()
    # Try UTF-8 decode (works for .txt); for PDF extract text
    filename = jd_file.filename or ""
    if filename.lower().endswith(".pdf"):
        import pdfplumber, io
        text = ""
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    else:
        text = raw.decode("utf-8", errors="ignore")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from uploaded JD file.")

    try:
        return tailor_resume(resume_id, text)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Resume ID not found: {e}")
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
def download_file(filename: str):
    path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
