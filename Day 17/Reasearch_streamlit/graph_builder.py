import operator
from typing import Annotated, List, TypedDict, Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ─────────────────────────────────────────
# STATE & SCHEMA
# ─────────────────────────────────────────

class AgentState(TypedDict):
    task: str
    research_notes: Annotated[List[str], operator.add]
    draft: str
    next_node: str
    retry_count: int
    revision_feedback: str


class Router(BaseModel):
    """Decide which worker to call next."""
    next_worker: Literal["researcher", "writer", "FINISH"] = Field(
        description="The next node to act"
    )
    instructions: str = Field(description="Specific instructions for the worker")
    is_critical: bool = Field(description="If True, system will pause for human review")


# ─────────────────────────────────────────
# MODELS & TOOLS
# ─────────────────────────────────────────

llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
search_tool = TavilySearchResults(k=2)


# ─────────────────────────────────────────
# AGENT NODES
# ─────────────────────────────────────────

def researcher(state: AgentState):
    query = state["task"]
    results = search_tool.invoke(query)
    return {"research_notes": [str(results)], "retry_count": 0}


def writer(state: AgentState):
    context = "\n".join(state["research_notes"])
    res = llm.invoke(f"Write a detailed, well-structured report on '{state['task']}' using this research:\n\n{context}")
    return {"draft": res.content}


def supervisor(state: AgentState):
    structured_llm = llm.with_structured_output(Router)
    prompt = f"""
    Task: {state['task']}
    Notes collected: {len(state['research_notes'])}
    Current Draft: {state['draft'][:100]}...
    If you have something in research_notes, select writer.
    """
    decision = structured_llm.invoke(prompt)
    return {
        "next_node": decision.next_worker,
        "revision_feedback": decision.instructions,
    }


# ─────────────────────────────────────────
# GRAPH BUILDER
# ─────────────────────────────────────────

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("supervisor", supervisor)
    builder.add_node("researcher", researcher)
    builder.add_node("writer", writer)

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        lambda x: x["next_node"],
        {"researcher": "researcher", "writer": "writer", "FINISH": END},
    )

    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer", "supervisor")

    memory = MemorySaver()
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["writer"],
    )
    return graph
