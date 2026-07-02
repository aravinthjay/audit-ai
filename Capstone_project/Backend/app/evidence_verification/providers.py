"""Concrete free-tier / keyless provider adapters for evidence verification.

These complement the generic ``ConfiguredHttpBenchmarkProvider`` (which POSTs a
claim to a configured wrapper URL). The adapters here talk to specific real APIs.

Currently implemented:
- ``FrankfurterFxProvider``: keyless currency conversion via https://frankfurter.app.
  Used for the "fx"/"currency" category to convert a claimed amount into a target
  currency. No API key required, so it works out of the box.

The GST, fuel, and hotel categories continue to use the generic configured-URL
provider; add a free-tier provider URL + key in the environment to enable them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from app.core.config import settings

if TYPE_CHECKING:  # pragma: no cover - hints only, avoids a runtime import cycle
    from app.evidence_verification.service import (
        ClaimEvidenceInput,
        ProviderBenchmarkResult,
    )


class FrankfurterFxProvider:
    """Keyless FX conversion using the Frankfurter API (ECB reference rates)."""

    provider_name = "frankfurter_fx"

    def fetch_benchmark(self, claim: "ClaimEvidenceInput") -> "ProviderBenchmarkResult":
        # Imported here to avoid a circular import at module load time.
        from app.evidence_verification.service import (
            STATUS_NEEDS_MANUAL_REVIEW,
            STATUS_VERIFIED,
            ProviderBenchmarkResult,
            ProviderUnavailableError,
        )

        base = (claim.currency or "INR").upper()
        target = str(
            claim.metadata.get("target_currency")
            or settings.DISPLAY_CURRENCY
            or "USD"
        ).upper()

        if claim.claimed_amount <= 0:
            return ProviderBenchmarkResult(
                provider_name=self.provider_name,
                reference_amount=None,
                provider_reference_id=None,
                confidence=0.4,
                reason="A positive claimed amount is required to convert currency.",
                raw_response={"base": base, "target": target},
                status_override=STATUS_NEEDS_MANUAL_REVIEW,
            )

        if base == target:
            return ProviderBenchmarkResult(
                provider_name=self.provider_name,
                reference_amount=round(claim.claimed_amount, 2),
                provider_reference_id=f"{base}->{target}",
                confidence=1.0,
                reason=f"Claim is already in {target}; no conversion required.",
                raw_response={"base": base, "target": target, "rate": 1.0},
                status_override=STATUS_VERIFIED,
            )

        url = f"{settings.FX_API_BASE_URL.rstrip('/')}/latest"
        try:
            response = requests.get(
                url,
                params={"amount": claim.claimed_amount, "from": base, "to": target},
                timeout=settings.EVIDENCE_VERIFICATION_PROVIDER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            converted = float(data["rates"][target])
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                f"Frankfurter FX lookup failed for {base}->{target}: {exc}"
            ) from exc

        implied_rate = converted / claim.claimed_amount if claim.claimed_amount else None
        return ProviderBenchmarkResult(
            provider_name=self.provider_name,
            reference_amount=round(converted, 2),
            provider_reference_id=f"{base}->{target}",
            confidence=0.97,
            reason=(
                f"Converted {claim.claimed_amount:,.2f} {base} to "
                f"{converted:,.2f} {target} at ECB reference rate"
                + (f" ({implied_rate:.4f})." if implied_rate else ".")
            ),
            raw_response=data,
            status_override=STATUS_VERIFIED,
        )
