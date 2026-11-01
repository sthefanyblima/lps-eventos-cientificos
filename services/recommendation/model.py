"""Model — entidades do Recommendation Service (banco ``lps_<tenant>_recommendation``).

Guarda cada recomendação gerada, para auditoria e para o histórico do usuário:
  recomendacao(id PK, usuario_id, sessao_id, titulo_sessao, score, estrategia, motivo, gerado_em)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Recomendacao(Base):
    __tablename__ = "recomendacao"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, index=True)
    sessao_id: Mapped[int] = mapped_column(Integer)
    titulo_sessao: Mapped[str] = mapped_column(String(200))
    score: Mapped[float] = mapped_column(Float)
    estrategia: Mapped[str] = mapped_column(String(30))
    motivo: Mapped[str] = mapped_column(String(300))
    gerado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
