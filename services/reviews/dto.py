"""DTO — objetos de transferência do Reviews Service."""
from __future__ import annotations

from pydantic import BaseModel, Field

ACCEPT_THRESHOLD = 1.0   # média das notas (escala -3..3) para aceitar


class ReviewIn(BaseModel):
    submission_id: int
    reviewer_id: int
    score: int = Field(ge=-3, le=3, description="-3 (rejeição forte) .. 3 (aceite forte)")
    comment: str = ""


class ReviewOut(BaseModel):
    id: int
    submission_id: int
    reviewer_id: int | None
    reviewer_name: str
    score: int
    comment: str
    created_at: str


class DecisionOut(BaseModel):
    submission_id: int
    average: float
    status: str
    reviews: int


class PolicyOut(BaseModel):
    variant: str
    label: str
    description: str
