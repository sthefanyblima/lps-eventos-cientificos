"""DTO — objetos de transferência do Notifications Service."""
from __future__ import annotations

from pydantic import BaseModel


class EventIn(BaseModel):
    type: str
    user_id: int
    subject: str
    message: str


class NotificationOut(BaseModel):
    id: int
    user_id: int
    subject: str
    message: str
    read: bool
    at: str


class EmailOut(BaseModel):
    id: int
    to: str
    subject: str
    body: str
    sent_at: str
