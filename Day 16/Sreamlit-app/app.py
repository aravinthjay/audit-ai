import os

import streamlit as st
from dotenv import load_dotenv

from agent import DEFAULT_MAX_ITERATIONS, DEFAULT_MODEL, build_graph, initial_state

load_dotenv()

st.set_page_config(page_title="Planner-Executor-Verifier Agent", page_icon="🧭", layout="centered")

st.title("🧭 Planner → Executor → Verifier")
st.caption(
    "A planner breaks your goal into tasks, an executor completes them "
    "(with web search when useful), and a verifier grades the result -- "
    "looping back to the executor if it's not good enough yet."
)

with st.sidebar:
    st.header("Settings")
    env_key = os.environ.get("GROQ_API_KEY", "")
    api_key = st.text_input(
        "Groq API key",
        value=env_key,
        type="password",
        help="Loaded automatically if GROQ_API_KEY is set in a .env file.",
    )
    model_name = st.text_input("Model", value=DEFAULT_MODEL)
    max_iterations = st.number_input(
        "Max iterations before force-approve", min_value=1, max_value=10, value=DEFAULT_MAX_ITERATIONS
    )
    st.markdown("---")
    st.caption("Get a free key at [console.groq.com/keys](https://console.groq.com/keys)")

goal = st.text_area(
    "What's your goal?",
    placeholder="e.g. Research and summarise the top 3 trends in agriculture for 2025",
    height=100,
)

run_clicked = st.button("Run agent", type="primary", disabled=not goal.strip())

if run_clicked:
    if not api_key:
        st.error("Add your Groq API key in the sidebar first.")
        st.stop()

    try:
        graph = build_graph(api_key=api_key, model_name=model_name, max_iterations=int(max_iterations))
    except Exception as e:
        st.error(f"Couldn't build the agent graph: {e}")
        st.stop()

    state = initial_state(goal)
    counters = {"executor": 0, "verifier": 0}
    final_state = state

    try:
        for update in graph.stream(state, stream_mode="updates"):
            for node_name, node_output in update.items():
                state = {**state, **node_output}

                if node_name == "planner":
                    with st.status("📋 Planner", state="complete", expanded=True):
                        for i, t in enumerate(state["tasks"], 1):
                            st.write(f"{i}. {t}")

                elif node_name == "executor":
                    counters["executor"] += 1
                    with st.status(f"⚙️ Executor -- iteration {counters['executor']}", state="complete", expanded=True):
                        for t, r in zip(state["tasks"], state["results"]):
                            st.markdown(f"**Task:** {t}")
                            st.write(r)
                            st.markdown("---")

                elif node_name == "verifier":
                    counters["verifier"] += 1
                    icon = "✅" if state["approved"] else "🔁"
                    label = f"{icon} Verifier -- iteration {counters['verifier']}"
                    with st.status(label, state="complete", expanded=True):
                        st.write(f"**Score:** {state.get('score', 'n/a')}")
                        st.write(f"**Approved:** {state['approved']}")
                        if state["critique"]:
                            st.write(f"**Critique:** {state['critique']}")

                final_state = state

    except Exception as e:
        st.error(f"The agent hit an error mid-run: {e}")
        st.stop()

    st.markdown("## Final result")
    if final_state["approved"]:
        st.success(f"Approved after {final_state['iterations']} iteration(s).")
    else:
        st.warning(f"Stopped after {final_state['iterations']} iteration(s) without a clean approval.")

    for t, r in zip(final_state["tasks"], final_state["results"]):
        st.markdown(f"**{t}**")
        st.write(r)

    report = f"# Goal\n{goal}\n\n" + "\n\n".join(
        f"## {t}\n{r}" for t, r in zip(final_state["tasks"], final_state["results"])
    )
    st.download_button("Download results as Markdown", report, file_name="agent_results.md")
