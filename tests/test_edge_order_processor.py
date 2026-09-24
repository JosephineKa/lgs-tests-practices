import pytest

from src.order_processor import (
    FREE_SHIPPING_THRESHOLD,
    MAX_LINE_QUANTITY,
    STANDARD_SHIPPING,
    LineItem,
    process_order,
)


# ---------- Free-shipping boundary ----------

def test_shipping_threshold_exactly_at_boundary_is_free():
    """EDGE: subtotal == $75.00 -> free shipping (>= comparison)."""
    result = process_order([LineItem("SKU-A", unit_price=75.00, quantity=1)])
    assert result.shipping == 0.0


def test_shipping_threshold_one_cent_below_charges_shipping():
    """EDGE: $74.99 must still incur shipping."""
    result = process_order([LineItem("SKU-A", unit_price=74.99, quantity=1)])
    assert result.shipping == STANDARD_SHIPPING


# ---------- Quantity edges ----------

def test_quantity_of_one_is_allowed_no_warning():
    result = process_order([LineItem("SKU-A", unit_price=10.00, quantity=1)])
    assert result.warnings == []


def test_quantity_of_exactly_100_does_not_warn():
    """Boundary: warning kicks in strictly above 100."""
    result = process_order([LineItem("SKU-A", unit_price=1.00, quantity=100)])
    assert result.warnings == []


def test_quantity_of_101_emits_warning():
    result = process_order([LineItem("SKU-A", unit_price=1.00, quantity=101)])
    assert any("Large quantity" in w for w in result.warnings)


def test_quantity_at_max_is_allowed():
    """Boundary: MAX_LINE_QUANTITY itself must pass."""
    result = process_order([LineItem("SKU-A", unit_price=0.01, quantity=MAX_LINE_QUANTITY)])
    assert result.subtotal == pytest.approx(9.99)


def test_quantity_above_max_raises():
    with pytest.raises(ValueError, match="exceeds max"):
        process_order([LineItem("SKU-A", unit_price=1.00, quantity=MAX_LINE_QUANTITY + 1)])


@pytest.mark.parametrize("qty", [0, -1, -100])
def test_non_positive_quantity_raises(qty):
    with pytest.raises(ValueError, match="must be positive"):
        process_order([LineItem("SKU-A", unit_price=1.00, quantity=qty)])


# ---------- Empty / degenerate input ----------

def test_empty_cart_raises():
    with pytest.raises(ValueError, match="at least one line item"):
        process_order([])


def test_negative_unit_price_raises():
    with pytest.raises(ValueError, match="cannot be negative"):
        process_order([LineItem("SKU-A", unit_price=-0.01, quantity=1)])


# ---------- Floating-point rounding edges ----------

def test_penny_rounding_is_deterministic():
    """EDGE: $0.01 x 3 should not drift. subtotal=0.03, total ~= 10.02."""
    result = process_order([LineItem("SKU-A", unit_price=0.01, quantity=3)])
    assert result.subtotal == 0.03
    assert result.total == pytest.approx(10.02, abs=0.01)


def test_zero_price_item_still_counts_toward_shipping_rules():
    """EDGE: free item, order under threshold -> shipping charged."""
    result = process_order([LineItem("SKU-FREE", unit_price=0.0, quantity=1)])
    assert result.subtotal == 0.0
    assert result.shipping == STANDARD_SHIPPING


def test_multi_item_just_over_threshold_gets_free_shipping():
    """EDGE: two lines sum to exactly $75.00 -> free shipping."""
    result = process_order([
        LineItem("SKU-A", unit_price=37.50, quantity=1),
        LineItem("SKU-B", unit_price=37.50, quantity=1),
    ])
    assert result.subtotal == FREE_SHIPPING_THRESHOLD
    assert result.shipping == 0.0