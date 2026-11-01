"""Registration Service · porta 8003 — Feature **Inscrição e Agenda** (obrigatória).

Ponto de variação **Pagamento** (xor): Gratuito | Pix | CartaoCredito — componente ``payment``.
"""
from common.service import create_service

from .controller import router

app = create_service("registration", "Registration Service", __doc__, router, bindings=["payment"])
