"""
Planner -> Executor -> Verifier multi-agent pipeline.

This is the same agent from your notebook, refactored out of notebook-global
variables into a small module that takes its API key and settings as
arguments. app.py (the Streamlit UI) imports build_graph() and streams it
node by node so the UI can show each agent's work as it happens.
"""

import json
from typing import List, TypedDict

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_ITERATIONS = 3


class AgentState(TypedDict):
    goal: str
    tasks: List[str]
    results: List[str]
    critique: str
    score: float
    approved: bool
    iterations: int


def initial_state(goal: str) -> AgentState:
    return {
        "goal": goal,
        "tasks": [],
        "results": [],
        "critique": "",
        "score": 0.0,
        "approved": False,
        "iterations": 0,
    }


# ---------------------------------------------------------------------------
# Agent 1: planner -- breaks the goal into at most 5 concrete tasks
# ---------------------------------------------------------------------------
def make_planner(llm: ChatGroq):
    def planner(state: AgentState) -> AgentState:
        system = (
            "You are a planning agent. Break the user's goal into "
            "at most 5 concrete, actionable tasks. Respond ONLY with a "
            "valid JSON array of strings. No preamble, no markdown."
        )
        messages = [SystemMessage(content=system), HumanMessage(content=f"Goal: {state['goal']}")]
        response = llm.invoke(messages).content.strip()

        try:
            clean = response.replace("```json", "").replace("```", "").strip()
            tasks = json.loads(clean)
        except json.JSONDecodeError:
            tasks = [response]  # fallback: treat the whole response as one task

        return {**state, "tasks": tasks}

    return planner


# ---------------------------------------------------------------------------
# Agent 2: executor -- completes each task, optionally using web search
# ---------------------------------------------------------------------------
def make_executor(llm: ChatGroq, search: DuckDuckGoSearchRun):
    def executor(state: AgentState) -> AgentState:
        results = []
        critique_ctx = ""
        if state["critique"]:
            critique_ctx = f"\n\nYour previous attempt was rejected. Previous critique: {state['critique']}"

        for task in state["tasks"]:
            system = (
                "You are an execution agent. Complete the task thoroughly. "
                f"Use web search if you need current information.{critique_ctx}"
            )

            search_ctx = ""
            try:
                search_result = search.run(task[:100])
                search_ctx = f"\n\nWeb search result for context:\n{search_result[:800]}"
            except Exception:
                pass  # web search is best-effort; the LLM can still answer without it

            messages = [SystemMessage(content=system), HumanMessage(content=f"Task: {task}{search_ctx}")]
            result = llm.invoke(messages).content
            results.append(result)

        return {**state, "results": results, "iterations": state["iterations"] + 1}

    return executor


# ---------------------------------------------------------------------------
# Agent 3: verifier -- LLM-as-judge, grades the results against the goal
# ---------------------------------------------------------------------------
def make_verifier(llm: ChatGroq, max_iterations: int = DEFAULT_MAX_ITERATIONS):
    def verifier(state: AgentState) -> AgentState:
        if state["iterations"] >= max_iterations:
            return {**state, "approved": True, "critique": "Max iterations reached -- force approved."}

        combined_results = "\n\n".join(
            f"Task {i + 1}: {t}\nResult: {r}"
            for i, (t, r) in enumerate(zip(state["tasks"], state["results"]))
        )
        system = (
            "You are a quality verifier. Evaluate the results against the "
            "original goal using this rubric: completeness (0-0.4), "
            "accuracy (0-0.3), clarity (0-0.3). Sum the scores for a total "
            'between 0.0 and 1.0. Respond ONLY as JSON: '
            '{"score": 0.9, "approved": true, "critique": "..."}'
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Original goal: {state['goal']}\n\nResults:\n{combined_results}"),
        ]
        raw = llm.invoke(messages).content.strip()

        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            verdict = json.loads(clean)
            approved = verdict.get("approved", False)
            critique = verdict.get("critique", "")
            score = verdict.get("score", 0)
        except Exception:
            approved, critique, score = False, raw, 0

        return {**state, "approved": approved, "critique": critique, "score": score}

    return verifier


def route_after_verify(state: AgentState) -> str:
    return "end" if state["approved"] else "executor"


# ---------------------------------------------------------------------------
# Wire the three agents into a LangGraph pipeline
# ---------------------------------------------------------------------------
def build_graph(api_key: str, model_name: str = DEFAULT_MODEL, max_iterations: int = DEFAULT_MAX_ITERATIONS):
    llm = ChatGroq(temperature=0, model_name=model_name, groq_api_key=api_key)
    search = DuckDuckGoSearchRun()

    graph = StateGraph(AgentState)
    graph.add_node("planner", make_planner(llm))
    graph.add_node("executor", make_executor(llm, search))
    graph.add_node("verifier", make_verifier(llm, max_iterations))

    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges("verifier", route_after_verify, {"end": END, "executor": "executor"})
    graph.set_entry_point("planner")

    return graph.compile()
