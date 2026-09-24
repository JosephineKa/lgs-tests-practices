import pytest
from fastapi.testclient import TestClient

from app.main import PROFILES, app

client = TestClient(app)

AUTH_501 = {
    "Authorization": "Bearer token-usr-501",
    "If-Match": '"1"',
    "Content-Type": "application/json",
}

VALID_PAYLOAD = {
    "display_name": "Alice Johnson",
    "locale": "en-US",
    "timezone": "America/New_York",
}


@pytest.fixture(autouse=True)
def reset_profiles():
    """Each test starts from the same baseline profile — no cross-test bleed."""
    PROFILES.clear()
    PROFILES["USR-501"] = {
        "user_id": "USR-501",
        "display_name": "Alice J.",
        "locale": "en-US",
        "timezone": "America/New_York",
        "version": 1,
    }
    yield
    PROFILES.clear()


# ---------- Successful PUT cases ----------

def test_put_profile_updates_and_bumps_version():
    """Happy path: 200, resource replaced, version incremented, ETag returned."""
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json=VALID_PAYLOAD,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Alice Johnson"
    assert body["version"] == 2
    assert resp.headers["ETag"] == '"2"'


def test_put_profile_is_idempotent_when_called_with_current_version():
    """
    Idempotency: after the first PUT returns version 2, a second PUT
    using If-Match: "2" with the same body yields the same resource (version 3).
    """
    first = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json=VALID_PAYLOAD,
    )
    assert first.status_code == 200
    new_version = first.json()["version"]

    second = client.put(
        "/api/v1/users/USR-501/profile",
        headers={
            "Authorization": "Bearer token-usr-501",
            "If-Match": f'"{new_version}"',
            "Content-Type": "application/json",
        },
        json=VALID_PAYLOAD,
    )
    assert second.status_code == 200
    assert second.json()["display_name"] == "Alice Johnson"
    assert second.json()["version"] == new_version + 1


def test_put_trims_display_name_before_persisting():
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json={**VALID_PAYLOAD, "display_name": "   Alice Johnson   "},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Alice Johnson"


# ---------- Concurrency failure cases ----------

def test_put_with_stale_version_returns_409():
    """Optimistic concurrency: If-Match older than server version -> 409."""
    # Bump the server to version 2 first
    client.put("/api/v1/users/USR-501/profile", headers=AUTH_501, json=VALID_PAYLOAD)

    # Client still sends If-Match: "1"
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json={**VALID_PAYLOAD, "display_name": "Changed by stale client"},
    )
    assert resp.status_code == 409
    assert "conflict" in resp.json()["detail"].lower()
    assert PROFILES["USR-501"]["display_name"] == "Alice Johnson"


def test_put_with_malformed_if_match_returns_400():
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers={**AUTH_501, "If-Match": "not-a-version"},
        json=VALID_PAYLOAD,
    )
    assert resp.status_code == 400


def test_put_without_if_match_returns_422():
    """Header is required by the contract."""
    headers = {k: v for k, v in AUTH_501.items() if k != "If-Match"}
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=headers,
        json=VALID_PAYLOAD,
    )
    assert resp.status_code == 422


# ---------- Auth / authorization failures ----------

def test_put_without_token_returns_401():
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers={"If-Match": '"1"', "Content-Type": "application/json"},
        json=VALID_PAYLOAD,
    )
    assert resp.status_code == 401


def test_put_to_another_users_profile_returns_403():
    """Caller is USR-501 but tries to write USR-999's profile."""
    resp = client.put(
        "/api/v1/users/USR-999/profile",
        headers=AUTH_501,
        json=VALID_PAYLOAD,
    )
    assert resp.status_code == 403


def test_put_unknown_user_returns_404():
    resp = client.put(
        "/api/v1/users/USR-404/profile",
        headers={
            "Authorization": "Bearer token-usr-404",
            "If-Match": '"1"',
            "Content-Type": "application/json",
        },
        json=VALID_PAYLOAD,
    )
    assert resp.status_code == 404


# ---------- Validation boundary cases ----------

@pytest.mark.parametrize(
    "field, value, expected_fragment",
    [
        ("display_name", "A", "2-50"),
        ("display_name", "A" * 51, "2-50"),
        ("display_name", "", "2-50"),
        ("locale", "english", "en-US"),
        ("locale", "EN-us", "en-US"),
        ("timezone", "Mars/Olympus_Mons", "timezone must be one of"),
    ],
)
def test_invalid_profile_fields_return_422(field, value, expected_fragment):
    payload = {**VALID_PAYLOAD, field: value}
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json=payload,
    )
    assert resp.status_code == 422
    assert expected_fragment in resp.json()["detail"][field]


@pytest.mark.parametrize("name_length", [2, 50])
def test_display_name_length_boundaries_are_inclusive(name_length):
    """Boundary: 2 and 50 are valid; 1 and 51 are not (covered above)."""
    payload = {**VALID_PAYLOAD, "display_name": "A" * name_length}
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json=payload,
    )
    assert resp.status_code == 200
    assert len(resp.json()["display_name"]) == name_length


def test_validation_failure_does_not_bump_version():
    """A rejected PUT must not mutate state or version."""
    resp = client.put(
        "/api/v1/users/USR-501/profile",
        headers=AUTH_501,
        json={**VALID_PAYLOAD, "display_name": "A"},
    )
    assert resp.status_code == 422
    assert PROFILES["USR-501"]["version"] == 1