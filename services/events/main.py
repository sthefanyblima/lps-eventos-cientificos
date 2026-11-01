"""Events Service · porta 8002 — Feature **Gestão do Evento** (obrigatória).

Programação (sessões, tags) e Trilhas temáticas (opcional, resolvida por parametrização).
"""
from common.service import create_service

from .controller import router

app = create_service("events", "Events Service", __doc__, router)
