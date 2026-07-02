"""LLM provider routing, fallback, token, and cost tests."""

import pytest

from app.core.config import settings
from app.db.models import LLMCallLog, RuntimeSetting
from app.db.session import SessionLocal
from app.llm.pricing import estimate_cost_usd
from app.llm.routing import route_model
from app.llm.service import LLMService
from app.llm.settings_store import LLM_SETTINGS_KEY, save_llm_settings
from app.llm.tokenization import compact_prompt, estimate_tokens
from app.llm.types import LLMFailureKind, LLMProviderError, LLMRequest, ProviderResponse


class FakeProvider:
    def __init__(self, name, response_text="ok", error: LLMProviderError | None = None):
        self.name = name
        self.response_text = response_text
        self.error = error
        self.calls = 0

    def complete(self, request, *, model, api_key, timeout_seconds):
        self.calls += 1
        if self.error:
            raise self.error
        return ProviderResponse(
            content=self.response_text,
            model=model,
            prompt_tokens=10,
            completion_tokens=5,
        )


@pytest.fixture()
def clean_llm_tables(db):
    db.query(LLMCallLog).delete()
    db.query(RuntimeSetting).filter(RuntimeSetting.key == LLM_SETTINGS_KEY).delete()
    db.commit()
    yield
    db.query(LLMCallLog).delete()
    db.query(RuntimeSetting).filter(RuntimeSetting.key == LLM_SETTINGS_KEY).delete()
    db.commit()


def test_token_estimation_and_prompt_compaction():
    assert estimate_tokens("Payments above materiality require approval.") >= 5
    compacted = compact_prompt("A\nA\nB\n" + ("long text " * 200), 30)
    assert compacted.count("A") == 1
    assert estimate_tokens(compacted) <= 35


def test_cost_calculation_uses_input_and_output_pricing():
    assert estimate_cost_usd("gpt-4.1-mini", prompt_tokens=1_000_000, completion_tokens=500_000) == 1.2


def test_model_routing_uses_reasoning_for_critical_tasks():
    model, tier, reason = route_model(
        "anthropic",
        LLMRequest(prompt="Render final audit verdict.", request_type="adjudication", complexity="critical"),
    )
    assert model == settings.CLAUDE_MODEL_REASONING
    assert tier == "reasoning"
    assert "audit-critical" in reason


def test_provider_fallback_tracks_failed_and_successful_calls(monkeypatch, db, clean_llm_tables):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "groq-key")
    save_llm_settings(
        db,
        {"default_provider": "anthropic", "fallback_enabled": True, "fallback_order": ["groq"]},
    )
    anthropic = FakeProvider(
        "anthropic",
        error=LLMProviderError(
            "context length exceeded",
            provider="anthropic",
            kind=LLMFailureKind.CONTEXT_LENGTH,
            retryable=True,
        ),
    )
    groq = FakeProvider("groq", response_text="fallback response")
    service = LLMService(
        providers={"anthropic": anthropic, "groq": groq, "openai": FakeProvider("openai")},
        session_factory=SessionLocal,
    )

    response = service.complete(
        LLMRequest(
            prompt="Evaluate this audit case.",
            request_type="adjudication",
            complexity="critical",
            request_id="llm-fallback-test",
        )
    )

    assert response.provider == "groq"
    assert response.fallback_used is True
    assert anthropic.calls == 1
    assert groq.calls == 1

    rows = (
        db.query(LLMCallLog)
        .filter(LLMCallLog.request_id == "llm-fallback-test")
        .order_by(LLMCallLog.created_at.asc())
        .all()
    )
    assert len(rows) == 2
    assert rows[0].provider_name == "anthropic"
    assert rows[0].success is False
    assert rows[1].provider_name == "groq"
    assert rows[1].success is True
    assert rows[1].fallback_used is True


def test_fallback_disabled_surfaces_provider_error(monkeypatch, db, clean_llm_tables):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "groq-key")
    save_llm_settings(
        db,
        {"default_provider": "anthropic", "fallback_enabled": False, "fallback_order": ["groq"]},
    )
    service = LLMService(
        providers={
            "anthropic": FakeProvider(
                "anthropic",
                error=LLMProviderError(
                    "rate limit",
                    provider="anthropic",
                    kind=LLMFailureKind.RATE_LIMIT,
                    retryable=True,
                ),
            ),
            "groq": FakeProvider("groq"),
            "openai": FakeProvider("openai"),
        },
        session_factory=SessionLocal,
    )

    with pytest.raises(LLMProviderError) as exc:
        service.complete(LLMRequest(prompt="x", request_type="verification", request_id="llm-no-fallback"))

    assert exc.value.kind == LLMFailureKind.RATE_LIMIT
    rows = db.query(LLMCallLog).filter(LLMCallLog.request_id == "llm-no-fallback").all()
    assert len(rows) == 1
    assert rows[0].provider_name == "anthropic"


def test_missing_default_provider_key_is_user_friendly(monkeypatch, db, clean_llm_tables):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(ValueError) as exc:
        save_llm_settings(
            db,
            {"default_provider": "openai", "fallback_enabled": False, "fallback_order": []},
        )
    assert "OPENAI_API_KEY" in str(exc.value)
