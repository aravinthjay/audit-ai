"""
Colab 2 — Extension Tasks 1 & 3
=================================
Extension 1: Custom selector_func — forces planner to go first,
             then lets the LLM router decide who speaks next.

Extension 3: Nested team inside a GraphFlow node — replaces the single
             researcher node with a RoundRobinGroupChat (researcher +
             fact_checker) wired in as one node. Patterns nest inside patterns.
"""

import os
import asyncio
from getpass import getpass

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import (
    SelectorGroupChat,
    RoundRobinGroupChat,
    DiGraphBuilder,
    GraphFlow,
)
from autogen_agentchat.ui import Console


# ---------------------------------------------------------------------------
# Step 1 — API Key
# ---------------------------------------------------------------------------
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass("Paste your OpenAI API key: ")

model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
print("Model client ready.\n")


# ---------------------------------------------------------------------------
# Shared agent factory — same three specialists used in both extensions
# ---------------------------------------------------------------------------
def make_specialists():
    planner = AssistantAgent(
        name="planner",
        model_client=model_client,
        description="Breaks a topic into 2-3 concrete sub-questions to research.",
        system_message=(
            "You plan research. Given a topic, list 2-3 specific "
            "sub-questions. Keep it short."
        ),
    )
    researcher = AssistantAgent(
        name="researcher",
        model_client=model_client,
        description="Answers factual sub-questions with concise bullet points.",
        system_message="You answer the planner's sub-questions with short factual bullets.",
    )
    writer = AssistantAgent(
        name="writer",
        model_client=model_client,
        description="Turns research bullets into a tight 4-sentence summary, ending with APPROVE.",
        system_message=(
            "Write a tight 4-sentence summary from the research. "
            "End your message with APPROVE."
        ),
    )
    return planner, researcher, writer


# ---------------------------------------------------------------------------
# EXTENSION 1 — Custom selector_func
# ---------------------------------------------------------------------------
#
# How it works:
#   SelectorGroupChat normally asks an LLM to pick the next speaker every turn.
#   By passing selector_func, we override that routing with our own Python logic.
#
#   The function receives the full message history and must return either:
#     - A string (the agent name to speak next)  → forces that speaker
#     - None                                      → defers back to the LLM router
#
#   Our rule: if this is the very first message (history has 1 entry — the
#   task), force "planner" so the topic is always broken down first.
#   After that, return None and let the model decide who's most useful next.
#
# Why this matters:
#   In a pure LLM-routed SelectorGroupChat the model might start with the
#   writer or researcher by mistake. The custom function gives you a guarantee
#   without abandoning the flexibility of LLM routing for all later turns.
# ---------------------------------------------------------------------------

def force_planner_first(messages) -> str | None:
    """
    Custom selector function for SelectorGroupChat.

    Rules:
      - First turn (only the task message exists): force 'planner'.
      - All subsequent turns: return None → defer to the LLM router.
    """
    if len(messages) <= 1:
        print("  [selector_func] First turn — forcing planner.\n")
        return "planner"
    print(f"  [selector_func] Turn {len(messages)} — deferring to LLM router.\n")
    return None


async def run_extension_1():
    print("=" * 60)
    print("  EXTENSION 1 — Custom selector_func")
    print("=" * 60)
    print()
    print("What to watch:")
    print("  Turn 1 : selector_func forces 'planner' (guaranteed)")
    print("  Turn 2+: LLM router picks the most relevant speaker")
    print("  This is different from RoundRobin (fixed order) and")
    print("  pure SelectorGroupChat (LLM routes every single turn).")
    print()

    planner, researcher, writer = make_specialists()

    termination = (
        TextMentionTermination("APPROVE") | MaxMessageTermination(max_messages=8)
    )

    team = SelectorGroupChat(
        participants=[planner, researcher, writer],
        model_client=model_client,          # LLM brain for turns where func returns None
        selector_func=force_planner_first,  # our custom override
        termination_condition=termination,
        allow_repeated_speaker=False,       # prevents one agent monopolising
    )

    await Console(
        team.run_stream(task="Topic: benefits of a standing desk.")
    )

    print("\n[Extension 1 complete]\n")


# ---------------------------------------------------------------------------
# EXTENSION 3 — Nested team inside a GraphFlow node
# ---------------------------------------------------------------------------
#
# How it works:
#   A normal GraphFlow node holds one agent. But DiGraphBuilder also accepts
#   a *team* as a node — the team runs internally until its own termination
#   condition fires, then the graph moves on to the next node.
#
#   We replace the single 'researcher' node with a RoundRobinGroupChat
#   containing:
#     - researcher : finds factual bullets
#     - fact_checker: verifies each bullet and flags anything uncertain
#
#   The graph is still: planner → research_team → writer
#   But the middle node is now a full sub-pipeline, not a single agent.
#
# Why this matters:
#   Composition is what makes complex systems manageable. Each "box" in your
#   graph can itself be a complete workflow. You can test, replace, or scale
#   each box independently without changing the outer graph.
# ---------------------------------------------------------------------------

async def run_extension_3():
    print("=" * 60)
    print("  EXTENSION 3 — Nested Team inside a GraphFlow node")
    print("=" * 60)
    print()
    print("Pipeline structure:")
    print("  planner → [researcher + fact_checker] → writer")
    print("             ↑ this middle box is a RoundRobinGroupChat ↑")
    print()
    print("What to watch:")
    print("  The planner breaks the topic into sub-questions.")
    print("  researcher and fact_checker take turns inside the nested team.")
    print("  Once the inner team finishes, the writer gets all the output.")
    print()

    planner, researcher, writer = make_specialists()

    # Extra agent only needed in Extension 3
    fact_checker = AssistantAgent(
        name="fact_checker",
        model_client=model_client,
        description="Verifies research bullets and flags anything uncertain.",
        system_message=(
            "You receive research bullet points. For each one, either confirm "
            "it is accurate or flag it with [UNCERTAIN]. Keep responses short. "
            "End with VERIFIED when done."
        ),
    )

    # Inner team: researcher and fact_checker alternate for up to 4 messages
    # The inner termination stops the sub-pipeline so the graph can move on
    research_team = RoundRobinGroupChat(
        participants=[researcher, fact_checker],
        termination_condition=(
            TextMentionTermination("VERIFIED") | MaxMessageTermination(max_messages=4)
        ),
    )

    # Build the outer graph: planner → research_team (nested) → writer
    builder = DiGraphBuilder()
    builder.add_node(planner)
    builder.add_node(research_team)   # <── a team, not a single agent
    builder.add_node(writer)

    builder.add_edge(planner, research_team)
    builder.add_edge(research_team, writer)

    graph = builder.build()

    flow = GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
    )

    await Console(
        flow.run_stream(task="Topic: the benefits of cycling to work.")
    )

    print("\n[Extension 3 complete]\n")


# ---------------------------------------------------------------------------
# Main — run both extensions in sequence
# ---------------------------------------------------------------------------
async def main():
    await run_extension_1()
    await run_extension_3()
    await model_client.close()
    print("=" * 60)
    print("  Both extensions complete. Model client closed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
