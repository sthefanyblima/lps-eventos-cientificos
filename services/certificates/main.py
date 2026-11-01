"""Certificates Service · porta 8007 — Feature **Emissão de Certificados** (opcional).

Ponto de variação **Tipos** (or): CertParticipacao | CertApresentacao (requires Submissão e Revisão).
"""
from common.service import create_service

from .controller import router

app = create_service("certificates", "Certificates Service", __doc__, router, bindings=["certificate_types"])
