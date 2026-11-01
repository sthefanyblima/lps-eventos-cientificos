"""Repository — persistência da memória de longo prazo e da caixa-preta do agente."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .model import Conhecimento, MemoriaEvento, RegistroCaixaPreta


class MemoryRepository:
    def __init__(self, session: Session):
        self.s = session

    def add_event(self, user_id: int, role: str, text: str) -> None:
        self.s.add(MemoriaEvento(usuario_id=user_id, papel=role, texto=text[:4000]))

    def recent_events(self, user_id: int, n: int = 6) -> list[MemoriaEvento]:
        q = select(MemoriaEvento).where(MemoriaEvento.usuario_id == user_id).order_by(MemoriaEvento.id.desc()).limit(n)
        return list(reversed(list(self.s.scalars(q))))

    def count_events(self, user_id: int) -> int:
        return len(list(self.s.scalars(select(MemoriaEvento.id).where(MemoriaEvento.usuario_id == user_id))))

    def put_knowledge(self, user_id: int, key: str, value: str) -> None:
        k = self.s.scalar(select(Conhecimento).where(Conhecimento.usuario_id == user_id, Conhecimento.chave == key))
        if not k:
            k = Conhecimento(usuario_id=user_id, chave=key)
            self.s.add(k)
        k.valor = value[:500]

    def knowledge(self, user_id: int) -> dict[str, str]:
        return {k.chave: k.valor for k in self.s.scalars(select(Conhecimento).where(Conhecimento.usuario_id == user_id))}

    def forget(self, user_id: int) -> None:
        self.s.execute(delete(MemoriaEvento).where(MemoriaEvento.usuario_id == user_id))
        self.s.execute(delete(Conhecimento).where(Conhecimento.usuario_id == user_id))


class BlackBoxRepository:
    def __init__(self, session: Session):
        self.s = session

    def save(self, request_id: str, user_id: int, records: list[dict]) -> None:
        for r in records:
            self.s.add(RegistroCaixaPreta(requisicao_id=request_id, usuario_id=user_id, ordem=r["order"],
                                          componente=r["component"], entrada=r["input"][:8000], saida=r["output"][:8000]))

    def by_request(self, request_id: str) -> list[RegistroCaixaPreta]:
        q = select(RegistroCaixaPreta).where(RegistroCaixaPreta.requisicao_id == request_id).order_by(RegistroCaixaPreta.ordem)
        return list(self.s.scalars(q))
