import pytest

from src.user_registration import ValidationError, register_user


class InMemoryUserRepo:
    """Simple fake — no DB needed for validation tests."""

    def __init__(self, existing_emails=None):
        self._emails = set(existing_emails or [])
        self.saved = []

    def exists_by_email(self, email: str) -> bool:
        return email in self._emails

    def save(self, user):
        self._emails.add(user.email)
        self.saved.append(user)


@pytest.fixture
def repo():
    return InMemoryUserRepo()


@pytest.fixture
def valid_payload():
    return {
        "email": "  Alice@Example.COM ",
        "full_name": "Alice Johnson",
        "age": 30,
        "phone": "+15551234567",
    }


# ---------- Successful case ----------

def test_valid_registration_persists_and_normalizes(repo, valid_payload):
    """Valid payload: saves user, normalizes email (trim + lowercase)."""
    user = register_user(valid_payload, repo)

    assert user.email == "alice@example.com"
    assert user.full_name == "Alice Johnson"
    assert repo.saved == [user]


# ---------- Validation failure cases ----------

@pytest.mark.parametrize(
    "field, value, expected_fragment",
    [
        ("email", "not-an-email", "invalid"),
        ("email", "", "required"),
        ("full_name", "   ", "required"),
        ("full_name", "", "required"),
        ("age", 12, "at least 13"),
        ("age", 121, "maximum"),
        ("age", "thirty", "integer"),
        ("phone", "abc", "digits"),
        ("phone", "12345", "digits"),
    ],
)
def test_field_validation_rejects_bad_input(
    repo, valid_payload, field, value, expected_fragment
):
    """Each invalid field must raise ValidationError with a helpful message."""
    payload = {**valid_payload, field: value}

    with pytest.raises(ValidationError) as exc:
        register_user(payload, repo)

    assert field in exc.value.errors
    assert expected_fragment in exc.value.errors[field].lower()
    assert repo.saved == []


def test_duplicate_email_is_rejected():
    """Business-rule validation: email uniqueness."""
    repo = InMemoryUserRepo(existing_emails={"alice@example.com"})
    payload = {
        "email": "alice@example.com",
        "full_name": "Alice Clone",
        "age": 25,
        "phone": "15551234567",
    }

    with pytest.raises(ValidationError) as exc:
        register_user(payload, repo)

    assert "already registered" in exc.value.errors["email"].lower()


# ---------- Boundary success cases ----------

@pytest.mark.parametrize("age", [13, 120])
def test_age_boundaries_are_inclusive(repo, valid_payload, age):
    """Age boundaries 13 and 120 are valid; 12 and 121 are not (covered above)."""
    user = register_user({**valid_payload, "age": age}, repo)
    assert user.age == age