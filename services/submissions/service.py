"""Service — submissões. Formatos aceitos = variantes do grupo *or* FormatoSubmissao."""
from __future__ import annotations

from common.config import component
from common.database import session_scope
from common.events import publish

from .model import Base, Submissao
from .repository import SubmissionRepository, seed

FORMATS = component("submission_formats", ["ArtigoCompleto"])
LABELS = {"ArtigoCompleto": "Artigo completo", "ResumoExpandido": "Resumo expandido", "Poster": "Pôster"}


def _split(text: str) -> list[str]:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def to_dto(x: Submissao) -> dict:
    return {"id": x.id, "author_id": x.autor_id, "title": x.titulo, "abstract": x.resumo,
            "authors": ", ".join(c.nome for c in x.coautores), "keywords": ", ".join(p.termo for p in x.palavras),
            "format": x.formato, "status": x.status,
            "created_at": x.criado_em.isoformat(sep=" ", timespec="seconds") if x.criado_em else ""}


class SubmissionService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("submissions", self.tenant, Base, seed)

    @staticmethod
    def formats() -> list[dict]:
        return [{"id": f, "label": LABELS[f]} for f in FORMATS]

    def create(self, body) -> dict:
        if body.format not in FORMATS:
            raise ValueError(f"Formato '{body.format}' não aceito neste evento. Aceitos: {FORMATS}")
        with self._tx() as s:
            out = to_dto(SubmissionRepository(s).add(body.author_id, body.title, body.abstract, _split(body.authors),
                                                      _split(body.keywords), body.format))
        publish("submission.created", body.author_id, "Submissão recebida", f"Recebemos \"{body.title}\" (#{out['id']}).", self.tenant)
        return out

    def get(self, sid: int) -> dict | None:
        with self._tx() as s:
            x = SubmissionRepository(s).get(sid)
            return to_dto(x) if x else None

    def list(self, author_id: int | None = None) -> list[dict]:
        with self._tx() as s:
            return [to_dto(x) for x in SubmissionRepository(s).list(author_id)]

    def set_status(self, sid: int, status: str) -> dict | None:
        with self._tx() as s:
            x = SubmissionRepository(s).get(sid)
            if not x:
                return None
            x.status = status
            return to_dto(x)
