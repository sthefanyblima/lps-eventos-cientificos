"""Configuração dos testes: usa o produto SBES 2026 como produto ativo."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PRODUCT_CONFIG", str(ROOT / "products" / "sbes-2026.json"))
