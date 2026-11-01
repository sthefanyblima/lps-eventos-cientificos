"""Model — entidades do Users Service (banco ``lps_<tenant>_users``).

Modelo relacional normalizado (3FN):
  usuario(id PK, nome, email UNIQUE, senha_hash, papel, criado_em)
  interesse(id PK, usuario_id FK→usuario, termo)            UNIQUE(usuario_id, termo)
  historico_interacao(id PK, usuario_id FK→usuario, sessao_id, acao, criado_em)

``sessao_id`` é referência lógica ao Events Service (database per service:
não há FK física entre bancos de microservices diferentes).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[str] = mapped_column(String(20), default="participante")
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    interesses: Mapped[list["Interesse"]] = relationship(back_populates="usuario", cascade="all, delete-orphan",
                                                          order_by="Interesse.id")
    historico: Mapped[list["HistoricoInteracao"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Interesse(Base):
    __tablename__ = "interesse"
    __table_args__ = (UniqueConstraint("usuario_id", "termo", name="uq_interesse_usuario_termo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    termo: Mapped[str] = mapped_column(String(80))
    usuario: Mapped[Usuario] = relationship(back_populates="interesses")


class HistoricoInteracao(Base):
    __tablename__ = "historico_interacao"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    sessao_id: Mapped[int] = mapped_column(Integer, index=True)
    acao: Mapped[str] = mapped_column(String(10))          # view | favorite | agenda
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    usuario: Mapped[Usuario] = relationship(back_populates="historico")
