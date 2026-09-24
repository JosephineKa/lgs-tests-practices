import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH_A = {"Authorization": "Bearer token-tenant-a"}
AUTH_B = {"Authorization": "Bearer token-tenant-b"}


# ---------- Successful GET cases ----------

def test_get_policy_returns_public_fields_only():
    """Happy path: 200 with public fields, internal_notes stripped."""
    resp = client.get("/api/v1/policies/POL-1001", headers=AUTH_A)

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "POL-1001"
    assert body["holder_name"] == "Alice Johnson"
    assert body["status"] == "active"
    assert "internal_notes" not in body


def test_get_policy_with_include_expands_related_resources():
    """?include=coverages,documents returns the expanded collections."""
    resp = client.get(
        "/api/v1/policies/POL-1001?include=coverages,documents",
        headers=AUTH_A,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["coverages"] == [{"code": "AUTO", "limit": 50000}]
    assert body["documents"][0]["name"] == "policy.pdf"


def test_get_policy_without_include_omits_related_resources():
    """Default response omits coverages/documents to keep payload small."""
    resp = client.get("/api/v1/policies/POL-1001", headers=AUTH_A)
    body = resp.json()
    assert "coverages" not in body
    assert "documents" not in body


# ---------- Auth / authorization failure cases ----------

def test_get_policy_without_token_returns_401():
    resp = client.get("/api/v1/policies/POL-1001")
    assert resp.status_code == 401


def test_get_policy_with_invalid_token_returns_401():
    resp = client.get(
        "/api/v1/policies/POL-1001",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_cross_tenant_access_returns_403():
    """Multi-tenant isolation: tenant-b cannot read tenant-a's policy."""
    resp = client.get("/api/v1/policies/POL-1001", headers=AUTH_B)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden"


def test_unknown_policy_returns_404():
    resp = client.get("/api/v1/policies/POL-DOES-NOT-EXIST", headers=AUTH_A)
    assert resp.status_code == 404


# ---------- Collection endpoint: filtering + pagination boundaries ----------

def test_list_policies_filters_by_status():
    resp = client.get("/api/v1/policies?status=active", headers=AUTH_A)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "POL-1001"


def test_list_policies_pagination_defaults():
    resp = client.get("/api/v1/policies", headers=AUTH_A)
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 10


@pytest.mark.parametrize(
    "query, expected_status",
    [
        ("?page=0", 422),
        ("?page_size=0", 422),
        ("?page_size=51", 422),
        ("?page=-1", 422),
    ],
)
def test_pagination_boundaries_reject_invalid_values(query, expected_status):
    """Boundary: page>=1 and 1<=page_size<=50 enforced by the API."""
    resp = client.get(f"/api/v1/policies{query}", headers=AUTH_A)
    assert resp.status_code == expected_status


def test_list_policies_never_leaks_other_tenant_data():
    """Every item returned must belong to the caller's tenant."""
    resp = client.get("/api/v1/policies", headers=AUTH_A)
    ids = [item["id"] for item in resp.json()["items"]]
    assert "POL-2002" not in ids