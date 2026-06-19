"""
Audio Emotion Analyzer — Hume AI Expression Measurement API
------------------------------------------------------------
Analyzes emotions in any audio file (mp3, wav, m4a, webm, mp4 …)
using the official Hume Python SDK.

Models run:
  • prosody  — 48 emotions from speech tone / rhythm / timbre
  • burst    — 48 emotions from non-verbal sounds (laughs, sighs …)

Usage:
    python audio_emotion_analyzer.py path/to/audio.mp3 YOUR_HUME_API_KEY

Or set the key as an env variable:
    export HUME_API_KEY=your_key_here
    python audio_emotion_analyzer.py path/to/audio.mp3

Install:
    pip install hume
"""

import os
import sys
import json
import time
import subprocess


# ── Auto-install hume SDK if missing ─────────────────────────────────────────
def _ensure_deps():
    try:
        import hume  # noqa: F401
    except ImportError:
        print("Installing hume SDK …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "hume", "-q"])

_ensure_deps()

from hume import HumeClient                                      # noqa: E402
from hume.expression_measurement.batch.types import (
    Models,
    Prosody,
)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".mp4", ".m4a", ".webm", ".ogg", ".flac", ".aac"}
TOP_N = 10          # how many top emotions to display per model
POLL_INTERVAL = 5   # seconds between status checks


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Validate the audio file
# ─────────────────────────────────────────────────────────────────────────────
def validate_audio(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'.\n"
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  File : {os.path.basename(path)}")
    print(f"  Size : {size_mb:.2f} MB")
    print(f"  Type : {ext}")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Submit batch job to Hume via official SDK
# ─────────────────────────────────────────────────────────────────────────────
def submit_job(client: HumeClient, audio_path: str) -> str:
    print("\n[2/3] Submitting to Hume AI …")

    with open(audio_path, "rb") as f:
        job_id = client.expression_measurement.batch.start_inference_job_from_local_file(
            file=f,
            models=Models(
                prosody=Prosody(granularity="utterance"),
                burst=Burst(),
            ),
        )

    print(f"  Job ID : {job_id}")
    return job_id


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Poll until complete, then fetch predictions
# ─────────────────────────────────────────────────────────────────────────────
def wait_and_fetch(client: HumeClient, job_id: str, timeout: int = 600) -> list:
    print("\n[3/3] Waiting for analysis to complete …")
    deadline = time.time() + timeout

    while time.time() < deadline:
        details = client.expression_measurement.batch.get_job_details(id=job_id)
        status = details.state.status
        print(f"  Status: {status}   ", end="\r")

        if status == "COMPLETED":
            print(f"\n  Done!")
            break
        elif status == "FAILED":
            raise RuntimeError(f"Hume job failed: {details}")

        time.sleep(POLL_INTERVAL)
    else:
        raise TimeoutError("Timed out waiting for Hume job.")

    return client.expression_measurement.batch.get_job_predictions(id=job_id)


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY — aggregate scores across segments and print ranked table
# ─────────────────────────────────────────────────────────────────────────────
def _aggregate(grouped_predictions) -> list[dict]:
    """Average emotion scores across all predicted segments."""
    acc: dict[str, list[float]] = {}
    for group in grouped_predictions:
        for pred in group.predictions:
            for e in pred.emotions:
                acc.setdefault(e.name, []).append(e.score)
    return [
        {"name": name, "score": sum(vals) / len(vals)}
        for name, vals in acc.items()
    ]


def _bar(score: float, width: int = 28) -> str:
    filled = int(score * width)
    return "█" * filled + "░" * (width - filled)


def display_results(predictions, audio_path: str) -> dict:
    sep = "═" * 62

    print(f"\n{sep}")
    print(f"  EMOTION ANALYSIS — {os.path.basename(audio_path)}")
    print(sep)

    all_prosody: dict[str, list[float]] = {}
    all_burst:   dict[str, list[float]] = {}
    segment_emotions: list[dict] = []

    for result in predictions:
        for file_pred in result.results.predictions:

            # ── Prosody ──────────────────────────────────────────────────────
            prosody_data = getattr(file_pred.models, "prosody", None)
            if prosody_data and prosody_data.grouped_predictions:
                for group in prosody_data.grouped_predictions:
                    for pred in group.predictions:
                        seg = {
                            "time": f"{pred.time.begin:.1f}s – {pred.time.end:.1f}s",
                            "text": getattr(pred, "text", ""),
                            "top": sorted(pred.emotions, key=lambda e: e.score, reverse=True)[:3],
                        }
                        segment_emotions.append(seg)
                        for e in pred.emotions:
                            all_prosody.setdefault(e.name, []).append(e.score)

            # ── Burst ─────────────────────────────────────────────────────────
            burst_data = getattr(file_pred.models, "burst", None)
            if burst_data and burst_data.grouped_predictions:
                for group in burst_data.grouped_predictions:
                    for pred in group.predictions:
                        for e in pred.emotions:
                            all_burst.setdefault(e.name, []).append(e.score)

    # ── Overall prosody table ─────────────────────────────────────────────────
    if all_prosody:
        ranked = sorted(all_prosody.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True)
        print("\n  SPEECH EMOTIONS — prosody (averaged across segments)")
        print(f"  {'Rank':<5} {'Emotion':<24} {'Score':>6}  Bar")
        print("  " + "─" * 55)
        for i, (name, vals) in enumerate(ranked[:TOP_N], 1):
            avg = sum(vals) / len(vals)
            print(f"  {i:<5} {name:<24} {avg:>6.3f}  {_bar(avg)}")

    # ── Overall burst table ───────────────────────────────────────────────────
    if all_burst:
        ranked_b = sorted(all_burst.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True)
        print("\n  VOCAL BURST EMOTIONS (non-verbal sounds)")
        print(f"  {'Rank':<5} {'Emotion':<24} {'Score':>6}  Bar")
        print("  " + "─" * 55)
        for i, (name, vals) in enumerate(ranked_b[:TOP_N], 1):
            avg = sum(vals) / len(vals)
            print(f"  {i:<5} {name:<24} {avg:>6.3f}  {_bar(avg)}")

    # ── Per-segment breakdown ─────────────────────────────────────────────────
    if segment_emotions:
        print("\n  PER-SEGMENT BREAKDOWN (top 3 emotions each)")
        print("  " + "─" * 55)
        for seg in segment_emotions:
            label = f"[{seg['time']}]"
            if seg["text"]:
                label += f"  \"{seg['text'][:50]}\""
            print(f"\n  {label}")
            for e in seg["top"]:
                print(f"    • {e.name:<22} {e.score:.3f}  {_bar(e.score, 20)}")

    print(f"\n{sep}\n")

    # ── Build summary dict for JSON export ───────────────────────────────────
    summary = {
        "file": os.path.basename(audio_path),
        "prosody_top10": [
            {"emotion": n, "avg_score": round(sum(v) / len(v), 4)}
            for n, v in sorted(all_prosody.items(), key=lambda x: -sum(x[1]) / len(x[1]))[:TOP_N]
        ] if all_prosody else [],
        "burst_top10": [
            {"emotion": n, "avg_score": round(sum(v) / len(v), 4)}
            for n, v in sorted(all_burst.items(), key=lambda x: -sum(x[1]) / len(x[1]))[:TOP_N]
        ] if all_burst else [],
        "segments": [
            {
                "time": s["time"],
                "text": s["text"],
                "top_emotions": [{"name": e.name, "score": round(e.score, 4)} for e in s["top"]],
            }
            for s in segment_emotions
        ],
    }
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def analyze_audio_emotions(audio_path: str, api_key: str | None = None) -> dict:
    """
    Analyze emotions in an audio file using Hume AI.

    Args:
        audio_path : Path to audio file (.mp3, .wav, .m4a, etc.)
        api_key    : Hume API key. Falls back to HUME_API_KEY env var.

    Returns:
        dict with prosody_top10, burst_top10, and segments.
    """
    key = api_key or os.environ.get("HUME_API_KEY", "")
    if not key:
        raise ValueError(
            "Hume API key required.\n"
            "  Pass it as the second argument, or:\n"
            "  export HUME_API_KEY=your_key_here"
        )

    print("\n[1/3] Validating audio file …")
    validated_path = validate_audio(audio_path)

    client = HumeClient(api_key=key)

    job_id      = submit_job(client, validated_path)
    predictions = wait_and_fetch(client, job_id)
    summary     = display_results(predictions, validated_path)

    # Save JSON results
    out_json = os.path.splitext(audio_path)[0] + "_emotions.json"
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
    print(f"  Full results saved → {out_json}\n")

    return summary


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python audio_emotion_analyzer.py speech.mp3 YOUR_HUME_KEY")
        print("  python audio_emotion_analyzer.py interview.wav")
        sys.exit(0)

    path = sys.argv[1]
    key  = sys.argv[2] if len(sys.argv) > 2 else None

    analyze_audio_emotions(path, api_key=key)