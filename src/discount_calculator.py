from dataclasses import dataclass


LOYALTY_RATES = {"none": 0.00, "silver": 0.05, "gold": 0.10, "platinum": 0.15}
MAX_TOTAL_DISCOUNT = 0.40


@dataclass
class DiscountBreakdown:
    subtotal: float
    coupon_rate: float
    loyalty_rate: float
    effective_rate: float
    total: float


def calculate_discount(subtotal: float, coupon_rate: float, loyalty_tier: str) -> DiscountBreakdown:
    if subtotal < 0:
        raise ValueError("subtotal must be non-negative")
    if not 0.0 <= coupon_rate <= 1.0:
        raise ValueError("coupon_rate must be between 0 and 1")

    loyalty_rate = LOYALTY_RATES.get(loyalty_tier.lower(), 0.0)

    # BUG FIX (JIRA-4821): stack multiplicatively, not max().
    effective = 1 - (1 - coupon_rate) * (1 - loyalty_rate)
    effective = min(effective, MAX_TOTAL_DISCOUNT)

    total = round(subtotal * (1 - effective), 2)
    return DiscountBreakdown(subtotal, coupon_rate, loyalty_rate, effective, total)