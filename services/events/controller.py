"""Controller — API REST do Events Service."""
from fastapi import APIRouter, Depends, HTTPException

from common.config import has_feature
from common.service import Caller, current_user, tenant_header

from .dto import EventOut, SessionIn, SessionOut
from .service import EventService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> EventService:
    return EventService(tenant)


@router.get("/event", response_model=EventOut, tags=["evento"], summary="Dados gerais do evento (tenant)")
def event(s: EventService = Depends(svc)):
    return s.event_info()


@router.get("/sessions", response_model=list[SessionOut], tags=["programação"], summary="Lista/busca sessões")
def sessions(q: str | None = None, track: str | None = None, day: str | None = None, s: EventService = Depends(svc)):
    return s.list_sessions(q, track, day)


@router.get("/sessions/{sid}", response_model=SessionOut, tags=["programação"], summary="Detalha uma sessão")
def session(sid: int, s: EventService = Depends(svc)):
    x = s.get(sid)
    if not x:
        raise HTTPException(404, "Sessão não encontrada")
    return x


@router.post("/sessions", response_model=SessionOut, status_code=201, tags=["programação"], summary="Cadastra sessão (organizador)")
def create(body: SessionIn, s: EventService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("organizador")
    return s.create(body)


@router.get("/tracks", response_model=list[str], tags=["trilhas"], summary="Trilhas temáticas (feature opcional Trilhas)")
def tracks(s: EventService = Depends(svc)):
    if not has_feature("Trilhas"):
        raise HTTPException(404, "Feature 'Trilhas' não incluída neste produto")
    return s.tracks()
