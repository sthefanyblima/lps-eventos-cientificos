"""Controller — API REST do Submissions Service."""
from fastapi import APIRouter, Depends, HTTPException

from common.service import Caller, current_user, tenant_header

from .dto import FormatOut, StatusIn, SubmissionIn, SubmissionOut
from .service import SubmissionService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> SubmissionService:
    return SubmissionService(tenant)


@router.get("/formats", response_model=list[FormatOut], tags=["submissão"], summary="Formatos aceitos neste produto")
def formats():
    return SubmissionService.formats()


@router.post("/submissions", response_model=SubmissionOut, status_code=201, tags=["submissão"], summary="Submete um trabalho")
def create(body: SubmissionIn, s: SubmissionService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(body.author_id)
    try:
        return s.create(body)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/submissions", response_model=list[SubmissionOut], tags=["submissão"], summary="Lista submissões (filtro por autor)")
def list_(author_id: int | None = None, s: SubmissionService = Depends(svc), who: Caller = Depends(current_user)):
    if author_id is None:
        who.ensure_role("revisor", "organizador")
    else:
        who.ensure_self_or(author_id, "revisor", "organizador")
    return s.list(author_id)


@router.get("/submissions/{sid}", response_model=SubmissionOut, tags=["submissão"], summary="Detalha submissão")
def get(sid: int, s: SubmissionService = Depends(svc)):
    x = s.get(sid)
    if not x:
        raise HTTPException(404, "Submissão não encontrada")
    return x


@router.patch("/submissions/{sid}/status", response_model=SubmissionOut, tags=["submissão"],
              summary="Atualiza status (chamado pelo Reviews Service)")
def status(sid: int, body: StatusIn, s: SubmissionService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_role("organizador")
    x = s.set_status(sid, body.status)
    if not x:
        raise HTTPException(404, "Submissão não encontrada")
    return x
