"""Service — recomendação baseada no perfil do usuário (interesses + histórico).

Monta o perfil consultando Users (interesses, histórico), Registration (agenda)
e Events (catálogo); a estratégia é um componente variável (Strategy) e cada
recomendação gerada é persistida no banco do serviço.
"""
from __future__ import annotations

from common.client import call
from common.config import component
from common.database import session_scope
from components.recommendation import rec_vp

from .model import Base
from .repository import RecommendationRepository

STRATEGY = rec_vp.create(component("recommendation_strategy", "BaseadaConteudo"))


class RecommendationService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("recommendation", self.tenant, Base)

    def profile(self, uid: int) -> dict | None:
        user = call("users", "GET", f"/users/{uid}", self.tenant)
        if not user:
            return None
        return {
            "user": user,
            "interests": user.get("interests", []),
            "history": call("users", "GET", f"/users/{uid}/history", self.tenant, default=[]),
            "agenda": call("registration", "GET", f"/agenda/{uid}/ids", self.tenant, default=[]),
        }

    def recommend(self, uid: int, k: int = 5) -> dict | None:
        prof = self.profile(uid)
        if prof is None:
            return None
        sessions = call("events", "GET", "/sessions", self.tenant, default=[])
        global_history = call("users", "GET", "/history", self.tenant, default=[])
        items = STRATEGY.recommend(prof, sessions, global_history, k)
        with self._tx() as s:
            RecommendationRepository(s).save_batch(uid, STRATEGY.feature_id, items)
        return {"user_id": uid, "strategy": STRATEGY.label, "variant": STRATEGY.feature_id,
                "based_on": {"interests": prof["interests"], "history_size": len(prof["history"])}, "items": items}

    def history(self, uid: int) -> list[dict]:
        with self._tx() as s:
            return [{"id": r.id, "session_id": r.sessao_id, "session_title": r.titulo_sessao, "score": round(r.score, 3),
                     "strategy": r.estrategia, "reason": r.motivo,
                     "generated_at": r.gerado_em.isoformat(sep=" ", timespec="seconds") if r.gerado_em else ""}
                    for r in RecommendationRepository(s).history(uid)]
