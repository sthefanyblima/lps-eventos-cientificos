"""Repository — acesso a dados do Certificates Service."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import Certificado


class CertificateRepository:
    def __init__(self, session: Session):
        self.s = session

    def save_if_new(self, user_id: int, cert: dict) -> None:
        if not self.s.get(Certificado, cert["code"]):
            self.s.add(Certificado(codigo=cert["code"], usuario_id=user_id, tipo=cert["type"], texto=cert["text"],
                                   carga_horaria=cert["hours"]))
            self.s.flush()

    def by_user(self, user_id: int) -> list[Certificado]:
        return list(self.s.scalars(select(Certificado).where(Certificado.usuario_id == user_id).order_by(Certificado.emitido_em)))

    def get(self, code: str) -> Certificado | None:
        return self.s.get(Certificado, code.upper())
