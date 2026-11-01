"""Service — inscrição, pagamento (componente variável) e agenda pessoal."""
from __future__ import annotations

import json

from common.client import call
from common.config import component
from common.database import session_scope
from common.events import publish
from components.payment import payment_vp

from .model import Base, Inscricao
from .repository import RegistrationRepository

# Ponto de variação resolvido UMA vez, na inicialização (configuração do produto).
PAYMENT = payment_vp.create(component("payment", "Gratuito"))
FEE = 0.0 if PAYMENT.feature_id == "Gratuito" else 150.0


def to_dto(r: Inscricao) -> dict:
    last = r.pagamentos[-1] if r.pagamentos else None
    return {"user_id": r.usuario_id, "status": r.status, "method": r.metodo, "amount": float(r.valor),
            "details": json.loads(last.detalhes) if last else {},
            "created_at": r.criado_em.isoformat(sep=" ", timespec="seconds") if r.criado_em else ""}


class RegistrationService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("registration", self.tenant, Base)

    @staticmethod
    def payment_method() -> dict:
        return {"variant": PAYMENT.feature_id, "label": PAYMENT.label, "fee": FEE}

    def get(self, uid: int) -> dict | None:
        with self._tx() as s:
            r = RegistrationRepository(s).get(uid)
            return to_dto(r) if r else None

    def list(self) -> list[dict]:
        with self._tx() as s:
            return [to_dto(r) for r in RegistrationRepository(s).list()]

    def register(self, uid: int, data: dict) -> dict:
        current = self.get(uid)
        if current and current["status"] == "approved":
            return current
        user = call("users", "GET", f"/users/{uid}", self.tenant) or {"id": uid}
        result = PAYMENT.charge(FEE, user, data)
        with self._tx() as s:
            out = to_dto(RegistrationRepository(s).save_attempt(uid, PAYMENT.feature_id, result))
        if result["status"] == "approved":
            publish("registration.confirmed", uid, "Inscrição confirmada", f"Sua inscrição foi confirmada ({PAYMENT.label}).", self.tenant)
        return out

    def confirm(self, uid: int) -> dict | None:
        with self._tx() as s:
            repo = RegistrationRepository(s)
            r = repo.get(uid)
            if not r:
                return None
            if r.status == "pending":
                result = PAYMENT.confirm(json.loads(r.pagamentos[-1].detalhes))
                r = repo.save_attempt(uid, PAYMENT.feature_id, result)
                approved = True
            else:
                approved = False
            out = to_dto(r)
        if approved:
            publish("registration.confirmed", uid, "Pagamento confirmado", "Recebemos seu PIX. Inscrição confirmada!", self.tenant)
        return out

    def agenda_ids(self, uid: int) -> list[int]:
        with self._tx() as s:
            return RegistrationRepository(s).agenda_ids(uid)

    def agenda(self, uid: int) -> list[dict]:
        sessions = [call("events", "GET", f"/sessions/{i}", self.tenant) for i in self.agenda_ids(uid)]
        return sorted([x for x in sessions if x], key=lambda x: (x["day"], x["start"]))

    def add_to_agenda(self, uid: int, sid: int) -> dict:
        reg = self.get(uid)
        if not reg or reg["status"] != "approved":
            return {"ok": False, "message": "Conclua sua inscrição antes de montar a agenda."}
        session = call("events", "GET", f"/sessions/{sid}", self.tenant)
        if not session:
            return {"ok": False, "message": f"Sessão {sid} não existe."}
        with self._tx() as s:
            RegistrationRepository(s).add_agenda(uid, sid)
        call("users", "POST", f"/users/{uid}/history", self.tenant, json={"session_id": sid, "action": "agenda"})
        publish("agenda.added", uid, "Sessão adicionada", f"\"{session['title']}\" — {session['day']} {session['start']}", self.tenant)
        return {"ok": True, "message": f"\"{session['title']}\" adicionada à sua agenda.", "session": session}

    def remove_from_agenda(self, uid: int, sid: int) -> dict:
        with self._tx() as s:
            RegistrationRepository(s).remove_agenda(uid, sid)
        return {"ok": True}
