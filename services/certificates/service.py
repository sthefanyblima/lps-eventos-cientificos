"""Service — emissão de certificados (componentes do grupo *or* TipoCertificado)."""
from __future__ import annotations

from html import escape

from common.client import call
from common.config import component
from common.database import session_scope
from components.certificate import cert_vp

from .model import Base, Certificado
from .repository import CertificateRepository

ISSUERS = cert_vp.create_many(component("certificate_types", ["CertParticipacao"]))


def to_dto(c: Certificado) -> dict:
    return {"code": c.codigo, "user_id": c.usuario_id, "type": c.tipo, "text": c.texto, "hours": c.carga_horaria,
            "issued_at": c.emitido_em.isoformat(sep=" ", timespec="seconds") if c.emitido_em else ""}


class CertificateService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def _tx(self):
        return session_scope("certificates", self.tenant, Base)

    def issue(self, uid: int) -> list[dict] | None:
        user = call("users", "GET", f"/users/{uid}", self.tenant)
        if not user:
            return None
        ctx = {
            "tenant": self.tenant,
            "event": call("events", "GET", "/event", self.tenant, default={"name": self.tenant}),
            "registration": call("registration", "GET", f"/registrations/{uid}", self.tenant),
            "agenda": call("registration", "GET", f"/agenda/{uid}/ids", self.tenant, default=[]),
            "submissions": call("submissions", "GET", f"/submissions?author_id={uid}", self.tenant, default=[]),
        }
        certs = [c for issuer in ISSUERS for c in issuer.eligible(user, ctx)]
        with self._tx() as s:
            repo = CertificateRepository(s)
            for c in certs:
                repo.save_if_new(uid, c)
            return [to_dto(c) for c in repo.by_user(uid)]

    def verify(self, code: str) -> dict | None:
        with self._tx() as s:
            c = CertificateRepository(s).get(code)
            return to_dto(c) if c else None

    def html(self, code: str) -> str | None:
        c = self.verify(code)
        if not c:
            return None
        ev = call("events", "GET", "/event", self.tenant, default={"name": self.tenant})
        return f"""<!doctype html><html lang="pt-br"><meta charset="utf-8"><title>Certificado</title>
<body style="font-family:Georgia,serif;display:grid;place-items:center;min-height:100vh;background:#f4f1ea">
<div style="border:8px double #8a6d3b;padding:48px 64px;max-width:760px;background:#fff;text-align:center">
<h1 style="letter-spacing:4px">CERTIFICADO</h1><h3>{escape(c['type'])}</h3>
<p style="font-size:20px;line-height:1.6">{escape(c['text'])}</p>
<p>{escape(ev['name'])} · emitido em {c['issued_at'][:10]}</p>
<small>Código de verificação: <b>{c['code']}</b></small></div></body></html>"""
