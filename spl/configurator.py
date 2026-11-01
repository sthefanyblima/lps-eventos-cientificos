"""Tela de Configuração (seletor de features) — porta 7000.

O engenheiro de aplicação marca as features desejadas; a tela valida a
configuração em tempo real contra o modelo de features, mostra os
microservices e componentes que serão usados, gera o produto e,
opcionalmente, já o coloca em execução.
"""
from __future__ import annotations

import json
import subprocess
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .derivation import PRODUCTS_DIR, SERVICE_CATALOG, derive, save
from .feature_model import ROOT, FeatureModel

app = FastAPI(title="Configurador da LPS", version="1.0.0")
MODEL = FeatureModel.load()
_running: subprocess.Popen | None = None


class Selection(BaseModel):
    features: list[str]
    name: str = "Novo Evento"
    theme: str = "#2563eb"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def page():
    return (ROOT / "spl" / "configurator.html").read_text(encoding="utf-8")


@app.get("/api/model")
def model():
    return {"name": MODEL.name, "tree": MODEL.to_tree(), "constraints": MODEL.constraints,
            "catalog": SERVICE_CATALOG}


@app.get("/api/products")
def products():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PRODUCTS_DIR.glob("*.json"))]


@app.post("/api/validate")
def validate(sel: Selection):
    full = MODEL.complete(sel.features)
    errors = MODEL.validate(full)
    preview = None
    if not errors:
        preview = derive(MODEL, list(full), sel.name, theme=sel.theme)
    return {"valid": not errors, "errors": errors, "features": sorted(full), "preview": preview}


@app.post("/api/derive")
def do_derive(sel: Selection):
    try:
        prod = derive(MODEL, sel.features, sel.name, theme=sel.theme)
    except ValueError as e:
        raise HTTPException(422, str(e))
    cfg, comp = save(prod)
    return {"product": prod, "files": [str(cfg.relative_to(ROOT)), str(comp.relative_to(ROOT))]}


@app.post("/api/run/{pid}")
def run(pid: str):
    global _running
    if not (PRODUCTS_DIR / f"{pid}.json").exists():
        raise HTTPException(404, "Produto não encontrado")
    if _running and _running.poll() is None:
        _running.terminate(); _running.wait(5)
    _running = subprocess.Popen([sys.executable, "-m", "spl.cli", "run", pid], cwd=ROOT)
    return {"started": pid, "url": "http://127.0.0.1:8080/", "ports": "http://127.0.0.1:8080/ports"}
