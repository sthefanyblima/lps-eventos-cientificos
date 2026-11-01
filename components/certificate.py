"""Ponto de variação **Tipo de Certificado** (or): CertParticipacao | CertApresentacao."""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from .base import VariationPoint


class CertificateIssuer(ABC):
    label = "?"

    @abstractmethod
    def eligible(self, user: dict, ctx: dict) -> list[dict]:
        """Retorna lista de certificados (dict) a que o usuário tem direito."""

    @staticmethod
    def code(*parts) -> str:
        return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16].upper()


cert_vp: VariationPoint[CertificateIssuer] = VariationPoint("certificate_types", CertificateIssuer)


@cert_vp.variant("CertParticipacao")
class ParticipationCertificate(CertificateIssuer):
    label = "Participação"

    def eligible(self, user, ctx):
        reg = ctx.get("registration")
        if not reg or reg.get("status") != "approved":
            return []
        hours = 2 * len(ctx.get("agenda", [])) or 2
        text = (f"Certificamos que {user['name']} participou do evento {ctx['event']['name']}, "
                f"com carga horária de {hours} horas.")
        return [{"type": "Participação", "text": text, "hours": hours,
                 "code": self.code("P", ctx["tenant"], user["id"])}]


@cert_vp.variant("CertApresentacao")
class PresentationCertificate(CertificateIssuer):
    label = "Apresentação de trabalho"

    def eligible(self, user, ctx):
        out = []
        for sub in ctx.get("submissions", []):
            if sub.get("status") == "accepted":
                text = (f"Certificamos que o trabalho \"{sub['title']}\", de autoria de {sub['authors']}, "
                        f"foi apresentado no evento {ctx['event']['name']} na modalidade {sub['format']}.")
                out.append({"type": "Apresentação", "text": text, "hours": 1,
                            "code": self.code("A", ctx["tenant"], user["id"], sub["id"])})
        return out
