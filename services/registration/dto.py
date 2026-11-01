"""DTO — objetos de transferência do Registration Service."""
from __future__ import annotations

from pydantic import BaseModel


class RegistrationIn(BaseModel):
    user_id: int
    card_number: str | None = None   # só para a variante CartaoCredito (simulada)


class RegistrationOut(BaseModel):
    user_id: int
    status: str
    method: str
    amount: float
    details: dict
    created_at: str


class AgendaIn(BaseModel):
    session_id: int


class PaymentMethodOut(BaseModel):
    variant: str
    label: str
    fee: float
