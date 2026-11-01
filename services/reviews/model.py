"""Model — entidades do Reviews Service (banco ``lps_<tenant>_reviews``).

  parecer(id PK, submissao_id, revisor_id, revisor_nome, nota, comentario, criado_em)
  UNIQUE(submissao_id, revisor_id) — um parecer por revisor por trabalho.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Parecer(Base):
    __tablename__ = "parecer"
    __table_args__ = (UniqueConstraint("submissao_id", "revisor_id", name="uq_parecer_submissao_revisor"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submissao_id: Mapped[int] = mapped_column(Integer, index=True)
    revisor_id: Mapped[int] = mapped_column(Integer, index=True)
    revisor_nome: Mapped[str] = mapped_column(String(120))
    nota: Mapped[int] = mapped_column(SmallInteger)                 # -3 .. 3
    comentario: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
