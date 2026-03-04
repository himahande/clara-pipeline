"""Generate a Retell-compatible agent specification from an account memo."""

from __future__ import annotations

from jinja2 import Template

from app.config import TEMPLATE_DIR
from app.models import AccountMemo, AgentSpec


def _load_template() -> Template:
    raw = (TEMPLATE_DIR / "agent_prompt.txt").read_text(encoding="utf-8")
    return Template(raw)


def generate_agent_spec(memo: AccountMemo, *, version: str = "v1") -> AgentSpec:
    tmpl = _load_template()
    system_prompt = tmpl.render(
        company_name=memo.company_name,
        business_hours=memo.business_hours,
        office_address=memo.office_address or "Not provided",
        services=memo.services_supported,
        emergency_definitions=memo.emergency_definition,
        emergency_routing=memo.emergency_routing_rules,
        non_emergency_routing=memo.non_emergency_routing_rules,
        transfer_rules=memo.call_transfer_rules,
        integration_constraints=memo.integration_constraints,
        after_hours_flow=memo.after_hours_flow_summary or "",
        office_hours_flow=memo.office_hours_flow_summary or "",
    )

    key_vars: dict = {
        "company_name": memo.company_name,
        "timezone": memo.business_hours.timezone if memo.business_hours else None,
        "business_hours": memo.business_hours.model_dump() if memo.business_hours else None,
        "office_address": memo.office_address,
        "emergency_routing": [r.model_dump() for r in memo.emergency_routing_rules],
    }

    transfer_protocol = _build_transfer_protocol(memo)
    fallback_protocol = _build_fallback_protocol(memo)

    return AgentSpec(
        agent_name=f"Clara – {memo.company_name}",
        voice_style="professional, calm, and friendly",
        system_prompt=system_prompt,
        key_variables=key_vars,
        tool_invocation_placeholders=[
            "transfer_call(phone_number)",
            "create_ticket(details)",
            "lookup_account(caller_number)",
        ],
        call_transfer_protocol=transfer_protocol,
        fallback_protocol=fallback_protocol,
        version=version,
    )


def _build_transfer_protocol(memo: AccountMemo) -> str:
    rules = memo.call_transfer_rules
    timeout = rules.timeout_seconds if rules else 30
    retries = rules.max_retries if rules else 2
    lines = [
        f"1. Attempt warm transfer to the designated on-call contact.",
        f"2. Allow the phone to ring for {timeout} seconds before considering it failed.",
        f"3. If no answer, retry up to {retries} time(s).",
        f"4. Between retries, inform the caller: \"I'm still trying to reach someone for you, one moment please.\"",
        f"5. If all attempts fail, execute fallback protocol.",
    ]
    return "\n".join(lines)


def _build_fallback_protocol(memo: AccountMemo) -> str:
    rules = memo.call_transfer_rules
    failure_msg = (
        rules.failure_message
        if rules and rules.failure_message
        else "I wasn't able to reach anyone right now. I've logged your information and someone will call you back shortly."
    )
    lines = [
        f"1. Apologize to the caller: \"{failure_msg}\"",
        "2. Confirm all collected details (name, number, nature of call).",
        "3. Create a callback ticket via internal system.",
        "4. Provide an estimated callback window if known.",
        "5. Ask: \"Is there anything else I can help you with?\"",
        "6. If no, close the call politely.",
    ]
    return "\n".join(lines)
