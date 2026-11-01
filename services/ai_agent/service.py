"""Service — orquestra o agente segundo a arquitetura de referência de Lu et al. (2024).

Fluxo de uma mensagem na interface de diálogo::

  input guardrail → persona creator → memory retrieval (curto + longo prazo)
  → passive goal creator → prompt generator → provedor (variante LLM ou Local):
        planning (single-path plan generator + plan reflection)
        execution engine (tool selector → execution guardrail → task executor + monitor)
  → response generator → output guardrail → explainer
  → atualização da memória → black box recorder (persistido no MySQL)
"""
from __future__ import annotations

from common.client import call
from common.config import component, has_feature
from components.agent import AgentContext, agent_vp

from .execution import TaskExecutor, TaskMonitor, ToolRegistry, ToolSelector
from .interaction import PassiveGoalCreator, PersonaCreator, PromptResponseGenerator
from .memory import LongTermMemory, ShortTermMemory
from .planning import PlanReflection, SinglePathPlanGenerator
from .rai import BlackBoxRecorder, ExecutionGuardrail, Explainer, InputGuardrail, OutputGuardrail

PROVIDER = agent_vp.create(component("ai_provider", "AgenteLocal"))

ARCHITECTURE = {
    "interaction engineering": ["dialogue interface (POST /chat)", "persona creator", "passive goal creator",
                                "prompt/response generator (templates)"],
    "memory": ["short-term memory (janela da conversa)", "long-term memory (MySQL) — feature MemoriaLongoPrazo",
               "memory retrieval"],
    "planning": ["single-path plan generator", "plan reflection (self-reflection)",
                 "one-shot (AgenteLocal) / incremental model querying (AgenteLLM)"],
    "execution engine": ["tool registry (operações dos microservices do produto)", "tool selector", "task executor",
                         "task monitor"],
    "RAI plugins": ["input guardrail (PII, prompt injection)", "execution guardrail (lista branca, limite)",
                    "output guardrail", "black box recorder (MySQL)", "explainer"],
    "AI models": ["AgenteLLM: external FM (Claude) — variante", "AgenteLocal: non-FM model (regras) — variante"],
}


def _facts(goal, tasks: list[dict]) -> dict[str, str]:
    """O que vale guardar como conhecimento de longo prazo após a interação."""
    f: dict[str, str] = {}
    if goal.intent == "buscar" and goal.entities.get("query"):
        f["ultimo_tema"] = goal.entities["query"]
    for t in tasks:
        if t["tool"] == "recomendar_sessoes" and t["output"]:
            f["ultima_recomendacao"] = t["output"][0]["title"]
        if t["tool"] == "adicionar_agenda" and isinstance(t["output"], dict) and t["output"].get("ok"):
            f["ultima_sessao_adicionada"] = t["output"]["session"]["title"]
    return f


class AgentService:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def tools(self, uid: int) -> list[dict]:
        return [{"name": t.name, "description": t.description, "feature": t.feature, "service": t.service}
                for t in ToolRegistry(self.tenant, uid).build().values()]

    def chat(self, uid: int, message: str) -> dict:
        recorder = BlackBoxRecorder(self.tenant, uid)
        notes: list[str] = []

        # 1. RAI — guardrail de entrada
        text, n, allowed = InputGuardrail().apply(message)
        notes += n
        recorder.record("input guardrail", message, {"text": text, "notes": n, "allowed": allowed})
        if not allowed:
            answer = "Não posso seguir instruções que alterem minhas regras. Posso ajudar com a programação do evento."
            recorder.record("dialogue interface", text, answer)
            recorder.flush()
            return {"request_id": recorder.request_id, "answer": answer, "provider": PROVIDER.label, "goal": {},
                    "plan": [], "trace": [], "explanation": [f"Guardrail: {x}" for x in notes], "guardrails": notes,
                    "memory": {}}

        # 2. Interaction engineering + memória
        user = call("users", "GET", f"/users/{uid}", self.tenant) or {"id": uid, "name": "?", "interests": []}
        event = call("events", "GET", "/event", self.tenant, default={"name": self.tenant})
        registry = ToolRegistry(self.tenant, uid).build()
        persona = PersonaCreator().create(event, registry)
        short, long_ = ShortTermMemory(self.tenant, uid), LongTermMemory(self.tenant, uid)
        retrieved = long_.retrieve()
        memory = {"recent": retrieved["recent"] or short.recent(), "knowledge": retrieved["knowledge"],
                  "long_term_enabled": has_feature("MemoriaLongoPrazo"), "long_term_events": retrieved["events"]}
        recorder.record("memory retrieval", {"user": uid}, memory)
        goal = PassiveGoalCreator().create(text, memory)
        recorder.record("passive goal creator", text, goal.__dict__)
        gen = PromptResponseGenerator()
        prompt = gen.prompt(persona, user, memory, goal)
        recorder.record("prompt generator", goal.__dict__, prompt)

        # 3. Planning + execution engine (via provedor = ponto de variação)
        monitor = TaskMonitor()
        executor = TaskExecutor(registry, ToolSelector(), monitor, ExecutionGuardrail(set(registry)), recorder)
        reflection = PlanReflection()

        def plan_generator(g, tools, mem):
            plan = SinglePathPlanGenerator().generate(g, tools, mem)
            kept, refl = reflection.reflect(plan, tools)
            notes.extend(refl)
            recorder.record("single-path plan generator + plan reflection", g.__dict__,
                            {"plan": [p.__dict__ for p in kept], "reflection": refl})
            return kept

        ctx = AgentContext(goal=goal, persona=persona, prompt=prompt, memory=memory, tools=registry,
                           execute=executor, plan_generator=plan_generator, respond=gen.respond)
        try:
            result = PROVIDER.solve(ctx)
        except PermissionError as exc:
            result = {"answer": f"Ação bloqueada pelo guardrail: {exc}", "plan": [], "model": PROVIDER.label}

        # 4. RAI — guardrail de saída + explainer
        answer, out_notes = OutputGuardrail().apply(result["answer"] or "")
        notes += out_notes
        explanation = Explainer().explain(goal, result["plan"], monitor.tasks, memory, result["model"], notes)
        recorder.record("output guardrail", result["answer"], {"answer": answer, "notes": out_notes})
        recorder.record("explainer", {"plan": result["plan"]}, explanation)

        # 5. Atualiza memória e grava a caixa-preta
        short.add("usuario", text)
        short.add("agente", answer)
        facts = _facts(goal, monitor.tasks)
        long_.store(text, answer, facts)
        recorder.record("memory update", {"facts": facts}, {"long_term": has_feature("MemoriaLongoPrazo")})
        recorder.flush()

        return {"request_id": recorder.request_id, "answer": answer, "provider": result["model"], "goal": goal.__dict__,
                "plan": result["plan"], "trace": monitor.tasks, "explanation": explanation, "guardrails": notes,
                "memory": {"knowledge": memory["knowledge"], "long_term_enabled": memory["long_term_enabled"],
                           "recent_messages": len(memory["recent"]), "facts_saved": facts}}

    def memory(self, uid: int) -> dict:
        return {"short_term": ShortTermMemory(self.tenant, uid).recent(), **LongTermMemory(self.tenant, uid).retrieve(),
                "long_term_enabled": has_feature("MemoriaLongoPrazo")}

    def forget(self, uid: int) -> dict:
        LongTermMemory(self.tenant, uid).forget()
        return {"ok": True}

    def audit(self, request_id: str) -> list[dict]:
        return BlackBoxRecorder.read(self.tenant, request_id)
