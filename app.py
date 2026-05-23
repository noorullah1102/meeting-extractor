"""
FastAPI application — Meeting Action Item Extractor
Accepts meeting transcripts, extracts action items + KG triples, sends notifications.
"""

import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

from extractor import extract_meeting_info
from formatter import format_html, format_plain
from graph_store import (
    add_triples,
    get_overloaded,
    get_pending,
    get_person_tasks,
    get_project_status,
)
from notifier import send_email

load_dotenv()

# Store the last extraction result for the /notify endpoint
_last_extraction: dict | None = None


class ExtractRequest(BaseModel):
    transcript: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure data directory exists on startup."""
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    yield


app = FastAPI(
    title="Meeting Action Item Extractor",
    lifespan=lifespan,
)


@app.post("/extract")
async def extract(body: ExtractRequest):
    """Extract action items and KG triples from a transcript string, then auto-send email."""
    global _last_extraction

    try:
        result = extract_meeting_info(body.transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    _last_extraction = result

    # Persist triples to graph
    meeting_id = result.get("meeting_title") or str(uuid.uuid4())
    if result.get("Triples"):
        add_triples(result["Triples"], meeting_id)

    # Auto-send email
    email_result = None
    to = os.environ.get("EMAIL_TO", "").split(",")
    to = [addr.strip() for addr in to if addr.strip()]
    if to and os.environ.get("RESEND_API_KEY"):
        title = result.get("meeting_title") or "Meeting Notes"
        date = result.get("meeting_date") or ""
        subject = f"{title} — {date}" if date else f"Meeting Recap — {title}"
        html = format_html(result)
        try:
            email_id = send_email(to=to, subject=subject, html_body=html)
            email_result = {"status": "sent", "email_id": email_id, "recipients": to}
        except Exception as e:
            email_result = {"status": "failed", "error": str(e)}

    return {"extraction": result, "email": email_result}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a .txt meeting transcript file."""
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted")

    content = (await file.read()).decode("utf-8")
    body = ExtractRequest(transcript=content)
    return await extract(body)


@app.post("/webhook")
async def webhook(payload: dict):
    """Zoom webhook compatible endpoint. Expects {"text": "..."} or {"object": {"body": "..."}}."""
    transcript = payload.get("text") or payload.get("object", {}).get("body", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript text found in payload")
    body = ExtractRequest(transcript=transcript)
    return await extract(body)


@app.post("/notify")
async def notify(to: list[str] | None = None):
    """Send the last extracted result via email using Resend."""
    if not _last_extraction:
        raise HTTPException(status_code=404, detail="No extraction result available. POST to /extract first.")

    to = to or os.environ.get("EMAIL_TO", "").split(",")
    to = [addr.strip() for addr in to if addr.strip()]
    if not to:
        raise HTTPException(status_code=400, detail="No recipients configured. Set EMAIL_TO in .env or pass 'to' in body.")

    title = _last_extraction.get("meeting_title") or "Meeting Notes"
    date = _last_extraction.get("meeting_date") or ""
    subject = f"{title} — {date}" if date else f"Meeting Recap — {title}"
    html = format_html(_last_extraction)

    try:
        email_id = send_email(to=to, subject=subject, html_body=html)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Email send failed: {e}")

    return {"status": "sent", "email_id": email_id, "recipients": to}


@app.get("/graph/person/{name}/tasks")
async def person_tasks(name: str):
    """Get all tasks associated with a person across all meetings."""
    return {"person": name, "tasks": get_person_tasks(name)}


@app.get("/graph/project/{name}/status")
async def project_status(name: str):
    """Get all items related to a project/client."""
    return {"project": name, "items": get_project_status(name)}


@app.get("/graph/pending")
async def pending():
    """Get all pending/open items across all meetings."""
    return {"pending": get_pending()}


@app.get("/graph/overloaded")
async def overloaded(threshold: int = 3):
    """Get people with N+ pending tasks."""
    return {"overloaded": get_overloaded(threshold)}


@app.get("/preview-email", response_class=HTMLResponse)
async def preview_email():
    """Preview the HTML email for the last extraction (dev tool)."""
    if not _last_extraction:
        raise HTTPException(status_code=404, detail="No extraction result available.")
    return format_html(_last_extraction)
