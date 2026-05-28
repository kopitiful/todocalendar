-- Zero-UI Tages-Copilot – Supabase (PostgreSQL) Schema

-- Kategorie A: Fixe Termine (festes Datum + Uhrzeit)
CREATE TABLE IF NOT EXISTS events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL,           -- z.B. Telegram-Chat-ID
    title       TEXT NOT NULL,
    description TEXT,
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ,             -- NULL = kein definiertes Ende
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Kategorie B: Flexible Aufgaben (kein fester Termin, nur Priorität)
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    priority        TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    due_date        DATE,                -- optionales Fälligkeitsdatum
    estimated_min   INT,                 -- geschätzte Dauer in Minuten
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'in_progress', 'done', 'skipped')),
    scheduled_for   DATE,                -- Tag, für den die Aufgabe eingeplant wurde
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_events_user_start  ON events (user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_tasks_user_status  ON tasks  (user_id, status, priority);
