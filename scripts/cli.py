"""CLI entry point – run pipelines from the command line."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline import run_pipeline_a, run_pipeline_b
from app.storage import list_accounts, load_memo, load_agent_spec
from app.config import DATA_DIR, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def cmd_demo(args):
    transcript = Path(args.file).read_text(encoding="utf-8")
    result = asyncio.run(run_pipeline_a(transcript, account_id=args.account_id))
    print(f"\n✓ Pipeline A complete → account_id={result.account_id}")
    print(f"  Outputs: {OUTPUT_DIR / result.account_id / 'v1'}")


def cmd_onboarding(args):
    transcript = Path(args.file).read_text(encoding="utf-8")
    result = asyncio.run(run_pipeline_b(transcript, args.account_id))
    print(f"\n✓ Pipeline B complete → account_id={result.account_id}")
    print(f"  Outputs: {OUTPUT_DIR / result.account_id / 'v2'}")
    print(f"  Changelog: {OUTPUT_DIR / result.account_id / 'changelog.md'}")


def cmd_batch(args):
    demo_dir = DATA_DIR / "demo"
    onboard_dir = DATA_DIR / "onboarding"

    demo_files = sorted(demo_dir.glob("*.txt")) if demo_dir.exists() else []
    onboard_files = sorted(onboard_dir.glob("*.txt")) if onboard_dir.exists() else []

    if not demo_files:
        print(f"No demo transcripts found in {demo_dir}")
        return

    print(f"Found {len(demo_files)} demo transcript(s), {len(onboard_files)} onboarding transcript(s)\n")

    account_map: dict[str, str] = {}

    for f in demo_files:
        print(f"── Pipeline A: {f.name} ──")
        transcript = f.read_text(encoding="utf-8")
        result = asyncio.run(run_pipeline_a(transcript))
        account_map[f.stem] = result.account_id
        print(f"   → {result.account_id} (v1)\n")

    for f in onboard_files:
        stem = f.stem.replace("_onboarding", "").replace("onboarding_", "")
        account_id = account_map.get(stem) or account_map.get(f.stem)
        if not account_id:
            for key, aid in account_map.items():
                if key in f.stem or f.stem in key:
                    account_id = aid
                    break
        if not account_id:
            print(f"── Pipeline B: {f.name} ── SKIPPED (no matching demo)")
            continue
        print(f"── Pipeline B: {f.name} → {account_id} ──")
        transcript = f.read_text(encoding="utf-8")
        result = asyncio.run(run_pipeline_b(transcript, account_id))
        print(f"   → {result.account_id} (v2)\n")

    print("═" * 50)
    print("Batch complete. Accounts processed:")
    for acc in list_accounts():
        print(f"  • {acc}")


def cmd_list(args):
    accounts = list_accounts()
    if not accounts:
        print("No accounts found.")
        return
    for acc in accounts:
        memo = load_memo(acc, "v1")
        v2 = load_memo(acc, "v2")
        tag = " [v1+v2]" if v2 else " [v1]"
        name = memo.company_name if memo else "?"
        print(f"  {acc}: {name}{tag}")


def cmd_show(args):
    version = args.version or "v1"
    memo = load_memo(args.account_id, version)
    if not memo:
        print(f"No {version} memo for {args.account_id}")
        return
    print(json.dumps(memo.model_dump(), indent=2))


def main():
    parser = argparse.ArgumentParser(description="Clara Pipeline CLI")
    sub = parser.add_subparsers(dest="command")

    p_demo = sub.add_parser("demo", help="Run Pipeline A on a demo transcript")
    p_demo.add_argument("file", help="Path to demo transcript file")
    p_demo.add_argument("--account-id", default=None)
    p_demo.set_defaults(func=cmd_demo)

    p_onboard = sub.add_parser("onboarding", help="Run Pipeline B on an onboarding transcript")
    p_onboard.add_argument("file", help="Path to onboarding transcript file")
    p_onboard.add_argument("--account-id", required=True)
    p_onboard.set_defaults(func=cmd_onboarding)

    p_batch = sub.add_parser("batch", help="Batch process all transcripts in data/transcripts/")
    p_batch.set_defaults(func=cmd_batch)

    p_list = sub.add_parser("list", help="List processed accounts")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show account memo")
    p_show.add_argument("account_id")
    p_show.add_argument("--version", default="v1")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
