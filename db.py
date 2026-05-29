"""PostgreSQL-Datenbankschicht via Supabase."""

import os
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

from models import EventCreate, TaskCreate


def _conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init():
    pass  # Schema wird einmalig in Supabase angelegt


def save_event(e: EventCreate) -> int:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO events (title, description, start_time, end_time) VALUES (%s,%s,%s,%s) RETURNING id",
                (e.title, e.description,
                 e.start_time.isoformat(),
                 e.end_time.isoformat() if e.end_time else None)
            )
            return cur.fetchone()[0]


def save_task(t: TaskCreate) -> int:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, description, priority, due_date, estimated_min) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (t.title, t.description, t.priority,
                 t.due_date.isoformat() if t.due_date else None,
                 t.estimated_min)
            )
            return cur.fetchone()[0]


def soft_delete(dtype: str, entry_id: int):
    tbl = "events" if dtype == "event" else "tasks"
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                f"UPDATE {tbl} SET deleted_at = NOW() WHERE id = %s",
                (entry_id,)
            )


def postpone_task(task_id: int) -> int:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT due_date, postpone_count FROM tasks WHERE id = %s",
                (task_id,)
            )
            row = cur.fetchone()
            if not row:
                return -1
            due_date, count = row
            if count >= 3:
                return count
            base     = due_date if due_date else date.today()
            new_date = (base + timedelta(days=1)).isoformat()
            new_count = count + 1
            cur.execute(
                "UPDATE tasks SET due_date = %s, postpone_count = %s WHERE id = %s",
                (new_date, new_count, task_id)
            )
            return new_count


def get_for_range(start: str, end: str):
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM events
                   WHERE DATE(start_time) BETWEEN %s AND %s
                     AND deleted_at IS NULL
                   ORDER BY start_time""",
                (start, end)
            )
            events = cur.fetchall()
            cur.execute(
                """SELECT * FROM tasks
                   WHERE status = 'pending'
                     AND deleted_at IS NULL
                     AND (due_date BETWEEN %s AND %s OR due_date IS NULL)
                   ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END""",
                (start, end)
            )
            tasks = cur.fetchall()
    return [dict(r) for r in events], [dict(r) for r in tasks]


def get_upcoming_reminders(within_minutes: int = 30):
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT title, start_time FROM events
                   WHERE deleted_at IS NULL
                     AND start_time BETWEEN NOW() AND NOW() + (%s * INTERVAL '1 minute')
                   ORDER BY start_time""",
                (within_minutes,)
            )
            return [dict(r) for r in cur.fetchall()]
