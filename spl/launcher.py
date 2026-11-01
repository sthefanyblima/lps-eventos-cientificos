"""Executa um produto derivado: sobe cada microservice + API Gateway em sua porta."""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

from .derivation import GATEWAY, PRODUCTS_DIR, REGISTRY, SERVICE_CATALOG
from .feature_model import ROOT

RUNTIME = ROOT / ".runtime"


def resolve(product: str) -> Path:
    p = Path(product)
    if not p.exists():
        p = PRODUCTS_DIR / f"{product}.json"
    if not p.exists():
        raise SystemExit(f"Produto não encontrado: {product}")
    return p


def start(product: str, wait: bool = True) -> list[subprocess.Popen]:
    cfg_path = resolve(product)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    RUNTIME.mkdir(exist_ok=True)
    active = RUNTIME / "active_product.json"
    shutil.copy(cfg_path, active)
    env = {**os.environ, "PRODUCT_CONFIG": str(active), "PYTHONPATH": str(ROOT)}
    env.setdefault("DATABASE_URL", "mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}")
    logs = RUNTIME / "logs"
    logs.mkdir(exist_ok=True)

    procs = []
    targets = [("registry", REGISTRY["module"], REGISTRY["port"])]          # Service Registry sobe primeiro
    targets += [(n, SERVICE_CATALOG[n]["module"], i["port"]) for n, i in cfg["services"].items()]
    targets.append(("gateway", GATEWAY["module"], GATEWAY["port"]))
    for name, module, port in targets:
        log = open(logs / f"{name}.log", "w")
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT))
    (RUNTIME / "pids.json").write_text(json.dumps([p.pid for p in procs]))

    if wait:
        deadline = time.time() + 30
        pending = {n: p for n, _, p in targets}
        while pending and time.time() < deadline:
            for n, port in list(pending.items()):
                path = "/api/product" if n == "gateway" else "/health"
                try:
                    if httpx.get(f"http://127.0.0.1:{port}{path}", timeout=1).status_code == 200:
                        pending.pop(n)
                except httpx.HTTPError:
                    pass
            time.sleep(0.3)
        print(f"\nProduto: {cfg['name']}  (tenant: {cfg['id']})")
        print(f"{'MICROSERVICE':<16}{'PORTA':<8}STATUS")
        for n, _, port in targets:
            print(f"{n:<16}{port:<8}{'DOWN' if n in pending else 'UP'}")
        print(f"\nBanco de dados: {env['DATABASE_URL'].split('@')[-1]}")
        print(f"Interface:  http://127.0.0.1:{GATEWAY['port']}/")
        print(f"Registry:   http://127.0.0.1:{REGISTRY['port']}/")
        print(f"Portas:     http://127.0.0.1:{GATEWAY['port']}/ports")
        print(f"Swagger:    http://127.0.0.1:<porta>/docs\n")
    return procs


def stop_previous():
    pids = RUNTIME / "pids.json"
    if pids.exists():
        for pid in json.loads(pids.read_text()):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        pids.unlink()
        time.sleep(0.8)


def run_forever(product: str):
    stop_previous()
    procs = start(product)
    try:
        print("Ctrl+C para encerrar.")
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()
        (RUNTIME / "pids.json").unlink(missing_ok=True)
