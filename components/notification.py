"""Ponto de variação **Canal de Notificação** (or): Email | InApp.

Grupo *or*: o produto pode combinar vários canais; a mensagem é entregue a
todos os componentes selecionados.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from .base import VariationPoint


class NotificationChannel(ABC):
    label = "?"

    def __init__(self, store: Callable | None = None, mail_store: Callable | None = None):
        self.store = store              # persiste notificação in-app (tabela notificacao)
        self.mail_store = mail_store    # persiste e-mail simulado (tabela email_enviado)

    @abstractmethod
    def send(self, user: dict, subject: str, message: str) -> dict: ...


channel_vp: VariationPoint[NotificationChannel] = VariationPoint("notification_channels", NotificationChannel)


@channel_vp.variant("Email")
class EmailChannel(NotificationChannel):
    label = "E-mail (simulado)"

    def send(self, user, subject, message):
        # Envio SIMULADO: o e-mail é gravado na caixa de saída (banco), nunca enviado de fato.
        self.mail_store(user.get("email") or f"usuario-{user.get('id')}@desconhecido", subject, message)
        return {"channel": "Email", "to": user.get("email"), "delivered": True}


@channel_vp.variant("InApp")
class InAppChannel(NotificationChannel):
    label = "No aplicativo"

    def send(self, user, subject, message):
        self.store(user["id"], subject, message)
        return {"channel": "InApp", "delivered": True}
