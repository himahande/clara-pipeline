"""Lightweight JSON-based task tracker (zero-cost alternative to Asana)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import TRACKER_FILE

log = logging.getLogger(__name__)


def _load_tasks() -> list[dict]:
    if not TRACKER_FILE.exists():
        return []
    return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))


def _save_tasks(tasks: list[dict]) -> None:
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(tasks, indent=2, default=str), encoding="utf-8")


def create_task(
    account_id: str,
    title: str,
    description: str = "",
    status: str = "pending",
) -> dict:
    tasks = _load_tasks()
    task = {
        "id": len(tasks) + 1,
        "account_id": account_id,
        "title": title,
        "description": description,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    tasks.append(task)
    _save_tasks(tasks)
    log.info("Created task #%d: %s", task["id"], title)
    return task


def update_task(task_id: int, **updates) -> dict | None:
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t.update(updates)
            t["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_tasks(tasks)
            return t
    return None


def get_tasks(account_id: str | None = None) -> list[dict]:
    tasks = _load_tasks()
    if account_id:
        return [t for t in tasks if t["account_id"] == account_id]
    return tasks
