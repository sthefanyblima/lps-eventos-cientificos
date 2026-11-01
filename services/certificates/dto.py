"""DTO — objetos de transferência do Certificates Service."""
from __future__ import annotations

from pydantic import BaseModel


class CertificateOut(BaseModel):
    code: str
    user_id: int
    type: str
    text: str
    hours: int
    issued_at: str
