"""Model — entidades do Events Service (banco ``lps_<tenant>_events``).

Modelo relacional normalizado (3FN). As tags e trilhas, que antes eram listas
dentro da sessão, viraram tabelas próprias (1FN: atributos atômicos) e a
relação N:N sessão–tag usa tabela associativa:
  trilha(id PK, nome UNIQUE)
  sessao(id PK, titulo, trilha_id FK→trilha NULL, palestrante, dia, inicio, sala, tipo)
  tag(id PK, nome UNIQUE)
  sessao_tag(sessao_id FK→sessao, tag_id FK→tag)  PK composta
"""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Table, Time
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


sessao_tag = Table(
    "sessao_tag", Base.metadata,
    Column("sessao_id", ForeignKey("sessao.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class Trilha(Base):
    __tablename__ = "trilha"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)


class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)


class Sessao(Base):
    __tablename__ = "sessao"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200))
    trilha_id: Mapped[int | None] = mapped_column(ForeignKey("trilha.id", ondelete="SET NULL"), nullable=True, index=True)
    palestrante: Mapped[str] = mapped_column(String(120), default="")
    dia: Mapped[date] = mapped_column(Date, index=True)
    inicio: Mapped[time] = mapped_column(Time)
    sala: Mapped[str] = mapped_column(String(60), default="")
    tipo: Mapped[str] = mapped_column(String(30), default="Palestra")
    trilha: Mapped[Trilha | None] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=sessao_tag, order_by=Tag.id)
