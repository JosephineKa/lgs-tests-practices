import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Validation failed")
        self.errors = errors


@dataclass
class User:
    email: str
    full_name: str
    age: int
    phone: str


def register_user(payload: dict, repo) -> User:
    errors: dict[str, str] = {}

    email = (payload.get("email") or "").strip().lower()
    full_name = (payload.get("full_name") or "").strip()
    age = payload.get("age")
    phone = (payload.get("phone") or "").strip()

    if not email:
        errors["email"] = "Email is required."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Email format is invalid."

    if not full_name:
        errors["full_name"] = "Full name is required."

    if age is None:
        errors["age"] = "Age is required."
    elif not isinstance(age, int):
        errors["age"] = "Age must be an integer."
    elif age < 13:
        errors["age"] = "Users must be at least 13 years old."
    elif age > 120:
        errors["age"] = "Age exceeds the supported maximum."

    if not PHONE_RE.match(phone):
        errors["phone"] = "Phone must be 10-15 digits, optionally prefixed with '+'."

    if errors:
        raise ValidationError(errors)

    if repo.exists_by_email(email):
        raise ValidationError({"email": "Email is already registered."})

    user = User(email=email, full_name=full_name, age=age, phone=phone)
    repo.save(user)
    return user