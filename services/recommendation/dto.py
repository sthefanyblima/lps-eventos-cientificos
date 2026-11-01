"""DTO — objetos de transferência do Recommendation Service."""
from __future__ import annotations

from pydantic import BaseModel


class RecommendedSession(BaseModel):
    id: int
    title: str
    track: str | None
    tags: list[str]
    speaker: str
    day: str
    start: str
    room: str
    kind: str
    score: float
    reason: str


class RecommendationOut(BaseModel):
    user_id: int
    strategy: str
    variant: str
    based_on: dict
    items: list[RecommendedSession]


class RecommendationLog(BaseModel):
    id: int
    session_id: int
    session_title: str
    score: float
    strategy: str
    reason: str
    generated_at: str
