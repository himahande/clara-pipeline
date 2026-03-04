"""File-based storage for pipeline outputs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import OUTPUT_DIR
from app.models import AccountMemo, AgentSpec

log = logging.getLogger(__name__)


def _account_dir(account_id: str, version: str) -> Path:
    d = OUTPUT_DIR / account_id / version
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_memo(memo: AccountMemo, version: str) -> Path:
    p = _account_dir(memo.account_id, version) / "account_memo.json"
    p.write_text(memo.model_dump_json(indent=2), encoding="utf-8")
    log.info("Saved memo → %s", p)
    return p


def save_agent_spec(spec: AgentSpec, account_id: str, version: str) -> Path:
    p = _account_dir(account_id, version) / "agent_spec.json"
    p.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    log.info("Saved agent spec → %s", p)
    return p


def save_changelog(changelog: str, account_id: str) -> Path:
    p = OUTPUT_DIR / account_id / "changelog.md"
    p.write_text(changelog, encoding="utf-8")
    log.info("Saved changelog → %s", p)
    return p


def save_diff(diff: dict, account_id: str) -> Path:
    p = OUTPUT_DIR / account_id / "diff.json"
    p.write_text(json.dumps(diff, indent=2, default=str), encoding="utf-8")
    log.info("Saved diff → %s", p)
    return p


def load_memo(account_id: str, version: str) -> AccountMemo | None:
    p = OUTPUT_DIR / account_id / version / "account_memo.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return AccountMemo.model_validate(data)


def load_agent_spec(account_id: str, version: str) -> AgentSpec | None:
    p = OUTPUT_DIR / account_id / version / "agent_spec.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return AgentSpec.model_validate(data)


def list_accounts() -> list[str]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(
        d.name
        for d in OUTPUT_DIR.iterdir()
        if d.is_dir() and (d / "v1").exists()
    )


def get_account_summary(account_id: str) -> dict:
    versions = []
    for v in ("v1", "v2"):
        memo = load_memo(account_id, v)
        if memo:
            versions.append(v)
    changelog_path = OUTPUT_DIR / account_id / "changelog.md"
    return {
        "account_id": account_id,
        "versions": versions,
        "has_changelog": changelog_path.exists(),
    }
