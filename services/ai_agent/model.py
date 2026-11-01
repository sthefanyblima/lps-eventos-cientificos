"""Model — entidades do AI Agent Service (banco ``lps_<tenant>_ai_agent``).

Componentes da arquitetura de referência de agentes (Lu et al., 2024) que precisam
de persistência:
  memoria_evento(id PK, usuario_id, papel, texto, criado_em)          — memória de longo prazo: histórico de eventos
  conhecimento(id PK, usuario_id, chave, valor, atualizado_em)         — memória de longo prazo: conhecimento/experiências
                UNIQUE(usuario_id, chave)
  registro_caixa_preta(id PK, requisicao_id, usuario_id, ordem, componente, entrada, saida, criado_em)
                                                                       — RAI plugin *black box recorder*
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MemoriaEvento(Base):
    __tablename__ = "memoria_evento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    papel: Mapped[str] = mapped_column(String(10))            # usuario | agente
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conhecimento(Base):
    __tablename__ = "conhecimento"
    __table_args__ = (UniqueConstraint("usuario_id", "chave", name="uq_conhecimento_usuario_chave"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    chave: Mapped[str] = mapped_column(String(60))
    valor: Mapped[str] = mapped_column(String(500))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RegistroCaixaPreta(Base):
    __tablename__ = "registro_caixa_preta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requisicao_id: Mapped[str] = mapped_column(String(32), index=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    componente: Mapped[str] = mapped_column(String(60))
    entrada: Mapped[str] = mapped_column(Text)
    saida: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
