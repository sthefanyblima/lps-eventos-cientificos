"""Controller — API REST do Notifications Service."""
from fastapi import APIRouter, Depends

from common.service import Caller, current_user, tenant_header

from .dto import EmailOut, EventIn, NotificationOut
from .service import NotificationService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> NotificationService:
    return NotificationService(tenant)


@router.post("/events", tags=["eventos"], summary="Recebe evento de domínio e notifica pelos canais ativos (interno)")
def event(body: EventIn, s: NotificationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("organizador")          # só chamadas internas (ou organizador) publicam eventos
    return s.handle_event(body)


@router.get("/notifications/{uid}", response_model=list[NotificationOut], tags=["notificações"], summary="Caixa de entrada in-app")
def inbox(uid: int, s: NotificationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.inbox(uid)


@router.get("/outbox", response_model=list[EmailOut], tags=["notificações"], summary="E-mails simulados enviados (organizador)")
def outbox(s: NotificationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("organizador")
    return s.outbox()


@router.get("/log", tags=["notificações"], summary="Últimos eventos processados (organizador)")
def log(s: NotificationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("organizador")
    return s.events()
