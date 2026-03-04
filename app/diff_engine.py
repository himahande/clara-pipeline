"""Compute structured diffs between account memo versions and generate changelogs."""

from __future__ import annotations

from datetime import datetime, timezone

from deepdiff import DeepDiff

from app.models import AccountMemo


def compute_diff(v1: AccountMemo, v2: AccountMemo) -> dict:
    d1 = v1.model_dump()
    d2 = v2.model_dump()
    diff = DeepDiff(d1, d2, ignore_order=True, verbose_level=2)
    return diff.to_dict() if diff else {}


def generate_changelog(
    v1: AccountMemo,
    v2: AccountMemo,
    diff_raw: dict | None = None,
) -> str:
    if diff_raw is None:
        diff_raw = compute_diff(v1, v2)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Changelog – {v2.company_name}",
        f"**Account ID:** {v2.account_id}",
        f"**Updated:** {ts}",
        f"**Version:** v1 → v2",
        "",
    ]

    if not diff_raw:
        lines.append("No changes detected between v1 and v2.")
        return "\n".join(lines)

    if "values_changed" in diff_raw:
        lines.append("## Fields Changed")
        for path, detail in diff_raw["values_changed"].items():
            field = _pretty_path(path)
            old = detail.get("old_value", detail.get("new_value", ""))
            new = detail.get("new_value", detail.get("old_value", ""))
            lines.append(f"- **{field}**: `{old}` → `{new}`")
        lines.append("")

    if "iterable_item_added" in diff_raw:
        lines.append("## Items Added")
        for path, val in diff_raw["iterable_item_added"].items():
            field = _pretty_path(path)
            lines.append(f"- **{field}**: `{val}`")
        lines.append("")

    if "iterable_item_removed" in diff_raw:
        lines.append("## Items Removed")
        for path, val in diff_raw["iterable_item_removed"].items():
            field = _pretty_path(path)
            lines.append(f"- **{field}**: `{val}`")
        lines.append("")

    if "dictionary_item_added" in diff_raw:
        lines.append("## Keys Added")
        for path in diff_raw["dictionary_item_added"]:
            lines.append(f"- `{_pretty_path(path)}`")
        lines.append("")

    if "dictionary_item_removed" in diff_raw:
        lines.append("## Keys Removed")
        for path in diff_raw["dictionary_item_removed"]:
            lines.append(f"- `{_pretty_path(path)}`")
        lines.append("")

    if "type_changes" in diff_raw:
        lines.append("## Type Changes")
        for path, detail in diff_raw["type_changes"].items():
            lines.append(f"- **{_pretty_path(path)}**: type changed")
        lines.append("")

    return "\n".join(lines)


def _pretty_path(path: str) -> str:
    return path.replace("root['", "").replace("']['", ".").replace("']", "").replace("root[", "").replace("]", "")
