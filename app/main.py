
import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings  # makedirs happen inside config.py now
from app.resume_service import analyze_resume, tailor_resume
from typing import Optional 

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
    screenshot: UploadFile | None = File(None, description="Optional screenshot PNG/JPG"),
):
    ext = os.path.splitext(resume_file.filename or "")[-1].lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX are supported.")

    temp_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(resume_file.file, f)

    image_bytes = b""
    if screenshot:
        image_bytes = await screenshot.read()

    try:
        result = analyze_resume(temp_path, image_bytes)
        return result
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


  # add this at the top of main.py with other imports

@app.post("/api/resume/{resume_id}/tailor")
async def api_tailor_resume(
    resume_id: str,
    jd_text: str = Form(default=""),
    jd_file: Optional[UploadFile] = File(default=None),
):
    text = jd_text.strip()
    if jd_file and not text:
        raw = await jd_file.read()
        text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Provide jd_text or upload jd_file.")

    try:
        return tailor_resume(resume_id, text)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{filename}")
def download_file(filename: str):
    path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
