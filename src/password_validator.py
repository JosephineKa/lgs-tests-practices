from dataclasses import dataclass, field


@dataclass
class PasswordResult:
    is_valid: bool
    reasons: list[str] = field(default_factory=list)


MIN_LENGTH = 12
SPECIAL_CHARS = set("!@#$%^&*()-_=+[]{};:,.<>?/|")


def validate_password_strength(password: str) -> PasswordResult:
    reasons: list[str] = []

    if len(password) < MIN_LENGTH:
        reasons.append(f"Password must be at least {MIN_LENGTH} characters long.")

    if not any(c.isupper() for c in password):
        reasons.append("Password must contain at least one uppercase letter.")

    if not any(c.islower() for c in password):
        reasons.append("Password must contain at least one lowercase letter.")

    if not any(c.isdigit() for c in password):
        reasons.append("Password must contain at least one digit.")

    if not any(c in SPECIAL_CHARS for c in password):
        reasons.append("Password must contain at least one special character.")

    if any(common in password.lower() for common in ("password", "123456", "qwerty")):
        reasons.append("Password contains a commonly used weak phrase.")

    return PasswordResult(is_valid=not reasons, reasons=reasons)