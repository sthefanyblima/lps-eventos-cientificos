"""Fábrica de microservices — ativo reutilizável do núcleo da LPS.

Todo microservice criado por ``create_service`` ganha, sem escrever código:

* ``GET /health`` e ``GET /info`` (observabilidade, variantes ativas);
* registro automático no **Service Registry** + heartbeat (descoberta de serviço);
* as dependências ``tenant_header`` (multi-tenancy pelo cabeçalho ``X-Tenant``,
  como no WISE) e ``current_user`` (identidade repassada pelo API Gateway).

Cada serviço segue a mesma organização interna (figura de referência da disciplina):
``controller.py`` (API REST) → ``service.py`` (regras de negócio) →
``repository.py`` (acesso a dados) → ``model.py`` (entidades ORM), com ``dto.py``
(objetos de transferência validados pelo Pydantic).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI, Header, HTTPException

from .client import breaker_states
from .config import component, product, tenant_id
from .discovery import register

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def _public_url(name: str, port: int) -> str:
    if os.environ.get("SERVICE_HOST_MODE") == "docker":
        return f"http://{name.replace('_', '-')}:{port}"
    return f"http://127.0.0.1:{port}"


def create_service(name: str, title: str, description: str, router: APIRouter,
                   bindings: list[str] | None = None) -> FastAPI:
    svc = product()["services"].get(name, {})
    port = svc.get("port", 0)

    @asynccontextmanager
    async def lifespan(_app):
        register(name, _public_url(name, port), port, svc.get("feature"), title)
        yield

    app = FastAPI(title=title, description=description, version="2.0.0", lifespan=lifespan)

    @app.get("/health", tags=["observabilidade"], summary="Verifica se o microservice está ativo")
    def health():
        return {"service": name, "status": "UP", "product": product()["id"]}

    @app.get("/info", tags=["observabilidade"], summary="Feature e variantes resolvidas neste produto")
    def info():
        return {
            "service": name,
            "title": title,
            "product": product()["name"],
            "variants": {b: component(b) for b in (bindings or [])},
            "circuit_breakers": breaker_states(),
        }

    app.include_router(router)
    return app


def tenant_header(x_tenant: str | None = Header(default=None, alias="X-Tenant")) -> str:
    """Dependência FastAPI: tenant da requisição (padrão = produto ativo)."""
    return x_tenant or tenant_id()


@dataclass
class Caller:
    """Quem fez a requisição. ``internal`` = chamada direta entre microservices."""
    user_id: int | None
    role: str | None

    @property
    def internal(self) -> bool:
        return self.user_id is None

    def ensure_self_or(self, user_id: int, *roles: str) -> None:
        """Usuário só acessa os próprios dados, salvo papéis autorizados."""
        if self.internal or self.user_id == user_id or self.role in roles:
            return
        raise HTTPException(403, "Acesso negado a dados de outro usuário")

    def ensure_role(self, *roles: str) -> None:
        if self.internal or self.role in roles:
            return
        raise HTTPException(403, f"Requer papel: {', '.join(roles)}")


def current_user(x_user_id: str | None = Header(default=None, alias="X-User-Id"),
                 x_user_role: str | None = Header(default=None, alias="X-User-Role")) -> Caller:
    return Caller(int(x_user_id) if x_user_id else None, x_user_role)
