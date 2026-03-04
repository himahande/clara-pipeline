"""Pipeline A (demo → v1) and Pipeline B (onboarding → v2) orchestration."""

from __future__ import annotations

import logging

from app import diff_engine, extractor, storage, tracker
from app.models import PipelineResult
from app.prompt_generator import generate_agent_spec

log = logging.getLogger(__name__)


async def run_pipeline_a(
    transcript: str,
    *,
    account_id: str | None = None,
) -> PipelineResult:
    """Demo call → preliminary agent (v1)."""
    log.info("Pipeline A: extracting demo memo...")
    memo = await extractor.extract_demo(transcript, account_id=account_id)

    log.info("Pipeline A: generating agent spec v1 for %s...", memo.account_id)
    spec = generate_agent_spec(memo, version="v1")

    storage.save_memo(memo, "v1")
    storage.save_agent_spec(spec, memo.account_id, "v1")

    tracker.create_task(
        account_id=memo.account_id,
        title=f"[v1] Agent created for {memo.company_name}",
        description="Preliminary agent generated from demo call. Awaiting onboarding.",
        status="review",
    )

    log.info("Pipeline A complete for %s", memo.account_id)
    return PipelineResult(
        account_id=memo.account_id,
        version="v1",
        memo=memo,
        agent_spec=spec,
    )


async def run_pipeline_b(
    transcript: str,
    account_id: str,
) -> PipelineResult:
    """Onboarding call → updated agent (v2)."""
    v1_memo = storage.load_memo(account_id, "v1")
    if v1_memo is None:
        raise ValueError(
            f"No v1 memo found for account '{account_id}'. Run Pipeline A first."
        )

    log.info("Pipeline B: extracting onboarding updates for %s...", account_id)
    v2_memo = await extractor.extract_onboarding(transcript, v1_memo)

    log.info("Pipeline B: generating agent spec v2...")
    v2_spec = generate_agent_spec(v2_memo, version="v2")

    diff = diff_engine.compute_diff(v1_memo, v2_memo)
    changelog = diff_engine.generate_changelog(v1_memo, v2_memo, diff)

    storage.save_memo(v2_memo, "v2")
    storage.save_agent_spec(v2_spec, account_id, "v2")
    storage.save_diff(diff, account_id)
    storage.save_changelog(changelog, account_id)

    tracker.create_task(
        account_id=account_id,
        title=f"[v2] Agent updated for {v2_memo.company_name}",
        description="Agent updated from onboarding call. Changelog generated.",
        status="review",
    )

    log.info("Pipeline B complete for %s", account_id)
    return PipelineResult(
        account_id=account_id,
        version="v2",
        memo=v2_memo,
        agent_spec=v2_spec,
        changelog=changelog,
    )
