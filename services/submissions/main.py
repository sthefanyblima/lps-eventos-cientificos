"""Submissions Service · porta 8005 — Feature **Submissão de Trabalhos** (opcional).

Ponto de variação **Formatos aceitos** (or): ArtigoCompleto | ResumoExpandido | Poster.
"""
from common.service import create_service

from .controller import router

app = create_service("submissions", "Submissions Service", __doc__, router, bindings=["submission_formats"])
