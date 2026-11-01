"""Modelo de features (Engenharia de Domínio).

Carrega o ``feature_model.json`` e valida configurações de produto segundo a
semântica FODA:

* feature **mandatory**  -> obrigatória sempre que o pai estiver selecionado;
* feature **optional**   -> pode ou não ser selecionada;
* grupo **xor**          -> exatamente um filho quando o pai está selecionado;
* grupo **or**           -> pelo menos um filho quando o pai está selecionado;
* restrições cruzadas    -> ``requires`` e ``excludes``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "feature_model.json"


@dataclass
class Feature:
    id: str
    name: str
    type: str = "mandatory"            # mandatory | optional (ignorado para filhos de grupo)
    group: str | None = None           # xor | or  (aplica-se aos filhos)
    binding: str | None = None         # nome do ponto de variação (componente)
    service: str | None = None         # microservice que implementa a feature
    parent: "Feature | None" = None
    children: list["Feature"] = field(default_factory=list)

    @property
    def in_group(self) -> bool:
        return self.parent is not None and self.parent.group is not None

    @property
    def kind(self) -> str:
        """Tipo exibido no diagrama: mandatory, optional, xor-child, or-child."""
        if self.in_group:
            return f"{self.parent.group}-child"
        return self.type


class FeatureModel:
    def __init__(self, data: dict):
        self.raw = data
        self.name = data["name"]
        self.features: dict[str, Feature] = {}
        self.root = self._build(data["root"], None)
        self.constraints = data.get("constraints", [])

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MODEL) -> "FeatureModel":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def _build(self, node: dict, parent: Feature | None) -> Feature:
        f = Feature(
            id=node["id"], name=node["name"], type=node.get("type", "mandatory"),
            group=node.get("group"), binding=node.get("binding"),
            service=node.get("service"), parent=parent,
        )
        if f.id in self.features:
            raise ValueError(f"Feature duplicada: {f.id}")
        self.features[f.id] = f
        f.children = [self._build(c, f) for c in node.get("children", [])]
        return f

    # ------------------------------------------------------------------ util
    def walk(self, f: Feature | None = None) -> Iterable[Feature]:
        f = f or self.root
        yield f
        for c in f.children:
            yield from self.walk(c)

    def variation_points(self) -> list[Feature]:
        """Features com grupo xor/or = pontos de variação; filhos = variantes."""
        return [f for f in self.walk() if f.group]

    def complete(self, selected: Iterable[str]) -> set[str]:
        """Propaga seleção: adiciona ancestrais e filhas obrigatórias."""
        sel = set(selected) | {self.root.id}
        changed = True
        while changed:
            changed = False
            for fid in list(sel):
                f = self.features.get(fid)
                if not f:
                    continue
                if f.parent and f.parent.id not in sel:
                    sel.add(f.parent.id); changed = True
                if not f.group:
                    for c in f.children:
                        if c.type == "mandatory" and c.id not in sel:
                            sel.add(c.id); changed = True
        return sel

    # ------------------------------------------------------------- validação
    def validate(self, selected: Iterable[str]) -> list[str]:
        sel = set(selected)
        errors: list[str] = []
        for fid in sel:
            if fid not in self.features:
                errors.append(f"Feature desconhecida: {fid}")
        if self.root.id not in sel:
            errors.append(f"A raiz '{self.root.name}' deve estar selecionada")
        for f in self.walk():
            on = f.id in sel
            if on and f.parent and f.parent.id not in sel:
                errors.append(f"'{f.name}' exige o pai '{f.parent.name}'")
            if not on:
                continue
            chosen = [c for c in f.children if c.id in sel]
            if f.group == "xor" and len(chosen) != 1:
                errors.append(f"'{f.name}' (alternativo/xor) exige exatamente 1 variante (selecionadas: {len(chosen)})")
            elif f.group == "or" and len(chosen) < 1:
                errors.append(f"'{f.name}' (grupo or) exige ao menos 1 variante")
            elif not f.group:
                for c in f.children:
                    if c.type == "mandatory" and c.id not in sel:
                        errors.append(f"'{c.name}' é obrigatória quando '{f.name}' está selecionada")
        for c in self.constraints:
            a, b = c["from"], c["to"]
            fa, fb = self.features[a].name, self.features[b].name
            if c["type"] == "requires" and a in sel and b not in sel:
                errors.append(f"Restrição: '{fa}' requer '{fb}'")
            if c["type"] == "excludes" and a in sel and b in sel:
                errors.append(f"Restrição: '{fa}' exclui '{fb}'")
        return errors

    def to_tree(self, f: Feature | None = None) -> dict:
        """Representação serializável usada pelo configurador web."""
        f = f or self.root
        return {
            "id": f.id, "name": f.name, "kind": f.kind, "group": f.group,
            "service": f.service, "binding": f.binding,
            "children": [self.to_tree(c) for c in f.children],
        }
