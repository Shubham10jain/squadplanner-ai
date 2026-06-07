"""Pydantic models for persisted documents."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TripDocument(BaseModel):
    id: str | None = Field(None, alias="_id")
    status: str = "pending"
    state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class UserDocument(BaseModel):
    id: str | None = Field(None, alias="_id")
    email: str
    name: str
    avatar_url: str = ""
    auth_provider: Literal["local", "google"] = "local"
    hashed_password: str | None = None
    created_at: str = ""

    model_config = {"populate_by_name": True}
