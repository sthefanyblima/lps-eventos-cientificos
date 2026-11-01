"""Users Service · porta 8001 — Feature **Gestão de Usuários** (obrigatória).

Autenticação (senha com PBKDF2 + token JWT), perfil de interesses e histórico
de interações — o histórico alimenta o Recommendation Service.

Organização interna (igual em todos os microservices):
controller.py → service.py → repository.py → model.py (+ dto.py)
"""
from common.service import create_service

from .controller import router

app = create_service("users", "Users Service", __doc__, router)
