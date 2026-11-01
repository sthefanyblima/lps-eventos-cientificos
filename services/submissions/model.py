"""Model — entidades do Submissions Service (banco ``lps_<tenant>_submissions``).

  submissao(id PK, autor_id, titulo, resumo, formato, status, criado_em)
  coautor(id PK, submissao_id FK→submissao, nome, ordem)
  palavra_chave(id PK, submissao_id FK→submissao, termo)

Autores e palavras-chave são multivalorados, então ficam em tabelas próprias (1FN).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Submissao(Base):
    __tablename__ = "submissao"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    autor_id: Mapped[int] = mapped_column(Integer, index=True)
    titulo: Mapped[str] = mapped_column(String(250))
    resumo: Mapped[str] = mapped_column(Text, default="")
    formato: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(15), default="submitted")
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    coautores: Mapped[list["Coautor"]] = relationship(cascade="all, delete-orphan", order_by="Coautor.ordem")
    palavras: Mapped[list["PalavraChave"]] = relationship(cascade="all, delete-orphan", order_by="PalavraChave.id")


class Coautor(Base):
    __tablename__ = "coautor"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submissao_id: Mapped[int] = mapped_column(ForeignKey("submissao.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    ordem: Mapped[int] = mapped_column(Integer)


class PalavraChave(Base):
    __tablename__ = "palavra_chave"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submissao_id: Mapped[int] = mapped_column(ForeignKey("submissao.id", ondelete="CASCADE"), index=True)
    termo: Mapped[str] = mapped_column(String(60))
