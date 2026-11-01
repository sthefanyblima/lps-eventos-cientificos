"""Repository — acesso a dados do Reviews Service."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import Parecer


class ReviewRepository:
    def __init__(self, session: Session):
        self.s = session

    def upsert(self, submission_id, reviewer_id, reviewer_name, score, comment) -> Parecer:
        p = self.s.scalar(select(Parecer).where(Parecer.submissao_id == submission_id, Parecer.revisor_id == reviewer_id))
        if not p:
            p = Parecer(submissao_id=submission_id, revisor_id=reviewer_id)
            self.s.add(p)
        p.revisor_nome, p.nota, p.comentario = reviewer_name, score, comment
        self.s.flush()
        return p

    def by_submission(self, submission_id: int) -> list[Parecer]:
        return list(self.s.scalars(select(Parecer).where(Parecer.submissao_id == submission_id).order_by(Parecer.id)))

    def reviewed_by(self, reviewer_id: int) -> set[int]:
        return set(self.s.scalars(select(Parecer.submissao_id).where(Parecer.revisor_id == reviewer_id)))
