"""Model — entidades do Registration Service (banco ``lps_<tenant>_registration``).

  inscricao(usuario_id PK, status, metodo, valor, criado_em, atualizado_em)
  pagamento(id PK, usuario_id FK→inscricao, metodo, valor, status, txid, detalhes, criado_em)
  agenda_item(usuario_id, sessao_id, adicionado_em)              PK composta (usuario_id, sessao_id)

Uma inscrição pode ter várias tentativas de pagamento (1:N) — por isso
``pagamento`` é tabela separada (evita grupo repetido, 1FN/2FN).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Inscricao(Base):
    __tablename__ = "inscricao"
    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(String(10))            # pending | approved | refused
    metodo: Mapped[str] = mapped_column(String(20))            # variante do componente de pagamento
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    pagamentos: Mapped[list["Pagamento"]] = relationship(cascade="all, delete-orphan", order_by="Pagamento.id")


class Pagamento(Base):
    __tablename__ = "pagamento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("inscricao.usuario_id", ondelete="CASCADE"), index=True)
    metodo: Mapped[str] = mapped_column(String(20))
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(10))
    txid: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detalhes: Mapped[str] = mapped_column(Text, default="{}")   # resposta do componente (JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgendaItem(Base):
    __tablename__ = "agenda_item"
    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sessao_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    adicionado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
