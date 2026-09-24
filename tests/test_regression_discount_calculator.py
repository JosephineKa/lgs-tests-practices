import pytest

from src.discount_calculator import MAX_TOTAL_DISCOUNT, calculate_discount


# ---------- Regression guard for JIRA-4821 ----------

def test_jira_4821_coupon_and_loyalty_stack_multiplicatively():
    """
    REGRESSION: before the fix, gold + 20% coupon returned only 20% off.
    Expected: 1 - (0.80 * 0.90) = 0.28  ->  $72.00 on a $100 subtotal.
    """
    result = calculate_discount(subtotal=100.00, coupon_rate=0.20, loyalty_tier="gold")

    assert result.loyalty_rate == pytest.approx(0.10)
    assert result.effective_rate == pytest.approx(0.28)
    assert result.total == pytest.approx(72.00)


def test_jira_4821_total_discount_is_capped_at_40_percent():
    """REGRESSION: stacking 50% coupon + 30% platinum must cap at 40%."""
    result = calculate_discount(subtotal=200.00, coupon_rate=0.50, loyalty_tier="platinum")

    assert result.effective_rate == pytest.approx(MAX_TOTAL_DISCOUNT)
    assert result.total == pytest.approx(120.00)


def test_jira_4821_unknown_loyalty_tier_does_not_crash_or_discount():
    """REGRESSION: unknown tier used to raise KeyError; must fall back to 0%."""
    result = calculate_discount(subtotal=50.00, coupon_rate=0.10, loyalty_tier="diamond")

    assert result.loyalty_rate == 0.0
    assert result.total == pytest.approx(45.00)


# ---------- Broader regression suite ----------

@pytest.mark.parametrize(
    "subtotal, coupon, tier, expected_total",
    [
        (100.0, 0.0,  "none",     100.0),
        (100.0, 0.0,  "silver",    95.0),
        (100.0, 0.10, "none",      90.0),
        (100.0, 0.10, "silver",    85.5),
        (100.0, 0.25, "gold",      67.5),
        (0.0,   0.50, "gold",       0.0),
        (99.99, 0.15, "platinum",  72.24),
    ],
)
def test_discount_matrix_remains_stable(subtotal, coupon, tier, expected_total):
    result = calculate_discount(subtotal, coupon, tier)
    assert result.total == pytest.approx(expected_total, abs=0.01)


@pytest.mark.parametrize("bad_subtotal", [-0.01, -100])
def test_negative_subtotal_still_raises(bad_subtotal):
    with pytest.raises(ValueError, match="non-negative"):
        calculate_discount(bad_subtotal, 0.10, "gold")


@pytest.mark.parametrize("bad_coupon", [-0.01, 1.01])
def test_out_of_range_coupon_still_raises(bad_coupon):
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_discount(100.0, bad_coupon, "gold")