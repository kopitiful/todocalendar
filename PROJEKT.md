# Zero-UI Tages-Copilot

KI-gestützter Tagesplaner, der vollständig per Freitext bedient wird — kein Formular, keine Buttons, keine Kategorien. Der Nutzer schreibt wie in einem Chat; die App erkennt automatisch ob es ein Termin, eine Aufgabe oder eine Abfrage ist.

**Repo:** https://github.com/kopitiful/todocalendar  
**Stack:** Python · FastAPI · Claude Haiku (Anthropic API) · SQLite · Vanilla JS

---

## Start

```bash
source ~/.zshrc
cd /Users/timhuebner/tradingbot/todocalendar
python3 -m uvicorn main:app --reload
# → http://localhost:8000
```

Voraussetzungen:
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # oder dauerhaft in ~/.zshrc
```

---

## Architektur

```
todocalendar/
├── main.py          FastAPI-Backend (Endpoints, Routing)
├── parser.py        Claude-API-Integration (NLP → strukturiertes JSON)
├── models.py        Pydantic-Datenmodelle
├── db.py            SQLite-Datenbankschicht
├── index.html       Frontend (reines HTML/CSS/Vanilla JS)
├── schema.sql       Supabase-kompatibles PostgreSQL-Schema (Referenz)
├── requirements.txt
└── PROJEKT.md
```

---

## Datenmodell

Zwei Kategorien:

### Kategorie A – Fixe Termine (`events`)
Hat ein festes Datum **und** eine Uhrzeit.  
Beispiel: `"Meeting mit Oskar um 14 Uhr am 24.12."`

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER | Primärschlüssel |
| `title` | TEXT | Titel |
| `description` | TEXT | Optionale Beschreibung |
| `start_time` | TEXT | ISO-8601 datetime |
| `end_time` | TEXT | Optionales Ende |
| `deleted_at` | TEXT | Soft-Delete Zeitstempel |
| `created_at` | TEXT | Erstellungszeitpunkt |

### Kategorie B – Flexible Aufgaben (`tasks`)
Hat **keine** feste Uhrzeit, nur Priorität und optionales Fälligkeitsdatum.  
Beispiel: `"Steuererklärung machen, hohe Prio"`

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | INTEGER | Primärschlüssel |
| `title` | TEXT | Titel |
| `description` | TEXT | Optionale Beschreibung |
| `priority` | TEXT | `high` / `medium` / `low` |
| `due_date` | TEXT | Optionales Fälligkeitsdatum (ISO-8601) |
| `estimated_min` | INTEGER | Geschätzte Dauer in Minuten |
| `status` | TEXT | `pending` / `in_progress` / `done` / `skipped` |
| `postpone_count` | INTEGER | Anzahl der Verschiebungen (max. 3) |
| `deleted_at` | TEXT | Soft-Delete Zeitstempel |
| `created_at` | TEXT | Erstellungszeitpunkt |

---

## API-Endpoints

| Method | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/` | Liefert das Frontend (index.html) |
| `POST` | `/parse` | Freitext → Claude → speichern oder abfragen |
| `DELETE` | `/entry/{type}/{id}` | Soft-Delete (setzt `deleted_at`) |
| `PATCH` | `/entry/task/{id}/postpone` | Aufgabe um 1 Tag verschieben |
| `GET` | `/reminders` | Termine in den nächsten 30 Minuten |

### POST /parse – Payload
```json
{ "text": "Meeting mit Oskar um 14 Uhr am 24.12." }
```

### POST /parse – Antwort (Termin)
```json
{ "type": "event", "id": 1, "title": "Meeting mit Oskar", "detail": "24.12.2024 · 14:00 Uhr" }
```

### POST /parse – Antwort (Abfrage)
```json
{
  "type": "query",
  "label": "24.12.2024",
  "events": [{ "id": 1, "title": "Meeting mit Oskar", "time": "14:00" }],
  "tasks":  [{ "id": 2, "title": "Steuererklärung", "priority": "high", "postpone_count": 0 }]
}
```

---

## Claude-Integration (parser.py)

- **Modell:** `claude-haiku-4-5` (günstigstes Modell, ~$0.01/Monat bei normaler Nutzung)
- **Structured Output:** JSON-Schema erzwingt valide Ausgabe ohne Parsing-Fehler
- **Prompt-Caching:** System-Prompt wird nach erstem Aufruf gecacht (~90 % Kostenersparnis)
- **3 Eingabetypen:** `event` · `task` · `query`
- **Query-Unterstützung:** Einzeldatum oder Zeitraum (`date` + `end_date`)

---

## UI-Verhalten (index.html)

### Eingabe
- Freitext in das Eingabefeld, Enter oder ↑-Button
- Textarea wächst automatisch mit

### Bestätigung (WhatsApp-Logik)
| Haken | Bedeutung |
|---|---|
| ✓ (grau) | Gesendet |
| ✓✓ (grau) | Server empfangen |
| ✓✓ (blau) | Claude hat verarbeitet & gespeichert |

Kein Text, keine Labels — nur die Haken.

### Abfrage-Ergebnisse
- Termine: Uhrzeit links, Titel rechts
- Aufgaben: Prioritäts-Dot (`●` hoch · `◐` mittel · `○` niedrig) links, Titel rechts

### Interaktion mit Einträgen
| Aktion | Effekt |
|---|---|
| Doppelklick auf Nachricht | Eintrag wird soft-gelöscht (verschwindet, bleibt in DB) |
| Doppelklick auf Ergebnis-Zeile | Eintrag wird soft-gelöscht |
| 1× Klick auf Aufgabe | Auf nächsten Tag verschieben |
| 3× verschoben | Aufgabe gesperrt (durchgestrichen), kein weiteres Verschieben |
| 3. Verschiebung | Toast-Warnung: "⚠️ Letzte mal verschoben!" |

### Erinnerungen
- Polling alle 60 Sekunden gegen `/reminders`
- Schwarzer Banner oben erscheint 30 Minuten vor jedem Termin
- Klick schließt den Banner
- Bereits angezeigte Erinnerungen werden nicht erneut gezeigt (Session-Set)

---

## Kosten

| Modell | 20 Einträge | 300/Monat |
|---|---|---|
| claude-haiku-4-5 | ~$0.001 | ~$0.01 |

Mit Prompt-Caching: System-Prompt (300 Token) wird ab dem 2. Aufruf für ~0.1× des normalen Preises geladen.

---

## Nächste mögliche Schritte

- [ ] Autopilot-Modus ("Lass uns den Tag beginnen") — Tag strukturieren, Push-Logik
- [ ] Supabase statt SQLite für persistente Cloud-Speicherung
- [ ] Aufgabe als "erledigt" markieren (z.B. Wischgeste oder Tastenkürzel)
- [ ] Wochenrückblick / Statistik
- [ ] PWA (offline-fähig, installierbar auf dem Handy)
