"""Agent state-machine tests (no LLM calls)."""

from app.agents.crew import create_supervisor_agent, route_debate


def test_route_debate_continues_until_max_rounds():
    assert route_debate({"debate_round": 0, "max_debate_rounds": 2}) == "challenger"
    assert route_debate({"debate_round": 1, "max_debate_rounds": 2}) == "challenger"


def test_route_debate_terminates_at_max_rounds():
    assert route_debate({"debate_round": 2, "max_debate_rounds": 2}) == "adjudicator"
    assert route_debate({"debate_round": 5, "max_debate_rounds": 2}) == "adjudicator"


def test_supervisor_advances_state():
    supervisor = create_supervisor_agent()
    state = {"investigation_id": "x", "workflow_state": "intake", "messages": []}
    out = supervisor(state)
    assert out["workflow_state"] == "evidence"
