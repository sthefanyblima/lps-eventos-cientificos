"""Notifications Service · porta 8008 — Feature **Notificações** (opcional).

Ponto de variação **Canais** (or): Email | InApp. Assina os eventos de domínio
publicados pelos outros serviços (coreografia).
"""
from common.service import create_service

from .controller import router

app = create_service("notifications", "Notifications Service", __doc__, router, bindings=["notification_channels"])
