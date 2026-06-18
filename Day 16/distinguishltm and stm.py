import json
from typing import List, TypedDict

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

# ============================================================
# CONFIG
# ============================================================

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_ITERATIONS = 3


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(TypedDict):
    goal: str

    stm_tasks: List[str]
    ltm_tasks: List[str]

    results: List[str]

    critique: str
    score: float
    approved: bool

    iterations: int


# ============================================================
# INITIAL STATE
# ============================================================

def initial_state(goal: str) -> AgentState:
    return {
        "goal": goal,

        "stm_tasks": [],
        "ltm_tasks": [],

        "results": [],

        "critique": "",
        "score": 0.0,
        "approved": False,

        "iterations": 0,
    }


# ============================================================
# PLANNER AGENT
# Distinguishes STM and LTM tasks
# ============================================================

def make_planner(llm):

    def planner(state: AgentState) -> AgentState:

        system_prompt = """
You are a budgeting planning agent.

Your job is to break the user's goal into:

1. STM Tasks (Short-Term Memory)
   - Information needed only for this budgeting session
   - Example:
       Current income
       Current expenses
       One-time purchases
       Utility bills

2. LTM Tasks (Long-Term Memory)
   - Information that should persist across sessions
   - Example:
       Savings goals
       Risk tolerance
       Investment preferences
       Recurring subscriptions

Return ONLY valid JSON.

Format:

{
    "stm_tasks": [
        "task1",
        "task2"
    ],
    "ltm_tasks": [
        "task1",
        "task2"
    ]
}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Goal: {state['goal']}")
        ]

        response = llm.invoke(messages).content.strip()

        try:
            clean = (
                response
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            plan = json.loads(clean)

            stm_tasks = plan.get("stm_tasks", [])
            ltm_tasks = plan.get("ltm_tasks", [])

        except Exception:

            stm_tasks = [
                "Collect current income",
                "Collect current expenses"
            ]

            ltm_tasks = [
                "Retrieve savings goals"
            ]

        return {
            **state,
            "stm_tasks": stm_tasks,
            "ltm_tasks": ltm_tasks
        }

    return planner


# ============================================================
# EXECUTOR AGENT
# Executes STM + LTM tasks
# ============================================================

def make_executor(llm, search):

    def executor(state: AgentState) -> AgentState:

        results = []

        critique_context = ""

        if state["critique"]:
            critique_context = (
                f"\n\nPrevious Critique:\n{state['critique']}"
            )

        all_tasks = (
            state["stm_tasks"] +
            state["ltm_tasks"]
        )

        for task in all_tasks:

            search_context = ""

            try:

                search_result = search.run(task[:100])

                search_context = (
                    f"\n\nSearch Context:\n"
                    f"{search_result[:800]}"
                )

            except Exception:
                pass

            system_prompt = f"""
You are a budgeting execution agent.

Complete the assigned task thoroughly.

{critique_context}
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=f"""
Task:
{task}

{search_context}
"""
                )
            ]

            result = llm.invoke(messages).content

            results.append(
                f"Task: {task}\n\n{result}"
            )

        return {
            **state,
            "results": results,
            "iterations": state["iterations"] + 1
        }

    return executor


# ============================================================
# VERIFIER AGENT
# ============================================================

def make_verifier(
    llm,
    max_iterations=DEFAULT_MAX_ITERATIONS
):

    def verifier(state: AgentState) -> AgentState:

        if state["iterations"] >= max_iterations:

            return {
                **state,
                "approved": True,
                "score": 1.0,
                "critique": (
                    "Maximum iterations reached. "
                    "Auto-approved."
                )
            }

        combined_results = "\n\n".join(
            state["results"]
        )

        system_prompt = """
You are a budgeting quality verifier.

Evaluate the output using:

Completeness (0.4)
Accuracy (0.3)
Clarity (0.3)

Total score must be between 0 and 1.

Return ONLY valid JSON.

Format:

{
    "score": 0.92,
    "approved": true,
    "critique": "reason"
}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"""
Original Goal:
{state['goal']}

Results:
{combined_results}
"""
            )
        ]

        response = llm.invoke(messages).content.strip()

        try:

            clean = (
                response
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            verdict = json.loads(clean)

            score = float(
                verdict.get("score", 0)
            )

            approved = verdict.get(
                "approved",
                False
            )

            critique = verdict.get(
                "critique",
                ""
            )

        except Exception:

            score = 0
            approved = False
            critique = response

        return {
            **state,
            "score": score,
            "approved": approved,
            "critique": critique
        }

    return verifier


# ============================================================
# ROUTER
# ============================================================

def route_after_verify(state: AgentState):

    if state["approved"]:
        return "end"

    return "executor"


# ============================================================
# GRAPH BUILDER
# ============================================================

def build_graph(
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    max_iterations: int = DEFAULT_MAX_ITERATIONS
):

    llm = ChatGroq(
        temperature=0,
        model_name=model_name,
        groq_api_key=api_key
    )

    search = DuckDuckGoSearchRun()

    graph = StateGraph(AgentState)

    graph.add_node(
        "planner",
        make_planner(llm)
    )

    graph.add_node(
        "executor",
        make_executor(llm, search)
    )

    graph.add_node(
        "verifier",
        make_verifier(
            llm,
            max_iterations
        )
    )

    graph.add_edge(
        "planner",
        "executor"
    )

    graph.add_edge(
        "executor",
        "verifier"
    )

    graph.add_conditional_edges(
        "verifier",
        route_after_verify,
        {
            "end": END,
            "executor": "executor"
        }
    )

    graph.set_entry_point(
        "planner"
    )

    return graph.compile()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    API_KEY = "YOUR_GROQ_API_KEY"

    graph = build_graph(API_KEY)

    state = initial_state(
        """
        Create a monthly budget plan for a family
        earning ₹100000 per month.
        Distinguish STM and LTM factors.
        """
    )

    final_state = graph.invoke(state)

    print("\n========== STM TASKS ==========")
    print(final_state["stm_tasks"])

    print("\n========== LTM TASKS ==========")
    print(final_state["ltm_tasks"])

    print("\n========== RESULTS ==========")

    for result in final_state["results"]:
        print(result)
        print("\n" + "=" * 80)

    print("\n========== SCORE ==========")
    print(final_state["score"])

    print("\n========== APPROVED ==========")
    print(final_state["approved"])

    print("\n========== CRITIQUE ==========")
    print(final_state["critique"])