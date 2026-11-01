"""DTO — objetos de transferência (entrada/saída da API), validados pelo Pydantic."""
from __future__ import annotations

from pydantic import BaseModel, Field

ROLES = "^(participante|autor|revisor|organizador)$"


class LoginIn(BaseModel):
    email: str = Field(examples=["ana@exemplo.edu.br"])
    password: str = Field(examples=["senha123"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=3)
    email: str
    password: str = Field(min_length=6)
    role: str = Field(default="participante", pattern=ROLES)
    interests: list[str] = []


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    interests: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class VerifyIn(BaseModel):
    token: str


class InterestsIn(BaseModel):
    interests: list[str]


class HistoryIn(BaseModel):
    session_id: int
    action: str = Field(pattern="^(view|favorite|agenda)$", description="view | favorite | agenda")


class HistoryOut(BaseModel):
    id: int
    user_id: int
    session_id: int
    action: str
    at: str
