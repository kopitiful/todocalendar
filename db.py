"""Lokale SQLite-Datenbank."""

import sqlite3
from pathlib import Path

from models import EventCreate, TaskCreate

DB = Path("copilot.db")


def init():
    with sqlite3.connect(DB) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT,
                start_time  TEXT NOT NULL,
                end_time    TEXT,
                deleted_at  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT NOT NULL,
                description   TEXT,
                priority      TEXT NOT NULL,
                due_date      TEXT,
                estimated_min INTEGER,
                status        TEXT NOT NULL DEFAULT 'pending',
                deleted_at    TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Migration: neue Spalten für bestehende DBs nachrüsten
        for tbl in ("events", "tasks"):
            try:
                c.execute(f"ALTER TABLE {tbl} ADD COLUMN deleted_at TEXT")
            except Exception:
                pass
        try:
            c.execute("ALTER TABLE tasks ADD COLUMN postpone_count INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass


def save_event(e: EventCreate) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO events (title, description, start_time, end_time) VALUES (?,?,?,?)",
            (e.title, e.description,
             e.start_time.isoformat(),
             e.end_time.isoformat() if e.end_time else None)
        )
        return cur.lastrowid


def save_task(t: TaskCreate) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO tasks (title, description, priority, due_date, estimated_min) VALUES (?,?,?,?,?)",
            (t.title, t.description, t.priority,
             t.due_date.isoformat() if t.due_date else None,
             t.estimated_min)
        )
        return cur.lastrowid


def soft_delete(dtype: str, entry_id: int):
    """Setzt deleted_at – Eintrag bleibt in der DB, wird aber nicht mehr angezeigt."""
    tbl = "events" if dtype == "event" else "tasks"
    with sqlite3.connect(DB) as c:
        c.execute(
            f"UPDATE {tbl} SET deleted_at = datetime('now') WHERE id = ?",
            (entry_id,)
        )


def get_for_range(start: str, end: str):
    with sqlite3.connect(DB) as c:
        c.row_factory = sqlite3.Row
        events = c.execute(
            """SELECT * FROM events
               WHERE DATE(start_time) BETWEEN ? AND ?
                 AND deleted_at IS NULL
               ORDER BY start_time""",
            (start, end)
        ).fetchall()
        tasks = c.execute(
            """SELECT * FROM tasks
               WHERE status = 'pending'
                 AND deleted_at IS NULL
                 AND (due_date BETWEEN ? AND ? OR due_date IS NULL)
               ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END""",
            (start, end)
        ).fetchall()
    return [dict(r) for r in events], [dict(r) for r in tasks]


def postpone_task(task_id: int) -> int:
    """Schiebt Aufgabe um 1 Tag vor. Gibt neuen postpone_count zurück, -1 wenn nicht gefunden."""
    from datetime import date, timedelta
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT due_date, postpone_count FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not row:
            return -1
        due_str, count = row
        if count >= 3:
            return count  # gesperrt
        base     = date.fromisoformat(due_str) if due_str else date.today()
        new_date = (base + timedelta(days=1)).isoformat()
        new_count = count + 1
        c.execute(
            "UPDATE tasks SET due_date = ?, postpone_count = ? WHERE id = ?",
            (new_date, new_count, task_id)
        )
        return new_count


def get_upcoming_reminders(within_minutes: int = 30):
    with sqlite3.connect(DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            """SELECT title, start_time FROM events
               WHERE deleted_at IS NULL
                 AND datetime(start_time) BETWEEN datetime('now', 'localtime')
                 AND datetime('now', 'localtime', ? || ' minutes')
               ORDER BY start_time""",
            (str(within_minutes),)
        ).fetchall()
    return [dict(r) for r in rows]
