"""Recommendation Service · porta 8004 — Feature **Recomendação por perfil (histórico)** (obrigatória).

Ponto de variação **Estratégia** (xor): BaseadaConteudo | Popularidade | Hibrida.
"""
from common.service import create_service

from .controller import router

app = create_service("recommendation", "Recommendation Service", __doc__, router, bindings=["recommendation_strategy"])
