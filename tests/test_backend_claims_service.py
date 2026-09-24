from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from src.claims_service import (
    ClaimValidationError,
    ClaimsService,
    FraudRuleViolation,
    MANUAL_REVIEW_THRESHOLD,
    MAX_CLAIMS_PER_30_DAYS,
)
from src.policy_repository import Claim, InMemoryClaimRepository


@pytest.fixture
def repo():
    return InMemoryClaimRepository()


@pytest.fixture
def service(repo):
    return ClaimsService(repo)


# ---------- Successful backend behavior ----------

def test_file_claim_persists_and_returns_domain_event(service, repo):
    """Happy path: valid claim is saved with generated ID and 'claim.created' event."""
    result = service.file_claim(
        policy_id="POL-1001",
        claimant_id="USR-501",
        amount=1500.00,
        description="Water damage to kitchen floor",
    )

    assert result.claim.id == 1
    assert result.claim.amount == 1500.00
    assert result.requires_manual_review is False
    assert result.domain_events == ["claim.created"]
    assert repo.get(1).policy_id == "POL-1001"


def test_high_value_claim_triggers_manual_review(service):
    """Business rule: amounts above $10,000 require manual review."""
    result = service.file_claim(
        policy_id="POL-1001",
        claimant_id="USR-501",
        amount=MANUAL_REVIEW_THRESHOLD + 0.01,
        description="Major structural damage",
    )

    assert result.requires_manual_review is True
    assert "claim.manual_review.required" in result.domain_events


def test_claim_at_review_threshold_does_not_trigger_review(service):
    """Boundary: exactly $10,000 is still auto-approved."""
    result = service.file_claim(
        policy_id="POL-1001",
        claimant_id="USR-501",
        amount=MANUAL_REVIEW_THRESHOLD,
        description="Exactly at threshold",
    )

    assert result.requires_manual_review is False


def test_description_is_trimmed_before_persisting(service):
    result = service.file_claim(
        policy_id="POL-1001",
        claimant_id="USR-501",
        amount=100.00,
        description="   burst pipe in basement   ",
    )
    assert result.claim.description == "burst pipe in basement"


# ---------- Validation failure cases ----------

@pytest.mark.parametrize(
    "field, value, expected_key",
    [
        ("policy_id", "", "policy_id"),
        ("claimant_id", "", "claimant_id"),
        ("amount", 0, "amount"),
        ("amount", -50.00, "amount"),
        ("amount", 1_000_001.00, "amount"),
        ("description", "no", "description"),
        ("description", "    ", "description"),
    ],
)
def test_invalid_claim_payload_is_rejected(
    service, repo, field, value, expected_key
):
    """Each invalid field must surface its own error; nothing persisted."""
    payload = {
        "policy_id": "POL-1001",
        "claimant_id": "USR-501",
        "amount": 500.00,
        "description": "Wind damage to roof",
    }
    payload[field] = value

    with pytest.raises(ClaimValidationError) as exc:
        service.file_claim(**payload)

    assert expected_key in exc.value.errors
    assert repo.get(1) is None


# ---------- Fraud rule (business logic) ----------

@freeze_time("2025-10-15 10:00:00")
def test_fraud_rule_blocks_fourth_claim_in_30_days(repo):
    """Anti-fraud: max 3 claims per claimant per rolling 30 days."""
    service = ClaimsService(repo)

    for i in range(MAX_CLAIMS_PER_30_DAYS):
        service.file_claim(
            policy_id="POL-1001",
            claimant_id="USR-501",
            amount=100.00 + i,
            description=f"Claim number {i + 1}",
        )

    with pytest.raises(FraudRuleViolation) as exc:
        service.file_claim(
            policy_id="POL-1001",
            claimant_id="USR-501",
            amount=100.00,
            description="Fourth claim attempt",
        )
    assert "exceeded" in str(exc.value)


@freeze_time("2025-10-15 10:00:00")
def test_fraud_window_rolls_after_30_days(repo):
    """Boundary: a claim exactly 31 days old does NOT count toward the limit."""
    service = ClaimsService(repo)

    for _ in range(MAX_CLAIMS_PER_30_DAYS):
        service.file_claim(
            policy_id="POL-1001",
            claimant_id="USR-501",
            amount=100.00,
            description="Old claim",
        )

    # Manually backdate them by 31 days -> they fall outside the window.
    for claim in repo._rows.values():
        claim.created_at = datetime.utcnow() - timedelta(days=31)

    # A fresh claim should now be accepted.
    result = service.file_claim(
        policy_id="POL-1001",
        claimant_id="USR-501",
        amount=200.00,
        description="Fresh claim after window roll",
    )
    assert result.claim.id == 4


def test_fraud_rule_is_scoped_per_claimant(repo):
    """A different claimant is not blocked by another claimant's history."""
    service = ClaimsService(repo)
    for _ in range(MAX_CLAIMS_PER_30_DAYS):
        service.file_claim("POL-1001", "USR-501", 100.00, "Regular claim")

    # Different claimant -> allowed
    result = service.file_claim("POL-1002", "USR-999", 100.00, "Different user claim")
    assert result.claim.claimant_id == "USR-999"