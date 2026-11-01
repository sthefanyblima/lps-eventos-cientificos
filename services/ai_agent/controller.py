"""Controller — interface de diálogo e auditoria do AI Agent Service."""
from fastapi import APIRouter, Depends, HTTPException

from common.service import Caller, current_user, tenant_header

from .dto import AuditOut, ChatIn, ChatOut, ToolOut
from .service import ARCHITECTURE, PROVIDER, AgentService

router = APIRouter()


def svc(tenant: str = Depends(tenant_header)) -> AgentService:
    return AgentService(tenant)


@router.post("/chat", response_model=ChatOut, tags=["agente"],
             summary="Dialogue interface: mensagem → objetivo, plano, execução, resposta e explicação")
def chat(body: ChatIn, s: AgentService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(body.user_id)
    try:
        return s.chat(body.user_id, body.message)
    except Exception as exc:
        raise HTTPException(502, f"Falha no agente: {exc}")


@router.get("/tools/{uid}", response_model=list[ToolOut], tags=["agente"], summary="Tool registry: ferramentas deste produto")
def tools(uid: int, s: AgentService = Depends(svc)):
    return s.tools(uid)


@router.get("/architecture", tags=["agente"], summary="Componentes da arquitetura de referência implementados")
def architecture():
    return {"reference": "Lu et al., Towards Responsible Generative AI: A Reference Architecture for Designing "
                         "Foundation Model based Agents (2024)", "provider": PROVIDER.label,
            "querying": PROVIDER.querying, "components": ARCHITECTURE}


@router.get("/memory/{uid}", tags=["memória"], summary="Memória de curto e longo prazo do usuário")
def memory(uid: int, s: AgentService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.memory(uid)


@router.delete("/memory/{uid}", tags=["memória"], summary="Esquece a memória do usuário (direito ao esquecimento)")
def forget(uid: int, s: AgentService = Depends(svc), who: Caller = Depends(current_user)):
    who.ensure_self_or(uid, "organizador")
    return s.forget(uid)


@router.get("/audit/{request_id}", response_model=list[AuditOut], tags=["RAI"],
            summary="Black box recorder: registro de cada componente para uma requisição")
def audit(request_id: str, s: AgentService = Depends(svc)):
    return s.audit(request_id)
