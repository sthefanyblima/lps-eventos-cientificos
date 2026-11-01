"""Repository — acesso a dados do Registration Service."""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .model import AgendaItem, Inscricao, Pagamento


class RegistrationRepository:
    def __init__(self, session: Session):
        self.s = session

    def get(self, user_id: int) -> Inscricao | None:
        return self.s.get(Inscricao, user_id)

    def list(self) -> list[Inscricao]:
        return list(self.s.scalars(select(Inscricao).order_by(Inscricao.usuario_id)))

    def save_attempt(self, user_id: int, method: str, result: dict) -> Inscricao:
        reg = self.get(user_id)
        if not reg:
            reg = Inscricao(usuario_id=user_id, status=result["status"], metodo=method, valor=Decimal(str(result["amount"])))
            self.s.add(reg)
        reg.status, reg.metodo, reg.valor = result["status"], method, Decimal(str(result["amount"]))
        reg.pagamentos.append(Pagamento(metodo=method, valor=Decimal(str(result["amount"])), status=result["status"],
                                        txid=result.get("txid"), detalhes=json.dumps(result, ensure_ascii=False)))
        self.s.flush()
        return reg

    def agenda_ids(self, user_id: int) -> list[int]:
        return list(self.s.scalars(select(AgendaItem.sessao_id).where(AgendaItem.usuario_id == user_id)))

    def add_agenda(self, user_id: int, session_id: int) -> None:
        if not self.s.get(AgendaItem, (user_id, session_id)):
            self.s.add(AgendaItem(usuario_id=user_id, sessao_id=session_id))

    def remove_agenda(self, user_id: int, session_id: int) -> None:
        self.s.execute(delete(AgendaItem).where(AgendaItem.usuario_id == user_id, AgendaItem.sessao_id == session_id))
