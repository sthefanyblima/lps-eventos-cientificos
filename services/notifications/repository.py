"""Repository — acesso a dados do Notifications Service."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import EmailEnviado, EventoRecebido, Notificacao


class NotificationRepository:
    def __init__(self, session: Session):
        self.s = session

    def add_inapp(self, user_id: int, subject: str, message: str) -> None:
        self.s.add(Notificacao(usuario_id=user_id, assunto=subject, mensagem=message))

    def add_email(self, to: str, subject: str, body: str) -> None:
        self.s.add(EmailEnviado(destinatario=to, assunto=subject, corpo=body))

    def log_event(self, tipo: str, user_id: int, canais: str) -> None:
        self.s.add(EventoRecebido(tipo=tipo, usuario_id=user_id, canais=canais))

    def inbox(self, user_id: int) -> list[Notificacao]:
        return list(self.s.scalars(select(Notificacao).where(Notificacao.usuario_id == user_id).order_by(Notificacao.id.desc())))

    def outbox(self, limit: int = 50) -> list[EmailEnviado]:
        return list(self.s.scalars(select(EmailEnviado).order_by(EmailEnviado.id.desc()).limit(limit)))

    def events(self, limit: int = 50) -> list[EventoRecebido]:
        return list(self.s.scalars(select(EventoRecebido).order_by(EventoRecebido.id.desc()).limit(limit)))
