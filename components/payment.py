"""Ponto de variação **Pagamento** (xor): Gratuito | Pix | CartaoCredito.

Todos os pagamentos são SIMULADOS (projeto acadêmico): nenhum dado real é
processado nem enviado a terceiros.
"""
from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod

from .base import VariationPoint


class PaymentMethod(ABC):
    label = "?"

    @abstractmethod
    def charge(self, amount: float, payer: dict, data: dict) -> dict:
        """Retorna {status: approved|pending|refused, amount, details}."""

    def confirm(self, payment: dict) -> dict:
        return {**payment, "status": "approved"}


payment_vp: VariationPoint[PaymentMethod] = VariationPoint("payment", PaymentMethod)


@payment_vp.variant("Gratuito")
class FreePayment(PaymentMethod):
    label = "Gratuito"

    def charge(self, amount, payer, data):
        return {"status": "approved", "amount": 0.0, "details": "Evento gratuito — inscrição confirmada"}


@payment_vp.variant("Pix")
class PixPayment(PaymentMethod):
    label = "PIX (simulado)"

    def charge(self, amount, payer, data):
        txid = uuid.uuid4().hex[:20].upper()
        code = f"SIMULADO|PIX|{txid}|{amount:.2f}"
        return {"status": "pending", "amount": amount,
                "details": "Use o código copia-e-cola e depois confirme o pagamento",
                "pix_code": code, "txid": txid}


@payment_vp.variant("CartaoCredito")
class CreditCardPayment(PaymentMethod):
    label = "Cartão de crédito (simulado)"
    TEST_PREFIX = "4111"   # só aceita números de teste

    @staticmethod
    def luhn(number: str) -> bool:
        digits = [int(d) for d in number if d.isdigit()][::-1]
        total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits))
        return len(digits) >= 13 and total % 10 == 0

    def charge(self, amount, payer, data):
        number = str(data.get("card_number", "")).replace(" ", "")
        if not number.startswith(self.TEST_PREFIX) or not self.luhn(number):
            return {"status": "refused", "amount": amount,
                    "details": "Use o cartão de teste 4111 1111 1111 1111"}
        token = hashlib.sha256(number.encode()).hexdigest()[:12]
        return {"status": "approved", "amount": amount, "details": f"Aprovado (token {token}, final {number[-4:]})"}
