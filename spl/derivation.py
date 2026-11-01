"""Derivação de produtos (Engenharia de Aplicação).

A partir de uma seleção de features válida, resolve os pontos de variação e
gera os artefatos de um produto concreto:

* ``products/<id>.json``           -> configuração do produto (parametrização);
* ``products/<id>.compose.yml``    -> docker-compose só com os microservices do produto.

O mapeamento feature -> microservice vem do atributo ``service`` do modelo; o
mapeamento ponto de variação -> componente vem do atributo ``binding``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .feature_model import FeatureModel, ROOT

PRODUCTS_DIR = ROOT / "products"

# Catálogo de microservices da LPS (ativos reutilizáveis do núcleo + opcionais).
SERVICE_CATALOG: dict[str, dict] = {
    "users":          {"port": 8001, "title": "Users Service",          "module": "services.users.main:app",          "db": "MySQL (lps_<tenant>_users)"},
    "events":         {"port": 8002, "title": "Events Service",         "module": "services.events.main:app",         "db": "MySQL (lps_<tenant>_events)"},
    "registration":   {"port": 8003, "title": "Registration Service",   "module": "services.registration.main:app",   "db": "MySQL (lps_<tenant>_registration)"},
    "recommendation": {"port": 8004, "title": "Recommendation Service", "module": "services.recommendation.main:app", "db": "MySQL (lps_<tenant>_recommendation)"},
    "submissions":    {"port": 8005, "title": "Submissions Service",    "module": "services.submissions.main:app",    "db": "MySQL (lps_<tenant>_submissions)"},
    "reviews":        {"port": 8006, "title": "Reviews Service",        "module": "services.reviews.main:app",        "db": "MySQL (lps_<tenant>_reviews)"},
    "certificates":   {"port": 8007, "title": "Certificates Service",   "module": "services.certificates.main:app",   "db": "MySQL (lps_<tenant>_certificates)"},
    "notifications":  {"port": 8008, "title": "Notifications Service",  "module": "services.notifications.main:app",  "db": "MySQL (lps_<tenant>_notifications)"},
    "ai_agent":       {"port": 8009, "title": "AI Agent Service",       "module": "services.ai_agent.main:app",       "db": "MySQL (lps_<tenant>_ai_agent)"},
}
GATEWAY = {"port": 8080, "title": "API Gateway", "module": "gateway.main:app"}
REGISTRY = {"port": 8761, "title": "Service Registry", "module": "services.registry.main:app"}


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "produto"


def derive(model: FeatureModel, selected: list[str], name: str, product_id: str | None = None,
           host: str = "127.0.0.1", theme: str = "#2563eb") -> dict:
    sel = model.complete(selected)
    errors = model.validate(sel)
    if errors:
        raise ValueError("; ".join(errors))

    services = {}
    for f in model.walk():
        if f.service and f.id in sel:
            meta = SERVICE_CATALOG[f.service]
            services[f.service] = {
                "port": meta["port"], "url": f"http://{host}:{meta['port']}",
                "title": meta["title"], "feature": f.id,
            }

    components: dict[str, object] = {}
    for vp in model.variation_points():
        if vp.id not in sel:
            continue
        chosen = [c.id for c in vp.children if c.id in sel]
        components[vp.binding] = chosen[0] if vp.group == "xor" else chosen

    pid = product_id or slugify(name)
    return {
        "id": pid,
        "name": name,
        "theme": theme,
        "features": sorted(sel),
        "services": services,
        "gateway": {"port": GATEWAY["port"], "url": f"http://{host}:{GATEWAY['port']}"},
        "registry": {"port": REGISTRY["port"], "url": f"http://{host}:{REGISTRY['port']}"},
        "components": components,
    }


def compose_yaml(product: dict) -> str:
    """Gera um docker-compose.yml só com os microservices do produto + MySQL + Registry + Gateway."""
    pid = product["id"]
    env = ["      PRODUCT_CONFIG: /app/products/%s.json" % pid, "      SERVICE_HOST_MODE: docker",
           "      DATABASE_URL: mysql+pymysql://lps:lps123@mysql:3306/{db}", "      REGISTRY_URL: http://registry:8761"]
    lines = ["# Gerado automaticamente pela LPS — produto: " + product["name"], "services:",
             "  mysql:", "    image: mysql:8.0", "    environment:", "      MYSQL_ROOT_PASSWORD: root",
             "      MYSQL_USER: lps", "      MYSQL_PASSWORD: lps123",
             "    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci",
             "    ports: [\"3306:3306\"]", "    volumes: [\"./mysql-init.sql:/docker-entrypoint-initdb.d/init.sql\", \"mysql-data:/var/lib/mysql\"]",
             "    healthcheck:", "      test: [\"CMD\", \"mysqladmin\", \"ping\", \"-h\", \"localhost\", \"-proot\"]",
             "      interval: 5s", "      retries: 20"]

    def block(name, module, port, depends):
        out = [f"  {name.replace('_', '-')}:", "    build: ..", f"    command: uvicorn {module} --host 0.0.0.0 --port {port}",
               "    environment:", *env, f"    ports: [\"{port}:{port}\"]"]
        if depends:
            out.append("    depends_on:")
            for d in depends:
                cond = "service_healthy" if d == "mysql" else "service_started"
                out += [f"      {d.replace('_', '-')}:", f"        condition: {cond}"]
        return out

    lines += block("registry", REGISTRY["module"], REGISTRY["port"], [])
    for svc, info in product["services"].items():
        lines += block(svc, SERVICE_CATALOG[svc]["module"], info["port"], ["mysql", "registry"])
    lines += block("gateway", GATEWAY["module"], GATEWAY["port"], ["registry", *product["services"]])
    lines += ["volumes:", "  mysql-data:"]
    return "\n".join(lines) + "\n"


MYSQL_INIT = """-- Permite ao usuário da aplicação criar um banco por microservice e por tenant.
GRANT ALL PRIVILEGES ON *.* TO 'lps'@'%';
FLUSH PRIVILEGES;
"""


def save(product: dict) -> tuple[Path, Path]:
    PRODUCTS_DIR.mkdir(exist_ok=True)
    cfg = PRODUCTS_DIR / f"{product['id']}.json"
    cfg.write_text(json.dumps(product, indent=2, ensure_ascii=False), encoding="utf-8")
    comp = PRODUCTS_DIR / f"{product['id']}.compose.yml"
    comp.write_text(compose_yaml(product), encoding="utf-8")
    (PRODUCTS_DIR / "mysql-init.sql").write_text(MYSQL_INIT, encoding="utf-8")
    return cfg, comp
