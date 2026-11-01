"""DTO — objetos de transferência do Events Service."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SessionIn(BaseModel):
    title: str = Field(min_length=3)
    track: str | None = None
    tags: list[str] = []
    speaker: str = ""
    day: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["2026-11-10"])
    start: str = Field(pattern=r"^\d{2}:\d{2}$", examples=["09:00"])
    room: str = ""
    kind: str = "Palestra"


class SessionOut(BaseModel):
    id: int
    title: str
    track: str | None
    tags: list[str]
    speaker: str
    day: str
    start: str
    room: str
    kind: str


class EventOut(BaseModel):
    tenant: str
    name: str
    theme: str | None
    has_tracks: bool
    period: str
    location: str
    fee: float
