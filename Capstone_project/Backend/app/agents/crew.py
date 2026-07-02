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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


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
            complexity=complexity,  # type: ignore[arg-type]
            temperature=settings.CLAUDE_TEMPERATURE if temperature is None else temperature,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
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
        prompt = f"""
You are the Evidence Collection Agent for an audit investigation system.

Transaction Details:
- Vendor: {state['vendor']}
- Category: {state['category']}
- Amount: ${state['amount']:,.2f}
- Materiality Threshold: ${state.get('materiality', 0):,.2f}

Attempt: {attempt}
Prior Evidence Summary: {previous_summary}
Verifier Feedback: {feedback or 'None yet'}
Retrieved Policy/Data Context:
{state.get('rag_context') or 'No policy chunks retrieved.'}

List key evidence sources, red flags, follow-up questions, and citations. If this
is a retry, focus the query on missing external corroboration such as vendor
master data, purchase orders, approvals, contracts, or policy authority.
Generate a concise evidence summary with actionable insights and clearly state
whether external corroboration was found, missing, or still pending.
Use the retrieved policy/data context when relevant and preserve citation ids.
"""
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
        prompt = f"""
You are the Challenger Agent in an audit investigation debate (round {round_num}).
Argue the WORST-CASE interpretation of this transaction, grounded ONLY in the evidence.

Transaction: {state['vendor']} - {state['category']} - ${state['amount']:,.2f}
Evidence Summary: {state.get('evidence_summary', 'Not yet collected')}

Defender's most recent rebuttal: {prior_defender[-1] if prior_defender else 'None yet'}
{f'Verifier feedback to address from the previous attempt: {feedback}' if feedback else ''}

If this is a later round, advance the argument: respond to the Defender's rebuttal and
sharpen the specific control risk instead of repeating your opening. Stay grounded in evidence.
"""
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
        prompt = f"""
You are the Defender Agent in an audit investigation debate (round {round_num}).
Argue the MOST LEGITIMATE interpretation of this transaction, grounded ONLY in the evidence.

Transaction: {state['vendor']} - {state['category']} - ${state['amount']:,.2f}
Evidence Summary: {state.get('evidence_summary', 'Not yet collected')}

Challenger's latest argument:
{challenger_args[-1] if challenger_args else 'None yet'}
Your previous rebuttal: {prior_defender[-1] if prior_defender else 'None yet'}
{f'New evidence / verifier feedback since the last attempt: {feedback}' if feedback else ''}

Directly rebut the Challenger's latest point and cite specific evidence. If new evidence is
available this round, use it - do not repeat your previous rebuttal verbatim.
"""
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
        evidence_items = state.get("evidence", [])
        prompt = f"""
You are the Adjudicator Agent. Weigh the debate and render a final risk verdict.

Transaction: {state['vendor']} - {state['category']} - ${state['amount']:,.2f}
Evidence Summary: {state.get('evidence_summary', 'None')}
Evidence Artifacts: {json.dumps(evidence_items, default=str)}

Challenger Arguments: {json.dumps(challenger_args, default=str)}
Defender Arguments: {json.dumps(defender_args, default=str)}

Return ONLY a JSON object:
{{"risk_level": "critical|high|medium|low|cleared", "confidence": 0.0,
  "reasoning": "...", "key_concerns": ["..."], "mitigating_factors": ["..."]}}
"""
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
        evidence_items = state.get("evidence", [])
        prompt = f"""
You are the Verifier Agent - your job is QA grounding.

Evidence Available: {state.get('evidence_summary', 'None')}
Evidence Artifacts: {json.dumps(evidence_items, default=str)}

Adjudication to check: risk={adjudication.get('risk_level', 'unknown')},
confidence={adjudication.get('confidence', 0)},
concerns={adjudication.get('key_concerns', [])}.

Decide whether EVERY material claim in the adjudication is supported by the evidence above.
If a claim is ungrounded, make the missing evidence actionable so the Supervisor can re-query.
Return ONLY a JSON object:
{{"is_grounded": true|false, "ungrounded_claims": ["..."], "verification_report": "..."}}
"""
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
