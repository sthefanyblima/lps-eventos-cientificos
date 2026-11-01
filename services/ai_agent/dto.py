"""DTO — objetos de transferência do AI Agent Service (interface de diálogo)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    user_id: int
    message: str = Field(min_length=1, max_length=2000)


class TraceItem(BaseModel):
    step: int
    tool: str
    service: str
    input: dict
    output: object
    status: str


class ChatOut(BaseModel):
    request_id: str
    answer: str
    provider: str
    goal: dict
    plan: list[dict]
    trace: list[TraceItem]
    explanation: list[str]
    guardrails: list[str]
    memory: dict


class ToolOut(BaseModel):
    name: str
    description: str
    feature: str
    service: str


class AuditOut(BaseModel):
    order: int
    component: str
    input: str
    output: str
    at: str
