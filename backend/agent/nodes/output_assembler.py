"""Final trip pitch assembly node."""

import asyncio
import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from agent.state import DecisionLogEntry, TripState
from config import get_llm, settings

logger = logging.getLogger(__name__)


def _message_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def _strip_json_fences(text: str) -> str:
    cleaned = str(text or "").strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    if not cleaned.startswith("{") and "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]
    return cleaned


def _destination_details(state: TripState) -> tuple[str, str]:
    selected = state.get("selected_destination") or ""
    for destination in state.get("candidate_destinations", []):
        if destination.get("id") == selected or destination.get("name") == selected:
            return destination.get("name", selected), destination.get("state", "")
    return selected, ""


def _confirmed_stops(day: dict) -> list[dict]:
    """Return the stops that actually rendered into the itinerary, as the single source
    of truth for any narrative copy. Falls back to activities/meals only when route stops
    are unavailable."""
    route_stops = sorted(
        day.get("route_stops", []) or [],
        key=lambda stop: int(stop.get("order", 0) or 0),
    )
    if route_stops:
        return [
            {
                "time": stop.get("time") or ("Base" if stop.get("type") == "hotel" else ""),
                "type": "meal" if stop.get("type") == "restaurant" else stop.get("type") or "activity",
                "label": stop.get("label") or "Stop",
            }
            for stop in route_stops
            if stop.get("label")
        ]

    fallback = [
        {"time": "", "type": "activity", "label": activity.get("name")}
        for activity in day.get("activities", [])
        if activity.get("name")
    ]
    fallback.extend(
        {"time": "", "type": "meal", "label": meal} for meal in day.get("meals", []) if meal
    )
    return fallback


def _days_summary(state: TripState) -> list[dict]:
    return [
        {
            "day_number": day.get("day_number"),
            "neighborhood": day.get("neighborhood"),
            "stops": _confirmed_stops(day),
            "constraint_notes": day.get("constraint_notes", []),
        }
        for day in state.get("days", [])
    ]


def _readable_days_summary(days: list[dict]) -> str:
    lines = []
    for day in days:
        stops = day.get("stops", [])
        stop_text = "; ".join(
            f"{stop.get('time') or '--'} {stop.get('label')} ({stop.get('type')})".strip()
            for stop in stops
            if stop.get("label")
        )
        lines.append(
            f"Day {day.get('day_number')}: {day.get('neighborhood', 'Neighborhood TBD')}\n"
            f"  Confirmed stops (the ONLY places you may mention for this day): "
            f"{stop_text or 'No confirmed stops'}"
        )
    return "\n".join(lines)


def _apply_grounded_narrative(state: TripState, raw_text: str) -> tuple[str, list[dict] | None]:
    """Parse the grounded JSON narrative. Returns (pitch, updated_days_or_None).

    On any parse failure we treat the model output as a plain-text pitch and leave the
    existing day rationales untouched, so the node degrades gracefully.
    """
    try:
        parsed = json.loads(_strip_json_fences(raw_text))
    except (json.JSONDecodeError, ValueError):
        return raw_text.strip(), None

    if not isinstance(parsed, dict):
        return raw_text.strip(), None

    pitch = str(parsed.get("pitch") or "").strip() or raw_text.strip()

    day_overrides: dict[int, dict] = {}
    for entry in parsed.get("days", []) or []:
        if not isinstance(entry, dict) or entry.get("day_number") is None:
            continue
        try:
            day_overrides[int(entry["day_number"])] = entry
        except (TypeError, ValueError):
            continue

    if not day_overrides:
        return pitch, None

    updated_days = deepcopy(state.get("days", []))
    for day in updated_days:
        override = day_overrides.get(int(day.get("day_number", 0)))
        if not override:
            continue
        rationale = str(override.get("rationale") or "").strip()
        if rationale:
            day["rationale"] = rationale
        notes = override.get("constraint_notes")
        if isinstance(notes, list):
            cleaned_notes = [str(note).strip() for note in notes if str(note).strip()]
            if cleaned_notes:
                day["constraint_notes"] = cleaned_notes

    return pitch, updated_days


async def assemble_output(state: TripState) -> dict:
    destination_name, destination_state = _destination_details(state)
    hotel = state.get("hotel") or {}
    weather = state.get("weather") or {}
    days = _days_summary(state)
    day_plan_summary = _readable_days_summary(days)
    preference_constraints = state.get("preference_constraints", {})
    constraint_satisfaction = state.get("constraint_satisfaction", {})
    current_refinement = state.get("current_refinement", {})
    refinement_directives = state.get("refinement_directives", {})

    if days:
        prompt = (
            "You are finalizing a group trip. Using ONLY the confirmed itinerary stops listed below, "
            "write marketing copy AND per-day descriptions. This is critical: you must NEVER mention a "
            "place, activity, or venue that is not in that day's confirmed stops. Do not reference removed, "
            "dropped, or hypothetical places. If a refinement asked to add a place, only claim it is included "
            "when it actually appears in that day's confirmed stops.\n\n"
            "Return ONLY valid JSON (no markdown, no backticks) with this exact shape:\n"
            '{"pitch": "<4 paragraphs separated by blank lines>", '
            '"days": [{"day_number": int, "rationale": "<2-4 sentences>", "constraint_notes": ["<short note>", ...]}]}\n\n'
            "Rules:\n"
            "- pitch: exactly 4 paragraphs, minimum 80 words each. Paragraph 1: destination overview and why it "
            "fits the group. Paragraph 2: itinerary highlights naming specific days and ONLY confirmed stops. "
            "Paragraph 3: logistics (hotel, weather, what to expect). Paragraph 4: closing hype.\n"
            "- For every day, rationale explains why that day's confirmed stops fit the group; reference only "
            "those stops.\n"
            "- constraint_notes lists concrete constraints actually satisfied that day (food restrictions, pace, "
            "avoided categories, and any requested swap that is genuinely present in the confirmed stops).\n\n"
            f"Destination: {destination_name}, {destination_state}\n"
            f"Trip dates: {state['start_date']} to {state['end_date']} "
            f"({state.get('trip_duration_days')} days)\n"
            f"Hotel: {hotel.get('name')}, ${float(hotel.get('price_per_night_usd', 0.0)):.0f} "
            f"per night, ${float(hotel.get('total_price_usd', 0.0)):.0f} total\n"
            f"Weather summary: {weather.get('summary', 'Not available')}\n"
            f"Confirmed itinerary by day:\n{day_plan_summary}\n"
            f"Group size: {len(state['members'])}\n"
            f"Preference conflicts: {json.dumps(state.get('preference_conflicts', []))}\n"
            f"Natural-language preference constraints: {json.dumps(preference_constraints)}\n"
            f"Constraint satisfaction: {json.dumps(constraint_satisfaction)}\n"
            f"Current refinement: {json.dumps(current_refinement)}\n"
            f"Refinement directives: {json.dumps(refinement_directives)}\n"
            "If this is a refinement, reflect the updated itinerary while keeping unchanged facts stable."
        )
    else:
        prompt = (
            "Generate a shorter trip pitch based on destination and hotel only. "
            "Write 2-3 concise paragraphs that sell the trip to the group.\n\n"
            f"Destination: {destination_name}, {destination_state}\n"
            f"Trip dates: {state['start_date']} to {state['end_date']} "
            f"({state.get('trip_duration_days')} days)\n"
            f"Hotel: {hotel.get('name')}, ${float(hotel.get('price_per_night_usd', 0.0)):.0f} "
            f"per night, ${float(hotel.get('total_price_usd', 0.0)):.0f} total\n"
            f"Weather summary: {weather.get('summary', 'Not available')}\n"
            f"Group size: {len(state['members'])}\n"
            f"Preference conflicts: {json.dumps(state.get('preference_conflicts', []))}\n"
            f"Natural-language preference constraints: {json.dumps(preference_constraints)}\n"
            f"Constraint satisfaction: {json.dumps(constraint_satisfaction)}\n"
            f"Current refinement: {json.dumps(current_refinement)}\n"
            f"Refinement directives: {json.dumps(refinement_directives)}\n"
            "If this is a refinement, reflect the updated itinerary while keeping unchanged facts stable."
        )

    response = await get_llm().ainvoke(prompt)
    raw_text = _message_text(response)

    result: dict[str, Any] = {
        "decision_log": [
            DecisionLogEntry(
                node="assemble_output",
                decision="Trip pitch generated",
                reason=f"{len(state.get('days', []))} days, {len(state['members'])} members",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        ],
    }

    if days:
        pitch, updated_days = _apply_grounded_narrative(state, raw_text)
        result["trip_pitch"] = pitch
        if updated_days is not None:
            result["days"] = updated_days
    else:
        result["trip_pitch"] = raw_text.strip()

    return result


if __name__ == "__main__":
    class _FakeLLM:
        async def ainvoke(self, prompt: str) -> str:
            return (
                "New Orleans gives this group a trip with flavor, music, history, and enough walkable texture "
                "to make every day feel full.\n\n"
                "The itinerary balances the French Quarter, Garden District, live music, food stops, and local "
                "urban exploring without turning the trip into a checklist.\n\n"
                "Hotel Monteleone keeps the group close to the action, while warm and mostly dry weather makes "
                "the outdoor wandering realistic.\n\n"
                "This is the kind of long weekend that should feel easy to say yes to: memorable meals, late "
                "nights if people want them, and plenty to talk about afterward."
            )

    def _fake_get_llm() -> _FakeLLM:
        return _FakeLLM()

    get_llm = _fake_get_llm
    mock_state: TripState = {
        "trip_id": "mock",
        "members": [
            {
                "member_id": "alice",
                "name": "Alice",
                "origin_city": "CHI",
                "budget_usd": 1200.0,
                "food_restrictions": [],
                "preference_vector": {
                    "outdoor": 0.4,
                    "food": 0.9,
                    "nightlife": 0.7,
                    "urban": 0.8,
                    "shopping": 0.2,
                },
                "is_leader": True,
            },
            {
                "member_id": "bob",
                "name": "Bob",
                "origin_city": "ATL",
                "budget_usd": 950.0,
                "food_restrictions": ["shellfish"],
                "preference_vector": {
                    "outdoor": 0.3,
                    "food": 0.8,
                    "nightlife": 0.4,
                    "urban": 0.9,
                    "shopping": 0.3,
                },
                "is_leader": False,
            },
            {
                "member_id": "carla",
                "name": "Carla",
                "origin_city": "DEN",
                "budget_usd": 1100.0,
                "food_restrictions": [],
                "preference_vector": {
                    "outdoor": 0.6,
                    "food": 0.7,
                    "nightlife": 0.9,
                    "urban": 0.5,
                    "shopping": 0.4,
                },
                "is_leader": False,
            },
        ],
        "start_date": "2026-06-01",
        "end_date": "2026-06-04",
        "trip_duration_days": 3,
        "selected_destination": "New Orleans",
        "candidate_destinations": [{"name": "New Orleans", "state": "LA"}],
        "hotel": {
            "name": "Hotel Monteleone",
            "price_per_night_usd": 180,
            "total_price_usd": 540,
            "rating": 4.5,
            "is_estimated": False,
        },
        "weather": {"summary": "Warm (28°C avg), mostly dry"},
        "days": [
            {
                "day_number": 1,
                "date": "2026-06-01",
                "neighborhood": "French Quarter",
                "activities": [
                    {"name": "Jackson Square"},
                    {"name": "French Market"},
                    {"name": "Preservation Hall"},
                ],
                "meals": ["Cafe du Monde", "Napoleon House", "GW Fins"],
                "routes": [],
                "estimated_day_cost_usd": 120.0,
            },
            {
                "day_number": 2,
                "date": "2026-06-02",
                "neighborhood": "Garden District and Magazine Street",
                "activities": [
                    {"name": "Lafayette Cemetery No. 1"},
                    {"name": "Garden District walking tour"},
                    {"name": "Magazine Street shops"},
                ],
                "meals": ["Surrey's Cafe", "Commander's Palace", "Cochon"],
                "routes": [],
                "estimated_day_cost_usd": 150.0,
            },
            {
                "day_number": 3,
                "date": "2026-06-03",
                "neighborhood": "Bywater and Marigny",
                "activities": [
                    {"name": "Crescent Park"},
                    {"name": "Studio BE"},
                    {"name": "Frenchmen Street live music"},
                ],
                "meals": ["Elizabeth's", "Bacchanal", "Dat Dog"],
                "routes": [],
                "estimated_day_cost_usd": 130.0,
            },
        ],
        "preference_conflicts": [
            "nightlife conflict: Bob=0.4, Carla=0.9",
            "outdoor conflict: Alice=0.4, Carla=0.6",
        ],
    }  # type: ignore[typeddict-item]

    print(asyncio.run(assemble_output(mock_state)))
