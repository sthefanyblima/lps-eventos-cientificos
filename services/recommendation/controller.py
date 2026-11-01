"""Controller — API REST do Recommendation Service."""
from fastapi import APIRouter, Depends, HTTPException

from common.service import Caller, current_user, tenant_header

from .dto import RecommendationLog, RecommendationOut
from .service import RecommendationService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> RecommendationService:
    return RecommendationService(tenant)


@router.get("/recommendations/{uid}", response_model=RecommendationOut, tags=["recomendação"],
            summary="Top-k sessões recomendadas pelo perfil (interesses + histórico)")
def recommend(uid: int, k: int = 5, s: RecommendationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    r = s.recommend(uid, k)
    if r is None:
        raise HTTPException(404, "Usuário não encontrado")
    return r


@router.get("/recommendations/{uid}/history", response_model=list[RecommendationLog], tags=["recomendação"],
            summary="Recomendações já geradas para o usuário (persistidas)")
def history(uid: int, s: RecommendationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.history(uid)


@router.get("/profile/{uid}", tags=["recomendação"], summary="Perfil consolidado usado pela recomendação")
def profile(uid: int, s: RecommendationService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    p = s.profile(uid)
    if p is None:
        raise HTTPException(404, "Usuário não encontrado")
    return p
