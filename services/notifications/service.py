"""Service — assina eventos de domínio e entrega por todos os canais selecionados (grupo *or*)."""
from __future__ import annotations

from common.client import call
from common.config import component
from common.database import session_scope
from components.notification import channel_vp

from .model import Base
from .repository import NotificationRepository

CHANNELS = component("notification_channels", ["InApp"])


def _ts(d) -> str:
    return d.isoformat(sep=" ", timespec="seconds") if d else ""


class NotificationService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("notifications", self.tenant, Base)

    def handle_event(self, ev) -> dict:
        user = call("users", "GET", f"/users/{ev.user_id}", self.tenant) or {"id": ev.user_id, "email": None}
        with self._tx() as s:
            repo = NotificationRepository(s)
            channels = channel_vp.create_many(CHANNELS, store=repo.add_inapp, mail_store=repo.add_email)
            results = [ch.send(user, ev.subject, ev.message) for ch in channels]
            repo.log_event(ev.type, ev.user_id, ",".join(r["channel"] for r in results))
        return {"event": ev.type, "deliveries": results}

    def inbox(self, uid: int) -> list[dict]:
        if "InApp" not in CHANNELS:
            return []
        with self._tx() as s:
            return [{"id": n.id, "user_id": n.usuario_id, "subject": n.assunto, "message": n.mensagem, "read": n.lida,
                     "at": _ts(n.criado_em)} for n in NotificationRepository(s).inbox(uid)]

    def outbox(self) -> list[dict]:
        with self._tx() as s:
            return [{"id": m.id, "to": m.destinatario, "subject": m.assunto, "body": m.corpo, "sent_at": _ts(m.enviado_em)}
                    for m in NotificationRepository(s).outbox()]

    def events(self) -> list[dict]:
        with self._tx() as s:
            return [{"id": e.id, "type": e.tipo, "user_id": e.usuario_id, "channels": e.canais, "at": _ts(e.criado_em)}
                    for e in NotificationRepository(s).events()]
