"""Execution engine (Lu et al., 2024, seção 3.4).

* **Tool registry** — catálogo das ferramentas do agente. Cada ferramenta é uma
  operação de outro microservice e só é registrada se a feature de que depende
  estiver no produto derivado (o agente também é derivado pela LPS).
* **Tool selector** — escolhe no registro a ferramenta pedida pelo plano.
* **Task executor + task monitor** — executa cada passo e acompanha o status
  (pendente → executando → concluído/bloqueado/falhou).
"""
from __future__ import annotations

from common.client import call
from common.config import has_feature
from components.agent import Tool


class ToolRegistry:
    def __init__(self, tenant: str, user_id: int):
        self.tenant, self.user_id = tenant, user_id

    def build(self) -> dict[str, Tool]:
        t, uid = self.tenant, self.user_id

        def buscar_sessoes(query: str = ""):
            return call("events", "GET", "/sessions", t, params={"q": query} if query else None, default=[])

        def recomendar_sessoes(k: int = 3):
            return (call("recommendation", "GET", f"/recommendations/{uid}", t, params={"k": int(k)}, default={"items": []}) or {}).get("items", [])

        def minha_agenda():
            return call("registration", "GET", f"/agenda/{uid}", t, default=[])

        def adicionar_agenda(session_id: int):
            if session_id is None:
                return {"ok": False, "message": "Nenhuma sessão para adicionar."}
            return call("registration", "POST", f"/agenda/{uid}", t, json={"session_id": int(session_id)},
                        default={"ok": False, "message": "Falha ao adicionar"})

        def status_submissoes():
            return call("submissions", "GET", "/submissions", t, params={"author_id": uid}, default=[])

        def meu_perfil():
            return call("users", "GET", f"/users/{uid}", t, default={})

        obj = {"type": "object", "properties": {}}
        tools = [
            Tool("buscar_sessoes", "Busca sessões da programação por tema, título ou palestrante.",
                 {"type": "object", "properties": {"query": {"type": "string"}}}, buscar_sessoes, "Programacao", "events"),
            Tool("recomendar_sessoes", "Recomenda sessões com base no perfil e histórico do usuário.",
                 {"type": "object", "properties": {"k": {"type": "integer"}}}, recomendar_sessoes, "Recomendacao", "recommendation"),
            Tool("minha_agenda", "Mostra a agenda pessoal do usuário.", obj, minha_agenda, "Inscricao", "registration"),
            Tool("adicionar_agenda", "Adiciona uma sessão (pelo id) à agenda do usuário.",
                 {"type": "object", "properties": {"session_id": {"type": "integer"}}, "required": ["session_id"]},
                 adicionar_agenda, "Inscricao", "registration"),
            Tool("status_submissoes", "Consulta o status das submissões do usuário.", obj, status_submissoes, "Submissao", "submissions"),
            Tool("meu_perfil", "Lê o perfil e os interesses cadastrados do usuário.", obj, meu_perfil, "PerfilInteresses", "users"),
        ]
        return {x.name: x for x in tools if has_feature(x.feature)}


class ToolSelector:
    def select(self, registry: dict[str, Tool], name: str) -> Tool:
        if name not in registry:
            raise KeyError(f"Ferramenta '{name}' não existe neste produto")
        return registry[name]


class TaskMonitor:
    def __init__(self):
        self.tasks: list[dict] = []

    def start(self, tool: Tool, args: dict) -> dict:
        task = {"step": len(self.tasks) + 1, "tool": tool.name, "service": tool.service, "input": args,
                "output": None, "status": "executando"}
        self.tasks.append(task)
        return task

    def finish(self, task: dict, output, status: str = "concluído") -> None:
        task["output"], task["status"] = output, status


class TaskExecutor:
    def __init__(self, registry: dict[str, Tool], selector: ToolSelector, monitor: TaskMonitor, guardrail, recorder):
        self.registry, self.selector, self.monitor = registry, selector, monitor
        self.guardrail, self.recorder = guardrail, recorder

    def __call__(self, name: str, args: dict, why: str = ""):
        tool = self.selector.select(self.registry, name)
        task = self.monitor.start(tool, args)
        ok, reason = self.guardrail.check(tool, args, len(self.monitor.tasks))
        if not ok:
            self.monitor.finish(task, {"blocked": reason}, "bloqueado")
            self.recorder.record("execution guardrail", {"tool": name, "args": args}, {"blocked": reason})
            raise PermissionError(reason)
        try:
            out = tool.fn(**args)
        except Exception as exc:
            self.monitor.finish(task, {"error": str(exc)}, "falhou")
            self.recorder.record(f"task executor · {name}", args, {"error": str(exc)})
            raise
        self.monitor.finish(task, out)
        self.recorder.record(f"task executor · {name} ({tool.service})", {"args": args, "why": why}, out)
        return out
