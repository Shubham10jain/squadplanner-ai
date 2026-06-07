"""Auth routes — register, login, google, logout, me."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.middleware.auth import get_current_user
from db.client import get_collection
from services.auth_service import (
    create_jwt,
    hash_password,
    verify_google_token,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_COOKIE = "access_token"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=JWT_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production behind HTTPS
        max_age=COOKIE_MAX_AGE,
    )


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleRequest(BaseModel):
    token: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response):
    users = get_collection("users")

    if await users.find_one({"email": body.email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    doc = {
        "_id": user_id,
        "email": body.email,
        "name": body.name,
        "avatar_url": "",
        "auth_provider": "local",
        "hashed_password": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await users.insert_one(doc)

    token = create_jwt(user_id, body.email)
    _set_auth_cookie(response, token)

    return {"id": user_id, "email": body.email, "name": body.name, "avatar_url": ""}


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    users = get_collection("users")
    user = await users.find_one({"email": body.email})

    if not user or user.get("auth_provider") != "local":
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_jwt(user["_id"], user["email"])
    _set_auth_cookie(response, token)

    return {
        "id": user["_id"],
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user.get("avatar_url", ""),
    }


@router.post("/google")
async def google_auth(body: GoogleRequest, response: Response):
    try:
        claims = await verify_google_token(body.token)
    except Exception as exc:
        logger.error("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {exc}")

    email = claims["email"]
    users = get_collection("users")
    user = await users.find_one({"email": email})

    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "_id": user_id,
            "email": email,
            "name": claims.get("name", ""),
            "avatar_url": claims.get("picture", ""),
            "auth_provider": "google",
            "hashed_password": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await users.insert_one(user)

    token = create_jwt(user["_id"], user["email"])
    _set_auth_cookie(response, token)

    return {
        "id": user["_id"],
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user.get("avatar_url", ""),
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=JWT_COOKIE)
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
