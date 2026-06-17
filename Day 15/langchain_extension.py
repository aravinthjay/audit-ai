# pip install langgraph langchain

from typing import TypedDict
from langgraph.graph import StateGraph, END

# ----------------------------
# State Definition
# ----------------------------

class LoanState(TypedDict):
    application_id: str
    loan_amount: float
    risk_score: float
    route: str
    decision: str

# ----------------------------
# Routing Node
# ----------------------------

def route_loan(state: LoanState):
    if state["loan_amount"] >= 1_000_000 or state["risk_score"] >= 0.7:
        state["route"] = "human_review"
    else:
        state["route"] = "auto_process"

    return state

# ----------------------------
# Auto Process Node
# ----------------------------

def auto_process(state: LoanState):
    state["decision"] = "AUTO_APPROVED"
    return state

# ----------------------------
# Human Review Node
# ----------------------------

def human_review(state: LoanState):
    # Simulated human decision
    if state["risk_score"] < 0.7:
        state["decision"] = "HUMAN_APPROVED"
    else:
        state["decision"] = "HUMAN_REJECTED"

    return state

# ----------------------------
# Conditional Edge Logic
# ----------------------------

def decide_next_node(state: LoanState):
    return state["route"]

# ----------------------------
# Build LangGraph
# ----------------------------

workflow = StateGraph(LoanState)

workflow.add_node("route_loan", route_loan)
workflow.add_node("auto_process", auto_process)
workflow.add_node("human_review", human_review)

workflow.set_entry_point("route_loan")

workflow.add_conditional_edges(
    "route_loan",
    decide_next_node,
    {
        "auto_process": "auto_process",
        "human_review": "human_review",
    },
)

workflow.add_edge("auto_process", END)
workflow.add_edge("human_review", END)

app = workflow.compile()

# ----------------------------
# Test Cases
# ----------------------------

loans = [
    {
        "application_id": "APP100301",
        "loan_amount": 500000,
        "risk_score": 0.25,
    },
    {
        "application_id": "APP100302",
        "loan_amount": 1500000,
        "risk_score": 0.62,
    },
    {
        "application_id": "APP100303",
        "loan_amount": 200000,
        "risk_score": 0.82,
    },
]

for loan in loans:
    result = app.invoke(loan)

    print(
        f"{result['application_id']} | "
        f"Amount={result['loan_amount']:,} | "
        f"Risk={result['risk_score']} | "
        f"Decision={result['decision']}"
    )