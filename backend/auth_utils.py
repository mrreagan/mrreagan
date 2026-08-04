"""Auth utilities: JWT, password hashing, role-based dependencies. Reads token from cookie OR Authorization header."""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = 30
COOKIE_NAME = "br_session"

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    # `iat` is second-precision (whole seconds, RFC 7519). We also embed a
    # millisecond-precision `iat_ms` so revocation can distinguish a token
    # minted in the same second as a rotate — see _is_token_revoked.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": now + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": now,
        "iat_ms": int(now.timestamp() * 1000),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None


def _extract_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    """Cookie first, Authorization header as fallback."""
    cookie_token = request.cookies.get(COOKIE_NAME) if request else None
    if cookie_token:
        return cookie_token
    if credentials:
        return credentials.credentials
    return None


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    token = _extract_token(request, credentials)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    from database import db
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    return user


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    from database import db
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Session revocation — if an admin action (e.g. counsel credential
    # rotate) marked this user's tokens revoked after this token was
    # issued, kill the session. `iat` is issued-at (unix seconds); the
    # revocation timestamp is stored as ISO-8601.
    revoked = await db.user_token_revocations.find_one(
        {"user_id": user["id"]}, {"_id": 0, "revoked_at": 1},
    )
    if revoked and _is_token_revoked(payload.get("iat"), payload.get("iat_ms"), revoked.get("revoked_at")):
        raise HTTPException(status_code=401, detail="Session revoked. Please sign in again.")
    return user


def _is_token_revoked(iat: Optional[int], iat_ms: Optional[int], revoked_at_iso: Optional[str]) -> bool:
    """Return True iff the token was issued STRICTLY BEFORE the recorded
    revocation instant.

    Precision matters here because rotations happen in real time. Two
    inputs are compared:
      - `iat_ms` (preferred): millisecond-precision timestamp we embed
        at token-creation time. Compared strict-<, microsecond-precise,
        against the full revoked_at value.
      - `iat` (fallback for legacy tokens): whole-second Unix time.
        Compared against revoked_at truncated to whole seconds using
        strict-<. That is imperfect (a same-second boundary is accepted)
        but only applies to tokens minted before we started embedding
        iat_ms — which is a bounded, decaying population.
    """
    if not revoked_at_iso:
        return False
    try:
        revoked_dt = datetime.fromisoformat(revoked_at_iso.replace("Z", "+00:00"))
    except Exception:
        return False

    if iat_ms:
        try:
            iat_ms_int = int(iat_ms)
        except (TypeError, ValueError):
            iat_ms_int = 0
        if iat_ms_int:
            iat_dt = datetime.fromtimestamp(iat_ms_int / 1000.0, tz=timezone.utc)
            return iat_dt < revoked_dt

    if not iat:
        return False
    revoked_s = revoked_dt.replace(microsecond=0)
    if isinstance(iat, datetime):
        iat_dt = iat.replace(microsecond=0)
    else:
        iat_dt = datetime.fromtimestamp(int(iat), tz=timezone.utc)
    return iat_dt < revoked_s


def require_roles(*roles: str):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        # `readonly_admin` is a counsel-review role: it inherits all `admin`
        # read permissions, but write attempts are blocked by the
        # ReadonlyEnforcementMiddleware. This keeps every existing
        # `require_roles("admin")` decorator working without edits.
        if "admin" in roles and user.get("role") == "readonly_admin":
            return user
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def set_session_cookie(response, token: str) -> None:
    """Set httpOnly session cookie."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=JWT_EXPIRE_DAYS * 24 * 3600,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")
