"""Production smoke checks for deployed API/UI endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
        if response.status >= 400:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return json.loads(payload)


def _get_status(url: str, timeout: float) -> int:
    request = urllib.request.Request(url, headers={"Accept": "text/html,application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a production deployment.")
    parser.add_argument("--api-base-url", default=os.getenv("API_BASE_URL", ""))
    parser.add_argument("--ui-base-url", default=os.getenv("UI_BASE_URL", ""))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("SMOKE_TIMEOUT", "10")))
    args = parser.parse_args()

    if not args.api_base_url:
        print("API_BASE_URL or --api-base-url is required", file=sys.stderr)
        return 2

    api_base = args.api_base_url.rstrip("/")
    health = _get_json(f"{api_base}/health", args.timeout)
    if health.get("status") != "healthy":
        raise RuntimeError(f"API health status is not healthy: {health}")
    print(f"API healthy: {health.get('app', 'unknown')} {health.get('version', '')}".strip())

    if args.ui_base_url:
        status = _get_status(args.ui_base_url.rstrip("/"), args.timeout)
        if status >= 400:
            raise RuntimeError(f"UI returned HTTP {status}")
        print(f"UI reachable: HTTP {status}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        print(f"Smoke check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
