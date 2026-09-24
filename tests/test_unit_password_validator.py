import pytest

from src.password_validator import (
    MIN_LENGTH,
    PasswordResult,
    validate_password_strength,
)


# ---------- Successful (happy path) cases ----------

@pytest.mark.parametrize(
    "password, description",
    [
        ("Str0ng!Passw0rd#2024", "typical strong password"),
        ("C0mpl3x@System$Key!", "mixed symbols + casing"),
        ("Aa1!" + "x" * (MIN_LENGTH - 4), "exactly minimum length, just valid"),
    ],
)
def test_strong_passwords_are_accepted(password, description):
    """A password meeting every rule must be marked valid with no reasons."""
    result = validate_password_strength(password)

    assert result == PasswordResult(is_valid=True, reasons=[]), (
        f"Expected acceptance for {description!r}, got {result.reasons}"
    )


# ---------- Failure cases ----------

def test_password_short_by_one_character_is_rejected():
    """Boundary: MIN_LENGTH - 1 must fail with the length reason."""
    short = "Aa1!" + "x" * (MIN_LENGTH - 5)
    assert len(short) == MIN_LENGTH - 1

    result = validate_password_strength(short)

    assert result.is_valid is False
    assert any("at least" in r for r in result.reasons)


def test_password_missing_all_character_classes_reports_every_reason():
    """A purely lowercase password should surface three distinct failures."""
    result = validate_password_strength("aaaaaaaaaaaa")

    assert result.is_valid is False
    assert len(result.reasons) == 3
    assert any("uppercase" in r for r in result.reasons)
    assert any("digit" in r for r in result.reasons)
    assert any("special" in r for r in result.reasons)


def test_common_weak_phrase_is_rejected_even_when_complex():
    """A password containing 'password' must be rejected regardless of entropy."""
    result = validate_password_strength("MyPassword!234")

    assert result.is_valid is False
    assert any("commonly used" in r for r in result.reasons)


def test_empty_password_is_rejected():
    """Empty input must never raise and must be invalid."""
    result = validate_password_strength("")

    assert result.is_valid is False
    assert len(result.reasons) >= 4