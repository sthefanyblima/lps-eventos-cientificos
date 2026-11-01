"""Interaction engineering (Lu et al., 2024, seção 3.1).

* **Persona creator** — define papel, estilo, capacidades e limites do agente.
* **Passive goal creator** — interpreta o pedido digitado na interface de diálogo
  e o transforma em um objetivo (intenção + parâmetros).
* **Prompt/response generator** — monta, a partir de *templates*, o prompt
  enviado ao modelo (variante LLM) e as respostas ao usuário (variante local).
"""
from __future__ import annotations

import re
import unicodedata

from components.agent import Goal


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


class PersonaCreator:
    def create(self, event: dict, tools: dict) -> dict:
        return {
            "role": f"Assistente do evento científico {event.get('name', '')}",
            "style": "português, cordial, objetivo; respostas curtas com listas",
            "capabilities": [t.description.split(".")[0] for t in tools.values()],
            "limits": ["só usa dados reais obtidos pelas ferramentas (nunca inventa sessões)",
                       "não altera dados de outros usuários", "não trata dados pessoais sensíveis"],
        }


class PassiveGoalCreator:
    """Classifica a intenção do pedido (o objetivo é explícito no texto do usuário)."""
    INTENTS = [
        ("recomendar", r"(recomend|sugir|sugest|indica|o que (devo|posso) (ver|assistir))"),
        ("adicionar_agenda", r"(adicion|inclu|coloc|inscrev).*(agenda|sess|palestra)|^adicion"),
        ("minha_agenda", r"(minha|meu).*(agenda|programa)"),
        ("submissoes", r"(submiss|artigo|trabalho|revis)"),
        ("memoria", r"(o que voce sabe|lembra|meus interesses|sobre mim|meu perfil)"),
        ("buscar", r"(busca|procur|tem .*sobre|sessoes? (de|sobre)|palestras? (de|sobre)|programacao|quando|mais sobre)"),
    ]

    def create(self, text: str, memory: dict) -> Goal:
        t = norm(text)
        intent = next((name for name, rx in self.INTENTS if re.search(rx, t)), "ajuda")
        entities: dict = {}
        if intent == "buscar":
            m = re.search(r"(?:sobre|de|com)\s+(.+)$", t)
            q = m.group(1).strip(" ?.!") if m else ""
            if q in ("isso", "esse tema", "esse assunto", "") and memory.get("knowledge", {}).get("ultimo_tema"):
                q = memory["knowledge"]["ultimo_tema"]          # resolve referência usando a memória
                entities["from_memory"] = True
            entities["query"] = q
        if intent in ("adicionar_agenda", "recomendar"):
            m = re.search(r"\b(?:sessao|sessão|id|numero|número|#)?\s*(\d{1,3})\b", t)
            if m and intent == "adicionar_agenda":
                entities["session_id"] = int(m.group(1))
            entities["add_to_agenda"] = bool(re.search(r"(adicion|agenda|inclu)", t))
        return Goal(text=text, intent=intent, entities=entities)


class PromptResponseGenerator:
    PROMPT_TEMPLATE = (
        "Você é: {role}. Estilo: {style}.\n"
        "Limites: {limits}.\n"
        "Usuário: {user_name} (interesses: {interests}).\n"
        "Memória — conversa recente: {recent}. Conhecimento sobre o usuário: {knowledge}.\n"
        "Objetivo identificado: {intent} {entities}.\n"
        "Use as ferramentas disponíveis para obter dados reais e responda em português."
    )

    def prompt(self, persona: dict, user: dict, memory: dict, goal: Goal) -> str:
        recent = " | ".join(f"{m['role']}: {m['text'][:80]}" for m in memory.get("recent", [])) or "—"
        return self.PROMPT_TEMPLATE.format(
            role=persona["role"], style=persona["style"], limits="; ".join(persona["limits"]),
            user_name=user.get("name", "?"), interests=", ".join(user.get("interests", [])) or "—",
            recent=recent, knowledge=memory.get("knowledge") or "—", intent=goal.intent, entities=goal.entities)

    def respond(self, goal: Goal, results: list[dict], memory: dict) -> str:
        out = {r["tool"]: r["output"] for r in results}
        if goal.intent == "recomendar":
            recs = out.get("recomendar_sessoes") or []
            lines = [f"• [{r['id']}] {r['title']} ({r['day']} {r['start']}) — {r['reason']}" for r in recs]
            text = "Com base no seu perfil e histórico, recomendo:\n" + "\n".join(lines) if lines else "Ainda não tenho recomendações para você."
            if "adicionar_agenda" in out:
                text += "\n" + (out["adicionar_agenda"] or {}).get("message", "")
            return text
        if goal.intent == "buscar":
            found = out.get("buscar_sessoes") or []
            q = goal.entities.get("query") or ""
            lines = [f"• [{s['id']}] {s['title']} — {s['day']} {s['start']}, {s['room']}" for s in found[:6]]
            pre = " (tema lembrado da nossa última conversa)" if goal.entities.get("from_memory") else ""
            return (f"Encontrei {len(found)} sessão(ões){' sobre ' + q if q else ''}{pre}:\n" + "\n".join(lines)) if found \
                else f"Não encontrei sessões sobre '{q}'."
        if goal.intent == "adicionar_agenda":
            r = out.get("adicionar_agenda") or {}
            return r.get("message", "Não consegui adicionar a sessão.")
        if goal.intent == "minha_agenda":
            ag = out.get("minha_agenda") or []
            lines = [f"• {s['day']} {s['start']} — {s['title']} ({s['room']})" for s in ag]
            return "Sua agenda:\n" + "\n".join(lines) if lines else "Sua agenda está vazia. Quer recomendações?"
        if goal.intent == "submissoes":
            subs = out.get("status_submissoes") or []
            names = {"submitted": "submetido", "under_review": "em revisão", "accepted": "aceito", "rejected": "não aceito"}
            lines = [f"• {s['title']} — {names.get(s['status'], s['status'])}" for s in subs]
            return "Suas submissões:\n" + "\n".join(lines) if lines else "Você não possui submissões."
        if goal.intent == "memoria":
            k = memory.get("knowledge") or {}
            prof = out.get("meu_perfil") or {}
            parts = [f"Seus interesses cadastrados: {', '.join(prof.get('interests', [])) or '—'}."]
            if k:
                parts.append("Da nossa conversa eu lembro: " + "; ".join(f"{a.replace('_', ' ')} = {b}" for a, b in k.items()) + ".")
            parts.append(f"Temos {memory.get('long_term_events', 0)} mensagens na memória de longo prazo.")
            return " ".join(parts)
        return "Posso recomendar sessões pelo seu perfil, buscar na programação, montar sua agenda e consultar suas submissões."
