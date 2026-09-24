from dataclasses import dataclass, field

FREE_SHIPPING_THRESHOLD = 75.00
STANDARD_SHIPPING = 9.99
MAX_LINE_QUANTITY = 999
TAX_RATE = 0.0825


@dataclass
class LineItem:
    sku: str
    unit_price: float
    quantity: int


@dataclass
class OrderResult:
    subtotal: float
    tax: float
    shipping: float
    total: float
    warnings: list[str] = field(default_factory=list)


def process_order(items: list[LineItem]) -> OrderResult:
    if not items:
        raise ValueError("Order must contain at least one line item")

    warnings: list[str] = []
    subtotal = 0.0

    for item in items:
        if item.quantity <= 0:
            raise ValueError(f"Quantity for {item.sku} must be positive")
        if item.quantity > MAX_LINE_QUANTITY:
            raise ValueError(f"Quantity for {item.sku} exceeds max of {MAX_LINE_QUANTITY}")
        if item.unit_price < 0:
            raise ValueError(f"Unit price for {item.sku} cannot be negative")
        if item.quantity > 100:
            warnings.append(f"Large quantity on {item.sku}: {item.quantity}")

        subtotal += round(item.unit_price * item.quantity, 2)

    subtotal = round(subtotal, 2)
    tax = round(subtotal * TAX_RATE, 2)
    shipping = 0.0 if subtotal >= FREE_SHIPPING_THRESHOLD else STANDARD_SHIPPING

    return OrderResult(
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        total=round(subtotal + tax + shipping, 2),
        warnings=warnings,
    )