"""Third-party evidence verification service.

The service keeps controllers thin: routes pass a claim/investigation and the
service chooses a configured real-time HTTP provider, normalizes the provider
result, applies tolerance rules, and persists an audit friendly verification row.
It never fabricates benchmark amounts locally; missing provider configuration is
reported as API_UNAVAILABLE.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Protocol

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Investigation, ThirdPartyEvidenceVerification

STATUS_VERIFIED = "VERIFIED"
STATUS_FLAGGED = "FLAGGED"
STATUS_API_UNAVAILABLE = "API_UNAVAILABLE"
STATUS_NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"

_GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_GSTIN_SEARCH_PATTERN = re.compile(
    r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"
)


class ProviderUnavailableError(Exception):
    """Raised when a configured external provider cannot return a benchmark."""


@dataclass
class ClaimEvidenceInput:
    """Normalized claim details used by providers and the rule engine."""

    claim_id: str | None
    category: str
    source_category: str
    claimed_amount: float
    vendor: str | None = None
    gstin: str | None = None
    route_from: str | None = None
    route_to: str | None = None
    service_date: str | None = None
    invoice_date: str | None = None
    quantity: float | None = None
    currency: str = "INR"
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderBenchmarkResult:
    """Provider output before tolerance classification."""

    provider_name: str
    reference_amount: float | None
    provider_reference_id: str | None
    confidence: float
    reason: str
    raw_response: dict[str, Any]
    status_override: str | None = None


@dataclass
class EvidenceVerificationResult:
    """Computed verification result independent of persistence."""

    id: str | None
    claim_id: str | None
    category: str
    claimed_amount: float
    fetched_amount: float | None
    min_acceptable_amount: float | None
    max_acceptable_amount: float | None
    difference_amount: float | None
    difference_percentage: float | None
    tolerance_percentage: float
    provider_name: str
    provider_reference_id: str | None
    verification_status: str
    confidence_score: float
    reason: str
    raw_provider_response_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PriceBenchmarkProvider(Protocol):
    """Provider contract for category-specific reference data."""

    provider_name: str

    def fetch_benchmark(self, claim: ClaimEvidenceInput) -> ProviderBenchmarkResult:
        """Fetch or calculate a benchmark for the claim."""


def normalize_category(value: str | None) -> str:
    text = (value or "").strip().lower()
    aliases = {
        "flight": ("flight", "airfare", "airline", "air ticket", "ticket"),
        "hotel": ("hotel", "lodging", "accommodation", "room", "stay"),
        "food": ("food", "meal", "restaurant", "catering", "dining"),
        "cab": ("cab", "taxi", "transport", "ride", "uber", "ola"),
        "fuel": ("fuel", "petrol", "diesel", "gasoline"),
        "gst": ("gst", "invoice", "vendor bill", "tax invoice", "supplier bill"),
    }
    for category, needles in aliases.items():
        if any(needle in text for needle in needles):
            return category
    return "generic"


def _clean_location(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.split(
        r"\b(claimed|amount|invoice|bill|fare|flight|ticket|trip|ride|for|on|dated|date|class)\b",
        value,
        flags=re.IGNORECASE,
    )[0]
    cleaned = re.sub(r"[^A-Za-z .'-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    return cleaned or None


def _first_text(metadata: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_float(metadata: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = metadata.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _date_to_string(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_description(description: str | None) -> dict[str, Any]:
    text = description or ""
    parsed: dict[str, Any] = {}

    gstin_match = _GSTIN_SEARCH_PATTERN.search(text.upper())
    if gstin_match:
        parsed["gstin"] = gstin_match.group(0)

    route_match = re.search(
        r"\b(?:from\s+)?([A-Za-z][A-Za-z .'-]{1,50}?)\s+(?:to|->)\s+"
        r"([A-Za-z][A-Za-z .'-]{1,80})",
        text,
        flags=re.IGNORECASE,
    )
    if route_match:
        parsed["route_from"] = _clean_location(route_match.group(1))
        parsed["route_to"] = _clean_location(route_match.group(2))

    quantity_match = re.search(
        r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:litres?|liters?|ltr|l)\b",
        text,
        flags=re.IGNORECASE,
    )
    if quantity_match:
        parsed["quantity"] = float(quantity_match.group(1))

    date_match = re.search(r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b", text)
    if date_match:
        parsed["service_date"] = date_match.group(1)
        parsed["invoice_date"] = date_match.group(1)

    return parsed


class ConfiguredHttpBenchmarkProvider:
    """HTTP adapter for real provider integrations configured by URL/API key."""

    def __init__(self, category: str, url: str, api_key: str | None):
        self.category = category
        self.url = url
        self.api_key = api_key or ""
        self.provider_name = f"{category}_http_provider"

    def fetch_benchmark(self, claim: ClaimEvidenceInput) -> ProviderBenchmarkResult:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "claim_id": claim.claim_id,
            "category": claim.category,
            "claimed_amount": claim.claimed_amount,
            "vendor": claim.vendor,
            "gstin": claim.gstin,
            "route_from": claim.route_from,
            "route_to": claim.route_to,
            "service_date": claim.service_date,
            "invoice_date": claim.invoice_date,
            "quantity": claim.quantity,
            "currency": claim.currency,
            "location": claim.location,
            "metadata": claim.metadata,
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=settings.EVIDENCE_VERIFICATION_PROVIDER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(str(exc)) from exc

        amount = data.get("reference_amount", data.get("fetched_amount", data.get("amount")))
        try:
            reference_amount = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            reference_amount = None

        return ProviderBenchmarkResult(
            provider_name=str(data.get("provider_name") or self.provider_name),
            reference_amount=reference_amount,
            provider_reference_id=(
                str(data.get("provider_reference_id"))
                if data.get("provider_reference_id") is not None
                else None
            ),
            confidence=float(data.get("confidence", 0.75)),
            reason=str(data.get("reason") or "Provider returned a benchmark response."),
            raw_response=data,
            status_override=data.get("status"),
        )


class UnconfiguredBenchmarkProvider:
    """Provider adapter that fails closed when real API config is missing."""

    def __init__(self, category: str):
        self.category = category
        self.provider_name = f"{category}_third_party_provider"

    def fetch_benchmark(self, claim: ClaimEvidenceInput) -> ProviderBenchmarkResult:
        del claim
        raise ProviderUnavailableError(
            f"No real-time third-party provider URL is configured for category '{self.category}'."
        )


def _is_valid_gstin(value: str | None) -> bool:
    return bool(value and _GSTIN_PATTERN.match(value.strip().upper()))


class EvidenceVerificationService:
    """Coordinates provider calls, tolerance checks, persistence, and flags."""

    def build_claim_input(
        self,
        investigation: Investigation,
        overrides: Mapping[str, Any] | None = None,
    ) -> ClaimEvidenceInput:
        data = dict(overrides or {})
        metadata = dict(data.get("metadata") or {})
        parsed = _parse_description(investigation.description)
        metadata.setdefault("description", investigation.description)

        source_category = str(data.get("category") or investigation.category)
        category = normalize_category(source_category)
        claimed_amount = float(data.get("claimed_amount", investigation.amount))
        currency = str(data.get("currency") or metadata.get("currency") or "INR").upper()

        return ClaimEvidenceInput(
            claim_id=investigation.id,
            category=category,
            source_category=source_category,
            claimed_amount=claimed_amount,
            vendor=str(data.get("vendor") or investigation.vendor),
            gstin=str(data.get("gstin") or parsed.get("gstin") or "").upper() or None,
            route_from=_clean_location(data.get("route_from") or parsed.get("route_from")),
            route_to=_clean_location(data.get("route_to") or parsed.get("route_to")),
            service_date=_date_to_string(data.get("service_date") or parsed.get("service_date")),
            invoice_date=_date_to_string(data.get("invoice_date") or parsed.get("invoice_date")),
            quantity=_coerce_float(data.get("quantity", parsed.get("quantity"))),
            currency=currency,
            location=_clean_location(data.get("location") or metadata.get("location")),
            metadata=metadata,
        )

    def build_preview_input(self, payload: Mapping[str, Any]) -> ClaimEvidenceInput:
        data = dict(payload)
        metadata = dict(data.get("metadata") or {})
        source_category = str(data.get("category") or "generic")
        return ClaimEvidenceInput(
            claim_id=None,
            category=normalize_category(source_category),
            source_category=source_category,
            claimed_amount=float(data.get("claimed_amount") or 0),
            vendor=_none_if_blank(data.get("vendor")),
            gstin=_none_if_blank(data.get("gstin")),
            route_from=_clean_location(data.get("route_from")),
            route_to=_clean_location(data.get("route_to")),
            service_date=_date_to_string(data.get("service_date")),
            invoice_date=_date_to_string(data.get("invoice_date")),
            quantity=_coerce_float(data.get("quantity")),
            currency=str(data.get("currency") or "INR").upper(),
            location=_clean_location(data.get("location")),
            metadata=metadata,
        )

    def verify_preview(self, payload: Mapping[str, Any]) -> EvidenceVerificationResult:
        claim = self.build_preview_input(payload)
        return self._verify_claim(claim, result_id=None)

    def verify_investigation(
        self,
        db: Session,
        investigation: Investigation,
        overrides: Mapping[str, Any] | None = None,
    ) -> ThirdPartyEvidenceVerification:
        claim = self.build_claim_input(investigation, overrides)
        result = self._verify_claim(claim, result_id=str(uuid.uuid4()))
        row = ThirdPartyEvidenceVerification(
            id=result.id,
            claim_id=investigation.id,
            category=result.category,
            claimed_amount=result.claimed_amount,
            fetched_amount=result.fetched_amount,
            min_acceptable_amount=result.min_acceptable_amount,
            max_acceptable_amount=result.max_acceptable_amount,
            difference_amount=result.difference_amount,
            difference_percentage=result.difference_percentage,
            tolerance_percentage=result.tolerance_percentage,
            provider_name=result.provider_name,
            provider_reference_id=result.provider_reference_id,
            verification_status=result.verification_status,
            confidence_score=result.confidence_score,
            reason=result.reason,
            raw_provider_response_json=result.raw_provider_response_json,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
        db.add(row)
        self._apply_case_flags(investigation, row)
        db.commit()
        db.refresh(row)
        return row

    def get_latest(self, db: Session, claim_id: str) -> ThirdPartyEvidenceVerification | None:
        return (
            db.query(ThirdPartyEvidenceVerification)
            .filter(ThirdPartyEvidenceVerification.claim_id == claim_id)
            .order_by(ThirdPartyEvidenceVerification.created_at.desc())
            .first()
        )

    def _verify_claim(
        self,
        claim: ClaimEvidenceInput,
        result_id: str | None,
    ) -> EvidenceVerificationResult:
        tolerance = self._tolerance_for(claim.category)
        now = datetime.utcnow()
        validation_result = self._validate_before_provider(claim)
        if validation_result:
            return self._classify_result(claim, validation_result, tolerance, result_id, now)

        provider = self._provider_for(claim.category)
        try:
            provider_result = provider.fetch_benchmark(claim)
        except ProviderUnavailableError as exc:
            return EvidenceVerificationResult(
                id=result_id,
                claim_id=claim.claim_id,
                category=claim.category,
                claimed_amount=claim.claimed_amount,
                fetched_amount=None,
                min_acceptable_amount=None,
                max_acceptable_amount=None,
                difference_amount=None,
                difference_percentage=None,
                tolerance_percentage=tolerance,
                provider_name=getattr(provider, "provider_name", f"{claim.category}_provider"),
                provider_reference_id=None,
                verification_status=STATUS_API_UNAVAILABLE,
                confidence_score=0.0,
                reason=f"Provider unavailable or timed out: {exc}",
                raw_provider_response_json={"error": str(exc)},
                created_at=now,
                updated_at=now,
            )

        return self._classify_result(claim, provider_result, tolerance, result_id, now)

    def _validate_before_provider(
        self,
        claim: ClaimEvidenceInput,
    ) -> ProviderBenchmarkResult | None:
        if claim.category == "generic":
            return ProviderBenchmarkResult(
                provider_name="local_claim_validation",
                reference_amount=None,
                provider_reference_id=None,
                confidence=0.35,
                reason=(
                    "No supported third-party provider category was detected; manual review "
                    "is required."
                ),
                raw_response={"source_category": claim.source_category},
                status_override=STATUS_NEEDS_MANUAL_REVIEW,
            )

        if claim.category == "gst":
            if not claim.gstin:
                return ProviderBenchmarkResult(
                    provider_name="local_gstin_validation",
                    reference_amount=None,
                    provider_reference_id=None,
                    confidence=0.4,
                    reason="GSTIN is missing; vendor identity cannot be validated automatically.",
                    raw_response={"missing_fields": ["gstin"]},
                    status_override=STATUS_NEEDS_MANUAL_REVIEW,
                )
            if not _is_valid_gstin(claim.gstin):
                return ProviderBenchmarkResult(
                    provider_name="local_gstin_validation",
                    reference_amount=None,
                    provider_reference_id=None,
                    confidence=0.95,
                    reason="GSTIN format is invalid.",
                    raw_response={"gstin": claim.gstin, "format_valid": False},
                    status_override=STATUS_FLAGGED,
                )

        missing_fields: list[str] = []
        if claim.category == "flight":
            if not claim.route_from:
                missing_fields.append("route_from")
            if not claim.route_to:
                missing_fields.append("route_to")
            if not claim.service_date:
                missing_fields.append("service_date")
        elif claim.category == "hotel":
            if not (claim.location or _first_text(claim.metadata, "city", "location")):
                missing_fields.append("location")
            if not (claim.service_date or claim.invoice_date):
                missing_fields.append("service_date")
        elif claim.category == "cab":
            if not (
                _first_float(claim.metadata, "distance_km", "distance")
                or (claim.route_from and claim.route_to)
            ):
                missing_fields.append("distance_km or pickup/drop")
        elif claim.category == "fuel" and (claim.quantity is None or claim.quantity <= 0):
            missing_fields.append("quantity")

        if not missing_fields:
            return None

        return ProviderBenchmarkResult(
            provider_name="local_claim_validation",
            reference_amount=None,
            provider_reference_id=None,
            confidence=0.45,
            reason=(
                "Critical claim fields are missing for real-time third-party verification: "
                f"{', '.join(missing_fields)}."
            ),
            raw_response={"missing_fields": missing_fields},
            status_override=STATUS_NEEDS_MANUAL_REVIEW,
        )

    def _classify_result(
        self,
        claim: ClaimEvidenceInput,
        provider_result: ProviderBenchmarkResult,
        tolerance: float,
        result_id: str | None,
        now: datetime,
    ) -> EvidenceVerificationResult:
        fetched = provider_result.reference_amount
        difference_amount = None
        difference_percentage = None
        min_acceptable = None
        max_acceptable = None

        if fetched is not None and fetched > 0:
            min_acceptable = round(fetched * (1 - tolerance), 2)
            max_acceptable = round(fetched * (1 + tolerance), 2)
            difference_amount = round(claim.claimed_amount - fetched, 2)
            difference_percentage = round(difference_amount / fetched, 6)

        status = provider_result.status_override
        reason = provider_result.reason
        if not status:
            if fetched is None or fetched <= 0:
                status = STATUS_NEEDS_MANUAL_REVIEW
                reason = (
                    "Fetched benchmark amount is unavailable; claim cannot be auto-verified."
                )
            elif abs(difference_percentage or 0) > tolerance:
                status = STATUS_FLAGGED
                reason = (
                    f"Claimed amount is outside the accepted +/-{tolerance * 100:.0f}% "
                    f"range. {provider_result.reason}"
                )
            else:
                status = STATUS_VERIFIED
                reason = f"Claimed amount is within +/-{tolerance * 100:.0f}% tolerance. {reason}"

        return EvidenceVerificationResult(
            id=result_id,
            claim_id=claim.claim_id,
            category=claim.category,
            claimed_amount=claim.claimed_amount,
            fetched_amount=fetched,
            min_acceptable_amount=min_acceptable,
            max_acceptable_amount=max_acceptable,
            difference_amount=difference_amount,
            difference_percentage=difference_percentage,
            tolerance_percentage=tolerance,
            provider_name=provider_result.provider_name,
            provider_reference_id=provider_result.provider_reference_id,
            verification_status=status,
            confidence_score=provider_result.confidence,
            reason=reason,
            raw_provider_response_json=provider_result.raw_response,
            created_at=now,
            updated_at=now,
        )

    def _provider_for(self, category: str) -> PriceBenchmarkProvider:
        url, api_key = self._configured_provider(category)
        if url:
            return ConfiguredHttpBenchmarkProvider(category, url, api_key)
        return UnconfiguredBenchmarkProvider(category)

    def _configured_provider(self, category: str) -> tuple[str, str]:
        providers = {
            "flight": (settings.FLIGHT_PRICE_PROVIDER_URL, settings.FLIGHT_PRICE_PROVIDER_API_KEY),
            "hotel": (settings.HOTEL_PRICE_PROVIDER_URL, settings.HOTEL_PRICE_PROVIDER_API_KEY),
            "food": (
                settings.FOOD_BENCHMARK_PROVIDER_URL,
                settings.FOOD_BENCHMARK_PROVIDER_API_KEY,
            ),
            "cab": (settings.CAB_FARE_PROVIDER_URL, settings.CAB_FARE_PROVIDER_API_KEY),
            "fuel": (settings.FUEL_PRICE_PROVIDER_URL, settings.FUEL_PRICE_PROVIDER_API_KEY),
            "gst": (
                settings.GST_VERIFICATION_PROVIDER_URL,
                settings.GST_VERIFICATION_PROVIDER_API_KEY,
            ),
        }
        return providers.get(category, ("", ""))

    def _tolerance_for(self, category: str) -> float:
        values = {
            "flight": settings.EVIDENCE_VERIFICATION_FLIGHT_TOLERANCE,
            "hotel": settings.EVIDENCE_VERIFICATION_HOTEL_TOLERANCE,
            "food": settings.EVIDENCE_VERIFICATION_FOOD_TOLERANCE,
            "cab": settings.EVIDENCE_VERIFICATION_CAB_TOLERANCE,
            "fuel": settings.EVIDENCE_VERIFICATION_FUEL_TOLERANCE,
            "gst": settings.EVIDENCE_VERIFICATION_GST_TOLERANCE,
        }
        return values.get(category, settings.EVIDENCE_VERIFICATION_DEFAULT_TOLERANCE)

    def _apply_case_flags(
        self,
        investigation: Investigation,
        verification: ThirdPartyEvidenceVerification,
    ) -> None:
        if verification.verification_status == STATUS_VERIFIED:
            return

        flags = list(investigation.flags or [])
        flag = f"third_party_evidence:{verification.verification_status.lower()}"
        if flag not in flags:
            flags.append(flag)
            investigation.flags = flags


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _none_if_blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
