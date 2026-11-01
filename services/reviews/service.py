"""Service — revisão por pares com política variável (Strategy)."""
from __future__ import annotations

from common.client import call
from common.config import component
from common.database import session_scope
from common.events import publish
from components.review_policy import review_vp

from .dto import ACCEPT_THRESHOLD
from .model import Base, Parecer
from .repository import ReviewRepository

POLICY = review_vp.create(component("review_policy", "SimplesCego"))


def to_dto(p: Parecer) -> dict:
    return {"id": p.id, "submission_id": p.submissao_id, "reviewer_id": p.revisor_id, "reviewer_name": p.revisor_nome,
            "score": p.nota, "comment": p.comentario,
            "created_at": p.criado_em.isoformat(sep=" ", timespec="seconds") if p.criado_em else ""}


class ReviewService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("reviews", self.tenant, Base)

    @staticmethod
    def policy() -> dict:
        return {"variant": POLICY.feature_id, "label": POLICY.label, "description": POLICY.describe()}

    def queue(self, reviewer_id: int) -> list[dict]:
        """Submissões para o revisor, já anonimizadas pela política."""
        subs = call("submissions", "GET", "/submissions", self.tenant, default=[])
        with self._tx() as s:
            done = ReviewRepository(s).reviewed_by(reviewer_id)
        return [{**POLICY.submission_for_reviewer(x), "reviewed": x["id"] in done}
                for x in subs if x["author_id"] != reviewer_id]

    def submit(self, r) -> dict:
        reviewer = call("users", "GET", f"/users/{r.reviewer_id}", self.tenant) or {"name": f"Revisor {r.reviewer_id}"}
        with self._tx() as s:
            repo = ReviewRepository(s)
            repo.upsert(r.submission_id, r.reviewer_id, reviewer["name"], r.score, r.comment)
            scores = [p.nota for p in repo.by_submission(r.submission_id)]
        avg = sum(scores) / len(scores)
        status = "accepted" if avg >= ACCEPT_THRESHOLD else ("rejected" if avg < 0 else "under_review")
        sub = call("submissions", "PATCH", f"/submissions/{r.submission_id}/status", self.tenant, json={"status": status})
        if sub and status in ("accepted", "rejected"):
            word = "ACEITO" if status == "accepted" else "não aceito"
            publish("review.decided", sub["author_id"], "Resultado da revisão",
                    f"Seu trabalho \"{sub['title']}\" foi {word} (média {avg:.1f}).", self.tenant)
        return {"submission_id": r.submission_id, "average": round(avg, 2), "status": status, "reviews": len(scores)}

    def for_author(self, submission_id: int) -> list[dict]:
        with self._tx() as s:
            data = [to_dto(p) for p in ReviewRepository(s).by_submission(submission_id)]
        return [POLICY.review_for_author(x) for x in data]
