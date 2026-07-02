"""
Multi-agent crew orchestration using LangGraph.
Defines the Supervisor, Evidence, Challenger, Defender, Adjudicator, and Verifier agents.

Heavy dependencies (langgraph and provider clients) are imported lazily so this
module can be imported in environments where they are not installed.
"""

import json
import logging
import re
from typing import Any, Callable, Optional, TypedDict

from app.core.config import settings

logger = logging.getLogger(__name__)


class InvestigationMessage(TypedDict, total=False):
    role: str
    content: str
    agent: Optional[str]


class InvestigationState(TypedDict, total=False):
    investigation_id: str
    transaction_id: str
    vendor: str
    category: str
    amount: float
    materiality: float
    evidence: list[dict]
    evidence_summary: str
    rag_context: str
    rag_citations: list[str]
    debate_round: int
    attempt: int
    has_corroboration: bool
    verification_feedback: str
    max_debate_rounds: int
    challenger_arguments: list[str]
    defender_arguments: list[str]
    debate_transcript: list[InvestigationMessage]
    adjudication: dict
    verification_results: dict
    messages: list[InvestigationMessage]
    workflow_state: str
    status: str
    llm_usage: list[dict]


def _extract_json(text: str) -> Optional[dict]:
    # Weaker models sometimes wrap JSON in markdown fences or prose; strip a
    # leading ```json / ``` fence before attempting to parse.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


# Static role instructions live in system prompts so they are sent once as a
# cacheable prefix instead of being re-billed inside every user prompt. This
# trims prompt tokens on every agent call without changing output quality.
SYSTEM_PROMPTS: dict[str, str] = {
    "evidence_collection": (
        "You are the Evidence Collection Agent in an audit investigation system. "
        "Return a concise, source-grounded evidence summary: key sources, red flags, "
        "follow-up questions, and citation ids. State clearly whether external "
        "corroboration was found, missing, or pending. Preserve any citation ids. "
        "Be terse - no preamble, no restating the task."
    ),
    "challenger_argument": (
        "You are the Challenger Agent in an audit debate. Argue the worst-case "
        "interpretation grounded ONLY in the evidence. Advance the argument each round; "
        "never repeat prior points. Be terse and specific about the control risk."
    ),
    "defender_argument": (
        "You are the Defender Agent in an audit debate. Argue the most legitimate "
        "interpretation grounded ONLY in the evidence. Directly rebut the Challenger's "
        "latest point with specific citations. Be terse; never repeat a prior rebuttal."
    ),
    "adjudication": (
        "You are the Adjudicator Agent. Weigh the debate and evidence and return a final "
        "risk verdict. Respond with ONLY a JSON object and no prose: "
        '{"risk_level":"critical|high|medium|low|cleared","confidence":0.0,'
        '"reasoning":"...","key_concerns":["..."],"mitigating_factors":["..."]}'
    ),
    "verification": (
        "You are the Verifier Agent doing QA grounding. Decide whether every material "
        "claim in the adjudication is supported by the evidence. Make any missing "
        "evidence actionable. Respond with ONLY a JSON object and no prose: "
        '{"is_grounded":true,"ungrounded_claims":["..."],"verification_report":"..."}'
    ),
}

# Per-agent output caps. Output tokens dominate cost, so we bound each agent to
# what a focused answer needs instead of the global 4000-token ceiling.
MAX_OUTPUT_TOKENS: dict[str, int] = {
    "evidence_collection": 700,
    "challenger_argument": 450,
    "defender_argument": 450,
    "adjudication": 600,
    "verification": 450,
}


def _compact_citations(evidence_items: list[dict]) -> str:
    """Summarize evidence artifacts as source+citation ids only.

    The full artifact content already lives in the evidence summary, so re-dumping
    it as JSON in adjudicator/verifier prompts just doubles the token bill. We keep
    the provenance (source name + citation ids) which is what grounding checks need.
    """
    if not evidence_items:
        return "None"
    parts = []
    for item in evidence_items:
        source = item.get("source", "unknown")
        citations = item.get("citations") or []
        cite_text = f" [{', '.join(map(str, citations))}]" if citations else ""
        parts.append(f"{source}{cite_text}")
    return "; ".join(parts)


def _join_points(points: list[str]) -> str:
    """Number a list of argument strings compactly, or 'None yet' when empty."""
    if not points:
        return "None yet"
    return "\n".join(f"{i}. {p}" for i, p in enumerate(points, 1))


def _complete_llm(
    state: InvestigationState,
    prompt: str,
    *,
    request_type: str,
    complexity: str = "complex",
    temperature: float | None = None,
):
    from app.llm import LLMRequest, get_llm_service

    response = get_llm_service().complete(
        LLMRequest(
            prompt=prompt,
            request_type=request_type,
            system_prompt=SYSTEM_PROMPTS.get(request_type),
            complexity=complexity,  # type: ignore[arg-type]
            temperature=temperature,  # None -> each provider applies its own configured temperature
            max_tokens=MAX_OUTPUT_TOKENS.get(request_type, settings.CLAUDE_MAX_TOKENS),
            metadata={"investigation_id": state.get("investigation_id")},
        )
    )
    state.setdefault("llm_usage", []).append(
        {
            "provider": response.provider,
            "model": response.model,
            "request_type": request_type,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "estimated_cost_usd": response.estimated_cost_usd,
            "fallback_used": response.fallback_used,
            "fallback_provider": response.fallback_provider,
            "routing_reason": response.routing_reason,
        }
    )
    return response


def create_supervisor_agent() -> Callable[[InvestigationState], InvestigationState]:
    def supervisor_node(state: InvestigationState) -> InvestigationState:
        logger.info(f"Supervisor routing investigation {state['investigation_id']}")
        state.setdefault("messages", [])
        current = state.get("workflow_state", "intake")

        transitions = {
            "intake": ("evidence", "Routing to Evidence Collection phase"),
            "evidence": ("debate", "Evidence collected. Initiating debate phase."),
            "adjudication": ("verification", "Adjudication complete. Verifying claims."),
        }
        if current in transitions:
            next_state, msg = transitions[current]
            state["workflow_state"] = next_state
            state["messages"].append(
                InvestigationMessage(role="system", content=f"Supervisor: {msg}", agent="supervisor")
            )
        elif current == "debate":
            if state.get("debate_round", 0) >= state.get("max_debate_rounds", 2):
                state["workflow_state"] = "adjudication"
                state["messages"].append(
                    InvestigationMessage(
                        role="system",
                        content="Supervisor: Debate complete. Moving to adjudication.",
                        agent="supervisor",
                    )
                )
        elif current == "verification":
            state["status"] = "completed"
            state["messages"].append(
                InvestigationMessage(
                    role="system", content="Supervisor: Investigation complete.", agent="supervisor"
                )
            )
        return state

    return supervisor_node


def create_evidence_agent() -> Callable[[InvestigationState], InvestigationState]:
    def evidence_node(state: InvestigationState) -> InvestigationState:
        logger.info(f"Evidence agent processing {state['investigation_id']}")
        attempt = state.get("attempt", 1)
        feedback = state.get("verification_feedback", "")
        previous_summary = state.get("evidence_summary", "None yet")
        retry_hint = (
            "\nThis is a retry - focus only on missing external corroboration "
            "(vendor master data, POs, approvals, contracts, policy authority)."
            if attempt > 1
            else ""
        )
        prompt = f"""Transaction: {state['vendor']} | {state['category']} | ${state['amount']:,.2f} | materiality ${state.get('materiality', 0):,.2f}
Attempt: {attempt}
Prior summary: {previous_summary}
Verifier feedback: {feedback or 'None'}
Policy/data context:
{state.get('rag_context') or 'No policy chunks retrieved.'}{retry_hint}"""
        response = _complete_llm(
            state,
            prompt,
            request_type="evidence_collection",
            complexity="complex",
        )
        summary = response.content
        if attempt > 1 and previous_summary not in ("", "None yet"):
            state["evidence_summary"] = f"{previous_summary}\n\nFollow-up corroboration query: {summary}"
        else:
            state["evidence_summary"] = summary
        state.setdefault("evidence", []).append(
            {
                "source": f"{response.provider}_analysis"
                if attempt == 1
                else f"{response.provider}_corroboration_query",
                "content": summary,
                "citations": state.get("rag_citations", []),
                "relevance_score": 0.75 if attempt == 1 else 0.85,
            }
        )
        state.setdefault("messages", []).append(
            InvestigationMessage(role="assistant", content=summary, agent="evidence_agent")
        )
        return state

    return evidence_node


def create_challenger_agent() -> Callable[[InvestigationState], InvestigationState]:
    def challenger_node(state: InvestigationState) -> InvestigationState:
        logger.info(f"Challenger processing {state['investigation_id']}")
        round_num = state.get("debate_round", 0) + 1
        prior_defender = state.get("defender_arguments", [])
        feedback = state.get("verification_feedback", "")
        prompt = f"""Round {round_num}. Transaction: {state['vendor']} - {state['category']} - ${state['amount']:,.2f}
Evidence: {state.get('evidence_summary', 'Not yet collected')}
Defender's last rebuttal: {prior_defender[-1] if prior_defender else 'None yet'}
{f'Verifier feedback to address: {feedback}' if feedback else ''}"""
        response = _complete_llm(
            state,
            prompt,
            request_type="challenger_argument",
            complexity="complex",
        )
        state.setdefault("challenger_arguments", []).append(response.content)
        state.setdefault("debate_transcript", []).append(
            InvestigationMessage(role="assistant", content=response.content, agent="challenger")
        )
        return state

    return challenger_node


def create_defender_agent() -> Callable[[InvestigationState], InvestigationState]:
    def defender_node(state: InvestigationState) -> InvestigationState:
        logger.info(f"Defender processing {state['investigation_id']}")
        challenger_args = state.get("challenger_arguments", [])
        prior_defender = state.get("defender_arguments", [])
        feedback = state.get("verification_feedback", "")
        round_num = state.get("debate_round", 0) + 1
        prompt = f"""Round {round_num}. Transaction: {state['vendor']} - {state['category']} - ${state['amount']:,.2f}
Evidence: {state.get('evidence_summary', 'Not yet collected')}
Challenger's latest argument: {challenger_args[-1] if challenger_args else 'None yet'}
Your previous rebuttal: {prior_defender[-1] if prior_defender else 'None yet'}
{f'New evidence / verifier feedback: {feedback}' if feedback else ''}"""
        response = _complete_llm(
            state,
            prompt,
            request_type="defender_argument",
            complexity="complex",
        )
        state.setdefault("defender_arguments", []).append(response.content)
        state.setdefault("debate_transcript", []).append(
            InvestigationMessage(role="assistant", content=response.content, agent="defender")
        )
        # A full round = challenger + defender. Increment here so the debate
        # routing terminates instead of looping forever.
        state["debate_round"] = state.get("debate_round", 0) + 1
        return state

    return defender_node


def create_adjudicator_agent() -> Callable[[InvestigationState], InvestigationState]:
    def adjudicator_node(state: InvestigationState) -> InvestigationState:
        logger.info(f"Adjudicator processing {state['investigation_id']}")
        challenger_args = state.get("challenger_arguments", [])
        defender_args = state.get("defender_arguments", [])
        prompt = f"""Transaction: {state['vendor']} - {state['category']} - ${state['amount']:,.2f}
Evidence summary: {state.get('evidence_summary', 'None')}
Evidence citations: {_compact_citations(state.get('evidence', []))}
Challenger arguments:
{_join_points(challenger_args)}
Defender arguments:
{_join_points(defender_args)}"""
        response = _complete_llm(
            state,
            prompt,
            request_type="adjudication",
            complexity="critical",
        )
        adjudication = _extract_json(response.content) or {
            "risk_level": "medium",
            "confidence": 0.5,
            "reasoning": response.content,
            "key_concerns": [],
            "mitigating_factors": [],
        }
        state["adjudication"] = adjudication
        state.setdefault("messages", []).append(
            InvestigationMessage(
                role="assistant",
                content=f"Adjudication: {adjudication.get('risk_level', 'unknown')} risk",
                agent="adjudicator",
            )
        )
        return state

    return adjudicator_node


def create_verifier_agent() -> Callable[[InvestigationState], InvestigationState]:
    def verifier_node(state: InvestigationState) -> InvestigationState:
        logger.info(f"Verifier processing {state['investigation_id']}")
        adjudication = state.get("adjudication", {})
        prompt = f"""Evidence: {state.get('evidence_summary', 'None')}
Evidence citations: {_compact_citations(state.get('evidence', []))}
Adjudication to check: risk={adjudication.get('risk_level', 'unknown')}, confidence={adjudication.get('confidence', 0)}, concerns={adjudication.get('key_concerns', [])}"""
        response = _complete_llm(
            state,
            prompt,
            request_type="verification",
            complexity="critical",
            temperature=0.2,
        )
        parsed = _extract_json(response.content) or {
            "is_grounded": True,
            "ungrounded_claims": [],
            "verification_report": response.content,
        }
        state["verification_results"] = {
            "is_grounded": bool(parsed.get("is_grounded", True)),
            "ungrounded_claims": parsed.get("ungrounded_claims") or [],
            "verification_report": parsed.get("verification_report", ""),
        }
        state.setdefault("messages", []).append(
            InvestigationMessage(role="assistant", content="Verification complete", agent="verifier")
        )
        return state

    return verifier_node


def route_debate(state: InvestigationState) -> str:
    if state.get("debate_round", 0) < state.get("max_debate_rounds", 2):
        return "challenger"
    return "adjudicator"


def create_investigation_graph() -> Any:
    from langgraph.graph import END, StateGraph

    graph = StateGraph(InvestigationState)
    graph.add_node("supervisor", create_supervisor_agent())
    graph.add_node("evidence", create_evidence_agent())
    graph.add_node("challenger", create_challenger_agent())
    graph.add_node("defender", create_defender_agent())
    graph.add_node("adjudicator", create_adjudicator_agent())
    graph.add_node("verifier", create_verifier_agent())

    graph.add_edge("supervisor", "evidence")
    graph.add_edge("evidence", "challenger")
    graph.add_edge("challenger", "defender")
    graph.add_conditional_edges(
        "defender", route_debate, {"challenger": "challenger", "adjudicator": "adjudicator"}
    )
    graph.add_edge("adjudicator", "verifier")
    graph.add_edge("verifier", END)
    graph.set_entry_point("supervisor")
    return graph.compile()
