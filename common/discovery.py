"""Cliente do Service Registry (descoberta de serviços, papel do Eureka).

* Ao iniciar, cada microservice se **registra** (nome, URL, feature, porta).
* A cada 10 s envia um **heartbeat**; sem heartbeat por 30 s ele fica DOWN.
* Gateway e serviços **descobrem** endereços consultando o registry, com cache
  local de 10 s. Se o registry cair, usam a configuração do produto.
"""
from __future__ import annotations

import logging
import threading
import time

import httpx

from .config import registry_url

log = logging.getLogger("discovery")
_cache: dict[str, tuple[float, str | None]] = {}
TTL = 10.0


def lookup(name: str) -> str | None:
    now = time.monotonic()
    hit = _cache.get(name)
    if hit and now - hit[0] < TTL:
        return hit[1]
    url = None
    try:
        r = httpx.get(f"{registry_url()}/registry/services/{name}", timeout=1.5)
        if r.status_code == 200 and r.json().get("status") == "UP":
            url = r.json()["url"]
    except httpx.HTTPError:
        pass
    _cache[name] = (now, url)
    return url


def register(name: str, url: str, port: int, feature: str | None, title: str) -> None:
    """Registra o serviço e mantém heartbeat em thread de fundo."""
    body = {"name": name, "url": url, "port": port, "feature": feature, "title": title}

    def loop():
        registered = False
        while True:
            try:
                if not registered:
                    httpx.post(f"{registry_url()}/registry/register", json=body, timeout=2).raise_for_status()
                    registered = True
                    log.info("Registrado no Service Registry: %s -> %s", name, url)
                else:
                    r = httpx.put(f"{registry_url()}/registry/heartbeat/{name}", timeout=2)
                    if r.status_code == 404:
                        registered = False
            except httpx.HTTPError:
                registered = False
            time.sleep(10 if registered else 2)

    threading.Thread(target=loop, daemon=True, name=f"heartbeat-{name}").start()
