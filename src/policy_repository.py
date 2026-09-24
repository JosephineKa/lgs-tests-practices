from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Claim:
    id: Optional[int]
    policy_id: str
    claimant_id: str
    amount: float
    description: str
    created_at: datetime


class ClaimRepository:
    """Thin repository contract; implementations may be SQL or in-memory."""

    def save(self, claim: Claim) -> Claim:
        raise NotImplementedError

    def count_recent_by_claimant(self, claimant_id: str, since: datetime) -> int:
        raise NotImplementedError

    def get(self, claim_id: int) -> Optional[Claim]:
        raise NotImplementedError


class InMemoryClaimRepository(ClaimRepository):
    """Used for both tests and lightweight local dev."""

    def __init__(self):
        self._rows: dict[int, Claim] = {}
        self._next_id = 1

    def save(self, claim: Claim) -> Claim:
        claim.id = self._next_id
        self._rows[claim.id] = claim
        self._next_id += 1
        return claim

    def count_recent_by_claimant(self, claimant_id: str, since: datetime) -> int:
        return sum(
            1
            for c in self._rows.values()
            if c.claimant_id == claimant_id and c.created_at >= since
        )

    def get(self, claim_id: int) -> Optional[Claim]:
        return self._rows.get(claim_id)