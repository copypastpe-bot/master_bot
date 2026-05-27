# Master Mini App UI for Self-Booking — Design

> **Status:** approved 2026-05-27. Next step: `writing-plans` for TDD implementation plan.

**Goal:** Give masters a self-service UI inside their Mini App for everything backend-side self-booking exposes. After this work, a pilot master can open the app, tap More → Автозапись, flip the toggle, set their weekly hours and any date exceptions, choose service durations and cancel cutoff — all without touching curl or the backend repo.

**Backend dependency:** all required endpoints already ship and are stable in production at SHA `6dac549` (130/130 tests). The contract is final; this work consumes it 1-to-1.

---

## Settled forks

| # | Fork | Choice |
|---|---|---|
| 1 | Date library | **No dependency** — own horizontal date strip rendered with native `Date` + `<button>` chips. |
| 2 | Weekly editor layout | **7-row list** + per-day bottom-sheet for interval edits + "apply to weekdays" copy button. |
| 3 | Mutations | **Optimistic via TanStack Query** (`onMutate` snapshots cache, `onError` rolls back, `onSettled` invalidates). |
| 4 | Service duration editing | **Inline in existing `Services.jsx` form** + `MissingDurationWarning` block on AutobookingPage when applicable. |
| 5 | Page split | **Single `AutobookingPage`** with four scrollable cards, not a router-style index. |

---

## Architecture overview

```
miniapp/src/master/pages/
├── AutobookingPage.jsx            (NEW — single view, four cards)
├── More.jsx                        (+ new cell "Автозапись")
├── Services.jsx                    (+ duration_minutes field)
└── components/autobooking/        (NEW directory)
    ├── BookingToggleCard.jsx
    ├── WeeklyScheduleCard.jsx
    ├── ExceptionsCard.jsx
    ├── PoliciesCard.jsx
    ├── DayIntervalsSheet.jsx
    ├── DateExceptionSheet.jsx
    └── MissingDurationWarning.jsx

miniapp/src/api/client.js           (+ 5 functions)
miniapp/src/i18n/                   (+ keys, ru first, en as scaffold)
miniapp/src/App.jsx                 (+ route 'autobooking')
```

No new external dependencies. ~800 LOC total.

---

## Navigation entry (More → Автозапись)

A new `Cell` in `More.jsx` after the existing Theme cell:

```jsx
<Cell
  icon={<CalendarClockIcon />}
  label={t('autobooking_title')}
  value={settings.enabled ? t('on') : t('off')}
  onClick={() => onNavigate('autobooking')}
/>
```

`value` reads from the cached `useQuery({ queryKey: ['booking-settings'] })` so the master sees on/off state without entering the section. Loading state hides `value` until the first fetch resolves.

---

## AutobookingPage layout

Single React view, four scrollable sections separated by `<section>` cards. When the main toggle is **off**, the rest of the cards stay visible and editable but render at `opacity: 0.65` — masters can pre-configure schedule and flip the toggle later in one tap.

Order top-down:
1. `BookingToggleCard` — single switch + one-line explanation.
2. `MissingDurationWarning` (conditional) — only when at least one service has `duration_minutes === 60` and that 60 looks like a default-never-touched (heuristic: every service equals 60).
3. `WeeklyScheduleCard` — 7 day-rows, "apply to weekdays" button.
4. `ExceptionsCard` — horizontal date strip + list of saved exceptions.
5. `PoliciesCard` — two `<input type="range">` sliders for cutoff and horizon.

All four cards share a single `useQuery({ queryKey: ['booking-settings'] })` that hits `GET /api/master/booking-settings` and returns the full bundle (toggle, cutoff, horizon, weekly, exceptions). Each mutation invalidates this one key.

---

## Weekly editor (card + sheet)

**Row** (per weekday, 7 rendered):
```
Пн   10:00-14:00, 16:00-20:00      ›
```
- Left: weekday label
- Center: intervals joined `", "` or `"выходной"` placeholder
- Right: chevron, opens `DayIntervalsSheet`

**DayIntervalsSheet** (Telegram-style bottom modal):
- List of intervals for that weekday, each with two `<input type="time">` and a `✕` remove button.
- "+ Добавить интервал" appends an empty interval row.
- "Применить к будням" (checkbox) — when sheet closes via Save, clones these intervals to Mon–Fri.
- "Сохранить" — closes the sheet, calls `replaceWeeklySchedule` with **full 7-day array** (the helper already replaces idempotently on backend).

Time input uses the native `<input type="time">` — Telegram WebView renders the platform time picker, no library needed.

---

## Exceptions editor (card + sheet)

**Horizontal date strip** showing today and the next `booking_horizon_days - 1` days. Each date is a `<button>` chip:
- Plain background when no exception applies.
- Red tint when an `off` exception lands on this date.
- Blue tint when an `override` does.

Below the strip — a list of saved exceptions sorted by date, with `✕` for quick removal.

Tap on a chip → `DateExceptionSheet`:
- Radio group: "Как обычно" / "Выходной" / "Особые часы".
- When "Особые часы" selected — two `<input type="time">` inputs appear.
- "Сохранить" routes to one of:
  - `DELETE /api/master/schedule/exceptions/{id}` if removing existing
  - `POST /api/master/schedule/exceptions` if creating new
  - delete+create pair if changing kind for the same date (simplest implementation)

Date math is hand-rolled: `new Date()` + `.getDate() + N` loop to build the chip array.

---

## Policies card (sliders)

Two `<input type="range">` controls:
- **Cancel cutoff**: `min=1 max=48 step=1` (hours), default 24.
- **Booking horizon**: `min=7 max=60 step=1` (days), default 30.

Each drag fires onChange → debounce 500 ms → `updateBookingSettings({ cancel_cutoff_hours, horizon_days })`. Optimistic update reflects the new value above the slider as the master drags ("За 24 ч" → "За 25 ч"). Server rejects bad values via Pydantic and we roll back.

---

## Service duration warning + Services.jsx field

**Services.jsx**: append `<input type="number" min="15" step="15">` labeled "Длительность (мин)". When master creates a service, the field defaults to 60 — value gets stored, no special "first touch" flag.

**MissingDurationWarning** (on AutobookingPage): rendered when
```js
services.length > 0 && services.every(s => s.duration_minutes === 60)
```
The condition fires when no service has ever been edited away from the default — a reasonable signal for "this master enabled self-booking without considering durations." Button "Перейти к услугам" → `onNavigate('services')`.

Once the master edits any service to a non-60 duration, the warning vanishes. If they truly mean "every service is one hour" they can dismiss the warning by editing-then-resetting to 60 — at that point they've made the choice consciously.

---

## API client extension

`miniapp/src/api/client.js` gets 5 short functions:

```js
export const getBookingSettings = () =>
  api.get('/api/master/booking-settings').then(r => r.data);
export const updateBookingSettings = (body) =>
  api.put('/api/master/booking-settings', body).then(r => r.data);
export const replaceWeeklySchedule = (intervals) =>
  api.put('/api/master/schedule/weekly', intervals).then(r => r.data);
export const addScheduleException = (body) =>
  api.post('/api/master/schedule/exceptions', body).then(r => r.data);
export const removeScheduleException = (id) =>
  api.delete(`/api/master/schedule/exceptions/${id}`).then(r => r.data);
```

`updateMasterService` already exists; the new `duration_minutes` field flows through its existing kwargs body.

---

## Optimistic mutation pattern

Same shape for every mutation:

```jsx
const updateSettings = useMutation({
  mutationFn: updateBookingSettings,
  onMutate: async (next) => {
    await qc.cancelQueries({ queryKey: ['booking-settings'] });
    const prev = qc.getQueryData(['booking-settings']);
    qc.setQueryData(['booking-settings'], (old) => ({ ...old, ...next }));
    return { prev };
  },
  onError: (_err, _next, ctx) => {
    qc.setQueryData(['booking-settings'], ctx.prev);
    showToast(t('save_failed'));
  },
  onSettled: () => qc.invalidateQueries({ queryKey: ['booking-settings'] }),
});
```

Toast: a small fixed-bottom styled-components box, 3 second auto-dismiss. No new library.

---

## i18n

All user-visible strings go through `useI18n()`. Russian keys land first; English placeholders go in at the same keys so future translation is mechanical. Project's existing fallback is "ru if no key found" — that matches our default behaviour.

Indicative key list: `autobooking_title`, `autobooking_toggle_label`, `autobooking_toggle_hint`, `weekly_schedule_title`, `weekly_apply_to_weekdays`, `day_off`, `interval_from`, `interval_to`, `exception_as_usual`, `exception_off`, `exception_override`, `exception_save`, `policy_cutoff_label`, `policy_horizon_label`, `missing_duration_warning_title`, `missing_duration_warning_cta`, `save_failed`.

---

## Testing strategy

Frontend testing infra is out of scope for this sprint (no Jest/Vitest in repo, see §11 below). Verification:

- **`npm run build`** must pass.
- **`npm run lint`** on the new files only must pass (the full repo lint is known-broken on legacy files).
- **Backend unit tests** (130/130) stay green — they protect the contract this UI consumes.
- **Manual smoke**: dev server walkthrough of the 4 cards + 2 sheets + Services field by the developer, then by one pilot master.

---

## Out of scope (explicit)

- **Vitest / Jest / RTL setup.** ~2 days of work to add testing infra; not worth it for ~800 LOC at pilot scale.
- **TypeScript migration.** Project is JSX; we don't touch that today.
- **Drag-to-reorder intervals.** Lists of 1–3 intervals don't need it.
- **Bulk schedule import (CSV / etc).** Master fills it in two minutes.
- **Dedicated "autobookings" view in master Calendar.** Auto-orders already appear in the regular calendar via the shared `orders` table; no separate tab needed.
- **In-app notification badges for new bookings.** Master already gets Telegram push — see backend §7.
- **Settings preview** ("here's what a client sees on /m/{slug}/book"). Useful but not required for v1.
- **Service-duration "explicit-vs-default" flag.** The 60-min heuristic is good enough for pilot; can be made smarter when a master complains.
- **Multi-master copy** ("copy this schedule from master A to master B"). Each master configures their own.

---

## Risks & open questions for implementation

- Telegram WebView `<input type="time">` rendering varies across iOS / Android — confirm during smoke that both work. If iOS fails, fall back to two `<select>` (hours, minutes).
- The 60-min heuristic for the missing-duration warning has a false positive: a master who genuinely runs all 60-min services sees a warning until they touch the field. Acceptable for v1.
- Optimistic updates for the weekly editor send the **full** 7-day array on every save; if the master rapidly opens-saves-opens-saves a single day, we ship the bundle 4 times. Debounce / coalesce can come later if observed.
