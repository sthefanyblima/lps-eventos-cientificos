"""Model — entidades do Certificates Service (banco ``lps_<tenant>_certificates``).

  certificado(codigo PK, usuario_id, tipo, texto, carga_horaria, emitido_em)
O código (hash SHA-256 truncado) é a chave natural e serve para verificação pública.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Certificado(Base):
    __tablename__ = "certificado"
    codigo: Mapped[str] = mapped_column(String(16), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    texto: Mapped[str] = mapped_column(Text)
    carga_horaria: Mapped[int] = mapped_column(SmallInteger)
    emitido_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
