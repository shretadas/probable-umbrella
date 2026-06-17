from __future__ import annotations

import json
import urllib.error
import urllib.request

import requests


RIGID_SYSTEM_PROMPT = """You are a clinical diabetes prevention assistant operating under WHO 2023 Physical Activity Guidelines and ADA Standards of Care 2024. You must never give vague advice. Every recommendation must be a specific, measurable, time-bound action. Return ONLY a valid JSON object with this exact schema:
{
  \"recommendations\": [
    {
      \"action\": \"<specific action verb + object>\",
      \"quantity\": \"<exact number + unit>\",
      \"timing\": \"<exact time of day or frequency>\",
      \"who_ada_reference\": \"<specific guideline name and section>\",
      \"expected_risk_impact_percent\": <float between 0.5 and 8.0>,
      \"priority\": <integer 1-5 where 1 is highest>
    }
  ],
  \"cheat_day_verdict\": \"<LOCKED or UNLOCKED>\",
  \"cheat_day_instruction\": \"<specific instructions if unlocked, else motivation message>\",
  \"weekly_focus\": \"<single most impactful change this week>\"
}
Return exactly 5 recommendations. No extra keys. No markdown. Pure JSON only."""

STRICT_CLINICAL_SYSTEM_PROMPT = """You are a clinical assistant. Return ONLY this JSON, no other text:

{
    "recommendations": [
                {
                        "action": "specific action",
                        "quantity": "number and unit",
                        "timing": "time of day",
                        "who_ada_reference": "ADA 2024 Section X",
                        "expected_risk_impact_percent": 2.5,
                        "priority": 1
                }
    ],
        "cheat_day_verdict": "LOCKED",
        "cheat_day_instruction": "specific instruction",
        "weekly_focus": "most important change"
}

Return only a JSON object. No markdown. No explanation.
Use exactly this structure with exactly 5 items in recommendations:
{
    "recommendations": [
        {
            "action": "specific action",
            "quantity": "number and unit",
            "timing": "time of day",
            "who_ada_reference": "ADA 2024 Section X",
            "expected_risk_impact_percent": 2.5,
            "priority": 1
        }
    ],
    "cheat_day_verdict": "LOCKED",
    "cheat_day_instruction": "specific instruction",
    "weekly_focus": "most important change"
}"""

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:1b"


def _validate_schema(parsed: dict) -> None:
    required_top = {"recommendations", "cheat_day_verdict", "cheat_day_instruction", "weekly_focus"}
    if not required_top.issubset(parsed.keys()):
        raise ValueError("invalid_schema_keys")

    recs = parsed.get("recommendations", [])
    if not isinstance(recs, list):
        raise ValueError("invalid_recommendation_type")
    if len(recs) == 0:
        raise ValueError("No recommendations returned")
    parsed["recommendations"] = recs[:5]
    recs = parsed["recommendations"]

    required_rec = {
        "action",
        "quantity",
        "timing",
        "who_ada_reference",
        "expected_risk_impact_percent",
        "priority",
    }
    for rec in recs:
        if not required_rec.issubset(rec.keys()):
            raise ValueError("missing_recommendation_keys")


def _default_request(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_recommendations_groq(
    patient_context: dict,
    api_key: str | None,
    cached_payload: dict,
    request_fn=None,
) -> tuple[dict, bool]:
    """Returns (payload, used_cache)."""
    if request_fn is None:
        request_fn = _default_request

    try:
        if not api_key:
            raise RuntimeError("missing_api_key")

        payload = {
            "model": "llama-3.1-8b-instant",
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": RIGID_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(patient_context)},
            ],
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = request_fn("https://api.groq.com/openai/v1/chat/completions", payload, headers)
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        _validate_schema(parsed)

        return parsed, False
    except (KeyError, ValueError, TypeError, urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
        error_summary = type(exc).__name__
        if isinstance(exc, urllib.error.HTTPError):
            error_summary = f"HTTP {exc.code}"
            try:
                body = exc.read().decode("utf-8", errors="replace").strip()
                if body:
                    error_summary = f"{error_summary}: {body[:200]}"
            except Exception:
                pass
        fallback = {
            "recommendations": cached_payload.get("recommendations", []),
            "cheat_day_verdict": "UNLOCKED" if cached_payload.get("cheat_day", {}).get("unlocked", False) else "LOCKED",
            "cheat_day_instruction": "Using cached recommendations from last valid run.",
            "weekly_focus": cached_payload.get("dqn_action", "Focus on consistency for this week."),
            "_error_summary": error_summary,
        }
        return fallback, True


def generate_recommendations_ollama(
    patient_context: dict,
    cached_payload: dict,
    request_fn=None,
) -> tuple[dict, bool]:
    """Returns (payload, used_cache) using a local Ollama model."""
    if request_fn is None:
        request_fn = requests.post

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.3},
            "messages": [
                {"role": "system", "content": STRICT_CLINICAL_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(patient_context)},
            ],
        }

        resp = request_fn(OLLAMA_URL, json=payload, timeout=90)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        parsed = json.loads(content)
        _validate_schema(parsed)
        return parsed, False
    except Exception as exc:
        error_summary = type(exc).__name__
        message = str(exc).strip()
        if message:
            error_summary = f"{error_summary}: {message[:220]}"
        fallback = {
            "recommendations": cached_payload.get("recommendations", []),
            "cheat_day_verdict": "UNLOCKED" if cached_payload.get("cheat_day", {}).get("unlocked", False) else "LOCKED",
            "cheat_day_instruction": "Using cached recommendations from last valid run.",
            "weekly_focus": cached_payload.get("dqn_action", "Focus on consistency for this week."),
            "_error_summary": error_summary,
        }
        return fallback, True
