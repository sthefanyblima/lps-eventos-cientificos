"""Repository — acesso a dados do Events Service."""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from common.seed import seed_data

from .model import Sessao, Tag, Trilha


def _parse(day: str, start: str):
    y, m, d = map(int, day.split("-"))
    hh, mm = map(int, start.split(":"))
    return date(y, m, d), time(hh, mm)


def seed(s: Session, tenant: str) -> None:
    if s.scalar(select(Sessao.id).limit(1)):
        return
    repo = EventRepository(s)
    for x in seed_data()["sessions"]:
        repo.add_session(x["title"], x["track"], x["tags"], x["speaker"], x["day"], x["start"], x["room"], x["kind"])


class EventRepository:
    def __init__(self, session: Session):
        self.s = session

    def _track(self, name: str | None) -> Trilha | None:
        if not name:
            return None
        t = self.s.scalar(select(Trilha).where(Trilha.nome == name))
        if not t:
            t = Trilha(nome=name)
            self.s.add(t)
            self.s.flush()
        return t

    def _tag(self, name: str) -> Tag:
        t = self.s.scalar(select(Tag).where(Tag.nome == name))
        if not t:
            t = Tag(nome=name)
            self.s.add(t)
            self.s.flush()
        return t

    def add_session(self, title, track, tags, speaker, day, start, room, kind) -> Sessao:
        d, h = _parse(day, start)
        s = Sessao(titulo=title, trilha=self._track(track), palestrante=speaker, dia=d, inicio=h, sala=room, tipo=kind,
                   tags=[self._tag(t.strip().lower()) for t in dict.fromkeys(tags) if t.strip()])
        self.s.add(s)
        self.s.flush()
        return s

    def list_sessions(self) -> list[Sessao]:
        q = select(Sessao).options(selectinload(Sessao.tags), selectinload(Sessao.trilha)).order_by(Sessao.dia, Sessao.inicio)
        return list(self.s.scalars(q))

    def get(self, sid: int) -> Sessao | None:
        return self.s.get(Sessao, sid)

    def tracks(self) -> list[str]:
        return list(self.s.scalars(select(Trilha.nome).order_by(Trilha.nome)))
