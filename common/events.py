"""Publicação de eventos de domínio (coreografia em vez de orquestração).

Serviços emitem eventos (``registration.confirmed``, ``review.decided`` ...) e
quem estiver interessado reage. Neste produto o assinante é o Notifications
Service; se a feature *Notificações* não foi selecionada, a publicação é no-op.
"""
from __future__ import annotations

from .client import call


def publish(event_type: str, user_id: int, subject: str, message: str, tenant: str | None = None):
    return call(
        "notifications", "POST", "/events", tenant=tenant, default=None,
        json={"type": event_type, "user_id": user_id, "subject": subject, "message": message},
    )
