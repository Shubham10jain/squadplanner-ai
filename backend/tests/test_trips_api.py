from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import trips as trips_api


class FakeTripsCollection:
    def __init__(self, trip=None):
        self.trip = trip
        self.inserted = None
        self.updated = None

    async def find_one(self, query, projection=None):
        return self.trip if query.get("trip_id") == self.trip.get("trip_id") else None

    async def insert_one(self, document):
        self.inserted = document

    async def update_one(self, query, update):
        self.updated = {"query": query, "update": update}


@pytest.mark.asyncio
async def test_get_trip_returns_invites_sent_shape(monkeypatch):
    created_at = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    collection = FakeTripsCollection(
        {
            "trip_id": "trip-1",
            "trip_name": "Chicago Weekend",
            "invite_code": "abc123",
            "created_at": created_at,
            "invited_members": [
                {"email": "a@example.com", "status": "pending"},
                {"email": "b@example.com", "status": "accepted"},
            ],
            "initial_state": {"internal": True},
        }
    )
    monkeypatch.setattr(trips_api, "get_collection", lambda name: collection)

    response = await trips_api.get_trip("trip-1")

    assert response == {
        "trip_id": "trip-1",
        "trip_name": "Chicago Weekend",
        "invite_code": "abc123",
        "created_at": "2026-06-16T12:00:00+00:00",
        "expires_at": "2026-06-17T12:00:00+00:00",
        "invited_members": [
            {"email": "a@example.com", "status": "pending"},
            {"email": "b@example.com", "status": "accepted"},
        ],
    }


@pytest.mark.asyncio
async def test_get_trip_backfills_invited_members_from_legacy_emails(monkeypatch):
    collection = FakeTripsCollection(
        {
            "trip_id": "trip-2",
            "trip_name": "Austin Weekend",
            "invite_code": "xyz789",
            "created_at": "2026-06-16T12:00:00+00:00",
            "invited_emails": ["a@example.com", "b@example.com"],
        }
    )
    monkeypatch.setattr(trips_api, "get_collection", lambda name: collection)

    response = await trips_api.get_trip("trip-2")

    assert response["invited_members"] == [
        {"email": "a@example.com", "status": "pending"},
        {"email": "b@example.com", "status": "pending"},
    ]
    assert collection.updated == {
        "query": {"trip_id": "trip-2"},
        "update": {
            "$set": {
                "invited_members": [
                    {"email": "a@example.com", "status": "pending"},
                    {"email": "b@example.com", "status": "pending"},
                ]
            }
        },
    }


@pytest.mark.asyncio
async def test_create_trip_persists_invited_members_with_pending_status(monkeypatch):
    collection = FakeTripsCollection({"trip_id": "unused"})
    monkeypatch.setattr(trips_api, "get_collection", lambda name: collection)

    async def send_trip_invite(*args, **kwargs):
        return None

    monkeypatch.setattr(trips_api, "send_trip_invite", send_trip_invite)

    await trips_api.create_trip(
        trips_api.CreateTripRequest(
            trip_name="Denver Weekend",
            created_by="leader@example.com",
            invited_emails=["a@example.com", "b@example.com"],
        )
    )

    assert collection.inserted["invited_members"] == [
        {"email": "a@example.com", "status": "pending"},
        {"email": "b@example.com", "status": "pending"},
    ]
