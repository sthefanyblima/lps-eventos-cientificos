"""Model — entidades do Notifications Service (banco ``lps_<tenant>_notifications``).

  evento_recebido(id PK, tipo, usuario_id, canais, criado_em)     — log dos eventos de domínio
  notificacao(id PK, usuario_id, assunto, mensagem, lida, criado_em)  — canal In-app
  email_enviado(id PK, destinatario, assunto, corpo, enviado_em)      — canal E-mail (simulado)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventoRecebido(Base):
    __tablename__ = "evento_recebido"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(40))
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    canais: Mapped[str] = mapped_column(String(60))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notificacao(Base):
    __tablename__ = "notificacao"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    assunto: Mapped[str] = mapped_column(String(150))
    mensagem: Mapped[str] = mapped_column(Text)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmailEnviado(Base):
    __tablename__ = "email_enviado"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    destinatario: Mapped[str] = mapped_column(String(160))
    assunto: Mapped[str] = mapped_column(String(150))
    corpo: Mapped[str] = mapped_column(Text)
    enviado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
