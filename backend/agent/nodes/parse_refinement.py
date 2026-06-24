"""Parse and apply natural-language post-generation refinements."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class UnsupportedRefinement(ValueError):
    """Raised when a request should create a new trip instead of refining one."""

    def __init__(self, message: str, code: str = "unsupported_refinement") -> None:
        super().__init__(message)
        self.code = code


CATEGORY_ALIASES = {
    "outdoor": (
        "outdoor",
        "outdoors",
        "outside",
        "park",
        "parks",
        "hiking",
        "trail",
        "trails",
        "nature",
        "scenic",
    ),
    "urban": ("museum", "museums", "gallery", "galleries", "architecture", "downtown", "landmark"),
    "food": ("food", "restaurant", "restaurants", "cafe", "cafes", "dining"),
    "nightlife": ("nightlife", "bar", "bars", "club", "clubs", "live music"),
    "shopping": ("shopping", "shops", "market", "markets", "boutique", "boutiques"),
}

CUISINES = (
    "italian",
    "mexican",
    "thai",
    "japanese",
    "chinese",
    "korean",
    "indian",
    "vegan",
    "vegetarian",
    "seafood",
    "bbq",
    "barbecue",
    "brunch",
    "pizza",
    "sushi",
)

CHEAPER_TERMS = (
    "cheaper",
    "less expensive",
    "lower cost",
    "lower-cost",
    "budget",
    "save money",
    "affordable",
    "inexpensive",
    "cut cost",
    "cut costs",
)

PITCH_TERMS = ("pitch", "summary", "description", "copy", "wording", "rewrite", "tone")


def parse_refinement_message(message: str) -> dict:
    """Return a normalized v1 refinement request."""
    original = str(message or "").strip()
    if not original:
        raise UnsupportedRefinement("Refinement message cannot be empty.", code="empty_refinement")

    text = _normalize(original)
    _reject_unsupported_scope(text)

    day_number = _extract_day_number(text)
    category = _extract_category(text)
    cuisine = _extract_cuisine(text)

    if _contains_any(text, CHEAPER_TERMS):
        target = "hotel" if _contains_any(text, ("hotel", "lodging", "stay")) else "day" if day_number else "trip"
        intent = "cheaper_day" if target == "day" else "cheaper_hotel" if target == "hotel" else "cheaper_trip"
        rerun_from = "search_hotel" if target == "day" else "budget_analysis"
        return _result(
            original,
            intent,
            rerun_from,
            day_number=day_number,
            target=target,
            directives={
                "cost_sensitivity": "lower_cost",
                "preserve_destination": True,
                "preserve_dates": True,
            },
        )

    activity_to_replace, activity_to_add = _extract_swap(text)
    if activity_to_add and not _is_specific_place(activity_to_add):
        # e.g. "swap the museum for something outdoors" is a category swap, not a
        # request for a specific venue, so let the category-fetch path handle it.
        activity_to_add = None
    if activity_to_replace or activity_to_add:
        preferred_categories = [category] if category else []
        directives: dict[str, Any] = {
            "preferred_categories": preferred_categories,
            "preserve_unaffected_days": True,
        }
        if activity_to_replace:
            directives["avoid_terms"] = [activity_to_replace]
        if activity_to_add:
            directives["add_place"] = activity_to_add
        return _result(
            original,
            "swap_activity",
            "search_hotel",
            day_number=day_number,
            target="itinerary",
            directives=directives,
            requires_activity_category=category,
            requires_named_place=activity_to_add,
        )

    activity_to_add = _extract_activity_to_add(text)
    if activity_to_add and _is_specific_place(activity_to_add):
        return _result(
            original,
            "add_activity",
            "search_hotel",
            day_number=day_number,
            target="itinerary",
            directives={
                "add_place": activity_to_add,
                "preserve_unaffected_days": True,
            },
            requires_named_place=activity_to_add,
        )

    if _contains_any(text, ("avoid", "remove", "skip", "no more", "without")):
        avoid_term = _extract_avoid_term(text) or category
        if avoid_term:
            return _result(
                original,
                "avoid_activity",
                "search_hotel",
                day_number=day_number,
                target="itinerary",
                directives={
                    "avoid_terms": [avoid_term],
                    "preserve_unaffected_days": True,
                },
            )

    pace = _extract_pace(text)
    if pace:
        return _result(
            original,
            "change_pace",
            "search_hotel",
            day_number=day_number,
            target="itinerary",
            directives={
                "pace": pace,
                "preserve_unaffected_days": True,
            },
        )

    if cuisine or _contains_any(text, ("meal", "meals", "dinner", "lunch", "breakfast", "restaurant")):
        return _result(
            original,
            "meal_requirement",
            "search_hotel",
            day_number=day_number,
            target="meals",
            directives={
                "meal": _extract_meal(text),
                "cuisine": cuisine,
                "preserve_unaffected_days": True,
            },
        )

    if category:
        return _result(
            original,
            "prefer_activity_category",
            "search_hotel",
            day_number=day_number,
            target="itinerary",
            directives={
                "preferred_categories": [category],
                "preserve_unaffected_days": True,
            },
            requires_activity_category=category,
        )

    if _contains_any(text, PITCH_TERMS):
        return _result(
            original,
            "pitch_update",
            "compute_fairness",
            day_number=day_number,
            target="pitch",
            directives={"pitch_instruction": original},
        )

    raise UnsupportedRefinement(
        "V1 refinements support cheaper plans, adding a specific place, activity swaps, "
        "outdoor/category preferences, pace changes, meal edits, and pitch wording.",
    )


def activity_category_to_fetch(parsed: dict, state: dict) -> str | None:
    """Return a category that needs fresh activity supply, if any."""
    category = parsed.get("requires_activity_category")
    if not category:
        return None

    existing = [
        activity
        for activity in state.get("activities", [])
        if str(activity.get("category", "")).lower() == str(category).lower()
    ]
    if existing:
        return None
    return str(category)


def named_place_to_fetch(parsed: dict, state: dict) -> str | None:
    """Return a specific place name (e.g. "Sears Tower") that must be fetched and added.

    Returns ``None`` when no named place was requested or when the requested place is
    already present in the activity pool, so refinement swaps actually pull in the exact
    place the user asked for instead of silently dropping it.
    """
    name = parsed.get("requires_named_place")
    normalized = _activity_key({"name": name}) if name else ""
    if not normalized:
        return None

    for activity in state.get("activities", []):
        existing = _activity_key({"name": activity.get("name", "")})
        existing_name = existing.split(":", 1)[-1].strip()
        target_name = normalized.split(":", 1)[-1].strip()
        if existing_name and target_name and (
            existing_name == target_name
            or target_name in existing_name
            or existing_name in target_name
        ):
            return None
    return str(name)


def dedupe_new_activities(existing: list[dict], candidates: list[dict]) -> list[dict]:
    """Keep only candidate activities that are not already in state."""
    seen = {_activity_key(activity) for activity in existing}
    deduped = []
    for activity in candidates:
        key = _activity_key(activity)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(activity)
    return deduped


def build_refinement_state_patch(
    state: dict,
    parsed: dict,
    extra_activities: list[dict] | None = None,
) -> tuple[dict, str]:
    """Build a LangGraph state patch and the node to mark as completed."""
    directives = deepcopy(parsed.get("directives", {}))
    current_refinement = {
        "message": parsed.get("message", ""),
        "intent": parsed.get("intent"),
        "target": parsed.get("target"),
        "target_day": parsed.get("day_number"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    history_entry = {
        **current_refinement,
        "summary": _summary_for(parsed),
    }
    history = list(state.get("refinement_history", [])) + [history_entry]

    patch: dict[str, Any] = {
        "current_refinement": current_refinement,
        "refinement_directives": directives,
        "refinement_history": history,
        "error": None,
    }

    intent = parsed.get("intent")
    if intent in {"cheaper_hotel", "cheaper_trip"}:
        patch.update(_budget_patch(state))

    if intent in {"swap_activity", "avoid_activity", "prefer_activity_category", "change_pace", "meal_requirement"}:
        patch["preference_constraints"] = _patched_constraints(state.get("preference_constraints", {}), parsed)

    if intent in {"cheaper_day", "swap_activity", "add_activity", "avoid_activity", "prefer_activity_category", "change_pace", "meal_requirement"}:
        patch["constraint_satisfaction"] = {"passed": None, "satisfied": [], "unmet": [], "warnings": []}

    if extra_activities:
        patch["activities"] = extra_activities
        categories = list(state.get("active_tool_categories", []))
        for activity in extra_activities:
            category = str(activity.get("category", "")).strip()
            if category and category not in categories:
                categories.append(category)
        patch["active_tool_categories"] = categories

    return patch, str(parsed.get("rerun_from") or "search_hotel")


def _result(
    message: str,
    intent: str,
    rerun_from: str,
    *,
    day_number: int | None,
    target: str,
    directives: dict,
    requires_activity_category: str | None = None,
    requires_named_place: str | None = None,
) -> dict:
    return {
        "message": message,
        "intent": intent,
        "target": target,
        "day_number": day_number,
        "directives": {
            "summary": message,
            "target_day": day_number,
            **directives,
        },
        "rerun_from": rerun_from,
        "requires_activity_category": requires_activity_category,
        "requires_named_place": requires_named_place,
    }


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip().lower())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _reject_unsupported_scope(text: str) -> None:
    if re.search(r"\b(add|remove|drop|invite)\b.{0,30}\b(member|traveler|person|friend|guest)\b", text):
        raise UnsupportedRefinement("Member changes should create a new trip.", code="unsupported_member_change")
    if re.search(r"\b(change|move|shift|reschedule|extend|shorten)\b.{0,40}\b(date|dates|weekend|month|start|end)\b", text):
        raise UnsupportedRefinement("Date changes should create a new trip.", code="unsupported_date_change")
    if (
        re.search(r"\b(change|switch|swap|move)\b.{0,35}\b(destination|city|location)\b", text)
        or re.search(r"\b(destination|city|location)\b.{0,35}\b(change|switch|swap|move)\b", text)
        or re.search(r"\b(go|travel|fly)\s+to\b", text)
    ):
        raise UnsupportedRefinement("Destination changes should create a new trip.", code="unsupported_destination_change")


def _extract_day_number(text: str) -> int | None:
    match = re.search(r"\bday\s*(\d{1,2})\b", text)
    return int(match.group(1)) if match else None


def _extract_category(text: str) -> str | None:
    for category, aliases in CATEGORY_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            return category
    return None


def _extract_cuisine(text: str) -> str | None:
    for cuisine in CUISINES:
        if re.search(rf"\b{re.escape(cuisine)}\b", text):
            return "barbecue" if cuisine == "bbq" else cuisine
    return None


def _extract_swap(text: str) -> tuple[str | None, str | None]:
    """Return (place_to_remove, place_to_add) for swap-style refinements.

    Handles "swap/replace/switch A for/with B" and "B instead of A" so the specific
    requested place is captured (not just the one being removed).
    """
    stop = (
        r"(?=\s+(?:on|in|for|if|please|during|this|next|that|day|sometime|someday|somewhere)\b|[.,!?]|$)"
    )

    match = re.search(
        r"\b(?:swap|replace|switch)\s+(?:out\s+)?(?:the\s+|a\s+|an\s+)?"
        r"(?P<remove>[a-z0-9 '&-]+?)\s+(?:for|with|to)\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<add>[a-z0-9 '&-]+?)" + stop,
        text,
    )
    if match:
        return _clean_term(match.group("remove")), _clean_place_name(match.group("add"))

    match = re.search(
        r"(?P<add>[a-z0-9 '&-]+?)\s+instead\s+of\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<remove>[a-z0-9 '&-]+?)" + stop,
        text,
    )
    if match:
        add_raw = match.group("add")
        # The "add" side often carries filler like "I want to visit X on day 1"; isolate
        # the actual place using the add-verb extractor and fall back to a plain clean.
        add_place = _extract_activity_to_add(add_raw) or _clean_place_name(add_raw)
        return _clean_term(match.group("remove")), add_place

    return None, None


_GENERIC_PLACE_WORDS = {
    "something",
    "anything",
    "somewhere",
    "anywhere",
    "else",
    "different",
    "more",
    "some",
    "any",
    "few",
    "another",
    "activity",
    "activities",
    "place",
    "places",
    "option",
    "options",
    "spot",
    "spots",
    "thing",
    "things",
    "fun",
    "outdoors",
}


def _is_specific_place(name: str) -> bool:
    """True only when the phrase names a concrete venue rather than a vague category.

    "something outdoors" / "a park" are generic (fetch by category), while "Sears Tower"
    or "Millennium Park" are specific (fetch the exact place by name).
    """
    words = [word for word in re.split(r"\s+", str(name or "").lower()) if word]
    if not words:
        return False
    if any(word in _GENERIC_PLACE_WORDS for word in words):
        return False

    generic = set(_GENERIC_PLACE_WORDS)
    for aliases in CATEGORY_ALIASES.values():
        generic.update(aliases)
    return not all(word in generic for word in words)


def _extract_activity_to_add(text: str) -> str | None:
    """Capture a specific place to ADD from phrasings like "visit/add/include X".

    Stops the place capture at trailing scheduling/filler words ("on day 1", "if you can
    accommodate it", etc.) so only the venue name is returned.
    """
    match = re.search(
        r"\b(?:add|include|visit|see|go\s+to|stop\s+by|check\s+out)\s+"
        r"(?:the\s+|a\s+|an\s+)?(?P<place>[a-z0-9 '&-]+?)"
        r"(?=\s+(?:on|in|for|to|instead|if|please|during|this|next|that|day|sometime|someday|somewhere)\b|[.,!?]|$)",
        text,
    )
    if not match:
        return None
    return _clean_place_name(match.group("place"))


def _clean_place_name(term: str) -> str:
    """Clean a proper-noun place name while stripping leading verbs/articles."""
    cleaned = str(term or "").strip()
    cleaned = re.sub(
        r"^(?:please\s+|just\s+)?(?:visit|go\s+to|go|see|do|add|include|put|have|book|check\s+out)\s+",
        "",
        cleaned,
    )
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,'\"")
    return cleaned


def _extract_avoid_term(text: str) -> str | None:
    match = re.search(r"\b(?:avoid|remove|skip|without)\s+(?:the\s+|a\s+|an\s+)?(?P<term>[a-z0-9 '&-]+)", text)
    if not match:
        return None
    return _clean_term(match.group("term"))


def _clean_term(term: str) -> str:
    cleaned = re.sub(r"\b(on|for|from|in|day|the|a|an|something|anything)\b", " ", term)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,'\"")
    return cleaned


def _extract_pace(text: str) -> str | None:
    if _contains_any(text, ("relaxed", "slower", "slow pace", "chill", "less packed", "fewer activities")):
        return "relaxed"
    if _contains_any(text, ("packed", "busier", "more activities", "fuller", "faster pace")):
        return "packed"
    return None


def _extract_meal(text: str) -> str | None:
    for meal in ("breakfast", "lunch", "dinner", "brunch"):
        if re.search(rf"\b{meal}\b", text):
            return meal
    return None


def _budget_patch(state: dict) -> dict:
    hotel = state.get("hotel") or {}
    group_budget = sum(float(member.get("budget_usd", 0.0)) for member in state.get("members", []))
    current_total = float(hotel.get("total_price_usd") or 0.0)
    ceiling = current_total * 0.85 if current_total else group_budget * 0.25
    existing_ceiling = state.get("budget_ceiling_hotel_usd")
    if existing_ceiling:
        ceiling = min(float(existing_ceiling), ceiling)
    return {
        "budget_status": "moderate",
        "budget_ceiling_hotel_usd": round(ceiling, 2),
    }


def _patched_constraints(constraints: dict, parsed: dict) -> dict:
    patched = deepcopy(constraints or {})
    patched.setdefault("hard_constraints", [])
    patched.setdefault("soft_preferences", [])
    patched.setdefault("schedule", {})
    patched.setdefault("activity_filters", {})
    patched["activity_filters"].setdefault("avoid_tags", [])
    patched["activity_filters"].setdefault("prefer_tags", [])
    patched["activity_filters"].setdefault("required_tags", [])
    patched.setdefault("meal_requirements", {})
    patched["meal_requirements"].setdefault("must_include", [])
    patched["meal_requirements"].setdefault("avoid_terms", [])

    directives = parsed.get("directives", {})
    for term in directives.get("avoid_terms", []) or []:
        _append_unique(patched["activity_filters"]["avoid_tags"], term)
        _append_hard_avoid(patched, term, parsed.get("message", ""))

    for category in directives.get("preferred_categories", []) or []:
        _append_unique(patched["activity_filters"]["prefer_tags"], category)

    if directives.get("pace"):
        patched["schedule"]["pace"] = directives["pace"]
        patched["soft_preferences"].append(
            {
                "source": "refinement",
                "type": "pace",
                "target": directives["pace"],
                "text": parsed.get("message", ""),
            }
        )

    cuisine = directives.get("cuisine")
    if cuisine:
        patched["meal_requirements"]["must_include"].append(
            {
                "cuisine": cuisine,
                "min_count": 1,
                "source": "refinement",
                "meal": directives.get("meal"),
            }
        )

    for key in ("avoid_tags", "prefer_tags", "required_tags"):
        patched["activity_filters"][key] = _dedupe_strings(patched["activity_filters"][key])
    return patched


def _append_unique(values: list, value: Any) -> None:
    clean = str(value or "").strip().lower()
    if clean and clean not in {str(item).lower() for item in values}:
        values.append(clean)


def _append_hard_avoid(constraints: dict, term: str, message: str) -> None:
    constraint = {
        "source": "refinement",
        "type": "avoid",
        "applies_to": "activities",
        "target": term,
        "terms": [term],
        "text": message,
    }
    key = (constraint["source"], constraint["type"], constraint["target"])
    existing = {
        (item.get("source"), item.get("type"), item.get("target"))
        for item in constraints.get("hard_constraints", [])
        if isinstance(item, dict)
    }
    if key not in existing:
        constraints["hard_constraints"].append(constraint)


def _dedupe_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value or "").strip().lower()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _activity_key(activity: dict) -> str:
    place_id = str(activity.get("place_id", "")).strip().lower()
    if place_id:
        return f"id:{place_id}"
    name = re.sub(r"[^a-z0-9]+", " ", str(activity.get("name", "")).lower()).strip()
    return f"name:{name}" if name else ""


def _summary_for(parsed: dict) -> str:
    day = parsed.get("day_number")
    day_part = f" Day {day}." if day else ""
    return f"{parsed.get('intent', 'refinement').replace('_', ' ').title()}.{day_part}".strip()
