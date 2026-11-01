"""Ponto de variação **Estratégia de Recomendação** (xor):
BaseadaConteudo | Popularidade | Hibrida.

Entrada comum a todas as estratégias:
* ``profile``  -> interesses declarados + histórico do usuário (sessões vistas,
  favoritadas, adicionadas à agenda);
* ``sessions`` -> catálogo da programação;
* ``global_history`` -> interações de todos os usuários (para popularidade).
"""
from __future__ import annotations

import math
import re
import unicodedata
from abc import ABC, abstractmethod
from collections import Counter

from .base import VariationPoint

ACTION_WEIGHT = {"view": 1.0, "favorite": 2.0, "agenda": 3.0}
STOP = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o", "as", "os", "um", "uma", "no", "na", "por", "the", "of", "and", "in"}


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+", text) if len(t) > 2 and t not in STOP]


def session_terms(s: dict) -> Counter:
    c = Counter(tokens(s.get("title", "")))
    for tag in s.get("tags", []):
        c.update({t: 3 for t in tokens(tag)})          # tags pesam mais
    c.update({t: 1 for t in tokens(s.get("track", "") or "")})
    return c


def cosine(a: Counter, b: Counter) -> float:
    num = sum(a[k] * b[k] for k in set(a) & set(b))
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


class RecommendationStrategy(ABC):
    label = "?"

    @abstractmethod
    def score(self, profile: dict, sessions: list[dict], global_history: list[dict]) -> dict[int, tuple[float, str]]:
        """Retorna {session_id: (score, justificativa)}."""

    def recommend(self, profile, sessions, global_history, k=5) -> list[dict]:
        seen = {h["session_id"] for h in profile.get("history", []) if h["action"] == "agenda"}
        seen |= set(profile.get("agenda", []))
        scores = self.score(profile, sessions, global_history)
        ranked = sorted((s for s in sessions if s["id"] not in seen),
                        key=lambda s: scores.get(s["id"], (0, ""))[0], reverse=True)
        out = []
        for s in ranked[:k]:
            sc, why = scores.get(s["id"], (0.0, ""))
            out.append({**s, "score": round(sc, 3), "reason": why})
        return out


rec_vp: VariationPoint[RecommendationStrategy] = VariationPoint("recommendation_strategy", RecommendationStrategy)


@rec_vp.variant("BaseadaConteudo")
class ContentBased(RecommendationStrategy):
    label = "Baseada em conteúdo"

    def user_vector(self, profile, sessions) -> Counter:
        by_id = {s["id"]: s for s in sessions}
        vec = Counter()
        for interest in profile.get("interests", []):
            vec.update({t: 4 for t in tokens(interest)})
        for h in profile.get("history", []):
            s = by_id.get(h["session_id"])
            if s:
                w = ACTION_WEIGHT.get(h["action"], 1.0)
                for t, v in session_terms(s).items():
                    vec[t] += v * w
        return vec

    def score(self, profile, sessions, global_history):
        uv = self.user_vector(profile, sessions)
        out = {}
        for s in sessions:
            sv = session_terms(s)
            common = sorted(set(uv) & set(sv), key=lambda t: -uv[t] * sv[t])[:3]
            why = ("Relacionada ao seu perfil: " + ", ".join(common)) if common else "Explorar novos temas"
            out[s["id"]] = (cosine(uv, sv), why)
        return out


@rec_vp.variant("Popularidade")
class Popularity(RecommendationStrategy):
    label = "Popularidade"

    def score(self, profile, sessions, global_history):
        pop = Counter()
        for h in global_history:
            pop[h["session_id"]] += ACTION_WEIGHT.get(h["action"], 1.0)
        top = max(pop.values(), default=1)
        return {s["id"]: (pop[s["id"]] / top, f"Popular entre participantes ({int(pop[s['id']])} interações)")
                for s in sessions}


@rec_vp.variant("Hibrida")
class Hybrid(RecommendationStrategy):
    label = "Híbrida"
    alpha = 0.7  # peso do conteúdo

    def score(self, profile, sessions, global_history):
        c = ContentBased().score(profile, sessions, global_history)
        p = Popularity().score(profile, sessions, global_history)
        return {sid: (self.alpha * c[sid][0] + (1 - self.alpha) * p[sid][0],
                      c[sid][1] + f" · {p[sid][1].lower()}") for sid in c}
