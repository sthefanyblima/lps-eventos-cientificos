"""Carrega os dados de demonstração compartilhados (seeds/seed.json)."""
import json
from functools import lru_cache

from .config import ROOT


@lru_cache(maxsize=1)
def seed_data() -> dict:
    return json.loads((ROOT / "seeds" / "seed.json").read_text(encoding="utf-8"))
