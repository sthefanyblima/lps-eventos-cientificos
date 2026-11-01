"""Cliente HTTP entre microservices, protegido por Circuit Breaker.

Toda comunicação entre serviços é REST. Se o serviço remoto não faz parte do
produto (feature não selecionada) ou está fora do ar, a chamada degrada de forma
graciosa e retorna ``default`` — princípio *isolate failure*.
"""
from __future__ import annotations

import logging

import httpx

from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .config import service_url, tenant_id

log = logging.getLogger("client")
_breakers: dict[str, CircuitBreaker] = {}


def _breaker(service: str) -> CircuitBreaker:
    return _breakers.setdefault(service, CircuitBreaker(service))


def call(service: str, method: str, path: str, tenant: str | None = None, default=None,
         timeout: float = 5.0, **kwargs):
    base = service_url(service)
    if base is None:                      # serviço não incluído no produto
        return default
    headers = {"X-Tenant": tenant or tenant_id()}

    def _do():
        r = httpx.request(method, base + path, headers=headers, timeout=timeout, **kwargs)
        if r.status_code >= 500:
            raise httpx.HTTPStatusError("erro remoto", request=r.request, response=r)
        return r

    try:
        r = _breaker(service).call(_do)
    except (httpx.HTTPError, CircuitOpenError) as exc:
        log.warning("Falha ao chamar %s %s: %s", service, path, exc)
        return default
    if r.status_code >= 400:
        return default
    return r.json() if r.content else default


def breaker_states() -> dict[str, str]:
    return {k: b.state for k, b in _breakers.items()}
