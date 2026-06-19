"""
YouTube Emotion Analyzer using Hume AI
- Downloads audio from YouTube using yt-dlp (no ffmpeg required)
- Submits audio to Hume AI Expression Measurement API
- Polls for results and displays top emotions

FIX for HTTP 403 Forbidden:
  YouTube blocks yt-dlp without a JS runtime. Two workarounds are tried
  automatically (in order):
    1. cookies-from-browser  – uses your logged-in Chrome/Firefox session
    2. android_vr extractor  – a client that doesn't require JS/cookies
  If both fail, instructions are printed for a manual cookie-file approach.
"""

import os
import sys
import time
import json
import tempfile
import requests

# ── Install / upgrade dependencies ───────────────────────────────────────────
def install_deps():
    import subprocess
    # Always upgrade yt-dlp – old versions are more likely to get 403s
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "requests", "-q"]
    )

install_deps()

import yt_dlp  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG – set your key here or pass via environment variable HUME_API_KEY
# ─────────────────────────────────────────────────────────────────────────────
HUME_API_KEY = os.environ.get("HUME_API_KEY", "YOUR_HUME_API_KEY_HERE")

HUME_BASE = "https://api.hume.ai/v0/batch"
HEADERS   = {"X-Hume-Api-Key": HUME_API_KEY}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 – Download audio from YouTube (no ffmpeg needed)
# ─────────────────────────────────────────────────────────────────────────────
def _base_opts(out_dir: str) -> dict:
    """Common yt-dlp options shared across all download attempts."""
    return {
        # m4a / webm are native containers – no muxing / ffmpeg needed
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "postprocessors": [],   # no ffmpeg post-processing
        "quiet": False,
        "no_warnings": False,
        # Mimic a real browser UA to reduce bot-detection flags
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        },
    }


def _find_file(out_dir: str, info: dict, ydl: yt_dlp.YoutubeDL) -> str:
    """Locate the downloaded file, handling extension variations."""
    filename = ydl.prepare_filename(info)
    if os.path.exists(filename):
        return filename
    base = os.path.splitext(filename)[0]
    candidates = [
        f for f in os.listdir(out_dir)
        if f.startswith(os.path.basename(base))
    ]
    if not candidates:
        raise FileNotFoundError(f"Downloaded file not found near: {filename}")
    return os.path.join(out_dir, candidates[0])


def download_audio(youtube_url: str, out_dir: str, cookie_file: str | None = None) -> str:
    """
    Downloads best native audio from YouTube without ffmpeg.

    Tries three strategies to defeat 403 / bot-detection:
      1. Browser cookies (Chrome → Firefox → Edge → auto-detect)
      2. android_vr extractor client hint (no JS runtime needed)
      3. Cookie file path (if supplied via --cookies argument)

    Returns the local audio file path.
    """
    print("\n[1/3] Downloading audio from YouTube …")

    # ── Strategy 1: cookies from an installed browser ────────────────────────
    for browser in ("chrome", "firefox", "edge", "brave", "opera", "safari"):
        opts = _base_opts(out_dir)
        opts["cookiesfrombrowser"] = (browser,)
        try:
            print(f"    Trying browser cookies ({browser}) …")
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                filename = _find_file(out_dir, info, ydl)
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"    ✓ Saved: {filename}  ({size_mb:.1f} MB)")
            return filename
        except Exception as e:
            err = str(e)
            if "403" in err or "Forbidden" in err or "not found" in err.lower():
                continue   # try next browser
            if "unsupported browser" in err.lower() or "not installed" in err.lower():
                continue
            # Unexpected error – still try next strategy but warn
            print(f"    ⚠ {browser} cookies failed: {err[:120]}")

    # ── Strategy 2: android_vr extractor (bypasses JS runtime requirement) ───
    print("    Trying android_vr extractor (no JS runtime needed) …")
    opts = _base_opts(out_dir)
    opts["extractor_args"] = {"youtube": {"player_client": ["android_vr"]}}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = _find_file(out_dir, info, ydl)
        size_mb = os.path.getsize(filename) / (1024 * 1024)
        print(f"    ✓ Saved: {filename}  ({size_mb:.1f} MB)")
        return filename
    except Exception as e:
        print(f"    ⚠ android_vr failed: {str(e)[:120]}")

    # ── Strategy 3: explicit cookie file ────────────────────────────────────
    if cookie_file and os.path.exists(cookie_file):
        print(f"    Trying cookie file: {cookie_file} …")
        opts = _base_opts(out_dir)
        opts["cookiefile"] = cookie_file
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                filename = _find_file(out_dir, info, ydl)
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"    ✓ Saved: {filename}  ({size_mb:.1f} MB)")
            return filename
        except Exception as e:
            print(f"    ⚠ Cookie file failed: {str(e)[:120]}")

    # ── All strategies exhausted ─────────────────────────────────────────────
    raise RuntimeError(
        "\n"
        "All download strategies failed (HTTP 403 – YouTube bot detection).\n\n"
        "Quick fixes:\n"
        "  1. Make sure you are LOGGED IN to YouTube in Chrome or Firefox,\n"
        "     then re-run – the script reads cookies automatically.\n\n"
        "  2. Export cookies manually and pass them:\n"
        "     a) Install the 'Get cookies.txt LOCALLY' Chrome extension\n"
        "     b) Visit youtube.com, export → save as  youtube_cookies.txt\n"
        "     c) Run:  python youtube_emotion_analyzer.py <url> <api_key> youtube_cookies.txt\n\n"
        "  3. Install Node.js (https://nodejs.org) and re-run:\n"
        "       yt-dlp --js-runtimes node  <url>\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 – Submit job to Hume Expression Measurement API
# ─────────────────────────────────────────────────────────────────────────────
def submit_hume_job(audio_path: str, max_retries: int = 5) -> str:
    """Uploads audio file to Hume and returns the job_id. Retries on 5xx errors."""
    print("\n[2/3] Submitting audio to Hume AI ...")

    models_payload = {
        "prosody": {},
        "burst":   {},
    }

    for attempt in range(1, max_retries + 1):
        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    f"{HUME_BASE}/jobs",
                    headers=HEADERS,
                    files={"file": (os.path.basename(audio_path), f)},
                    data={"json": json.dumps({"models": models_payload})},
                    timeout=180,
                )

            if response.status_code in (200, 201):
                job_id = response.json().get("job_id")
                print(f"    Job submitted. job_id = {job_id}")
                return job_id

            if response.status_code in (429, 500, 502, 503, 504):
                wait = 2 ** attempt
                print(f"    Attempt {attempt}/{max_retries} - HTTP {response.status_code}. Retrying in {wait}s ...")
                time.sleep(wait)
                continue

            raise RuntimeError(
                f"Hume job submission failed [{response.status_code}]: {response.text}"
            )

        except requests.exceptions.ConnectionError as e:
            wait = 2 ** attempt
            print(f"    Attempt {attempt}/{max_retries} - Connection error. Retrying in {wait}s ...")
            time.sleep(wait)

        except requests.exceptions.Timeout:
            wait = 2 ** attempt
            print(f"    Attempt {attempt}/{max_retries} - Timeout. Retrying in {wait}s ...")
            time.sleep(wait)

    raise RuntimeError(
        f"Hume submission failed after {max_retries} attempts. "
        "The Hume API may be temporarily down - please try again in a few minutes."
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – Poll until done, then fetch & display results
# ─────────────────────────────────────────────────────────────────────────────
def wait_for_job(job_id: str, poll_interval: int = 5, timeout: int = 600) -> dict:
    """Polls Hume until the job completes and returns the predictions."""
    print(f"\n[3/3] Waiting for Hume to finish analysing …")
    deadline = time.time() + timeout

    while time.time() < deadline:
        r = requests.get(
            f"{HUME_BASE}/jobs/{job_id}",
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        status = r.json().get("state", {}).get("status", "unknown")
        print(f"    Status: {status}", end="\r")

        if status == "COMPLETED":
            print("\n    ✓ Job completed!")
            break
        elif status == "FAILED":
            raise RuntimeError(f"Hume job failed: {r.json()}")

        time.sleep(poll_interval)
    else:
        raise TimeoutError("Timed out waiting for Hume job to complete.")

    # Fetch predictions
    pred_r = requests.get(
        f"{HUME_BASE}/jobs/{job_id}/predictions",
        headers=HEADERS,
        timeout=60,
    )
    pred_r.raise_for_status()
    return pred_r.json()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS – parse & pretty-print results
# ─────────────────────────────────────────────────────────────────────────────
def top_emotions(scores: list[dict], n: int = 5) -> list[tuple[str, float]]:
    """Return the top-n emotions sorted by score."""
    return sorted(
        [(e["name"], e["score"]) for e in scores],
        key=lambda x: x[1],
        reverse=True,
    )[:n]


def display_results(predictions: list) -> None:
    print("\n" + "═" * 60)
    print("  EMOTION ANALYSIS RESULTS")
    print("═" * 60)

    for file_pred in predictions:
        file_name = file_pred.get("file", "unknown")
        print(f"\nFile: {file_name}")

        models_data = file_pred.get("models", {})

        # ── Prosody (speech emotion) ─────────────────────────────────────
        prosody = models_data.get("prosody", {})
        grouped = prosody.get("grouped_predictions", [])
        if grouped:
            print("\n  📢 SPEECH EMOTIONS (Prosody)")
            print("  " + "─" * 40)

            all_scores: dict[str, list[float]] = {}
            for group in grouped:
                for pred in group.get("predictions", []):
                    for e in pred.get("emotions", []):
                        all_scores.setdefault(e["name"], []).append(e["score"])

            # Average across all segments
            avg_scores = [
                {"name": name, "score": sum(vals) / len(vals)}
                for name, vals in all_scores.items()
            ]
            for rank, (name, score) in enumerate(top_emotions(avg_scores, 10), 1):
                bar = "█" * int(score * 30)
                print(f"  {rank:2}. {name:<22} {bar:<30} {score:.3f}")

        # ── Burst (non-verbal) ───────────────────────────────────────────
        burst = models_data.get("burst", {})
        b_grouped = burst.get("grouped_predictions", [])
        if b_grouped:
            print("\n  🎙️  VOCAL BURST EMOTIONS")
            print("  " + "─" * 40)

            all_b: dict[str, list[float]] = {}
            for group in b_grouped:
                for pred in group.get("predictions", []):
                    for e in pred.get("emotions", []):
                        all_b.setdefault(e["name"], []).append(e["score"])

            avg_b = [
                {"name": n, "score": sum(v) / len(v)}
                for n, v in all_b.items()
            ]
            for rank, (name, score) in enumerate(top_emotions(avg_b, 10), 1):
                bar = "█" * int(score * 30)
                print(f"  {rank:2}. {name:<22} {bar:<30} {score:.3f}")

    # ── Save full JSON ───────────────────────────────────────────────────
    out_path = "hume_results.json"
    with open(out_path, "w") as fp:
        json.dump(predictions, fp, indent=2)
    print(f"\n  Full results saved → {out_path}")
    print("═" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def analyze_youtube_emotions(
    youtube_url: str,
    api_key: str | None = None,
    cookie_file: str | None = None,
) -> None:
    global HUME_API_KEY, HEADERS

    if api_key:
        HUME_API_KEY = api_key
        HEADERS = {"X-Hume-Api-Key": HUME_API_KEY}

    if HUME_API_KEY == "YOUR_HUME_API_KEY_HERE":
        raise ValueError(
            "Please set your Hume API key:\n"
            "  • edit HUME_API_KEY in this script, or\n"
            "  • export HUME_API_KEY=<your-key> before running"
        )

    with tempfile.TemporaryDirectory() as tmp:
        audio_file  = download_audio(youtube_url, tmp, cookie_file=cookie_file)
        job_id      = submit_hume_job(audio_file)
        predictions = wait_for_job(job_id)

    display_results(predictions)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── CLI usage ────────────────────────────────────────────────────────
    if len(sys.argv) < 2:
        print("Usage: python youtube_emotion_analyzer.py <youtube_url> [hume_api_key] [cookies.txt]")
        print("\nExamples:")
        print("  python youtube_emotion_analyzer.py https://www.youtube.com/watch?v=VIDEO_ID YOUR_HUME_KEY")
        print("  python youtube_emotion_analyzer.py https://www.youtube.com/watch?v=VIDEO_ID YOUR_HUME_KEY youtube_cookies.txt")
        print("\nOr set your key via environment variable:")
        print("  set HUME_API_KEY=your_key_here   (Windows)")
        print("  export HUME_API_KEY=your_key_here (Mac/Linux)")
        sys.exit(1)

    url     = sys.argv[1]
    key     = sys.argv[2] if len(sys.argv) > 2 else None
    cookies = sys.argv[3] if len(sys.argv) > 3 else None

    analyze_youtube_emotions(url, api_key=key, cookie_file=cookies)
