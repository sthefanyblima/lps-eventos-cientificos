"""Controller — API REST do Registration Service."""
from fastapi import APIRouter, Depends, HTTPException

from common.service import Caller, current_user, tenant_header

from .dto import AgendaIn, PaymentMethodOut, RegistrationIn, RegistrationOut
from .service import RegistrationService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> RegistrationService:
    return RegistrationService(tenant)


@router.get("/payment-method", response_model=PaymentMethodOut, tags=["pagamento"], summary="Variante de pagamento ativa")
def payment_method():
    return RegistrationService.payment_method()


@router.post("/registrations", response_model=RegistrationOut, status_code=201, tags=["inscrição"],
             summary="Realiza inscrição e cobra via componente de pagamento")
def register(body: RegistrationIn, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(body.user_id, "organizador")
    return s.register(body.user_id, body.model_dump())


@router.get("/registrations", response_model=list[RegistrationOut], tags=["inscrição"], summary="Lista inscrições (organizador)")
def list_all(s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("organizador")
    return s.list()


@router.get("/registrations/{uid}", response_model=RegistrationOut, tags=["inscrição"], summary="Situação da inscrição")
def get(uid: int, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    r = s.get(uid)
    if not r:
        raise HTTPException(404, "Usuário não inscrito")
    return r


@router.post("/registrations/{uid}/confirm", response_model=RegistrationOut, tags=["pagamento"],
             summary="Confirma pagamento pendente (PIX simulado)")
def confirm(uid: int, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    r = s.confirm(uid)
    if not r:
        raise HTTPException(404, "Usuário não inscrito")
    return r


@router.get("/agenda/{uid}", tags=["agenda"], summary="Agenda pessoal (sessões detalhadas)")
def agenda(uid: int, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.agenda(uid)


@router.get("/agenda/{uid}/ids", response_model=list[int], tags=["agenda"], summary="IDs das sessões na agenda")
def agenda_ids(uid: int, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.agenda_ids(uid)


@router.post("/agenda/{uid}", tags=["agenda"], summary="Adiciona sessão à agenda (gera histórico)")
def add(uid: int, body: AgendaIn, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid)
    return s.add_to_agenda(uid, body.session_id)


@router.delete("/agenda/{uid}/{sid}", tags=["agenda"], summary="Remove sessão da agenda")
def remove(uid: int, sid: int, s: RegistrationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid)
    return s.remove_from_agenda(uid, sid)
