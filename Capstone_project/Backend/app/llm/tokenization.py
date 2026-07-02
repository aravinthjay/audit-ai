"""Small dependency-free token estimation and prompt trimming helpers."""

from __future__ import annotations

import math
import re

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def estimate_tokens(text: str | None) -> int:
    """Estimate tokens without provider SDK tokenizers.

    The heuristic intentionally errs a little high so cost estimates and prompt
    trimming stay conservative when provider usage metadata is absent.
    """
    if not text:
        return 0
    lexical = len(TOKEN_PATTERN.findall(text))
    char_based = math.ceil(len(text) / 4)
    return max(1, math.ceil(max(lexical * 1.1, char_based)))


def dedupe_lines(text: str) -> str:
    """Remove exact duplicate non-empty lines while preserving first order."""
    seen: set[str] = set()
    output: list[str] = []
    for line in text.splitlines():
        normalized = line.strip()
        if normalized and normalized in seen:
            continue
        if normalized:
            seen.add(normalized)
        output.append(line)
    return "\n".join(output).strip()


def trim_text_to_token_budget(text: str, max_tokens: int) -> str:
    if max_tokens <= 0 or estimate_tokens(text) <= max_tokens:
        return text.strip()

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    selected: list[str] = []
    running = 0
    for paragraph in paragraphs:
        paragraph_tokens = estimate_tokens(paragraph)
        if running + paragraph_tokens > max_tokens:
            break
        selected.append(paragraph)
        running += paragraph_tokens

    if selected:
        return "\n\n".join(selected).strip()

    approx_chars = max(64, max_tokens * 4)
    return text[:approx_chars].strip()


def compact_prompt(prompt: str, max_prompt_tokens: int) -> str:
    """Remove repeated context and trim to the configured prompt budget."""
    compacted = dedupe_lines(prompt)
    return trim_text_to_token_budget(compacted, max_prompt_tokens)
