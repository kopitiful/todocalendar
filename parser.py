"""Natürlichsprachliche Eingaben → strukturiertes JSON via Claude API."""

from __future__ import annotations

import json
import os
from datetime import datetime

import anthropic

from models import EventCreate, ParsedInput, TaskCreate

SYSTEM_PROMPT = """\
Du bist der Parser des Zero-UI Tages-Copiloten.
Analysiere die Nutzereingabe und klassifiziere sie als genau einen dieser Typen:

• event  → fixer Termin mit Datum UND Uhrzeit ("Meeting um 14 Uhr am 24.12.")
• task   → flexible Aufgabe ohne feste Uhrzeit ("Steuererklärung, hohe Prio")
• query  → Abfrage nach Einträgen für ein Datum ("Was habe ich am Montag?", "Zeig mir den 24.12.")

Antworte ausschließlich als valides JSON – kein Text davor oder danach.
Heute ist: {today}
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "input_type": {
            "type": "string",
            "enum": ["event", "task", "query"]
        },
        "event": {
            "type": "object",
            "properties": {
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "start_time":  {"type": "string", "description": "ISO-8601 datetime"},
                "end_time":    {"type": "string", "description": "ISO-8601 datetime oder leer"}
            },
            "required": ["title", "start_time", "description", "end_time"],
            "additionalProperties": False
        },
        "task": {
            "type": "object",
            "properties": {
                "title":         {"type": "string"},
                "description":   {"type": "string"},
                "priority":      {"type": "string", "enum": ["high", "medium", "low"]},
                "due_date":      {"type": "string", "description": "ISO-8601 date oder leer"},
                "estimated_min": {"type": "integer"}
            },
            "required": ["title", "priority", "description", "due_date", "estimated_min"],
            "additionalProperties": False
        },
        "query": {
            "type": "object",
            "properties": {
                "date":     {"type": "string", "description": "ISO-8601 date YYYY-MM-DD – Startdatum"},
                "end_date": {"type": "string", "description": "ISO-8601 date YYYY-MM-DD – Enddatum bei Zeitraum-Abfragen, sonst leer"}
            },
            "required": ["date", "end_date"],
            "additionalProperties": False
        }
    },
    "required": ["input_type"],
    "additionalProperties": False
}


def parse_user_input(text: str, *, client: anthropic.Anthropic | None = None) -> ParsedInput:
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system = SYSTEM_PROMPT.format(today=datetime.now().strftime("%d.%m.%Y"))

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        messages=[{"role": "user", "content": text}],
    )

    raw = next(b.text for b in response.content if b.type == "text")
    data = json.loads(raw)

    if data["input_type"] == "event" and data.get("event"):
        e = data["event"]
        return ParsedInput(
            input_type="event",
            event=EventCreate(
                title=e["title"],
                description=e["description"] or None,
                start_time=e["start_time"],
                end_time=e["end_time"] or None,
            )
        )

    if data["input_type"] == "task" and data.get("task"):
        t = data["task"]
        return ParsedInput(
            input_type="task",
            task=TaskCreate(
                title=t["title"],
                description=t["description"] or None,
                priority=t["priority"],
                due_date=t["due_date"] or None,
                estimated_min=t["estimated_min"] or None,
            )
        )

    if data["input_type"] == "query" and data.get("query"):
        q = data["query"]
        return ParsedInput(
            input_type="query",
            query_date=q["date"],
            query_end_date=q["end_date"] or None,
        )

    raise ValueError(f"Unerwartete Claude-Antwort: {data}")
