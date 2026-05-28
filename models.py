"""
Pydantic-Datenmodelle für den Zero-UI Tages-Copiloten.

Spiegeln 1:1 die SQL-Tabellen wider und werden sowohl
für die Claude-API-Ausgabe (structured output) als auch
für die Datenbankschicht verwendet.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# Enums
# ──────────────────────────────────────────

class Priority(str, Enum):
    high   = "high"
    medium = "medium"
    low    = "low"


class TaskStatus(str, Enum):
    pending     = "pending"
    in_progress = "in_progress"
    done        = "done"
    skipped     = "skipped"


# ──────────────────────────────────────────
# Kategorie A – Fixe Termine
# ──────────────────────────────────────────

class Event(BaseModel):
    id:          UUID     = Field(default_factory=uuid4)
    user_id:     str
    title:       str
    description: Optional[str]   = None
    start_time:  datetime                     # festes Datum + Uhrzeit
    end_time:    Optional[datetime] = None
    created_at:  datetime = Field(default_factory=datetime.utcnow)


class EventCreate(BaseModel):
    """Eingabe-Schema – wird von der Parse-Funktion zurückgegeben."""
    title:       str
    description: Optional[str]   = None
    start_time:  datetime
    end_time:    Optional[datetime] = None


# ──────────────────────────────────────────
# Kategorie B – Flexible Aufgaben
# ──────────────────────────────────────────

class Task(BaseModel):
    id:            UUID        = Field(default_factory=uuid4)
    user_id:       str
    title:         str
    description:   Optional[str]      = None
    priority:      Priority           = Priority.medium
    due_date:      Optional[date]     = None
    estimated_min: Optional[int]      = None
    status:        TaskStatus         = TaskStatus.pending
    scheduled_for: Optional[date]     = None
    created_at:    datetime           = Field(default_factory=datetime.utcnow)
    completed_at:  Optional[datetime] = None


class TaskCreate(BaseModel):
    """Eingabe-Schema – wird von der Parse-Funktion zurückgegeben."""
    title:         str
    description:   Optional[str]  = None
    priority:      Priority        = Priority.medium
    due_date:      Optional[date]  = None
    estimated_min: Optional[int]   = None


# ──────────────────────────────────────────
# Structured-Output-Schema für Claude
# ──────────────────────────────────────────

class ParsedInput(BaseModel):
    """Was Claude aus einem Freitext-Satz extrahiert."""
    input_type:  str                  = Field(description="'event', 'task' oder 'query'")
    event:       Optional[EventCreate] = None
    task:        Optional[TaskCreate]  = None
    query_date:     Optional[str] = None  # YYYY-MM-DD
    query_end_date: Optional[str] = None  # YYYY-MM-DD (Zeitraum-Abfragen)
