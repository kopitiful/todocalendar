"""Zero-UI Tages-Copilot – FastAPI Backend"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import db
from parser import parse_user_input

app = FastAPI()
db.init()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


class InputPayload(BaseModel):
    text: str


@app.post("/parse")
async def parse(payload: InputPayload):
    try:
        result = parse_user_input(payload.text, client=_client)
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

    if result.input_type == "event" and result.event:
        entry_id = db.save_event(result.event)
        e = result.event
        return {
            "type": "event",
            "id":   entry_id,
            "title": e.title,
            "detail": e.start_time.strftime("%d.%m.%Y · %H:%M Uhr"),
        }

    if result.input_type == "task" and result.task:
        entry_id = db.save_task(result.task)
        t = result.task
        prio = {"high": "hoch", "medium": "mittel", "low": "niedrig"}[t.priority]
        detail = f"Priorität: {prio}"
        if t.due_date:
            detail += f" · bis {t.due_date.strftime('%d.%m.%Y')}"
        return {
            "type": "task",
            "id":   entry_id,
            "title": t.title,
            "detail": detail,
        }

    if result.input_type == "query" and result.query_date:
        start = result.query_date
        end   = result.query_end_date or start
        events, tasks = db.get_for_range(start, end)

        start_d = date.fromisoformat(start)
        end_d   = date.fromisoformat(end)
        label   = start_d.strftime("%d.%m.%Y") if start == end else \
                  f"{start_d.strftime('%d.%m.')} – {end_d.strftime('%d.%m.%Y')}"

        return {
            "type":   "query",
            "label":  label,
            "events": [{"id": e["id"], "title": e["title"], "time": e["start_time"].strftime("%H:%M")} for e in events],
            "tasks":  [{"id": t["id"], "title": t["title"], "priority": t["priority"], "postpone_count": t["postpone_count"]} for t in tasks],
        }

    return JSONResponse({"error": "Konnte nicht verarbeitet werden."}, status_code=422)


@app.patch("/entry/task/{task_id}/postpone")
async def postpone(task_id: int):
    count = db.postpone_task(task_id)
    if count < 0:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return {"count": count, "locked": count >= 3}


@app.delete("/entry/{dtype}/{entry_id}")
async def delete_entry(dtype: str, entry_id: int):
    if dtype not in ("event", "task"):
        raise HTTPException(status_code=400, detail="Unbekannter Typ")
    db.soft_delete(dtype, entry_id)
    return {"ok": True}


@app.get("/today")
async def today():
    from datetime import date
    today_str = date.today().isoformat()
    events, tasks = db.get_for_range(today_str, today_str)
    return {
        "events": [{"id": e["id"], "title": e["title"], "time": e["start_time"].strftime("%H:%M")} for e in events],
        "tasks":  [{"id": t["id"], "title": t["title"], "priority": t["priority"], "postpone_count": t["postpone_count"]} for t in tasks],
    }


@app.get("/reminders")
async def reminders():
    items = db.get_upcoming_reminders(within_minutes=30)
    return {"reminders": [{"title": r["title"], "time": r["start_time"].strftime("%H:%M")} for r in items]}


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(Path("index.html").read_text(encoding="utf-8"))
