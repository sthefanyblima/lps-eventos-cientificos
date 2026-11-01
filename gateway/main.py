"""API Gateway — porta 8080. Ponto único de entrada do produto derivado (papel do Zuul).

Responsabilidades
-----------------
1. **Autenticação** — ``_verify_token`` valida o JWT do cabeçalho
   ``Authorization: Bearer`` chamando o Users Service (``/auth/verify-token``),
   com cache de 60 s. Rotas públicas (login, cadastro, programação, verificação
   de certificado) dispensam token.
2. **Descoberta + roteamento** — ``_proxy_request`` resolve o endereço do
   microservice no **Service Registry** (Eureka) e encaminha
   ``/api/<servico>/<caminho>``. Microservice fora do produto → 404 "feature não
   incluída"; fora do ar → 503 (Circuit Breaker).
3. **Multi-tenancy e identidade** — injeta ``X-Tenant`` (id do produto, como o
   parâmetro *tenant* do WISE) e ``X-User-Id``/``X-User-Role`` vindos do token.
4. **Observabilidade** — ``/api/ports`` e ``/ports`` mostram porta, status e
   heartbeat de todos os microservices registrados.
5. **Frontend** — serve a interface web do produto em ``/``.

Rotas
-----
=====================  =====================================================
GET  /api/product      Produto ativo: nome, features, variantes, serviços (público)
GET  /api/ports        JSON com porta, URL, status e heartbeat de cada serviço
GET  /ports            Página HTML com a tabela de portas (item 6.4)
ANY  /api/{svc}/{p}    Proxy reverso autenticado para o microservice ``svc``
GET  /                 Frontend (SPA) do produto
=====================  =====================================================
"""
from __future__ import annotations

import re
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from common.circuit_breaker import CircuitBreaker
from common.config import ROOT, product, registry_url, service_url

app = FastAPI(title="API Gateway — LPS Eventos Científicos", description=__doc__, version="2.0.0")
_client = httpx.AsyncClient(timeout=60)
_breakers: dict[str, CircuitBreaker] = {}
_token_cache: dict[str, tuple[float, dict]] = {}
HOP_HEADERS = {"host", "content-length", "connection", "transfer-encoding", "content-encoding",
               "x-user-id", "x-user-role", "x-tenant"}

# (método, regex do caminho "<svc>/<path>") que não exigem token
PUBLIC_ROUTES = [
    ("POST", r"^users/auth/(login|register|verify-token)$"),
    ("GET", r"^users/auth/demo-accounts$"),
    ("GET", r"^events/(event|sessions(/\d+)?|tracks)$"),
    ("GET", r"^certificates/(verify|view)/\w+$"),
    ("GET", r"^registration/payment-method$"),
    ("GET", r"^submissions/formats$"),
    ("GET", r"^reviews/policy$"),
    ("GET", r"^ai_agent/architecture$"),
]


def _is_public(method: str, svc: str, path: str) -> bool:
    target = f"{svc}/{path}".rstrip("/")
    return any(method == m and re.match(rx, target) for m, rx in PUBLIC_ROUTES)


async def _verify_token(request: Request) -> dict | None:
    """Valida o JWT no Users Service; devolve as claims ou ``None``."""
    auth = request.headers.get("Authorization", "")
    token = auth.split(" ")[-1] if auth.lower().startswith("bearer ") else None
    if not token:
        return None
    hit = _token_cache.get(token)
    if hit and time.monotonic() - hit[0] < 60:
        return hit[1]
    base = service_url("users")
    try:
        r = await _client.post(f"{base}/auth/verify-token", json={"token": token},
                               headers={"X-Tenant": product()["id"]}, timeout=3)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    claims = r.json()
    _token_cache[token] = (time.monotonic(), claims)
    return claims


@app.get("/api/product", tags=["produto"], summary="Configuração pública do produto ativo")
def product_info():
    p = product()
    return {k: p[k] for k in ("id", "name", "theme", "features", "components", "services", "gateway")}


async def _registered() -> dict[str, dict]:
    try:
        r = await _client.get(f"{registry_url()}/registry/services", timeout=2)
        return {i["name"]: i for i in r.json()}
    except (httpx.HTTPError, ValueError):
        return {}


@app.get("/api/ports", tags=["observabilidade"], summary="Portas e saúde de todos os microservices")
async def ports():
    p = product()
    reg = await _registered()
    items = [
        {"service": "registry", "title": "Service Registry (Eureka)", "feature": "núcleo", "port": 8761,
         "url": registry_url(), "status": "UP" if reg or await _ping(registry_url() + "/health") else "DOWN",
         "heartbeat": "—"},
        {"service": "gateway", "title": "API Gateway", "feature": "núcleo", "port": p["gateway"]["port"],
         "url": p["gateway"]["url"], "status": "UP", "heartbeat": "—"},
    ]
    for name, info in p["services"].items():
        r = reg.get(name)
        items.append({"service": name, "title": info["title"], "feature": info["feature"], "port": info["port"],
                      "url": r["url"] if r else info["url"], "status": r["status"] if r else "NÃO REGISTRADO",
                      "heartbeat": f"{r['seconds_since_heartbeat']} s" if r else "—"})
    return {"product": p["name"], "database": "MySQL (um banco por serviço e por tenant)", "services": items}


async def _ping(url: str) -> bool:
    try:
        return (await _client.get(url, timeout=1)).status_code == 200
    except httpx.HTTPError:
        return False


@app.get("/ports", response_class=HTMLResponse, include_in_schema=False)
async def ports_page():
    data = await ports()
    trs = "".join(
        f"<tr><td><b>{s['title']}</b><br><code>{s['service']}</code></td><td>{s['feature']}</td>"
        f"<td class=port>{s['port']}</td><td><code>{s['url']}</code></td>"
        f"<td><span class='st {'up' if s['status'] == 'UP' else 'down'}'>{s['status']}</span></td>"
        f"<td>{s['heartbeat']}</td></tr>" for s in data["services"])
    return f"""<!doctype html><html lang=pt-br><meta charset=utf-8><title>Portas dos microservices</title>
<style>body{{font-family:system-ui,sans-serif;margin:32px;background:#f8fafc;color:#0f172a}}
table{{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px #0002}}
th,td{{padding:10px 14px;border-bottom:1px solid #e2e8f0;text-align:left}}th{{background:#0f172a;color:#fff}}
.port{{font:700 18px ui-monospace,monospace}}.st{{padding:3px 10px;border-radius:99px;font-weight:600}}
.up{{background:#dcfce7;color:#166534}}.down{{background:#fee2e2;color:#991b1b}}</style>
<h1>Microservices em execução</h1><p>Produto: <b>{data['product']}</b> · {len(data['services'])} processos ·
banco: {data['database']} · endereços resolvidos pelo Service Registry</p>
<table><tr><th>Microservice</th><th>Feature</th><th>Porta</th><th>URL</th><th>Status</th><th>Último heartbeat</th></tr>{trs}</table>
<p><a href="/">← voltar ao produto</a> · <a href="http://127.0.0.1:8761/">painel do registry</a> · <a href="/docs">Swagger do gateway</a></p></html>"""


@app.api_route("/api/{svc}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], tags=["proxy"],
               summary="Proxy reverso autenticado para o microservice")
async def proxy(svc: str, path: str, request: Request):
    return await _proxy_request(svc, path, request)


async def _proxy_request(svc: str, path: str, request: Request) -> Response:
    """Autentica (se a rota não for pública), descobre o serviço e encaminha a requisição."""
    if svc not in product()["services"]:
        raise HTTPException(404, f"Microservice '{svc}' não faz parte do produto (feature não selecionada)")
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
    headers["X-Tenant"] = product()["id"]
    headers["X-Forwarded-From-Gateway"] = "true"
    claims = await _verify_token(request)
    if claims:
        headers["X-User-Id"], headers["X-User-Role"] = str(claims["user_id"]), claims["role"]
    elif not _is_public(request.method, svc, path):
        raise HTTPException(401, "Autenticação necessária (Authorization: Bearer <token>)")
    elif svc != "users" or not path.startswith("auth/"):
        headers["X-User-Id"], headers["X-User-Role"] = "0", "anonimo"   # público: identidade anônima

    base = service_url(svc)
    breaker = _breakers.setdefault(svc, CircuitBreaker(svc))
    if breaker.state == "OPEN":
        raise HTTPException(503, f"Circuito para '{svc}' aberto — serviço indisponível")
    try:
        r = await _client.request(request.method, f"{base}/{path}", params=request.query_params,
                                  content=await request.body(), headers=headers)
        if r.status_code >= 500:
            breaker.failures += 1
            if breaker.failures >= breaker.threshold:
                breaker.opened_at = time.monotonic()
        else:
            breaker.failures, breaker.opened_at = 0, None
    except httpx.HTTPError:
        breaker.failures += 1
        if breaker.failures >= breaker.threshold:
            breaker.opened_at = time.monotonic()
        raise HTTPException(503, f"Microservice '{svc}' indisponível")
    out_headers = {k: v for k, v in r.headers.items() if k.lower() not in HOP_HEADERS}
    out_headers["X-Served-By"] = f"{svc}:{product()['services'][svc]['port']}"
    return Response(r.content, status_code=r.status_code, headers=out_headers)


app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
