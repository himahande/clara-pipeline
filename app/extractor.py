"""Extract structured account data from demo/onboarding transcripts via LLM."""

from __future__ import annotations

import logging
import re

from app.config import TEMPLATE_DIR
from app.llm import call_llm_json
from app.models import AccountMemo

log = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "unknown"


def _load_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


async def extract_demo(transcript: str, *, account_id: str | None = None) -> AccountMemo:
    """Pipeline A: extract a preliminary (v1) account memo from a demo call transcript."""
    system = _load_template("extraction_demo.txt")
    prompt = f"TRANSCRIPT:\n\n{transcript}"
    data = await call_llm_json(prompt, system=system)

    if not account_id:
        account_id = _slugify(data.get("company_name", "unknown"))

    data["account_id"] = account_id
    memo = AccountMemo.model_validate(data)
    log.info("Extracted demo memo for %s", memo.account_id)
    return memo


async def extract_onboarding(
    transcript: str,
    existing_memo: AccountMemo,
) -> AccountMemo:
    """Pipeline B: extract onboarding updates and merge with existing v1 memo."""
    system = _load_template("extraction_onboarding.txt")
    existing_json = existing_memo.model_dump_json(indent=2)
    prompt = (
        f"EXISTING ACCOUNT MEMO (v1):\n```json\n{existing_json}\n```\n\n"
        f"ONBOARDING TRANSCRIPT:\n\n{transcript}"
    )
    data = await call_llm_json(prompt, system=system)
    data["account_id"] = existing_memo.account_id
    memo = AccountMemo.model_validate(data)
    log.info("Extracted onboarding memo for %s", memo.account_id)
    return memo
