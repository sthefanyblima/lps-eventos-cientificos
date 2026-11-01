"""Controller — API REST do Certificates Service."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from common.service import Caller, current_user, tenant_header

from .dto import CertificateOut
from .service import CertificateService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> CertificateService:
    return CertificateService(tenant)


@router.get("/certificates/{uid}", response_model=list[CertificateOut], tags=["certificados"],
            summary="Emite (idempotente) e lista certificados do usuário")
def issue(uid: int, s: CertificateService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    r = s.issue(uid)
    if r is None:
        raise HTTPException(404, "Usuário não encontrado")
    return r


@router.get("/verify/{code}", response_model=CertificateOut, tags=["certificados"], summary="Verifica autenticidade (público)")
def verify(code: str, s: CertificateService = Depends(svc)):
    c = s.verify(code)
    if not c:
        raise HTTPException(404, "Certificado inválido")
    return c


@router.get("/view/{code}", response_class=HTMLResponse, tags=["certificados"], summary="Certificado em HTML (público)")
def view(code: str, s: CertificateService = Depends(svc)):
    h = s.html(code)
    if not h:
        raise HTTPException(404, "Certificado inválido")
    return h
