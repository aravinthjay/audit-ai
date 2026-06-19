"""
globalflow_crew.py — GlobalFlow Logistics: Complete CrewAI Pipeline
All agents, tasks, and extension runners in one file.

Run modes
---------
    python globalflow_crew.py                        # core pipeline only
    python globalflow_crew.py --ext1                 # + Financial Analyst agent
    python globalflow_crew.py --ext2                 # + parallel async execution (with timing comparison)
    python globalflow_crew.py --ext3                 # + human-in-the-loop gate before report
    python globalflow_crew.py --ext4                 # model-tier comparison (standalone)
    python globalflow_crew.py --ext1 --ext2 --ext3   # combine any extensions

Setup
-----
    pip install "crewai[litellm]" crewai-tools langchain-groq python-dotenv
    Create a .env file with: GROQ_API_KEY=your_key_here
"""

import os
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

from crewai import Agent, Task, Crew, Process
from crewai_tools import FileWriterTool
from crewai.tools import BaseTool

# ─────────────────────────────────────────────────────────────────
# LLM TIERS
# ─────────────────────────────────────────────────────────────────
GROQ_FAST    = "groq/llama-3.1-8b-instant"       # fast + cheap, good for simple tasks
GROQ_SMART   = "groq/llama-3.3-70b-versatile"    # capable, good for reasoning
GROQ_MANAGER = "groq/llama-3.3-70b-versatile"    # hierarchical manager LLM

# ─────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────
file_writer = FileWriterTool()


class MockSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web for supply-chain disruption news, "
        "shipping route data, and regulatory information."
    )

    def _run(self, query: str) -> str:
        return (
            f"[SIMULATED SEARCH] Results for: '{query}'\n"
            "Rotterdam: 18h closure, storm surge, severity 8/10\n"
            "Alternative 1 - Hamburg: +5h, -6% cost, low risk\n"
            "Alternative 2 - Felixstowe: +8h, -10% cost, medium risk\n"
            "Alternative 3 - Antwerp: +3h, +2% cost, low risk\n"
            "Singapore PSA: normal operations, no disruption\n"
        )


search_tool = MockSearchTool()

# ─────────────────────────────────────────────────────────────────
# TRIGGER INPUT
# ─────────────────────────────────────────────────────────────────
TRIGGER_INPUT = {
    "disruption_alert": (
        "ALERT: Port of Rotterdam (GlobalFlow EU hub) has declared force majeure "
        "due to severe North Sea storm surge. Expected closure: 18-24 hours. "
        "340 containers from GlobalFlow clients are currently docked. "
        "12 Maersk vessels en-route have been diverted to Felixstowe. "
        "Incident started: 2025-06-18 06:30 UTC. "
        "Client SLA breach window opens in 6 hours."
    )
}


# ─────────────────────────────────────────────────────────────────
# AGENTS
# ─────────────────────────────────────────────────────────────────

def make_agents(fast_model=GROQ_FAST, smart_model=GROQ_SMART):
    """
    Build and return all 6 agents.
    Pass different model strings to support Extension 4 tier swapping.
    """

    # Agent 1: Disruption Monitor
    disruption_monitor = Agent(
        role="Supply Chain Disruption Monitor",
        goal=(
            "Continuously scan for logistics disruptions - port closures, weather events, "
            "customs delays, and supplier failures - and assess their severity on a 1-10 scale."
        ),
        backstory=(
            "You are a veteran logistics intelligence analyst with 12 years at Maersk and DHL. "
            "You have seen every kind of supply-chain disruption imaginable, from Suez Canal "
            "blockages to pandemic port shutdowns. You are calm under pressure, deeply data-driven, "
            "and always quantify impact before escalating. You write in crisp bullet points."
        ),
        llm=smart_model,
        tools=[search_tool],
        verbose=True,
        max_iter=4,
    )

    # Agent 2: Route Optimiser
    route_optimiser = Agent(
        role="Logistics Route Optimiser",
        goal=(
            "Given a disruption report, calculate the 3 best alternative routes for affected "
            "shipments, ranking by total cost + estimated delay. Provide a clear recommendation."
        ),
        backstory=(
            "You are a PhD-level operations research specialist who spent 8 years building "
            "real-time routing algorithms for FedEx. You think in graphs, costs, and probabilities. "
            "You know every major shipping lane, air corridor, and rail route. You always present "
            "a primary recommendation plus two ranked alternatives with a weighted score."
        ),
        llm=smart_model,
        tools=[search_tool],
        verbose=True,
        max_iter=4,
    )

    # Agent 3: Supplier Communications Specialist
    supplier_comms = Agent(
        role="Supplier Communications Specialist",
        goal=(
            "Draft professional, urgent communications to affected suppliers and carriers "
            "explaining the disruption, proposing alternatives, and requesting confirmation "
            "within 4 hours."
        ),
        backstory=(
            "You are a senior procurement manager who has negotiated contracts in 22 countries. "
            "You are culturally fluent, direct but diplomatic, and always frame disruptions as "
            "collaborative problems to solve, never as blame assignments. You know that tone "
            "in a crisis email can make or break a supplier relationship worth millions."
        ),
        llm=fast_model,     # Drafting emails does not need the 70B model
        verbose=True,
        max_iter=3,
    )

    # Agent 4: Compliance Officer
    compliance_officer = Agent(
        role="Trade Compliance Officer",
        goal=(
            "For each proposed re-route, verify customs requirements, check for sanctions or "
            "restricted-goods regulations, and flag any compliance risks. Issue a COMPLIANCE "
            "CLEARED or COMPLIANCE HOLD recommendation."
        ),
        backstory=(
            "You are a Certified Customs Specialist (CCS) with deep expertise in EU, US, and "
            "APAC trade regulations. You have worked with the WTO and have a zero-tolerance "
            "approach to compliance shortcuts. A single customs violation can cost more than "
            "the disruption itself."
        ),
        llm=smart_model,
        tools=[search_tool],
        verbose=True,
        max_iter=4,
    )

    # Agent 5: Executive Report Writer
    report_writer = Agent(
        role="Executive Communications Writer",
        goal=(
            "Synthesise the disruption intelligence, route options, supplier actions, and "
            "compliance status into a clear, actionable executive briefing. "
            "Format: Situation -> Impact -> Response -> Next Steps. Maximum 1 page."
        ),
        backstory=(
            "You are a former management consultant who spent 10 years writing board-level "
            "crisis communications for Fortune 500 logistics companies. You eliminate jargon "
            "ruthlessly, lead with the bottom line, and always end with exactly 3 numbered "
            "action items with named owners and deadlines."
        ),
        llm=smart_model,
        tools=[file_writer],
        verbose=True,
        max_iter=3,
    )

    # Agent 6: Financial Analyst (Extension 1)
    financial_analyst = Agent(
        role="Supply Chain Financial Analyst",
        goal=(
            "Calculate total EUR exposure from the disruption: rerouting cost delta, "
            "SLA penalty clauses triggered, insurance deductible, "
            "and opportunity cost of delayed deliveries."
        ),
        backstory=(
            "CFA-qualified financial analyst specialising in logistics cost modelling at "
            "GlobalFlow for 7 years. You always present three scenarios — base, worst, and "
            "best case — with clear assumptions listed for each. Your outputs go directly "
            "to the CFO, so precision and brevity are non-negotiable."
        ),
        llm=smart_model,
        verbose=True,
        max_iter=3,
    )

    return (
        disruption_monitor,
        route_optimiser,
        supplier_comms,
        compliance_officer,
        report_writer,
        financial_analyst,
    )


# ─────────────────────────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────────────────────────

def make_tasks(
    disruption_monitor,
    route_optimiser,
    supplier_comms,
    compliance_officer,
    report_writer,
    financial_analyst,
    async_parallel=False,    # Extension 2
    human_gate=False,        # Extension 3
    include_financial=False, # Extension 1
):
    """
    Build and return the ordered task list.

    Parameters
    ----------
    async_parallel   : Extension 2 — run task_comms & task_compliance asynchronously
    human_gate       : Extension 3 — pause for human input before writing the report
    include_financial: Extension 1 — include the financial exposure analysis task
    """

    # Task 1: Monitor disruptions (no dependencies)
    task_monitor = Task(
        description=(
            "Search for active logistics disruptions affecting GlobalFlow's key corridors: "
            "Rotterdam (EU hub), Singapore (APAC hub), Houston (US hub), and the AE-1 "
            "Asia-Europe shipping lane. Report: (1) disruption type and location, "
            "(2) severity score 1-10, (3) estimated duration, (4) shipments likely affected. "
            "Start your report with 'SEVERITY: X/10' on the first line."
        ),
        expected_output=(
            "Structured disruption report: severity score, affected corridors, "
            "shipment count, estimated duration, recommended escalation level."
        ),
        agent=disruption_monitor,
    )

    # Task 2: Route optimisation (depends on Task 1)
    task_route = Task(
        description=(
            "Using the disruption report in your context, calculate 3 alternative routes "
            "for the 50 highest-priority shipments. For each route: "
            "(1) route name and via-points, (2) cost delta vs standard (%), "
            "(3) delay in hours, (4) risk score 1-5, (5) CO2 delta. "
            "Rank by weighted score: 60% cost, 30% time, 10% risk."
        ),
        expected_output=(
            "Ranked table of 3 alternative routes with cost delta, delay, risk, "
            "weighted score, and a one-sentence rationale for the top choice."
        ),
        agent=route_optimiser,
        context=[task_monitor],
    )

    # Task 3: Supplier comms (depends on Tasks 1 + 2)
    # Extension 2: async_execution makes this run in parallel with task_compliance
    task_comms = Task(
        description=(
            "Draft communications to the 3 most critical affected suppliers. "
            "For each: (1) subject line, (2) 150-word email body explaining the disruption, "
            "the proposed re-routing option, and requesting confirmation within 4 hours. "
            "Tone: professional, urgent, collaborative."
        ),
        expected_output=(
            "Three complete email drafts formatted as:\n"
            "[SUPPLIER NAME] / [SUBJECT LINE]\n[EMAIL BODY]"
        ),
        agent=supplier_comms,
        context=[task_monitor, task_route],
        async_execution=async_parallel,
    )

    # Task 4: Compliance check (depends on Task 2)
    # Extension 2: async_execution makes this run in parallel with task_comms
    task_compliance = Task(
        description=(
            "Review the top-ranked re-routing option from the route optimisation team. "
            "Check: (1) customs requirements per transit country, "
            "(2) sanctions or dual-use goods restrictions, "
            "(3) certificate of origin implications. "
            "Issue COMPLIANCE CLEARED or COMPLIANCE HOLD with detailed reasoning."
        ),
        expected_output=(
            "Compliance status (CLEARED or HOLD), per-country requirements, "
            "flags with remediation steps, estimated customs processing time."
        ),
        agent=compliance_officer,
        context=[task_route],
        async_execution=async_parallel,
    )

    # Task 5: Financial analysis (Extension 1 only)
    task_financial = None
    if include_financial:
        task_financial = Task(
            description=(
                "Using the disruption report and route options in your context, calculate "
                "the total EUR financial exposure for GlobalFlow. Break down into: "
                "(1) re-routing cost delta across 50 affected shipments, "
                "(2) SLA penalty clauses triggered (assume EUR 50K per hour beyond 6h SLA), "
                "(3) insurance deductible estimate, "
                "(4) opportunity cost of delayed deliveries. "
                "Present three scenarios: base case, worst case, and best case. "
                "End with a single TOTAL EXPOSURE line per scenario."
            ),
            expected_output=(
                "Financial exposure table in EUR: "
                "base / worst / best case with itemised breakdown and totals."
            ),
            agent=financial_analyst,
            context=[task_monitor, task_route],
        )

    # Task 6: Executive report (all context)
    # Extension 3: human_input=True pauses for human approval before writing
    report_context = [task_monitor, task_route, task_comms, task_compliance]
    if task_financial:
        report_context.append(task_financial)

    task_report = Task(
        description=(
            "Compile all outputs into a single executive briefing.\n"
            "Use these exact headings:\n"
            "  SITUATION: what happened and severity\n"
            "  IMPACT: shipments affected, EUR cost exposure\n"
            "  RESPONSE: chosen re-route, supplier actions, compliance status\n"
            "  NEXT STEPS: exactly 3 numbered actions with owners and deadlines\n"
            "Maximum 400 words. Save to file 'globalflow_disruption_report.txt'."
        ),
        expected_output=(
            "Complete executive briefing saved to 'globalflow_disruption_report.txt', "
            "4-section structure, maximum 400 words."
        ),
        agent=report_writer,
        context=report_context,
        output_file="globalflow_disruption_report.txt",
        human_input=human_gate,
    )

    tasks = [task_monitor, task_route, task_comms, task_compliance]
    if task_financial:
        tasks.append(task_financial)
    tasks.append(task_report)

    return tasks


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_result(result, label: str = "FINAL EXECUTIVE BRIEFING"):
    print_header(label)
    print(result.raw)
    if hasattr(result, "token_usage") and result.token_usage:
        tu = result.token_usage
        print(f"\n{'─'*40}")
        print(f"  Prompt tokens:     {tu.prompt_tokens:>8,}")
        print(f"  Completion tokens: {tu.completion_tokens:>8,}")
        print(f"  Total tokens:      {tu.total_tokens:>8,}")
        input_cost  = (tu.prompt_tokens     / 1_000_000) * 0.59
        output_cost = (tu.completion_tokens / 1_000_000) * 0.79
        print(f"  Est. cost (70B):   ${input_cost + output_cost:.5f}")


def read_report_file(path: str = "globalflow_disruption_report.txt"):
    if os.path.exists(path):
        with open(path) as f:
            print(f"\n[FILE] {path}:\n")
            print(f.read())
    else:
        print(f"[WARN] Report file '{path}' not found.")


# ─────────────────────────────────────────────────────────────────
# CORE RUNNER
# ─────────────────────────────────────────────────────────────────

def run_crew(
    include_financial=False,
    async_parallel=False,
    human_gate=False,
    fast_model=GROQ_FAST,
    smart_model=GROQ_SMART,
    verbose_label="GlobalFlow Disruption Response Crew",
):
    """Assemble and kick off the crew with the given extension flags."""

    (
        disruption_monitor,
        route_optimiser,
        supplier_comms,
        compliance_officer,
        report_writer,
        financial_analyst,
    ) = make_agents(fast_model=fast_model, smart_model=smart_model)

    tasks = make_tasks(
        disruption_monitor,
        route_optimiser,
        supplier_comms,
        compliance_officer,
        report_writer,
        financial_analyst,
        async_parallel=async_parallel,
        human_gate=human_gate,
        include_financial=include_financial,
    )

    agents = [
        disruption_monitor,
        route_optimiser,
        supplier_comms,
        compliance_officer,
        report_writer,
    ]
    if include_financial:
        agents.insert(4, financial_analyst)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.hierarchical,
        manager_llm=GROQ_MANAGER,
        verbose=True,
        memory=True,
        output_log_file="crew_run.log",
    )

    print_header(verbose_label)
    print(f"  Alert   : {TRIGGER_INPUT['disruption_alert'][:75]}…")
    print(f"  Agents  : {len(crew.agents)}")
    print(f"  Tasks   : {len(crew.tasks)}")
    print(f"  Process : {crew.process.value}")
    print(f"  Parallel: {async_parallel}")
    print(f"  Human   : {human_gate}")
    print(f"  Finance : {include_financial}\n")

    start = time.time()
    result = crew.kickoff(inputs=TRIGGER_INPUT)
    elapsed = time.time() - start

    print_result(result)
    print(f"\n  Wall-clock time: {elapsed:.1f}s")
    read_report_file()
    return result, elapsed


# ─────────────────────────────────────────────────────────────────
# EXTENSION 2: Sequential vs Parallel timing comparison
# ─────────────────────────────────────────────────────────────────

def run_ext2_comparison():
    print_header("EXTENSION 2 — Sequential vs Parallel Async")

    print("► Run 1: Sequential (baseline)")
    _, t_seq = run_crew(async_parallel=False, verbose_label="Run 1: Sequential")

    print("\n► Run 2: Parallel (async_execution=True on comms + compliance)")
    _, t_par = run_crew(async_parallel=True, verbose_label="Run 2: Parallel")

    print_header("TIMING COMPARISON")
    print(f"  Sequential : {t_seq:.1f}s")
    print(f"  Parallel   : {t_par:.1f}s")
    delta = t_seq - t_par
    pct   = (delta / t_seq) * 100 if t_seq > 0 else 0
    print(f"  Saved      : {delta:.1f}s  ({pct:.1f}% faster with async)")


# ─────────────────────────────────────────────────────────────────
# EXTENSION 4: Model tier comparison
# ─────────────────────────────────────────────────────────────────

def run_ext4_model_comparison():
    """
    Run supplier_comms task once with the fast (8B) model and once with the
    smart (70B) model, then print both outputs with timing and token cost.
    """
    print_header("EXTENSION 4 — Model Tier Comparison")

    task_desc = (
        "Draft a single urgent email to a critical supplier informing them of the "
        "Rotterdam port closure and proposing re-routing via Hamburg. "
        "Request confirmation within 4 hours. Keep it under 150 words."
    )
    expected = "One professional email with subject line and body, under 150 words."

    results = {}
    for tier_name, model in [("FAST  llama-3.1-8b-instant", GROQ_FAST),
                              ("SMART llama-3.3-70b-versatile", GROQ_SMART)]:
        agent = Agent(
            role="Supplier Communications Specialist",
            goal="Draft urgent, professional supplier communications during disruptions.",
            backstory=(
                "Senior procurement manager, culturally fluent, direct but diplomatic."
            ),
            llm=model,
            verbose=False,
            max_iter=2,
        )
        task  = Task(description=task_desc, expected_output=expected, agent=agent)
        crew  = Crew(agents=[agent], tasks=[task], verbose=False)

        start  = time.time()
        result = crew.kickoff(inputs=TRIGGER_INPUT)
        elapsed = time.time() - start

        results[tier_name] = {
            "output": result.raw,
            "time": elapsed,
            "tokens": getattr(result, "token_usage", None),
        }

    print_header("MODEL TIER RESULTS")
    for tier, data in results.items():
        print(f"\n{'─'*50}")
        print(f"  Model : {tier}")
        print(f"  Time  : {data['time']:.1f}s")
        if data["tokens"]:
            tu = data["tokens"]
            cost = (tu.prompt_tokens / 1e6) * 0.59 + (tu.completion_tokens / 1e6) * 0.79
            print(f"  Tokens: {tu.total_tokens:,}  (est. ${cost:.5f})")
        print(f"\n{data['output']}\n")


# ─────────────────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GlobalFlow CrewAI pipeline — core + all 4 extension tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python globalflow_crew.py                  # core only\n"
            "  python globalflow_crew.py --ext1           # + Financial Analyst\n"
            "  python globalflow_crew.py --ext2           # sequential vs parallel comparison\n"
            "  python globalflow_crew.py --ext3           # human approval gate\n"
            "  python globalflow_crew.py --ext4           # model tier quality/cost comparison\n"
            "  python globalflow_crew.py --ext1 --ext3    # combine extensions\n"
        ),
    )
    parser.add_argument("--ext1", action="store_true",
                        help="Extension 1: add Financial Analyst agent + task")
    parser.add_argument("--ext2", action="store_true",
                        help="Extension 2: parallel async (runs seq vs parallel timing comparison)")
    parser.add_argument("--ext3", action="store_true",
                        help="Extension 3: human-in-the-loop gate before report is written")
    parser.add_argument("--ext4", action="store_true",
                        help="Extension 4: model tier comparison — fast vs smart (standalone)")
    args = parser.parse_args()

    # Extension 4 is fully standalone
    if args.ext4:
        run_ext4_model_comparison()
        return

    # Extension 2 alone → run the full sequential vs parallel comparison
    if args.ext2 and not (args.ext1 or args.ext3):
        run_ext2_comparison()
        return

    # All other combinations go through the standard runner
    run_crew(
        include_financial=args.ext1,
        async_parallel=args.ext2,
        human_gate=args.ext3,
    )


if __name__ == "__main__":
    main()
