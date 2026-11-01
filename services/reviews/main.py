"""Reviews Service · porta 8006 — Feature **Revisão por Pares** (opcional; requires Submissão).

Ponto de variação **Política de revisão** (xor): SimplesCego | DuploCego | Aberta.
"""
from common.service import create_service

from .controller import router

app = create_service("reviews", "Reviews Service", __doc__, router, bindings=["review_policy"])
