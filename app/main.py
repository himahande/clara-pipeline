"""FastAPI server – provides HTTP endpoints for n8n / external orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app import storage, tracker
from app.config import BASE_DIR, OUTPUT_DIR
from app.pipeline import run_pipeline_a, run_pipeline_b

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Clara Pipeline", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class TranscriptInput(BaseModel):
    transcript: str
    account_id: str | None = None


class OnboardingInput(BaseModel):
    transcript: str
    account_id: str


# ── Pipeline endpoints ────────────────────────────────────────────────────────

@app.post("/api/pipeline-a")
async def pipeline_a(body: TranscriptInput):
    try:
        result = await run_pipeline_a(body.transcript, account_id=body.account_id)
        return {
            "status": "ok",
            "account_id": result.account_id,
            "version": result.version,
            "memo": result.memo.model_dump(),
            "agent_spec": result.agent_spec.model_dump(),
        }
    except Exception as e:
        log.exception("Pipeline A failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline-b")
async def pipeline_b(body: OnboardingInput):
    try:
        result = await run_pipeline_b(body.transcript, body.account_id)
        return {
            "status": "ok",
            "account_id": result.account_id,
            "version": result.version,
            "memo": result.memo.model_dump(),
            "agent_spec": result.agent_spec.model_dump(),
            "changelog": result.changelog,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("Pipeline B failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline-a/upload")
async def pipeline_a_upload(file: UploadFile = File(...), account_id: str = Form(None)):
    content = (await file.read()).decode("utf-8")
    try:
        result = await run_pipeline_a(content, account_id=account_id)
        return {
            "status": "ok",
            "account_id": result.account_id,
            "version": result.version,
        }
    except Exception as e:
        log.exception("Pipeline A upload failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline-b/upload")
async def pipeline_b_upload(file: UploadFile = File(...), account_id: str = Form(...)):
    content = (await file.read()).decode("utf-8")
    try:
        result = await run_pipeline_b(content, account_id)
        return {
            "status": "ok",
            "account_id": result.account_id,
            "version": result.version,
        }
    except Exception as e:
        log.exception("Pipeline B upload failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── Data endpoints ────────────────────────────────────────────────────────────

@app.get("/api/accounts")
def list_accounts():
    accounts = storage.list_accounts()
    return {"accounts": [storage.get_account_summary(a) for a in accounts]}


@app.get("/api/accounts/{account_id}")
def get_account(account_id: str):
    v1_memo = storage.load_memo(account_id, "v1")
    if not v1_memo:
        raise HTTPException(404, f"Account {account_id} not found")
    v2_memo = storage.load_memo(account_id, "v2")
    v1_spec = storage.load_agent_spec(account_id, "v1")
    v2_spec = storage.load_agent_spec(account_id, "v2")

    changelog_path = OUTPUT_DIR / account_id / "changelog.md"
    changelog = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else None

    return {
        "account_id": account_id,
        "v1": {"memo": v1_memo.model_dump(), "agent_spec": v1_spec.model_dump() if v1_spec else None},
        "v2": {
            "memo": v2_memo.model_dump() if v2_memo else None,
            "agent_spec": v2_spec.model_dump() if v2_spec else None,
        },
        "changelog": changelog,
    }


@app.get("/api/tasks")
def list_tasks(account_id: str | None = None):
    return {"tasks": tracker.get_tasks(account_id)}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    index = BASE_DIR / "web" / "index.html"
    if index.exists():
        return index.read_text(encoding="utf-8")
    return "<h1>Clara Pipeline</h1><p>Dashboard not found. Place web/index.html.</p>"
