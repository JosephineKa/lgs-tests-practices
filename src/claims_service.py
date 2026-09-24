from dataclasses import dataclass
from datetime import datetime, timedelta

from src.policy_repository import Claim, ClaimRepository


MAX_CLAIMS_PER_30_DAYS = 3
MANUAL_REVIEW_THRESHOLD = 10_000.00


class ClaimValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Claim validation failed")
        self.errors = errors


class FraudRuleViolation(Exception):
    pass


@dataclass
class ClaimResult:
    claim: Claim
    requires_manual_review: bool
    domain_events: list[str]


class ClaimsService:
    def __init__(self, repo: ClaimRepository, clock=None):
        self._repo = repo
        self._clock = clock or datetime.utcnow

    def file_claim(
        self,
        policy_id: str,
        claimant_id: str,
        amount: float,
        description: str,
    ) -> ClaimResult:
        errors: dict[str, str] = {}

        if not policy_id:
            errors["policy_id"] = "policy_id is required"
        if not claimant_id:
            errors["claimant_id"] = "claimant_id is required"
        if amount is None or amount <= 0:
            errors["amount"] = "amount must be positive"
        if amount and amount > 1_000_000:
            errors["amount"] = "amount exceeds maximum allowed"
        if not description or len(description.strip()) < 5:
            errors["description"] = "description must be at least 5 characters"

        if errors:
            raise ClaimValidationError(errors)

        since = self._clock() - timedelta(days=30)
        recent = self._repo.count_recent_by_claimant(claimant_id, since)
        if recent >= MAX_CLAIMS_PER_30_DAYS:
            raise FraudRuleViolation(
                f"Claimant {claimant_id} exceeded "
                f"{MAX_CLAIMS_PER_30_DAYS} claims in 30 days"
            )

        claim = Claim(
            id=None,
            policy_id=policy_id,
            claimant_id=claimant_id,
            amount=round(amount, 2),
            description=description.strip(),
            created_at=self._clock(),
        )
        saved = self._repo.save(claim)

        events = ["claim.created"]
        requires_review = saved.amount > MANUAL_REVIEW_THRESHOLD
        if requires_review:
            events.append("claim.manual_review.required")

        return ClaimResult(
            claim=saved,
            requires_manual_review=requires_review,
            domain_events=events,
        )