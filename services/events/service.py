"""Service — regras do Events Service. A feature *Trilhas* é resolvida por parametrização."""
from __future__ import annotations

import unicodedata

from common.config import has_feature, product
from common.database import session_scope

from .model import Base, Sessao
from .repository import EventRepository, seed


def _norm(t: str | None) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def to_dto(s: Sessao) -> dict:
    return {"id": s.id, "title": s.titulo, "track": (s.trilha.nome if s.trilha else None) if has_feature("Trilhas") else None,
            "tags": [t.nome for t in s.tags], "speaker": s.palestrante, "day": s.dia.isoformat(),
            "start": s.inicio.strftime("%H:%M"), "room": s.sala, "kind": s.tipo}


class EventService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("events", self.tenant, Base, seed)

    def event_info(self) -> dict:
        p = product()
        return {"tenant": self.tenant, "name": p["name"], "theme": p.get("theme"), "has_tracks": has_feature("Trilhas"),
                "period": "10 a 12 de novembro de 2026", "location": "Maceió — AL",
                "fee": 0.0 if p["components"].get("payment") == "Gratuito" else 150.0}

    def list_sessions(self, q=None, track=None, day=None) -> list[dict]:
        with self._tx() as s:
            data = [to_dto(x) for x in EventRepository(s).list_sessions()]
        if q:
            nq = _norm(q)
            data = [x for x in data if nq in _norm(x["title"]) or any(nq in _norm(t) for t in x["tags"])
                    or nq in _norm(x["speaker"]) or nq in _norm(x["track"])]
        if track and has_feature("Trilhas"):
            data = [x for x in data if x["track"] == track]
        if day:
            data = [x for x in data if x["day"] == day]
        return data

    def get(self, sid: int) -> dict | None:
        with self._tx() as s:
            x = EventRepository(s).get(sid)
            return to_dto(x) if x else None

    def create(self, body) -> dict:
        with self._tx() as s:
            x = EventRepository(s).add_session(body.title, body.track, body.tags, body.speaker, body.day, body.start,
                                               body.room, body.kind)
            return to_dto(x)

    def tracks(self) -> list[str]:
        with self._tx() as s:
            return EventRepository(s).tracks()
