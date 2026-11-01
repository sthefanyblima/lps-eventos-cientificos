"""Repository — acesso a dados do Recommendation Service."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import Recomendacao


class RecommendationRepository:
    def __init__(self, session: Session):
        self.s = session

    def save_batch(self, user_id: int, strategy: str, items: list[dict]) -> None:
        for it in items:
            self.s.add(Recomendacao(usuario_id=user_id, sessao_id=it["id"], titulo_sessao=it["title"][:200],
                                    score=it["score"], estrategia=strategy, motivo=it["reason"][:300]))

    def history(self, user_id: int, limit: int = 30) -> list[Recomendacao]:
        q = (select(Recomendacao).where(Recomendacao.usuario_id == user_id)
             .order_by(Recomendacao.id.desc()).limit(limit))
        return list(self.s.scalars(q))
