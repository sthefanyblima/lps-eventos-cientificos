"""Configuração do produto em execução (técnica de *parametrização*).

Assim como no WISE (Tizzei et al., 2017), tudo o que varia entre produtos/tenants
fica fora do código, em um arquivo de configuração por produto. Cada
microservice lê ``PRODUCT_CONFIG`` e decide quais componentes instanciar.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / ".runtime" / "active_product.json"


@lru_cache(maxsize=1)
def product() -> dict:
    path = Path(os.environ.get("PRODUCT_CONFIG", RUNTIME))
    if not path.exists():
        raise RuntimeError(
            f"Configuração de produto não encontrada em {path}. "
            "Gere um produto com `python -m spl.cli derive` ou o configurador web."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def has_feature(feature_id: str) -> bool:
    return feature_id in product()["features"]


def component(binding: str, default=None):
    """Variante escolhida para um ponto de variação (ex.: ``payment`` -> ``Pix``)."""
    return product()["components"].get(binding, default)


REGISTRY_PORT = 8761


def registry_url() -> str:
    """Endereço do Service Registry (papel do Eureka na figura de referência)."""
    if os.environ.get("REGISTRY_URL"):
        return os.environ["REGISTRY_URL"]
    host = "registry" if os.environ.get("SERVICE_HOST_MODE") == "docker" else "127.0.0.1"
    return f"http://{host}:{REGISTRY_PORT}"


def static_service_url(name: str) -> str | None:
    """Endereço do serviço segundo a configuração do produto (fallback do registry)."""
    svc = product()["services"].get(name)
    if not svc:
        return None
    if os.environ.get("SERVICE_HOST_MODE") == "docker":
        return f"http://{name.replace('_', '-')}:{svc['port']}"
    return svc["url"]


def service_url(name: str) -> str | None:
    """Descoberta de serviço: consulta o registry; se ele estiver fora, usa a configuração."""
    if name not in product()["services"]:
        return None                      # feature não selecionada neste produto
    from .discovery import lookup         # import tardio evita ciclo
    return lookup(name) or static_service_url(name)


def tenant_id() -> str:
    return product()["id"]
