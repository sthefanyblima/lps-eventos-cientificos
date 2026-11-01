"""Service — regras de negócio do Users Service: autenticação JWT, perfil e histórico."""
from __future__ import annotations

import jwt

from common.database import session_scope
from common.security import create_token, decode_token, hash_password, verify_password

from .model import Base, Usuario
from .repository import DEMO_PASSWORD, UserRepository, seed


class DomainError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def to_dto(u: Usuario) -> dict:
    return {"id": u.id, "name": u.nome, "email": u.email, "role": u.papel, "interests": [i.termo for i in u.interesses]}


def history_dto(h) -> dict:
    return {"id": h.id, "user_id": h.usuario_id, "session_id": h.sessao_id, "action": h.acao,
            "at": h.criado_em.isoformat(sep=" ", timespec="seconds") if h.criado_em else ""}


class UserService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("users", self.tenant, Base, seed)

    # ---- autenticação
    def login(self, email: str, password: str) -> dict:
        with self._tx() as s:
            u = UserRepository(s).by_email(email)
            if not u or not verify_password(password, u.senha_hash):
                raise DomainError(401, "E-mail ou senha inválidos")
            return {"access_token": create_token(u.id, u.papel, u.nome, self.tenant), "token_type": "bearer", "user": to_dto(u)}

    def register(self, data) -> dict:
        with self._tx() as s:
            repo = UserRepository(s)
            if repo.by_email(data.email):
                raise DomainError(409, "E-mail já cadastrado")
            u = repo.add(Usuario(nome=data.name, email=data.email.lower().strip(), papel=data.role,
                                 senha_hash=hash_password(data.password)))
            repo.replace_interests(u, data.interests)
            s.flush()
            return to_dto(u)

    def verify(self, token: str) -> dict:
        try:
            claims = decode_token(token)
        except jwt.InvalidTokenError as exc:
            raise DomainError(401, f"Token inválido: {exc}")
        if claims.get("tenant") != self.tenant:
            raise DomainError(401, "Token emitido para outro tenant")
        return {"valid": True, "user_id": int(claims["sub"]), "role": claims["role"], "name": claims["name"]}

    def demo_accounts(self) -> list[dict]:
        with self._tx() as s:
            return [{"name": u.nome, "email": u.email, "role": u.papel, "password": DEMO_PASSWORD}
                    for u in UserRepository(s).list()][:5]

    # ---- perfil
    def list(self) -> list[dict]:
        with self._tx() as s:
            return [to_dto(u) for u in UserRepository(s).list()]

    def get(self, user_id: int) -> dict:
        with self._tx() as s:
            u = UserRepository(s).get(user_id)
            if not u:
                raise DomainError(404, "Usuário não encontrado")
            return to_dto(u)

    def set_interests(self, user_id: int, interests: list[str]) -> dict:
        with self._tx() as s:
            repo = UserRepository(s)
            u = repo.get(user_id)
            if not u:
                raise DomainError(404, "Usuário não encontrado")
            repo.replace_interests(u, interests)
            s.flush()
            return to_dto(u)

    # ---- histórico (alimenta o Recommendation Service)
    def add_history(self, user_id: int, session_id: int, action: str) -> dict:
        with self._tx() as s:
            repo = UserRepository(s)
            if not repo.get(user_id):
                raise DomainError(404, "Usuário não encontrado")
            return history_dto(repo.add_history(user_id, session_id, action))

    def history(self, user_id: int | None = None) -> list[dict]:
        with self._tx() as s:
            return [history_dto(h) for h in UserRepository(s).history(user_id)]
