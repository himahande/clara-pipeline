from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessHours(BaseModel):
    days: list[str] = Field(default_factory=list, description="e.g. ['Monday','Tuesday',...]")
    start: str | None = Field(None, description="e.g. '08:00'")
    end: str | None = Field(None, description="e.g. '17:00'")
    timezone: str | None = None


class RoutingContact(BaseModel):
    contact_name: str | None = None
    phone_number: str | None = None
    role: str | None = None
    order: int = 1
    fallback: str | None = None


class CallTransferRules(BaseModel):
    timeout_seconds: int | None = None
    max_retries: int | None = None
    failure_message: str | None = None


class AccountMemo(BaseModel):
    account_id: str
    company_name: str
    business_hours: BusinessHours | None = None
    office_address: str | None = None
    services_supported: list[str] = Field(default_factory=list)
    emergency_definition: list[str] = Field(default_factory=list)
    emergency_routing_rules: list[RoutingContact] = Field(default_factory=list)
    non_emergency_routing_rules: list[RoutingContact] = Field(default_factory=list)
    call_transfer_rules: CallTransferRules | None = None
    integration_constraints: list[str] = Field(default_factory=list)
    after_hours_flow_summary: str | None = None
    office_hours_flow_summary: str | None = None
    questions_or_unknowns: list[str] = Field(default_factory=list)
    notes: str | None = None


class AgentSpec(BaseModel):
    agent_name: str
    voice_style: str = "professional, calm, and friendly"
    system_prompt: str
    key_variables: dict = Field(default_factory=dict)
    tool_invocation_placeholders: list[str] = Field(default_factory=list)
    call_transfer_protocol: str = ""
    fallback_protocol: str = ""
    version: str = "v1"


class PipelineResult(BaseModel):
    account_id: str
    version: str
    memo: AccountMemo
    agent_spec: AgentSpec
    changelog: str | None = None
