"""Repository — acesso a dados do Users Service (único ponto que fala SQL/ORM)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.security import hash_password
from common.seed import seed_data

from .model import HistoricoInteracao, Interesse, Usuario

DEMO_PASSWORD = "senha123"


def seed(s: Session, tenant: str) -> None:
    if s.scalar(select(Usuario.id).limit(1)):
        return
    data = seed_data()
    for u in data["users"]:
        s.add(Usuario(nome=u["name"], email=u["email"], papel=u["role"], senha_hash=hash_password(DEMO_PASSWORD),
                      interesses=[Interesse(termo=t) for t in u["interests"]]))
    s.flush()
    for h in data["history"]:
        s.add(HistoricoInteracao(usuario_id=h["user"], sessao_id=h["session"], acao=h["action"]))


class UserRepository:
    def __init__(self, session: Session):
        self.s = session

    def get(self, user_id: int) -> Usuario | None:
        return self.s.get(Usuario, user_id)

    def by_email(self, email: str) -> Usuario | None:
        return self.s.scalar(select(Usuario).where(Usuario.email == email.lower().strip()))

    def list(self) -> list[Usuario]:
        return list(self.s.scalars(select(Usuario).order_by(Usuario.id)))

    def add(self, user: Usuario) -> Usuario:
        self.s.add(user)
        self.s.flush()
        return user

    def replace_interests(self, user: Usuario, terms: list[str]) -> None:
        user.interesses.clear()
        self.s.flush()
        for t in dict.fromkeys(x.strip().lower() for x in terms if x.strip()):
            user.interesses.append(Interesse(termo=t))

    def add_history(self, user_id: int, session_id: int, action: str) -> HistoricoInteracao:
        h = HistoricoInteracao(usuario_id=user_id, sessao_id=session_id, acao=action)
        self.s.add(h)
        self.s.flush()
        return h

    def history(self, user_id: int | None = None) -> list[HistoricoInteracao]:
        q = select(HistoricoInteracao).order_by(HistoricoInteracao.id)
        if user_id is not None:
            q = q.where(HistoricoInteracao.usuario_id == user_id)
        return list(self.s.scalars(q))
