"""Controller — API REST do Users Service (rotas públicas e protegidas)."""
from fastapi import APIRouter, Depends, HTTPException

from common.service import Caller, current_user, tenant_header

from .dto import HistoryIn, HistoryOut, InterestsIn, LoginIn, RegisterIn, TokenOut, UserOut, VerifyIn
from .service import DomainError, UserService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> UserService:
    return UserService(tenant)


def guard(fn, *args):
    try:
        return fn(*args)
    except DomainError as e:
        raise HTTPException(e.status, str(e))


@router.post("/auth/login", response_model=TokenOut, tags=["autenticação"], summary="Login: e-mail + senha → token JWT")
def login(body: LoginIn, s: UserService = Depends(svc)):
    return guard(s.login, body.email, body.password)


@router.post("/auth/register", response_model=UserOut, status_code=201, tags=["autenticação"], summary="Cadastro de usuário")
def register(body: RegisterIn, s: UserService = Depends(svc)):
    return guard(s.register, body)


@router.post("/auth/verify-token", tags=["autenticação"], summary="Valida um JWT (usado pelo API Gateway)")
def verify(body: VerifyIn, s: UserService = Depends(svc)):
    return guard(s.verify, body.token)


@router.get("/auth/demo-accounts", tags=["autenticação"], summary="Contas de demonstração (ambiente acadêmico)")
def demo(s: UserService = Depends(svc)):
    return s.demo_accounts()


@router.get("/users", response_model=list[UserOut], tags=["usuários"], summary="Lista usuários")
def list_users(s: UserService = Depends(svc)):
    return s.list()


@router.get("/users/{uid}", response_model=UserOut, tags=["usuários"], summary="Detalha usuário (com interesses)")
def get_user(uid: int, s: UserService = Depends(svc)):
    return guard(s.get, uid)


@router.put("/users/{uid}/interests", response_model=UserOut, tags=["perfil"], summary="Atualiza interesses declarados")
def set_interests(uid: int, body: InterestsIn, s: UserService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return guard(s.set_interests, uid, body.interests)


@router.post("/users/{uid}/history", response_model=HistoryOut, status_code=201, tags=["perfil"],
             summary="Registra interação (view/favorite/agenda)")
def add_history(uid: int, body: HistoryIn, s: UserService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return guard(s.add_history, uid, body.session_id, body.action)


@router.get("/users/{uid}/history", response_model=list[HistoryOut], tags=["perfil"], summary="Histórico de um usuário")
def user_history(uid: int, s: UserService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.history(uid)


@router.get("/history", response_model=list[HistoryOut], tags=["perfil"], summary="Histórico global (estratégia Popularidade)")
def all_history(s: UserService = Depends(svc)):
    return s.history()
