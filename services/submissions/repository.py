"""Repository — acesso a dados do Submissions Service."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from common.config import component
from common.seed import seed_data

from .model import Coautor, PalavraChave, Submissao


def seed(s: Session, tenant: str) -> None:
    """Trabalhos de demonstração do autor, no primeiro formato que o produto aceita."""
    if s.scalar(select(Submissao.id).limit(1)):
        return
    accepted = component("submission_formats", ["ArtigoCompleto"])
    repo = SubmissionRepository(s)
    for x in seed_data().get("submissions", []):
        fmt = next((f for f in x["formats"] if f in accepted), accepted[0])
        repo.add(x["author"], x["title"], x["abstract"], x["authors"], x["keywords"], fmt)


class SubmissionRepository:
    def __init__(self, session: Session):
        self.s = session

    def add(self, author_id, title, abstract, authors: list[str], keywords: list[str], fmt) -> Submissao:
        sub = Submissao(autor_id=author_id, titulo=title, resumo=abstract, formato=fmt,
                        coautores=[Coautor(nome=n, ordem=i + 1) for i, n in enumerate(authors)],
                        palavras=[PalavraChave(termo=k) for k in keywords])
        self.s.add(sub)
        self.s.flush()
        return sub

    def get(self, sid: int) -> Submissao | None:
        return self.s.get(Submissao, sid)

    def list(self, author_id: int | None = None) -> list[Submissao]:
        q = select(Submissao).options(selectinload(Submissao.coautores), selectinload(Submissao.palavras)).order_by(Submissao.id)
        if author_id:
            q = q.where(Submissao.autor_id == author_id)
        return list(self.s.scalars(q))
