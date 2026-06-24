"""
agents.py  —  Observability for a Multi-Agent System
=====================================================
Coding Assignment Solution (all 4 tasks + stretch goals)

Tasks completed:
  Task 1  — trace_id + span_id correlation on every event
  Task 2  — pipeline % complete, throughput, per-agent duration
  Task 3  — structured JSON events (agent_started, agent_progress
             throttled to ~25%, agent_completed)
  Task 4  — agent_failed event + run_summary at the end

Stretch goals completed:
  A  — persist every event to trace.jsonl + print per-agent timeline
  B  — detect a stall (gap between steps > STALL_THRESHOLD_SEC)
  C  — fan-out: one agent spawns child sub-agents; parent/child tree
       is reconstructed from trace_id / span_id / parent_span_id

Run:
    python agents.py              # normal happy-path run
    python agents.py --fail       # force Writer to fail at step 2
    python agents.py --fanout     # enable fan-out sub-agents
    python agents.py --timeline   # print timeline from trace.jsonl
    python agents.py --all        # run everything, then print timeline

Standard library only — no pip install needed.
"""

import json
import math
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACE_FILE   = Path("trace.jsonl")
STALL_THRESHOLD_SEC = 0.5   # seconds between steps before agent_stalled fires


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_id() -> str:
    """Return a short unique ID (first 8 chars of a UUID4)."""
    return uuid.uuid4().hex[:8]


def emit(event: dict) -> None:
    """
    Print a structured JSON event to stdout AND append it to trace.jsonl.
    This is the single place all telemetry goes.
    """
    line = json.dumps(event)
    print(line)
    with open(TRACE_FILE, "a") as f:
        f.write(line + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 + 2 + 3 + 4 — ObservabilityListener
# ─────────────────────────────────────────────────────────────────────────────

class ObservabilityListener:
    """
    Replaces the raw progress_listener function.

    Holds all the state needed to compute pipeline-level signals and
    emit structured, correlated, throttled JSON events.

    One instance is created per run (one trace_id).
    One span_id is created per agent execution.
    """

    def __init__(self, agents_config: list[tuple[str, int]]):
        """
        agents_config: list of (name, total_steps) for every agent in
        the pipeline — needed to compute pipeline percent complete.
        """
        # ── Task 1: run-level correlation ID ─────────────────────────────────
        self.trace_id   = new_id()
        self.run_start  = time.monotonic()

        # ── Task 2: pipeline-level totals ─────────────────────────────────────
        self.total_pipeline_steps = sum(s for _, s in agents_config)
        self.steps_done_global    = 0   # incremented on every step across all agents

        # ── Per-agent tracking ────────────────────────────────────────────────
        # span_id, start_time, last_step_time — keyed by agent name
        self._spans:      dict[str, str]   = {}
        self._start_times: dict[str, float] = {}
        self._last_step:   dict[str, float] = {}

        # ── Agents that completed successfully ────────────────────────────────
        self.completed_agents: list[str] = []

    # ── span management ───────────────────────────────────────────────────────

    def start_agent(self, agent_name: str,
                    parent_span_id: str | None = None) -> str:
        """
        Called once before an agent begins its steps.
        Creates a new span_id and emits agent_started.
        Returns the span_id (needed by fan-out children).
        """
        span_id   = new_id()
        now       = time.monotonic()
        self._spans[agent_name]       = span_id
        self._start_times[agent_name] = now
        self._last_step[agent_name]   = now

        event: dict = {
            "timestamp":  now_iso(),
            "trace_id":   self.trace_id,
            "span_id":    span_id,
            "event":      "agent_started",
            "agent":      agent_name,
        }
        if parent_span_id:
            event["parent_span_id"] = parent_span_id   # stretch-C fan-out

        emit(event)
        return span_id

    def finish_agent(self, agent_name: str) -> None:
        """Called once after an agent completes all steps successfully."""
        duration = time.monotonic() - self._start_times[agent_name]
        self.completed_agents.append(agent_name)

        emit({
            "timestamp":      now_iso(),
            "trace_id":       self.trace_id,
            "span_id":        self._spans[agent_name],
            "event":          "agent_completed",
            "agent":          agent_name,
            "duration_sec":   round(duration, 3),       # Task 2: per-agent duration
            "pipeline_pct":   self._pipeline_pct(),     # Task 2: overall progress
        })

    # ── the listener callable passed to each Agent ────────────────────────────

    def __call__(self, agent_name: str, step: int, total_steps: int) -> None:
        """
        Called by Agent.run() after every step.
        Implements:
          - Task 2: global step counter, throughput, pipeline %
          - Task 3: throttled agent_progress (~every 25%)
          - Stretch B: stall detection
        """
        self.steps_done_global += 1
        now = time.monotonic()

        # ── Stretch B: stall detection ────────────────────────────────────────
        gap = now - self._last_step.get(agent_name, now)
        if gap > STALL_THRESHOLD_SEC:
            emit({
                "timestamp":    now_iso(),
                "trace_id":     self.trace_id,
                "span_id":      self._spans[agent_name],
                "event":        "agent_stalled",
                "agent":        agent_name,
                "step":         step,
                "total_steps":  total_steps,
                "gap_sec":      round(gap, 3),
                "threshold_sec": STALL_THRESHOLD_SEC,
            })
        self._last_step[agent_name] = now

        # ── Task 3: throttle to ~every 25% of agent's own steps ──────────────
        # Emit at step 1 (start), last step (end captured by finish_agent),
        # and whenever step crosses a 25% boundary.
        milestone = math.ceil(total_steps * 0.25)
        if milestone < 1:
            milestone = 1
        should_emit = (step == 1) or (step % milestone == 0)

        if should_emit:
            emit({
                "timestamp":      now_iso(),
                "trace_id":       self.trace_id,
                "span_id":        self._spans[agent_name],
                "event":          "agent_progress",
                "agent":          agent_name,
                "step":           step,
                "total_steps":    total_steps,
                "agent_pct":      round(step / total_steps * 100, 1),
                "pipeline_pct":   self._pipeline_pct(),    # Task 2
                "throughput_sps": self._throughput(),       # Task 2
            })

    # ── Task 4: failure event ─────────────────────────────────────────────────

    def record_failure(self, agent_name: str,
                       step: int, error: str) -> None:
        """Emit agent_failed capturing agent, step, error, and pipeline % at death."""
        duration = time.monotonic() - self._start_times.get(agent_name, self.run_start)
        emit({
            "timestamp":      now_iso(),
            "trace_id":       self.trace_id,
            "span_id":        self._spans.get(agent_name, "unknown"),
            "event":          "agent_failed",
            "agent":          agent_name,
            "failed_at_step": step,
            "error":          error,
            "pipeline_pct":   self._pipeline_pct(),
            "duration_sec":   round(duration, 3),
        })

    # ── Task 4: run summary ───────────────────────────────────────────────────

    def emit_run_summary(self, status: str,
                         failed_agent: str | None = None) -> None:
        """
        Emit one run_summary at the very end — success or failure.
        status: 'success' | 'failed'
        """
        total_duration = time.monotonic() - self.run_start
        emit({
            "timestamp":        now_iso(),
            "trace_id":         self.trace_id,
            "event":            "run_summary",
            "status":           status,
            "total_duration_sec": round(total_duration, 3),
            "pipeline_pct":     self._pipeline_pct(),
            "agents_completed": self.completed_agents,
            "failed_agent":     failed_agent,
            "total_steps_done": self.steps_done_global,
            "total_steps":      self.total_pipeline_steps,
        })

    # ── private helpers ───────────────────────────────────────────────────────

    def _pipeline_pct(self) -> float:
        """Steps finished across ALL agents ÷ total steps (Task 2)."""
        if self.total_pipeline_steps == 0:
            return 0.0
        return round(self.steps_done_global / self.total_pipeline_steps * 100, 1)

    def _throughput(self) -> float:
        """Steps per second since the run started (Task 2)."""
        elapsed = time.monotonic() - self.run_start
        if elapsed < 0.001:
            return 0.0
        return round(self.steps_done_global / elapsed, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Agent  (same structure as starter code, unchanged interface)
# ─────────────────────────────────────────────────────────────────────────────

class Agent:
    """
    Simulated agent — does N steps of work.
    fail_at_step: set to an int to force a deterministic crash at that step.
    """

    def __init__(self, name: str, steps: int,
                 fail_at_step: int | None = None):
        self.name         = name
        self.steps        = steps
        self.fail_at_step = fail_at_step

    def run(self, listener: ObservabilityListener,
            parent_span_id: str | None = None) -> None:
        """
        Run all steps, calling listener after each one.
        parent_span_id is used by fan-out children (Stretch C).
        """
        listener.start_agent(self.name, parent_span_id=parent_span_id)

        for step in range(1, self.steps + 1):
            time.sleep(random.uniform(0.05, 0.2))   # simulate work

            if self.fail_at_step and step == self.fail_at_step:
                raise RuntimeError(f"{self.name} failed at step {step}")

            listener(self.name, step, self.steps)

        listener.finish_agent(self.name)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator  (wraps agents, catches failures, emits run_summary)
# ─────────────────────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Runs agents sequentially, catches agent_failed, always emits run_summary.
    """

    def __init__(self, agents: list[Agent],
                 listener: ObservabilityListener):
        self.agents   = agents
        self.listener = listener

    def run(self) -> bool:
        """
        Returns True on full success, False if any agent failed.
        """
        failed_agent = None

        for agent in self.agents:
            try:
                agent.run(self.listener)
            except RuntimeError as exc:
                # ── Task 4: record failure and stop cleanly ───────────────────
                # Extract which step failed from the exception message
                failed_step = _parse_failed_step(str(exc))
                self.listener.record_failure(
                    agent_name = agent.name,
                    step       = failed_step,
                    error      = str(exc),
                )
                failed_agent = agent.name
                break   # stop the pipeline; don't run remaining agents

        # ── Task 4: always emit run_summary ───────────────────────────────────
        status = "failed" if failed_agent else "success"
        self.listener.emit_run_summary(status, failed_agent=failed_agent)

        return failed_agent is None


def _parse_failed_step(error_msg: str) -> int:
    """Extract the step number from 'AgentName failed at step N'."""
    try:
        return int(error_msg.split("step")[-1].strip())
    except (ValueError, IndexError):
        return -1


# ─────────────────────────────────────────────────────────────────────────────
# Stretch Goal A — print per-agent timeline from trace.jsonl
# ─────────────────────────────────────────────────────────────────────────────

def print_timeline(trace_file: Path = TRACE_FILE) -> None:
    """
    Read trace.jsonl and print a human-readable per-agent timeline.
    Groups events by trace_id → agent, shows lifecycle and duration.
    """
    if not trace_file.exists():
        print(f"[timeline] No trace file found at {trace_file}")
        return

    events: list[dict] = []
    with open(trace_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not events:
        print("[timeline] Trace file is empty.")
        return

    # Group by trace_id
    traces: dict[str, list[dict]] = {}
    for ev in events:
        tid = ev.get("trace_id", "unknown")
        traces.setdefault(tid, []).append(ev)

    print("\n" + "=" * 60)
    print("  AGENT TIMELINE")
    print("=" * 60)

    for trace_id, evs in traces.items():
        print(f"\n  Run  trace_id={trace_id}")
        print(f"  {'─' * 54}")

        # Find run_summary for overall status
        summary = next((e for e in evs if e.get("event") == "run_summary"), None)
        if summary:
            print(f"  Status   : {summary.get('status','?').upper()}")
            print(f"  Duration : {summary.get('total_duration_sec','?')}s")
            print(f"  Progress : {summary.get('pipeline_pct','?')}%")

        print()

        # Per-agent rows
        seen_agents: list[str] = []
        for ev in evs:
            agent = ev.get("agent")
            if not agent or agent in seen_agents:
                continue
            seen_agents.append(agent)

            agent_evs = [e for e in evs if e.get("agent") == agent]

            started   = next((e for e in agent_evs if e.get("event") == "agent_started"),   None)
            completed = next((e for e in agent_evs if e.get("event") == "agent_completed"), None)
            failed    = next((e for e in agent_evs if e.get("event") == "agent_failed"),    None)
            stalled   = [e for e in agent_evs if e.get("event") == "agent_stalled"]
            progress  = [e for e in agent_evs if e.get("event") == "agent_progress"]

            if completed:
                status_str = f"COMPLETED in {completed.get('duration_sec','?')}s"
            elif failed:
                status_str = f"FAILED at step {failed.get('failed_at_step','?')} — {failed.get('error','?')}"
            else:
                status_str = "INCOMPLETE"

            print(f"  Agent : {agent}")
            print(f"  Status: {status_str}")

            if progress:
                pcts = [f"{e.get('agent_pct','?')}%" for e in progress]
                print(f"  Steps : {' → '.join(pcts)}")

            if stalled:
                for s in stalled:
                    print(f"  STALL : step {s.get('step')} gap={s.get('gap_sec')}s")

            parent = started.get("parent_span_id") if started else None
            if parent:
                print(f"  Parent span: {parent}")

            print()

    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# Stretch Goal C — Fan-out: one agent spawns child sub-agents
# ─────────────────────────────────────────────────────────────────────────────

def run_fanout_example(listener: ObservabilityListener) -> None:
    """
    Researcher spawns 3 child sub-agents.
    Each child carries the Researcher's span_id as parent_span_id,
    so the parent/child tree can be reconstructed from the trace.
    """
    parent_name = "Researcher"
    parent_span = listener.start_agent(parent_name)

    # Simulate the parent doing a bit of work
    listener(parent_name, 1, 3)
    time.sleep(0.05)

    # Spawn child sub-agents
    children = [
        Agent("Researcher.child_A", 2),
        Agent("Researcher.child_B", 2),
        Agent("Researcher.child_C", 2),
    ]
    for child in children:
        child.run(listener, parent_span_id=parent_span)

    # Parent finishes
    listener(parent_name, 2, 3)
    time.sleep(0.05)
    listener(parent_name, 3, 3)
    listener.finish_agent(parent_name)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def main(force_fail: bool = False,
         fanout:     bool = False) -> None:

    # Clear trace file for a fresh run
    if TRACE_FILE.exists():
        TRACE_FILE.unlink()

    # Define agents
    # Set fail_at_step on Writer to test failure path
    agents_config = [
        ("Planner",    3),
        ("Researcher", 6),
        ("Writer",     4),
        ("Reviewer",   2),
    ]

    agents = [
        Agent("Planner",    3),
        Agent("Researcher", 6),
        Agent("Writer",     4, fail_at_step=2 if force_fail else None),
        Agent("Reviewer",   2),
    ]

    # Create the observability listener — knows total steps for pipeline %
    listener = ObservabilityListener(agents_config)

    print("=" * 60)
    print(f"  Starting run   trace_id={listener.trace_id}")
    print(f"  Total steps    {listener.total_pipeline_steps}")
    print(f"  Failure mode   {'ON (Writer fails at step 2)' if force_fail else 'OFF'}")
    print(f"  Fan-out mode   {'ON' if fanout else 'OFF'}")
    print("=" * 60)
    print()

    if fanout:
        # Stretch C: run Planner normally then do fan-out Researcher
        Agent("Planner", 3).run(listener)
        run_fanout_example(listener)
        Agent("Writer",    4).run(listener)
        Agent("Reviewer",  2).run(listener)
        listener.emit_run_summary("success")
    else:
        # Normal sequential orchestration (Tasks 1-4)
        Orchestrator(agents, listener).run()


# ─────────────────────────────────────────────────────────────────────────────
# CLI — parse simple flags
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args      = sys.argv[1:]
    do_fail   = "--fail"     in args
    do_fanout = "--fanout"   in args
    do_tl     = "--timeline" in args
    do_all    = "--all"      in args

    if do_tl and not do_all:
        print_timeline()
    elif do_all:
        main(force_fail=False, fanout=False)
        print_timeline()
    else:
        main(force_fail=do_fail, fanout=do_fanout)
        if not do_fanout:
            print()
            print_timeline()
