"""Linha de comando da LPS.

Exemplos::

    python -m spl.cli tree                         # mostra o diagrama de features em texto
    python -m spl.cli list                         # produtos já derivados
    python -m spl.cli validate products/sbes-2026.json
    python -m spl.cli derive "Meu Evento" Gratuito Popularidade Certificados CertParticipacao InApp Notificacoes
    python -m spl.cli run sbes-2026                # sobe microservices + gateway
    python -m spl.cli configurator                 # seletor de features web (porta 7000)
"""
from __future__ import annotations

import argparse
import json
import sys

from .derivation import PRODUCTS_DIR, derive, save
from .feature_model import FeatureModel

SYMBOL = {"mandatory": "●", "optional": "○", "xor-child": "◇", "or-child": "◆"}


def print_tree(model, f=None, prefix=""):
    f = f or model.root
    grp = f"  [{f.group.upper()}]" if f.group else ""
    svc = f"  → {f.service}" if f.service else ""
    print(f"{prefix}{SYMBOL.get(f.kind, '●')} {f.name} ({f.id}){grp}{svc}")
    for c in f.children:
        print_tree(model, c, prefix + "    ")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="spl", description="LPS de Sistemas de Gerenciamento de Eventos Científicos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tree")
    sub.add_parser("list")
    v = sub.add_parser("validate"); v.add_argument("product")
    d = sub.add_parser("derive"); d.add_argument("name"); d.add_argument("features", nargs="*")
    d.add_argument("--id"); d.add_argument("--theme", default="#2563eb")
    r = sub.add_parser("run"); r.add_argument("product")
    c = sub.add_parser("configurator"); c.add_argument("--port", type=int, default=7000)
    args = ap.parse_args(argv)
    model = FeatureModel.load()

    if args.cmd == "tree":
        print("● obrigatória  ○ opcional  ◇ alternativa (xor)  ◆ or\n")
        print_tree(model)
        for c in model.constraints:
            print(f"  restrição: {c['from']} {c['type']} {c['to']}")
    elif args.cmd == "list":
        for p in sorted(PRODUCTS_DIR.glob("*.json")):
            cfg = json.loads(p.read_text(encoding="utf-8"))
            print(f"{cfg['id']:<18}{cfg['name']:<62}{len(cfg['services'])} microservices")
    elif args.cmd == "validate":
        cfg = json.loads(open(args.product, encoding="utf-8").read())
        errs = model.validate(cfg["features"])
        print("Configuração válida ✔" if not errs else "\n".join("✘ " + e for e in errs))
        sys.exit(1 if errs else 0)
    elif args.cmd == "derive":
        try:
            prod = derive(model, args.features, args.name, args.id, theme=args.theme)
        except ValueError as e:
            print("Configuração inválida:\n  ✘ " + str(e).replace("; ", "\n  ✘ ")); sys.exit(1)
        cfg, comp = save(prod)
        print(f"Produto '{prod['name']}' derivado:\n  {cfg}\n  {comp}")
        print("Microservices:", ", ".join(prod["services"]))
        print("Componentes:", json.dumps(prod["components"], ensure_ascii=False))
    elif args.cmd == "run":
        from .launcher import run_forever
        run_forever(args.product)
    elif args.cmd == "configurator":
        import uvicorn
        uvicorn.run("spl.configurator:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
