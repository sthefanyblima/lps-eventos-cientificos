"""Service Registry — porta 8761 (papel do **Eureka** na figura de referência).

Infraestrutura do núcleo da LPS (presente em todo produto). Cada microservice
se registra ao iniciar e envia heartbeat a cada 10 s; o API Gateway e os
próprios serviços descobrem endereços aqui, em vez de usar portas fixas no código.
O registro é mantido em memória, como no Eureka.

Rotas
-----
=======================================  ===========================================
POST /registry/register                  registra (ou re-registra) uma instância
PUT  /registry/heartbeat/{name}          renova a instância (sem heartbeat por 30 s → DOWN)
DELETE /registry/services/{name}         remove a instância
GET  /registry/services                  lista todas as instâncias com status
GET  /registry/services/{name}           resolve o endereço de um serviço
GET  /                                   painel HTML com os serviços registrados
=======================================  ===========================================
"""
from __future__ import annotations

import time
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Service Registry (Eureka-like)", description=__doc__, version="2.0.0")
LEASE = 30.0
_instances: dict[str, dict] = {}


class InstanceIn(BaseModel):
    name: str
    url: str
    port: int
    feature: str | None = None
    title: str = ""


def _view(i: dict) -> dict:
    age = time.time() - i["last_heartbeat"]
    return {**i, "status": "UP" if age <= LEASE else "DOWN", "seconds_since_heartbeat": round(age, 1),
            "registered_at": datetime.fromtimestamp(i["registered_at"]).strftime("%H:%M:%S")}


@app.post("/registry/register", tags=["registro"], summary="Registra uma instância de microservice")
def register(body: InstanceIn):
    now = time.time()
    _instances[body.name] = {**body.model_dump(), "registered_at": now, "last_heartbeat": now}
    return _view(_instances[body.name])


@app.put("/registry/heartbeat/{name}", tags=["registro"], summary="Renova o lease da instância")
def heartbeat(name: str):
    if name not in _instances:
        raise HTTPException(404, "Instância não registrada")
    _instances[name]["last_heartbeat"] = time.time()
    return {"name": name, "status": "UP"}


@app.delete("/registry/services/{name}", tags=["registro"], summary="Cancela o registro")
def deregister(name: str):
    _instances.pop(name, None)
    return {"removed": name}


@app.get("/registry/services", tags=["descoberta"], summary="Lista as instâncias registradas")
def services():
    return sorted((_view(i) for i in _instances.values()), key=lambda i: i["port"])


@app.get("/registry/services/{name}", tags=["descoberta"], summary="Resolve o endereço de um serviço")
def resolve(name: str):
    if name not in _instances:
        raise HTTPException(404, f"Serviço '{name}' não registrado")
    return _view(_instances[name])


@app.get("/health", include_in_schema=False)
def health():
    return {"service": "registry", "status": "UP"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    rows = "".join(
        f"<tr><td><b>{i['name'].upper()}</b><br><small>{i['title']}</small></td><td>{i['feature'] or '—'}</td>"
        f"<td class=p>{i['port']}</td><td><code>{i['url']}</code></td>"
        f"<td><span class='s {i['status'].lower()}'>{i['status']}</span></td><td>{i['seconds_since_heartbeat']} s</td>"
        f"<td>{i['registered_at']}</td></tr>" for i in services())
    return f"""<!doctype html><html lang=pt-br><meta charset=utf-8><meta http-equiv=refresh content=10>
<title>Service Registry</title><style>body{{font-family:system-ui,sans-serif;margin:32px;background:#f5f7f9;color:#1f2937}}
h1{{margin:0}}.sub{{color:#6b7280;margin:4px 0 20px}}table{{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px #0002}}
th{{background:#5a8f29;color:#fff;text-align:left}}th,td{{padding:9px 12px;border-bottom:1px solid #e5e7eb}}.p{{font:700 17px ui-monospace,monospace}}
.s{{padding:2px 10px;border-radius:99px;font-weight:600}}.up{{background:#dcfce7;color:#166534}}.down{{background:#fee2e2;color:#991b1b}}</style>
<h1>Service Registry</h1><p class=sub>Instâncias registradas (papel do Eureka) · porta 8761 · lease de {int(LEASE)} s</p>
<table><tr><th>Aplicação</th><th>Feature</th><th>Porta</th><th>URL</th><th>Status</th><th>Último heartbeat</th><th>Registrado às</th></tr>{rows}</table></html>"""
