import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, status
import jwt
from config import settings
from database import get_user, get_session

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def create_access_token(user_id: int):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = secrets.token_urlsafe(24)
    payload = {"sub": str(user_id), "jti": jti, "iat": now, "exp": exp}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, jti, exp

def decode_token(token: str):
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

def get_token_from_request(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token")

def get_current_user(request: Request):
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in to continue.")
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Please log in again.")
    session = get_session(jti)
    if not session or session["revoked"]:
        raise HTTPException(status_code=401, detail="Your session has ended. Please log in again.")
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")
    return user
