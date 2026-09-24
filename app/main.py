from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Response

app = FastAPI()

# Simulated data store -------------------------------------------------
POLICIES = {
    "POL-1001": {
        "id": "POL-1001",
        "tenant_id": "tenant-a",
        "holder_name": "Alice Johnson",
        "premium": 1200.00,
        "status": "active",
        "coverages": [{"code": "AUTO", "limit": 50000}],
        "documents": [{"id": "DOC-1", "name": "policy.pdf"}],
        "internal_notes": "VIP customer — do not expose",
    },
    "POL-2002": {
        "id": "POL-2002",
        "tenant_id": "tenant-b",
        "holder_name": "Bob Smith",
        "premium": 800.00,
        "status": "lapsed",
        "coverages": [],
        "documents": [],
        "internal_notes": "collections risk",
    },
}

TENANTS_BY_TOKEN = {
    "token-tenant-a": "tenant-a",
    "token-tenant-b": "tenant-b",
}


def current_tenant(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    tenant = TENANTS_BY_TOKEN.get(token)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid token")
    return tenant

def _public_view(policy: dict, include: list[str]) -> dict:
    view = {k: v for k, v in policy.items() if k != "internal_notes"}
    if "coverages" not in include:
        view.pop("coverages", None)
    if "documents" not in include:
        view.pop("documents", None)
    return view


@app.get("/api/v1/policies/{policy_id}")
def get_policy(
    policy_id: str,
    include: str = Query(default=""),
    tenant: str = Depends(current_tenant),
):
    policy = POLICIES.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy["tenant_id"] != tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    include_list = [x.strip() for x in include.split(",") if x.strip()]
    return _public_view(policy, include_list)


@app.get("/api/v1/policies")
def list_policies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    status: str | None = None,
    tenant: str = Depends(current_tenant),
):
    rows = [p for p in POLICIES.values() if p["tenant_id"] == tenant]
    if status:
        rows = [p for p in rows if p["status"] == status]
    start = (page - 1) * page_size
    return {
        "items": [_public_view(p, []) for p in rows[start:start + page_size]],
        "page": page,
        "page_size": page_size,
        "total": len(rows),
    }


# ============================================================================
# PUT /api/v1/users/{user_id}/profile
# ============================================================================

import re

PROFILES = {
    "USR-501": {
        "user_id": "USR-501",
        "display_name": "Alice J.",
        "locale": "en-US",
        "timezone": "America/New_York",
        "version": 1,
    }
}

ALLOWED_TIMEZONES = {"America/New_York", "America/Los_Angeles", "UTC"}
LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def _validate_profile(payload: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    name = payload.get("display_name", "")
    if not isinstance(name, str) or not (2 <= len(name.strip()) <= 50):
        errors["display_name"] = "display_name must be 2-50 characters"

    locale = payload.get("locale", "")
    if not isinstance(locale, str) or not LOCALE_RE.match(locale):
        errors["locale"] = "locale must look like 'en-US'"

    tz = payload.get("timezone", "")
    if tz not in ALLOWED_TIMEZONES:
        errors["timezone"] = f"timezone must be one of {sorted(ALLOWED_TIMEZONES)}"

    return errors


@app.put("/api/v1/users/{user_id}/profile")
def put_user_profile(
    user_id: str,
    payload: dict = Body(...),
    authorization: str = Header(default=""),
    if_match: str = Header(..., alias="If-Match"),
    response: Response = None,
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    # Ownership check (simplified: token == user_id prefix)
    if token != f"token-{user_id.lower()}":
        raise HTTPException(status_code=403, detail="Forbidden")

    profile = PROFILES.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        client_version = int(if_match.strip('"'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid If-Match header")

    if client_version != profile["version"]:
        raise HTTPException(
            status_code=409,
            detail=f"Version conflict: server is at {profile['version']}",
        )

    errors = _validate_profile(payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    new_profile = {
        "user_id": user_id,
        "display_name": payload["display_name"].strip(),
        "locale": payload["locale"],
        "timezone": payload["timezone"],
        "version": profile["version"] + 1,
    }
    PROFILES[user_id] = new_profile

    response.headers["ETag"] = f'"{new_profile["version"]}"'
    return new_profile