import streamlit as st
from dotenv import load_dotenv
from graph_builder import build_graph

load_dotenv()

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# DESIGN SYSTEM  — deep navy + electric indigo
# ─────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Background */
.stApp {
    background: #0b0f1a;
    color: #e2e8f0;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}

/* ── Block container ── */
.block-container {
    padding: 2rem 2.5rem 3rem;
    max-width: 1300px;
}

/* ── Hero header ── */
.hero {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 2rem 2.4rem;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid #312e81;
    border-radius: 16px;
    margin-bottom: 2rem;
}
.hero-icon {
    font-size: 3rem;
    line-height: 1;
    flex-shrink: 0;
}
.hero-title {
    font-size: 1.85rem;
    font-weight: 700;
    color: #e0e7ff;
    letter-spacing: -0.02em;
    margin: 0 0 4px;
}
.hero-sub {
    font-size: 0.92rem;
    color: #818cf8;
    margin: 0;
    font-weight: 400;
}

/* ── Pipeline badges ── */
.pipeline {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    flex-wrap: wrap;
}
.badge {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    padding: 3px 10px;
    border-radius: 999px;
    text-transform: uppercase;
}
.badge-supervisor { background: #1e293b; color: #818cf8; border: 1px solid #312e81; }
.badge-researcher { background: #1e293b; color: #34d399; border: 1px solid #065f46; }
.badge-writer     { background: #1e293b; color: #fb923c; border: 1px solid #7c2d12; }
.badge-arrow      { color: #475569; font-size: 0.8rem; }

/* ── Cards ── */
.card {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
}
.card-title {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 12px;
}

/* ── Agent status rows ── */
.agent-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 0;
    border-bottom: 1px solid #1e293b;
}
.agent-row:last-child { border-bottom: none; }
.agent-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-idle    { background: #334155; }
.dot-active  { background: #818cf8; box-shadow: 0 0 8px #818cf8; animation: pulse 1.4s infinite; }
.dot-done    { background: #34d399; }
.dot-waiting { background: #fb923c; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.agent-name  { font-size: 0.88rem; font-weight: 600; color: #e2e8f0; }
.agent-label { font-size: 0.75rem; color: #64748b; margin-left: auto; }

/* ── Metric tiles ── */
.metric-grid { display: flex; gap: 12px; flex-wrap: wrap; }
.metric-tile {
    flex: 1; min-width: 80px;
    background: #0b0f1a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
}
.metric-val {
    font-size: 1.6rem;
    font-weight: 700;
    color: #818cf8;
    line-height: 1;
}
.metric-lbl {
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── Textarea ── */
.stTextArea textarea {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    resize: vertical;
}
.stTextArea textarea:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 3px rgba(129,140,248,0.15) !important;
}

/* ── Buttons ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 1.5rem !important;
    transition: opacity 0.2s, transform 0.1s !important;
    width: 100%;
}
div[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* Approve button variant */
.approve-btn div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #059669, #047857) !important;
}

/* ── Progress bar ── */
div[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #4f46e5, #818cf8) !important;
    border-radius: 999px !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #111827 !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ── Alert boxes ── */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-width: 1px !important;
}

/* ── Section headers ── */
.section-header {
    font-size: 1rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0 0 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #1e293b;
    margin-left: 8px;
}

/* ── Report output ── */
.report-wrapper {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 2rem 2.2rem;
    font-size: 0.93rem;
    line-height: 1.75;
    color: #cbd5e1;
}
.report-wrapper h1, .report-wrapper h2, .report-wrapper h3 {
    color: #e0e7ff;
}
.report-wrapper code {
    font-family: 'JetBrains Mono', monospace;
    background: #1e293b;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.85em;
}

/* ── Log entry ── */
.log-entry {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #64748b;
    padding: 3px 0;
    border-bottom: 1px solid #0f172a;
}
.log-entry .log-time { color: #4f46e5; }
.log-entry .log-msg  { color: #94a3b8; }

/* ── Approval box ── */
.approval-box {
    background: linear-gradient(135deg, #0c1a2e, #0f2318);
    border: 1px solid #065f46;
    border-radius: 14px;
    padding: 1.5rem;
    margin: 1rem 0;
}
.approval-title { font-size: 1rem; font-weight: 700; color: #34d399; margin-bottom: 6px; }
.approval-desc  { font-size: 0.85rem; color: #94a3b8; }

/* ── Download button ── */
div[data-testid="stDownloadButton"] > button {
    background: #1e293b !important;
    color: #818cf8 !important;
    border: 1px solid #312e81 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #312e81 !important;
    color: #e0e7ff !important;
}

/* ── Divider ── */
hr { border-color: #1e293b !important; }

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
defaults = {
    "notes": [],
    "final_report": "",
    "logs": [],
    "agent_states": {
        "supervisor": "idle",
        "researcher": "idle",
        "writer":     "idle",
    },
    "notes_count": 0,
    "draft_chars": 0,
    "workflow_done": False,
    # Persisted across reruns so the Approve button can resume the same graph
    "graph": None,
    "graph_config": None,
    "awaiting_approval": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def set_agent(name: str, state: str):
    st.session_state.agent_states[name] = state

def add_log(msg: str):
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append((ts, msg))

def dot_class(state: str) -> str:
    return {"idle": "dot-idle", "active": "dot-active",
            "done": "dot-done", "waiting": "dot-waiting"}.get(state, "dot-idle")

def agent_label(state: str) -> str:
    return {"idle": "Idle", "active": "Running…",
            "done": "Complete", "waiting": "Waiting"}.get(state, "")

def render_agent_row(icon: str, name: str, key: str):
    state = st.session_state.agent_states[key]
    st.markdown(f"""
    <div class="agent-row">
        <div class="agent-dot {dot_class(state)}"></div>
        <span class="agent-name">{icon} {name}</span>
        <span class="agent-label">{agent_label(state)}</span>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# HERO
# ─────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-icon">🔬</div>
  <div>
    <p class="hero-title">Multi-Agent Research Assistant</p>
    <p class="hero-sub">LangGraph · Groq LLaMA 3.3 70B · Tavily Search · Human-in-the-Loop</p>
    <div class="pipeline">
      <span class="badge badge-supervisor">Supervisor</span>
      <span class="badge-arrow">→</span>
      <span class="badge badge-researcher">Researcher</span>
      <span class="badge-arrow">→</span>
      <span class="badge badge-writer">Writer</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="card-title">Agent Status</p>', unsafe_allow_html=True)

    render_agent_row("🧠", "Supervisor", "supervisor")
    render_agent_row("🔍", "Researcher", "researcher")
    render_agent_row("✍️", "Writer",     "writer")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<p class="card-title">Run Metrics</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-tile">
            <div class="metric-val">{st.session_state.notes_count}</div>
            <div class="metric-lbl">Notes</div>
        </div>
        <div class="metric-tile">
            <div class="metric-val">{st.session_state.draft_chars}</div>
            <div class="metric-lbl">Chars</div>
        </div>
        <div class="metric-tile">
            <div class="metric-val">{len(st.session_state.logs)}</div>
            <div class="metric-lbl">Events</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.logs:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="card-title">Event Log</p>', unsafe_allow_html=True)
        log_html = ""
        for ts, msg in st.session_state.logs[-12:]:
            log_html += f'<div class="log-entry"><span class="log-time">{ts}</span> <span class="log-msg">{msg}</span></div>'
        st.markdown(log_html, unsafe_allow_html=True)


# ─────────────────────────────────────────
# MAIN COLUMNS
# ─────────────────────────────────────────
left, right = st.columns([5, 7], gap="large")

# ── LEFT: Input ──────────────────────────
with left:
    st.markdown('<p class="section-header">🎯 Research Task</p>', unsafe_allow_html=True)

    task = st.text_area(
        label="task_hidden",
        label_visibility="collapsed",
        height=200,
        placeholder="e.g. Analyse the impact of LPU architecture on AI inference speeds and compare with GPU alternatives.",
        key="task_input",
    )

    run_workflow = st.button("🚀  Run Workflow", use_container_width=True)

    # Tips card
    st.markdown("""
    <div class="card" style="margin-top:1.25rem;">
        <p class="card-title">How it works</p>
        <div style="font-size:0.82rem;color:#94a3b8;line-height:1.7;">
            <b style="color:#818cf8;">1 · Supervisor</b> — analyses your task and routes to the right agent.<br>
            <b style="color:#34d399;">2 · Researcher</b> — searches the web via Tavily for live data.<br>
            <b style="color:#fb923c;">3 · You approve</b> — review notes before the Writer starts.<br>
            <b style="color:#fb923c;">4 · Writer</b> — composes a structured report using gathered notes.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── RIGHT: Execution & Output ─────────────
with right:
    st.markdown('<p class="section-header">⚡ Execution</p>', unsafe_allow_html=True)

    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    content_placeholder = st.empty()

# ─────────────────────────────────────────
# RUN GRAPH  —  Phase 1: kick off research
# ─────────────────────────────────────────
if run_workflow:
    if not task.strip():
        with right:
            st.error("Please enter a research task before running.")
    else:
        # Reset all state for a fresh run
        st.session_state.notes = []
        st.session_state.final_report = ""
        st.session_state.logs = []
        st.session_state.notes_count = 0
        st.session_state.draft_chars = 0
        st.session_state.workflow_done = False
        st.session_state.awaiting_approval = False
        st.session_state.graph = None
        st.session_state.graph_config = None
        for k in st.session_state.agent_states:
            st.session_state.agent_states[k] = "idle"

        # Build graph ONCE and store in session_state so the Approve
        # button can resume it on the next Streamlit rerun
        graph = build_graph()
        config = {"configurable": {"thread_id": "streamlit-user"}}
        st.session_state.graph = graph
        st.session_state.graph_config = config

        initial_input = {
            "task": task,
            "research_notes": [],
            "retry_count": 0,
            "draft": "",
            "next_node": "",
            "revision_feedback": "",
        }

        progress_bar.progress(5)

        with right:
            with st.spinner(""):
                set_agent("supervisor", "active")
                add_log("Workflow started")
                status_placeholder.info("🧠 Supervisor analysing task…")

                for event in graph.stream(initial_input, config, stream_mode="values"):

                    if event.get("next_node"):
                        routed_to = event["next_node"]
                        add_log(f"Supervisor → {routed_to}")
                        status_placeholder.info(f"🧠 Supervisor routed to **{routed_to}**")
                        set_agent("supervisor", "done")

                        if routed_to == "researcher":
                            set_agent("researcher", "active")
                            progress_bar.progress(30)
                            status_placeholder.info("🔍 Researcher searching the web…")

                    if event.get("research_notes"):
                        st.session_state.notes = event["research_notes"]
                        st.session_state.notes_count = len(event["research_notes"])
                        add_log(f"Researcher collected {len(event['research_notes'])} note(s)")
                        set_agent("researcher", "done")
                        set_agent("supervisor", "active")
                        progress_bar.progress(55)
                        status_placeholder.info("🧠 Supervisor reviewing research notes…")

                progress_bar.progress(65)

        snapshot = graph.get_state(config)

        if snapshot.next:
            # Graph is paused at the writer breakpoint — flag it and rerun
            # so the approval UI renders cleanly on its own pass
            set_agent("writer", "waiting")
            add_log("Workflow paused — awaiting human approval")
            st.session_state.awaiting_approval = True
            st.rerun()
        else:
            progress_bar.progress(100)
            status_placeholder.success("✅ Workflow complete")
            st.session_state.workflow_done = True

# ─────────────────────────────────────────
# APPROVAL UI  —  rendered on every rerun
# while awaiting_approval is True
# ─────────────────────────────────────────
if st.session_state.awaiting_approval and not st.session_state.final_report:

    # Restore sidebar dot states
    set_agent("writer", "waiting")

    with right:
        status_placeholder.warning("⏸️  Paused — review notes and approve to continue")
        progress_bar.progress(65)

        # Research notes
        if st.session_state.notes:
            with st.expander("📚 Research Notes  —  click to review", expanded=True):
                for i, note in enumerate(st.session_state.notes, 1):
                    st.markdown(f"**Source {i}**")
                    st.markdown(f"```\n{note[:1200]}{'…' if len(note) > 1200 else ''}\n```")

        st.markdown("""
        <div class="approval-box">
            <p class="approval-title">✅ Human Approval Required</p>
            <p class="approval-desc">
                The Supervisor has finished gathering research.
                Review the notes above, then approve to let the Writer compose your report.
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="approve-btn">', unsafe_allow_html=True)
            approve = st.button("✅  Approve & Generate Report", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    if approve:
        # Retrieve the graph that was built in Phase 1
        graph  = st.session_state.graph
        config = st.session_state.graph_config

        set_agent("writer", "active")
        add_log("Approved — Writer started")

        with right:
            progress_bar.progress(75)
            status_placeholder.info("✍️ Writer composing report…")

            with st.spinner("Writer at work…"):
                for event in graph.stream(None, config, stream_mode="values"):
                    if event.get("draft"):
                        st.session_state.final_report = event["draft"]
                        st.session_state.draft_chars = len(event["draft"])

        set_agent("writer", "done")
        add_log("Report generated")
        st.session_state.awaiting_approval = False
        st.session_state.workflow_done = True
        progress_bar.progress(100)
        status_placeholder.success("✅ Workflow complete — report ready")
        st.rerun()  # rerun to render the final report section cleanly


# ─────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────
if st.session_state.final_report:
    st.markdown("---")
    st.markdown('<p class="section-header">📄 Final Report</p>', unsafe_allow_html=True)

    col_report, col_dl = st.columns([5, 1])

    with col_report:
        st.markdown(
            f'<div class="report-wrapper">{st.session_state.final_report}</div>',
            unsafe_allow_html=True,
        )

    with col_dl:
        st.download_button(
            label="⬇ Download",
            data=st.session_state.final_report,
            file_name="research_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
