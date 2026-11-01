"""Controller — API REST do Reviews Service."""
from fastapi import APIRouter, Depends

from common.service import Caller, current_user, tenant_header

from .dto import DecisionOut, PolicyOut, ReviewIn, ReviewOut
from .service import ReviewService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> ReviewService:
    return ReviewService(tenant)


@router.get("/policy", response_model=PolicyOut, tags=["revisão"], summary="Política de revisão ativa")
def policy():
    return ReviewService.policy()


@router.get("/queue/{reviewer_id}", tags=["revisão"], summary="Fila do revisor (com anonimização da política)")
def queue(reviewer_id: int, s: ReviewService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("revisor", "organizador")
    who.ensure_self_or(reviewer_id, "organizador")
    return s.queue(reviewer_id)


@router.post("/reviews", response_model=DecisionOut, status_code=201, tags=["revisão"],
             summary="Registra parecer e decide aceite pela média")
def review(body: ReviewIn, s: ReviewService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("revisor", "organizador")
    who.ensure_self_or(body.reviewer_id, "organizador")
    return s.submit(body)


@router.get("/reviews/submission/{sid}", response_model=list[ReviewOut], tags=["revisão"],
            summary="Pareceres vistos pelo autor (com anonimização)")
def for_author(sid: int, s: ReviewService = Depends(svc)):
    return s.for_author(sid)
