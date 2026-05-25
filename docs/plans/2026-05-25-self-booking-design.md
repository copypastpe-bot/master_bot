# Client Self-Booking — Design

> **Status:** approved 2026-05-25. Next step: `writing-plans` for TDD implementation tasks.

**Goal:** Give each master an optional self-service booking flow so clients can reserve a slot through a public link (without subscribing to the client bot), through the existing client bot, or from the master's existing minisite. Auto-confirms, restart-safe under concurrent bookings, no new processes.

**Pilot scope:** five real masters operating in Moscow. Everything below is sized for that — out-of-scope items are listed at the end.

---

## Settled decisions

| # | Fork | Choice |
|---|---|---|
| 1 | Confirmation model | **Auto** — booking is created with `status='confirmed'` immediately. Master is notified, no manual approval step. |
| 2 | Slot duration | **Per-service** — new column `services.duration_minutes`. One booking = one service. |
| 3 | Public-page identity | **Name + phone required, @username optional**; Telegram WebApp initData prefills name / tg_id / @username when the page is opened inside Telegram. |
| 4 | Schedule storage | **Weekly template + date-level overrides** (Cal.com pattern). |
| 5 | Concurrent booking | **`BEGIN IMMEDIATE` transaction + overlap check** built on the WAL/busy_timeout=5000ms enabled in sprint 1. |
| 6 | Client cancellation | **Yes, with master-configured cutoff in hours** (default 24h). |
| 7 | Anti-spam | **Per-IP rate limit** (5/h on POST) + server-side phone validation (`phonenumbers` already in `requirements.txt`). No CAPTCHA. |
| 8 | Master notifications | **Telegram push via `master_bot`** — reuses the existing aiogram instance attached to `app.state`. |
| 9 | Client reminders | **Unchanged from current behavior** — `scheduler.send_reminders_24h` already pushes only when `tg_id` is set. Public clients without tg_id receive nothing. |
| 10 | Public booking page | **CTA on existing `/m/{slug}` + dedicated URL `/m/{slug}/book`**. Section appears only when the master enabled self-booking. |
| A1 | Data model | **Reuse `orders`** with extra columns (`source`, `cancel_token`, `duration_minutes`). No separate `bookings` table. |
| B1 | Public page tech | **SSR via FastAPI Jinja**, minimal vanilla JS (or HTMX). No React SPA. |

---

## Architecture overview

```
                ┌─────────────────────────────┐
                │  Master Mini App (React)    │
                │  - Settings: toggle + sched.│
                │  - Calendar: shows bookings │
                └───────────────┬─────────────┘
                                │ FastAPI API (initData auth)
                                │
┌────────────────┐    ┌─────────▼──────────┐    ┌────────────────────┐
│ Public visitor │───▶│  FastAPI + Jinja   │◀───│ Telegram client_bot│
│  (browser)     │    │  - /m/{slug}/book  │    │  - /book flow      │
│  per-IP RL     │    │  - /b/{token}      │    │  (subscribed)      │
└────────────────┘    │  - /api/public/*   │    └────────────────────┘
                      └─────────┬──────────┘
                                │
                      ┌─────────▼──────────┐
                      │  SQLite + WAL      │
                      │  orders + 3 new tbl│
                      └─────────┬──────────┘
                                │
                      ┌─────────▼──────────┐
                      │  master_bot push   │
                      │  (notifications)   │
                      └────────────────────┘
```

No new processes. No new infra. Just FastAPI routes + one DB migration + Mini App settings UI.

---

## Database schema — migration 026

```sql
-- 1. Service duration (used by overlap math + slot grid).
ALTER TABLE services ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 60;

-- 2. Booking metadata on orders.
ALTER TABLE orders ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE orders ADD COLUMN cancel_token TEXT;
ALTER TABLE orders ADD COLUMN duration_minutes INTEGER;
CREATE INDEX idx_orders_cancel_token ON orders(cancel_token) WHERE cancel_token IS NOT NULL;

-- 3. Master-level self-booking settings.
ALTER TABLE masters ADD COLUMN self_booking_enabled BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE masters ADD COLUMN booking_cancel_cutoff_hours INTEGER NOT NULL DEFAULT 24;
ALTER TABLE masters ADD COLUMN booking_horizon_days INTEGER NOT NULL DEFAULT 30;

-- 4. Weekly schedule template.
CREATE TABLE master_schedule_weekly (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    weekday     INTEGER NOT NULL,        -- 0=Mon … 6=Sun
    start_time  TEXT NOT NULL,           -- "10:00"
    end_time    TEXT NOT NULL,           -- "18:00"
    UNIQUE(master_id, weekday, start_time)
);

-- 5. Date-level overrides (vacation, one-off availability).
CREATE TABLE master_schedule_exceptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    date        TEXT NOT NULL,           -- "2026-06-15"
    kind        TEXT NOT NULL,           -- 'off' | 'override'
    start_time  TEXT,                    -- NULL when kind='off'
    end_time    TEXT,
    UNIQUE(master_id, date, start_time)
);
```

Defaults let the migration apply to existing data without backfill. `services.duration_minutes=60` is a reasonable starting estimate; masters tweak it per service when they enable self-booking.

---

## Master settings UI

New section in Mini App: `More → Автозапись`.

- **Toggle** "Принимать онлайн-записи" (writes `masters.self_booking_enabled`).
- **Weekly schedule**: 7 rows (Mon-Sun). Each row holds zero, one, or more "from-to" intervals. UI: tap day → modal with list of intervals + "add interval" button.
- **Date exceptions**: month calendar; tap a date → choose "off" or "override with custom hours".
- **Cancel cutoff slider** 1–48h, default 24.
- **Horizon slider** 7–60 days, default 30.
- **Service duration**: extends existing services editor with a `Длительность (мин)` field.

### Mini App ↔ API contract

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/master/booking-settings` | Returns the full bundle: toggle, cutoff, horizon, weekly template, exceptions. |
| PUT | `/api/master/booking-settings` | Update toggle + cutoff + horizon. |
| PUT | `/api/master/schedule/weekly` | Idempotent replace of the weekly template (body: `[{weekday, intervals:[{start,end}]}]`). |
| POST | `/api/master/schedule/exceptions` | Add an exception. |
| DELETE | `/api/master/schedule/exceptions/{id}` | Remove an exception. |
| PUT | `/api/master/services/{id}` | Extend existing endpoint to accept `duration_minutes`. |

All authed by Telegram initData (existing `get_current_master` dependency).

---

## Public booking page UX

Existing `/m/{slug}` minisite gains a new section **"Запись онлайн"** with a button → `/m/{slug}/book`. Section renders only when the master has `self_booking_enabled=1`.

The booking page is server-rendered Jinja, four steps progressively revealed in one viewport:

1. **Service picker** (skipped if only one service): cards with name + duration + price.
2. **Date strip**: horizontal scroll from today to `today + horizon_days`. Days that are entirely off (exception or empty weekly) are visually disabled.
3. **Slot grid**: 30-min steps inside the day's available windows, filtered by overlap with existing orders. Slots in the past for today are removed server-side.
4. **Contact form**: name* / phone* / @username (opt). Pre-filled from Telegram WebApp initData when present.

Submit → `POST /api/public/book` → success page with "Open my booking" link to `/b/{cancel_token}`. If the visitor came from Telegram, also a deep link back to the client bot.

Anti-spam: rate-limit `POST /api/public/book` at 5 requests per IP per hour using the existing `RateLimiter` class from `src/api/ratelimit.py`.

---

## Booking API

### `GET /api/public/{slug}/slots?service_id=X&date=YYYY-MM-DD`
No auth. Returns `{"slots": ["10:00","10:30", …]}`.

Algorithm:
1. Look up master by slug; 404 if not found or self-booking disabled.
2. Resolve service → take `duration_minutes`.
3. For requested date: load weekly[weekday] intervals, apply exception if any (`off` → empty, `override` → replace).
4. Generate candidate starts in each interval with 30-min step.
5. Filter out candidates whose `[start, start+duration)` overlaps with existing orders in `{new, confirmed, pending}` for that master on that date.
6. Filter out past times for today.

No caching. Expected at SQLite-local <5ms per call for typical data volumes.

### `POST /api/public/book`
No auth. Body:
```json
{"slug":"...", "service_id":1, "date":"2026-06-01", "start":"14:00",
 "name":"Иван", "phone":"+79991234567",
 "tg_username":"ivan_iv", "tg_id":12345678}
```

Transaction (`BEGIN IMMEDIATE`):

1. Validate slug → master with `self_booking_enabled=1` (404/403 otherwise).
2. Validate service belongs to master, active, has duration → take `duration_minutes`.
3. Apply rate-limit by IP (429 if exceeded).
4. Validate phone via `phonenumbers` (422 if malformed).
5. **Overlap check** against existing `orders` rows for `master_id` on date:
   `existing.start < new.end AND existing.start + existing.duration > new.start`
   → 409 if any match.
6. Upsert client:
   - If `tg_id` provided → look up `clients.tg_id`.
   - Else → look up by `master_clients` → `clients.phone`.
   - If neither found → create `clients` row (`tg_id=NULL` allowed).
7. Upsert `master_clients` link.
8. Insert `orders(status='confirmed', source='public', cancel_token=uuid4(), duration_minutes=service.duration_minutes)`.
9. COMMIT.
10. Post-commit (outside transaction): push to `master_bot`; if Google Calendar connected, sync via existing `gc_event_id` flow.

Response 201: `{"order_id": N, "cancel_token": "...", "cancel_url": "https://.../b/..."}`.

---

## Client cancellation — `/b/{token}`

Public page, no auth. Looks up `orders.cancel_token`:

- Renders: service name, master name + contact, date+time.
- If `now < scheduled_at − cutoff_hours`: button "Отменить запись" → `POST /api/public/cancel/{token}` → `status='cancelled'` + master push.
- Otherwise: message "Свяжитесь с мастером лично" + master phone/Telegram link.

Stale tokens (cancelled/done orders) render a read-only "Запись неактивна" view.

---

## Notifications

Single channel: `master_bot.send_message(master.tg_id, …)` immediately after commit.

**On new booking:**
```
🆕 Новая запись
{client_name}, {phone}
{service_name}, {date} {time}
[Открыть в Mini App]
```

**On client cancellation:**
```
❌ Клиент отменил запись
{client_name}, {service_name}, {date} {time}
```

Synchronous send (Telegram API latency ≈100 ms; acceptable on a single HTTP request). No background task — keeps the surface area small.

---

## Client bot integration

In `client_bot` add a `/book` command (and a button in the main menu). The flow is a thin client over the same public API:

1. If the client is linked to one master via `master_clients` → skip master selection. Otherwise show a master picker.
2. Inline service picker → inline date picker → inline time picker.
3. Confirmation step calls `POST /api/public/book` server-side with `tg_id` from the bot session (no public-facing rate limit because the request is authenticated via Telegram).
4. Bot returns confirmation message with the same link to `/b/{token}`.

No new tables. The bot owns only the conversational flow; persistence reuses the public API.

---

## Testing strategy

New file `tests/test_self_booking.py`. Covers:

- **Schema test:** migration 026 produces the expected columns/tables.
- **Slot generator test:** for a synthetic weekly+exceptions+orders fixture, the generator returns the expected slots — including past-time pruning, overlap pruning, and exception override.
- **Concurrent booking test:** spin up two `asyncio.create_task`s racing on the same slot → exactly one returns 201, the other returns 409. Validates `BEGIN IMMEDIATE` + overlap check work as designed (pairs with sprint-1 WAL/busy_timeout).
- **Rate-limit test:** 6th POST from the same IP within an hour returns 429.
- **Cancellation cutoff test:** before cutoff → 200; after → 403.
- **Public-page render test:** SSR returns 200 with expected texts when self-booking enabled; returns 404 when disabled.
- **Public booking → client created when tg_id absent.**
- **Master notification fires on book + cancel** (mocked `master_bot.send_message`).

Target: bring suite from 64 to ~80 tests.

---

## Out of scope (explicit)

These are **not** implemented in MVP. Recording them here so they're not silently introduced later.

- **Timezone:** everything stored and displayed in МСК. Public page shows an explicit "Время указано по Москве" note. Multi-tz comes in a follow-up sprint.
- **Multi-service booking:** one service per booking. Bundling stays for later.
- **Bonuses on auto-bookings:** inherit existing behaviour — bonus accrues when `status='done'` (master closes the order manually).
- **Email notifications:** none.
- **SMS reminders to tg-less clients:** none.
- **Google Calendar:** auto-bookings sync through the existing `gc_event_id` path; no new GC integration code.
- **Paid prepayment / Telegram Stars deposit:** none.
- **Rescheduling by client:** none. Cancel + new booking only.
- **Multi-master per master_clients link** in booking flow: if a client is linked to multiple masters, the bot asks them to pick one (already supported by `get_current_client`).

---

## Open questions to revisit during implementation

- **Override partial intervals:** when `kind='override'`, do we allow multiple intervals per date? MVP: single interval per exception row; multiple intervals via multiple exception rows. Possible re-think if it makes the UI clumsy.
- **Cancellation of past records:** scrubbing `cancel_token` after the booking date passes (privacy hygiene). Probably fine to keep token forever; revisit if regulators complain.
- **Concurrent settings edits:** what if a master toggles off self-booking while a client is mid-flow? Server-side check at `POST /api/public/book` rejects with 403; client sees a friendly error.
