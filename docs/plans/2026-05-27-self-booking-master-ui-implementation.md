# Master Mini App UI for Self-Booking — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the master-facing React UI that lets a pilot master configure self-booking entirely inside the Mini App — toggle, weekly schedule, date exceptions, cancel cutoff, horizon, and per-service duration — consuming the backend deployed at SHA `6dac549`.

**Architecture:** Single `AutobookingPage.jsx` with four cards, opened from `More.jsx`. State lives in TanStack Query under one cache key `['booking-settings']`; every mutation does optimistic update + rollback on error. Bottom-sheets for per-day intervals and date exceptions. Date math hand-rolled, no new dependencies. ~800 LOC across 9 new files + 3 edits.

**Tech Stack:** React 19, Vite 8, `@tanstack/react-query` 5.91 (already in deps), axios, styled-components, lucide-react. No new libraries.

**Design doc:** `docs/plans/2026-05-27-self-booking-master-ui-design.md` (commit `ce038bd`).

**Verification model:** No frontend test framework in repo (deferred per design §10). Each task's verification step is:
- `npm run build` must pass.
- Manual smoke after the final integration task.

---

## Prerequisites (run once before Task 1)

The worktree's `miniapp/node_modules` is empty and `vite` is not on PATH.

```bash
cd miniapp
npm install
npm run build
```

Expected: build succeeds, prints output asset hashes. If this fails, **STOP** and resolve before continuing.

After confirming the baseline:

```bash
git status --short
# .gitignored: miniapp/node_modules — should not appear
```

If `node_modules` appears in `git status`, abort: `.gitignore` is missing a rule.

---

## Task 1: API client extension

**Files:**
- Modify: `miniapp/src/api/client.js` (append at end of file, near other `export const get...` lines)

**Step 1: Write the new functions**

Append to the end of `miniapp/src/api/client.js`:

```js
// Self-booking endpoints (backend deployed at 6dac549).
export const getBookingSettings = () =>
  api.get('/api/master/booking-settings', { params: masterParams() }).then(r => r.data);

export const updateBookingSettings = (body) =>
  api.put('/api/master/booking-settings', body, { params: masterParams() }).then(r => r.data);

export const replaceWeeklySchedule = (intervals) =>
  api.put('/api/master/schedule/weekly', intervals, { params: masterParams() }).then(r => r.data);

export const addScheduleException = (body) =>
  api.post('/api/master/schedule/exceptions', body, { params: masterParams() }).then(r => r.data);

export const removeScheduleException = (id) =>
  api.delete(`/api/master/schedule/exceptions/${id}`, { params: masterParams() }).then(r => r.data);
```

Verify `masterParams` is the helper used by sibling functions — grep for it. If sibling functions don't use it, drop the `params` arg from yours too.

**Step 2: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS. New functions are exported but unused at this point — that's fine.

**Step 3: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(miniapp): API client for self-booking endpoints"
```

---

## Task 2: i18n keys (ru + en scaffolds)

**Files:**
- Modify: `miniapp/src/i18n/` — find the dictionaries (likely `index.js` + `ru.js` + `en.js` or inline objects). Grep for an existing key like `theme_picker_title` to locate.

**Step 1: Identify the file shape**

```bash
grep -rn "theme_picker_title\|t('autobooking" miniapp/src/i18n/ | head -10
```

Likely: one file per locale, default export object of `key: string`. Add the keys below to **both** `ru` and `en`. Russian first, English optional but fill in a literal or English placeholder.

**Step 2: Append keys**

To `ru` (in whatever file holds Russian):
```js
autobooking_title: 'Автозапись',
autobooking_toggle_label: 'Принимать онлайн-записи',
autobooking_toggle_hint: 'Клиенты смогут бронировать слоты по публичной ссылке',
weekly_schedule_title: 'Расписание',
weekly_apply_to_weekdays: 'Применить к будням',
day_off: 'выходной',
day_short_mon: 'Пн', day_short_tue: 'Вт', day_short_wed: 'Ср',
day_short_thu: 'Чт', day_short_fri: 'Пт', day_short_sat: 'Сб', day_short_sun: 'Вс',
interval_from: 'с', interval_to: 'до',
interval_add: 'Добавить интервал',
exceptions_title: 'Исключения',
exception_add: 'Добавить исключение',
exception_as_usual: 'Как обычно',
exception_off: 'Выходной',
exception_override: 'Особые часы',
policies_title: 'Политики',
policy_cutoff_label: 'До отмены клиентом',
policy_cutoff_unit: 'ч',
policy_horizon_label: 'Горизонт записи',
policy_horizon_unit: 'дн',
missing_duration_warning_title: 'У некоторых услуг не задана длительность',
missing_duration_warning_body: 'Слоты будут рассчитаны как 60 минут',
missing_duration_warning_cta: 'Перейти к услугам',
service_duration_label: 'Длительность (мин)',
save: 'Сохранить', cancel: 'Отмена', back: 'Назад',
save_failed: 'Не удалось сохранить',
on: 'вкл', off: 'выкл',
```

To `en` (English placeholders — translate to taste):
```js
autobooking_title: 'Self-booking',
autobooking_toggle_label: 'Accept online bookings',
// ... same keys with English strings, or keep Russian if i18n falls back to ru.
```

If `en` dictionary doesn't exist yet, **don't create it** — leave the keys in `ru` only and rely on existing fallback.

**Step 3: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 4: Commit**

```bash
git add miniapp/src/i18n/
git commit -m "feat(miniapp): i18n keys for self-booking UI"
```

---

## Task 3: Shared booking-settings hook (cache + optimistic mutations)

**Files:**
- Create: `miniapp/src/master/hooks/useBookingSettings.js`

This consolidates the read query + four mutation hooks so individual cards don't repeat the `onMutate / onError / onSettled` ceremony.

**Step 1: Write the file**

```js
// miniapp/src/master/hooks/useBookingSettings.js
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getBookingSettings,
  updateBookingSettings,
  replaceWeeklySchedule,
  addScheduleException,
  removeScheduleException,
} from '../../api/client';

const KEY = ['booking-settings'];

/** GET /api/master/booking-settings — bundle: enabled/cutoff/horizon/weekly/exceptions. */
export function useBookingSettings() {
  return useQuery({ queryKey: KEY, queryFn: getBookingSettings });
}

/** Generic optimistic mutation factory — patches the bundle in cache,
 *  rolls back on error, re-fetches on settle. */
function useBundleMutation(mutationFn, patchFn) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    onMutate: async (input) => {
      await qc.cancelQueries({ queryKey: KEY });
      const prev = qc.getQueryData(KEY);
      qc.setQueryData(KEY, (old) => patchFn(old, input));
      return { prev };
    },
    onError: (_err, _input, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateBookingSettings() {
  return useBundleMutation(updateBookingSettings, (old, next) => ({ ...old, ...next }));
}

export function useReplaceWeeklySchedule() {
  // Server returns {ok, count}; we still need to invalidate so weekly comes back fresh.
  // Optimistic patch: overwrite the weekly array in the bundle.
  return useBundleMutation(replaceWeeklySchedule, (old, intervals) => ({
    ...old,
    weekly: intervals.map((i, idx) => ({
      id: idx, weekday: i.weekday, start_time: i.start, end_time: i.end,
    })),
  }));
}

export function useAddScheduleException() {
  return useBundleMutation(addScheduleException, (old, body) => ({
    ...old,
    exceptions: [
      ...(old?.exceptions ?? []),
      { id: -1, ...body, start_time: body.start || null, end_time: body.end || null },
    ],
  }));
}

export function useRemoveScheduleException() {
  return useBundleMutation(removeScheduleException, (old, id) => ({
    ...old,
    exceptions: (old?.exceptions ?? []).filter(e => e.id !== id),
  }));
}
```

**Step 2: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS. Hook is exported but unused yet.

**Step 3: Commit**

```bash
git add miniapp/src/master/hooks/useBookingSettings.js
git commit -m "feat(miniapp): shared booking-settings cache + optimistic mutations"
```

---

## Task 4: AutobookingPage skeleton + route + More entry

This is the **smallest end-to-end thing that renders**. After this task a master can tap More → Автозапись and see "Coming soon" with a back button. Subsequent tasks fill in cards one by one.

**Files:**
- Create: `miniapp/src/master/pages/AutobookingPage.jsx`
- Modify: `miniapp/src/master/pages/More.jsx` (add one Cell)
- Modify: `miniapp/src/App.jsx` (add route 'autobooking')

**Step 1: Page skeleton**

```jsx
// miniapp/src/master/pages/AutobookingPage.jsx
import { useI18n } from '../../i18n';
import { useBookingSettings } from '../hooks/useBookingSettings';

export default function AutobookingPage({ onNavigate }) {
  const { t } = useI18n();
  const { data, isLoading } = useBookingSettings();

  return (
    <div style={{ padding: 16 }}>
      <button onClick={() => onNavigate('more')} style={{ marginBottom: 12 }}>
        ← {t('back')}
      </button>
      <h1 style={{ fontSize: 20, margin: '0 0 16px' }}>{t('autobooking_title')}</h1>
      {isLoading
        ? <div>…</div>
        : <pre style={{ fontSize: 11 }}>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
```

This temporary `<pre>` is for sanity-checking the bundle structure during dev — replaced in Task 5.

**Step 2: Route**

Find the route-dispatch in `miniapp/src/App.jsx` — grep for `case 'more'` or similar. Add:
```jsx
case 'autobooking':
  return <AutobookingPage onNavigate={navigate} />;
```
And import: `import AutobookingPage from './master/pages/AutobookingPage';`.

**Step 3: More cell**

In `More.jsx`, after the existing "Theme" Cell:
```jsx
<Cell
  icon={null /* TODO: import CalendarClock from lucide-react if matching existing icon pattern */}
  label={t('autobooking_title')}
  onClick={() => { haptic(); onNavigate('autobooking'); }}
/>
```
Read the existing pattern in More.jsx first to mirror it — if it uses a specific Cell shape with `value`, supply `value={null}` for now and add status text in Task 5.

**Step 4: Build + smoke**

```bash
cd miniapp && npm run build
```
Expected: PASS.

Optional manual smoke:
```bash
npm run dev
# open localhost:5173, tap More → Автозапись, see the page render with JSON dump
```

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/AutobookingPage.jsx miniapp/src/master/pages/More.jsx miniapp/src/App.jsx
git commit -m "feat(miniapp): AutobookingPage skeleton + More navigation entry"
```

---

## Task 5: BookingToggleCard

**Files:**
- Create: `miniapp/src/master/components/autobooking/BookingToggleCard.jsx`
- Modify: `miniapp/src/master/pages/AutobookingPage.jsx` (replace `<pre>` debug with the card)
- Modify: `miniapp/src/master/pages/More.jsx` (now that we know the bundle shape, update the Cell's `value` to show on/off)

**Step 1: Component**

```jsx
// miniapp/src/master/components/autobooking/BookingToggleCard.jsx
import { useI18n } from '../../../i18n';
import { useUpdateBookingSettings } from '../../hooks/useBookingSettings';

export default function BookingToggleCard({ settings }) {
  const { t } = useI18n();
  const updateMut = useUpdateBookingSettings();

  const toggle = () => {
    updateMut.mutate({
      enabled: !settings.enabled,
      cancel_cutoff_hours: settings.cancel_cutoff_hours,
      horizon_days: settings.horizon_days,
    });
  };

  return (
    <section style={{
      background: 'var(--tg-card-bg, #fff)',
      borderRadius: 12, padding: 16, marginBottom: 12,
    }}>
      <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 15 }}>{t('autobooking_toggle_label')}</span>
        <input type="checkbox" checked={!!settings.enabled} onChange={toggle} />
      </label>
      <p style={{ fontSize: 13, color: 'var(--tg-hint-color, #888)', marginTop: 8 }}>
        {t('autobooking_toggle_hint')}
      </p>
    </section>
  );
}
```

**Step 2: Wire into AutobookingPage**

Replace the `<pre>` debug block in AutobookingPage.jsx with:
```jsx
{!isLoading && data && (
  <>
    <BookingToggleCard settings={data} />
    {/* TODO: more cards in Tasks 6-9 */}
  </>
)}
```
Import: `import BookingToggleCard from '../components/autobooking/BookingToggleCard';`

**Step 3: Update More cell value**

Now bundle is known to have `data.enabled`. In More.jsx where you fetch master settings (or via `useBookingSettings()` directly), set `value={data?.enabled ? t('on') : t('off')}`.

**Step 4: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 5: Commit**

```bash
git add miniapp/src/master/components/autobooking/BookingToggleCard.jsx miniapp/src/master/pages/AutobookingPage.jsx miniapp/src/master/pages/More.jsx
git commit -m "feat(miniapp): self-booking toggle card with optimistic update"
```

---

## Task 6: PoliciesCard (sliders for cutoff + horizon)

**Files:**
- Create: `miniapp/src/master/components/autobooking/PoliciesCard.jsx`
- Modify: `miniapp/src/master/pages/AutobookingPage.jsx` (mount the card)

**Step 1: Component**

```jsx
// miniapp/src/master/components/autobooking/PoliciesCard.jsx
import { useEffect, useRef, useState } from 'react';
import { useI18n } from '../../../i18n';
import { useUpdateBookingSettings } from '../../hooks/useBookingSettings';

export default function PoliciesCard({ settings }) {
  const { t } = useI18n();
  const updateMut = useUpdateBookingSettings();
  const [cutoff, setCutoff] = useState(settings.cancel_cutoff_hours);
  const [horizon, setHorizon] = useState(settings.horizon_days);

  // Debounce: collapse rapid slider drags into one PUT.
  const timer = useRef(null);
  const queueSave = (next) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      updateMut.mutate({
        enabled: settings.enabled,
        cancel_cutoff_hours: next.cutoff,
        horizon_days: next.horizon,
      });
    }, 500);
  };

  useEffect(() => () => timer.current && clearTimeout(timer.current), []);

  return (
    <section style={{ background: 'var(--tg-card-bg, #fff)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{t('policies_title')}</h3>

      <label style={{ display: 'block', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span>{t('policy_cutoff_label')}</span>
          <span>{cutoff} {t('policy_cutoff_unit')}</span>
        </div>
        <input
          type="range" min={1} max={48} step={1} value={cutoff}
          onChange={(e) => {
            const v = Number(e.target.value);
            setCutoff(v); queueSave({ cutoff: v, horizon });
          }}
          style={{ width: '100%' }}
        />
      </label>

      <label style={{ display: 'block' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span>{t('policy_horizon_label')}</span>
          <span>{horizon} {t('policy_horizon_unit')}</span>
        </div>
        <input
          type="range" min={7} max={60} step={1} value={horizon}
          onChange={(e) => {
            const v = Number(e.target.value);
            setHorizon(v); queueSave({ cutoff, horizon: v });
          }}
          style={{ width: '100%' }}
        />
      </label>
    </section>
  );
}
```

**Step 2: Mount in AutobookingPage**

Append after BookingToggleCard:
```jsx
<PoliciesCard settings={data} />
```

**Step 3: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 4: Commit**

```bash
git add miniapp/src/master/components/autobooking/PoliciesCard.jsx miniapp/src/master/pages/AutobookingPage.jsx
git commit -m "feat(miniapp): policy sliders for cancel cutoff + booking horizon"
```

---

## Task 7: Services.jsx duration field + MissingDurationWarning

**Files:**
- Modify: `miniapp/src/master/pages/Services.jsx` (add `duration_minutes` field to create/edit form)
- Create: `miniapp/src/master/components/autobooking/MissingDurationWarning.jsx`
- Modify: `miniapp/src/master/pages/AutobookingPage.jsx` (mount the warning)

**Step 1: Services.jsx field**

Grep for the existing service-form input in Services.jsx (likely there's a price `<input type="number">`). Add right below it:

```jsx
<label style={{ display: 'block', marginTop: 8 }}>
  <span style={{ fontSize: 13 }}>{t('service_duration_label')}</span>
  <input
    type="number" min={15} step={15}
    value={formState.duration_minutes ?? 60}
    onChange={(e) => setFormState(s => ({ ...s, duration_minutes: Number(e.target.value) }))}
    style={{ width: '100%', padding: 8 }}
  />
</label>
```

Adjust to the file's actual form-state pattern (could be useState, useReducer, or react-hook-form). The form's submit handler likely posts to `createMasterService` / `updateMasterService` — those already pass extra fields through to the backend.

**Step 2: MissingDurationWarning component**

```jsx
// miniapp/src/master/components/autobooking/MissingDurationWarning.jsx
import { useQuery } from '@tanstack/react-query';
import { getServices } from '../../../api/client';
import { useI18n } from '../../../i18n';

export default function MissingDurationWarning({ onGotoServices }) {
  const { t } = useI18n();
  const { data: services } = useQuery({ queryKey: ['services'], queryFn: getServices });

  // Heuristic: if ALL services still sit at exactly 60, treat as "never touched".
  // False positives (master genuinely wants 60-min everything) self-resolve after one edit.
  const needsAttention =
    services && services.length > 0 &&
    services.every(s => (s.duration_minutes ?? 60) === 60);

  if (!needsAttention) return null;

  return (
    <section style={{
      background: '#fff7e0', borderRadius: 12, padding: 12,
      marginBottom: 12, fontSize: 13,
    }}>
      <strong>⚠ {t('missing_duration_warning_title')}</strong>
      <p style={{ margin: '6px 0' }}>{t('missing_duration_warning_body')}</p>
      <button onClick={onGotoServices} style={{
        background: 'transparent', border: 'none', color: '#1a73e8',
        padding: 0, fontSize: 13,
      }}>
        {t('missing_duration_warning_cta')} →
      </button>
    </section>
  );
}
```

Confirm `getServices` exists in `api/client.js`; if not, use the closest equivalent (likely it's already there since Services.jsx works).

**Step 3: Mount in AutobookingPage**

Between BookingToggleCard and PoliciesCard:
```jsx
<MissingDurationWarning onGotoServices={() => onNavigate('services')} />
```

**Step 4: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/Services.jsx \
        miniapp/src/master/components/autobooking/MissingDurationWarning.jsx \
        miniapp/src/master/pages/AutobookingPage.jsx
git commit -m "feat(miniapp): service duration_minutes field + missing-duration warning"
```

---

## Task 8: WeeklyScheduleCard + DayIntervalsSheet

The biggest task. Splitting into one commit is fine because the card is unusable without the sheet.

**Files:**
- Create: `miniapp/src/master/components/autobooking/WeeklyScheduleCard.jsx`
- Create: `miniapp/src/master/components/autobooking/DayIntervalsSheet.jsx`
- Modify: `miniapp/src/master/pages/AutobookingPage.jsx` (mount the card)

**Step 1: Sheet component**

```jsx
// miniapp/src/master/components/autobooking/DayIntervalsSheet.jsx
import { useState } from 'react';
import { useI18n } from '../../../i18n';

const DAY_KEY = ['day_short_mon','day_short_tue','day_short_wed',
                  'day_short_thu','day_short_fri','day_short_sat','day_short_sun'];

export default function DayIntervalsSheet({
  weekday,           // 0..6
  initialIntervals,  // [{start,end}, ...]
  onClose,
  onSave,            // (intervalsForThisDay, applyToWeekdays) => void
}) {
  const { t } = useI18n();
  const [rows, setRows] = useState(initialIntervals.length ? initialIntervals : [{ start: '10:00', end: '18:00' }]);
  const [applyAll, setApplyAll] = useState(false);

  const setRow = (i, k, v) => setRows(rs => rs.map((r, idx) => idx === i ? { ...r, [k]: v } : r));
  const removeRow = (i) => setRows(rs => rs.filter((_, idx) => idx !== i));
  const addRow = () => setRows(rs => [...rs, { start: '10:00', end: '18:00' }]);

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'flex-end', zIndex: 100,
    }} onClick={onClose}>
      <div style={{ background: '#fff', width: '100%', borderRadius: '16px 16px 0 0', padding: 16 }}
           onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 12px' }}>{t(DAY_KEY[weekday])}</h3>

        {rows.map((r, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
            <input type="time" value={r.start} onChange={(e) => setRow(i, 'start', e.target.value)} />
            <span>—</span>
            <input type="time" value={r.end} onChange={(e) => setRow(i, 'end', e.target.value)} />
            <button onClick={() => removeRow(i)} style={{ marginLeft: 'auto' }}>✕</button>
          </div>
        ))}

        <button onClick={addRow} style={{ marginTop: 8 }}>+ {t('interval_add')}</button>

        {weekday < 5 && (
          <label style={{ display: 'block', marginTop: 16, fontSize: 13 }}>
            <input type="checkbox" checked={applyAll} onChange={(e) => setApplyAll(e.target.checked)} />
            {' '}{t('weekly_apply_to_weekdays')}
          </label>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={onClose} style={{ flex: 1 }}>{t('cancel')}</button>
          <button onClick={() => onSave(rows, applyAll)} style={{ flex: 1 }}>{t('save')}</button>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Card component**

```jsx
// miniapp/src/master/components/autobooking/WeeklyScheduleCard.jsx
import { useState } from 'react';
import { useI18n } from '../../../i18n';
import { useReplaceWeeklySchedule } from '../../hooks/useBookingSettings';
import DayIntervalsSheet from './DayIntervalsSheet';

const DAY_KEYS = ['day_short_mon','day_short_tue','day_short_wed',
                  'day_short_thu','day_short_fri','day_short_sat','day_short_sun'];

function summarise(intervals, tDayOff) {
  if (!intervals.length) return tDayOff;
  return intervals.map(i => `${i.start_time}-${i.end_time}`).join(', ');
}

export default function WeeklyScheduleCard({ settings }) {
  const { t } = useI18n();
  const replaceMut = useReplaceWeeklySchedule();
  const [editingDay, setEditingDay] = useState(null);

  const weekly = settings.weekly ?? [];
  const byDay = (d) => weekly.filter(i => i.weekday === d);

  const handleSave = (rows, applyToWeekdays) => {
    // Build new full-7-day array. Keep other days' intervals untouched
    // (or overwrite Mon-Fri with `rows` if applyToWeekdays).
    const next = [];
    for (let d = 0; d < 7; d++) {
      const dayRows = (applyToWeekdays && d < 5) ? rows
                    : (d === editingDay)        ? rows
                    : byDay(d).map(i => ({ start: i.start_time, end: i.end_time }));
      dayRows.forEach(r => next.push({ weekday: d, start: r.start, end: r.end }));
    }
    replaceMut.mutate(next);
    setEditingDay(null);
  };

  return (
    <section style={{ background: 'var(--tg-card-bg, #fff)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{t('weekly_schedule_title')}</h3>

      {DAY_KEYS.map((k, d) => (
        <button
          key={d}
          onClick={() => setEditingDay(d)}
          style={{
            display: 'flex', justifyContent: 'space-between', width: '100%',
            background: 'transparent', border: 'none', padding: '10px 0',
            borderBottom: '1px solid #eee', fontSize: 14, cursor: 'pointer',
          }}
        >
          <span>{t(k)}</span>
          <span style={{ color: byDay(d).length ? 'inherit' : '#888' }}>
            {summarise(byDay(d), t('day_off'))} ›
          </span>
        </button>
      ))}

      {editingDay !== null && (
        <DayIntervalsSheet
          weekday={editingDay}
          initialIntervals={byDay(editingDay).map(i => ({ start: i.start_time, end: i.end_time }))}
          onClose={() => setEditingDay(null)}
          onSave={handleSave}
        />
      )}
    </section>
  );
}
```

**Step 3: Mount in AutobookingPage**

After MissingDurationWarning:
```jsx
<WeeklyScheduleCard settings={data} />
```

**Step 4: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 5: Commit**

```bash
git add miniapp/src/master/components/autobooking/WeeklyScheduleCard.jsx \
        miniapp/src/master/components/autobooking/DayIntervalsSheet.jsx \
        miniapp/src/master/pages/AutobookingPage.jsx
git commit -m "feat(miniapp): weekly schedule editor with per-day bottom-sheet"
```

---

## Task 9: ExceptionsCard + DateExceptionSheet

**Files:**
- Create: `miniapp/src/master/components/autobooking/ExceptionsCard.jsx`
- Create: `miniapp/src/master/components/autobooking/DateExceptionSheet.jsx`
- Modify: `miniapp/src/master/pages/AutobookingPage.jsx` (mount)

**Step 1: Sheet component**

```jsx
// miniapp/src/master/components/autobooking/DateExceptionSheet.jsx
import { useState } from 'react';
import { useI18n } from '../../../i18n';

export default function DateExceptionSheet({
  date,              // 'YYYY-MM-DD'
  existing,          // null or {id, kind, start_time, end_time}
  onClose,
  onSubmit,          // (action, payload) — action: 'delete'|'upsert'
}) {
  const { t } = useI18n();
  const initialKind = existing?.kind ?? null;
  const [kind, setKind] = useState(initialKind);
  const [start, setStart] = useState(existing?.start_time ?? '10:00');
  const [end, setEnd] = useState(existing?.end_time ?? '18:00');

  const save = () => {
    if (kind === null) {
      if (existing) onSubmit('delete', existing.id);
      else onClose();
      return;
    }
    onSubmit('upsert', {
      existingId: existing?.id ?? null,
      body: { date, kind, start: kind === 'override' ? start : null, end: kind === 'override' ? end : null },
    });
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
                  display: 'flex', alignItems: 'flex-end', zIndex: 100 }} onClick={onClose}>
      <div style={{ background: '#fff', width: '100%', borderRadius: '16px 16px 0 0', padding: 16 }}
           onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 12px' }}>{date}</h3>

        <label style={{ display: 'block', padding: '8px 0' }}>
          <input type="radio" checked={kind === null} onChange={() => setKind(null)} /> {t('exception_as_usual')}
        </label>
        <label style={{ display: 'block', padding: '8px 0' }}>
          <input type="radio" checked={kind === 'off'} onChange={() => setKind('off')} /> {t('exception_off')}
        </label>
        <label style={{ display: 'block', padding: '8px 0' }}>
          <input type="radio" checked={kind === 'override'} onChange={() => setKind('override')} /> {t('exception_override')}
        </label>

        {kind === 'override' && (
          <div style={{ display: 'flex', gap: 8, margin: '8px 0' }}>
            <input type="time" value={start} onChange={(e) => setStart(e.target.value)} />
            <span>—</span>
            <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={onClose} style={{ flex: 1 }}>{t('cancel')}</button>
          <button onClick={save} style={{ flex: 1 }}>{t('save')}</button>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Card component**

```jsx
// miniapp/src/master/components/autobooking/ExceptionsCard.jsx
import { useState } from 'react';
import { useI18n } from '../../../i18n';
import {
  useAddScheduleException, useRemoveScheduleException,
} from '../../hooks/useBookingSettings';
import DateExceptionSheet from './DateExceptionSheet';

function isoDate(d) {
  // YYYY-MM-DD in local tz. Hand-rolled — no library.
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function buildDates(horizonDays) {
  const out = [];
  const today = new Date();
  for (let i = 0; i < horizonDays; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    out.push({ iso: isoDate(d), label: `${d.getDate()}.${d.getMonth() + 1}` });
  }
  return out;
}

export default function ExceptionsCard({ settings }) {
  const { t } = useI18n();
  const [picking, setPicking] = useState(null); // 'YYYY-MM-DD' or null
  const addMut = useAddScheduleException();
  const removeMut = useRemoveScheduleException();

  const exceptions = settings.exceptions ?? [];
  const byIso = Object.fromEntries(exceptions.map(e => [e.date, e]));
  const dates = buildDates(settings.horizon_days || 30);

  const submit = async (action, payload) => {
    if (action === 'delete') {
      removeMut.mutate(payload);
    } else if (action === 'upsert') {
      // If editing existing of different kind, delete-then-add (simplest).
      if (payload.existingId) removeMut.mutate(payload.existingId);
      addMut.mutate(payload.body);
    }
    setPicking(null);
  };

  return (
    <section style={{ background: 'var(--tg-card-bg, #fff)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{t('exceptions_title')}</h3>

      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '4px 0' }}>
        {dates.map(d => {
          const exc = byIso[d.iso];
          const bg = !exc ? '#f3f4f6' : exc.kind === 'off' ? '#fee2e2' : '#dbeafe';
          return (
            <button key={d.iso} onClick={() => setPicking(d.iso)}
              style={{
                flex: '0 0 auto', padding: '6px 10px', borderRadius: 8,
                border: '1px solid #ddd', background: bg, fontSize: 13,
              }}>
              {d.label}
            </button>
          );
        })}
      </div>

      {exceptions.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, marginTop: 12, fontSize: 13 }}>
          {[...exceptions].sort((a, b) => a.date.localeCompare(b.date)).map(e => (
            <li key={e.id} style={{ padding: '6px 0', display: 'flex', justifyContent: 'space-between' }}>
              <span>{e.date} — {e.kind === 'off' ? t('exception_off') : `${e.start_time}–${e.end_time}`}</span>
              <button onClick={() => removeMut.mutate(e.id)} style={{ background: 'transparent', border: 'none' }}>✕</button>
            </li>
          ))}
        </ul>
      )}

      {picking && (
        <DateExceptionSheet
          date={picking}
          existing={byIso[picking] ?? null}
          onClose={() => setPicking(null)}
          onSubmit={submit}
        />
      )}
    </section>
  );
}
```

**Step 3: Mount in AutobookingPage**

After WeeklyScheduleCard:
```jsx
<ExceptionsCard settings={data} />
```

**Step 4: Build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 5: Commit**

```bash
git add miniapp/src/master/components/autobooking/ExceptionsCard.jsx \
        miniapp/src/master/components/autobooking/DateExceptionSheet.jsx \
        miniapp/src/master/pages/AutobookingPage.jsx
git commit -m "feat(miniapp): date exceptions strip + per-date bottom-sheet"
```

---

## Task 10: Final polish — disabled-state styling + ESLint + manual smoke

**Files:**
- Modify: `miniapp/src/master/pages/AutobookingPage.jsx`

**Step 1: Disabled-state visual**

Wrap the non-toggle cards so they dim when the toggle is off (master can still edit; this is UX-only):

```jsx
<div style={{ opacity: data.enabled ? 1 : 0.65, pointerEvents: 'auto' }}>
  <MissingDurationWarning onGotoServices={() => onNavigate('services')} />
  <WeeklyScheduleCard settings={data} />
  <ExceptionsCard settings={data} />
  <PoliciesCard settings={data} />
</div>
```

(BookingToggleCard stays outside this wrapper — full opacity, always editable.)

**Step 2: Targeted lint**

```bash
cd miniapp && npx eslint src/master/pages/AutobookingPage.jsx \
                       src/master/components/autobooking/ \
                       src/master/hooks/useBookingSettings.js
```
Expected: clean. If warnings about unused imports / undef vars — fix them now.

(Full `npm run lint` is known-broken on legacy files — don't run it.)

**Step 3: Final build**

```bash
cd miniapp && npm run build
```
Expected: PASS.

**Step 4: Manual smoke (developer first)**

```bash
cd miniapp && npm run dev
# In Telegram desktop or browser with mocked initData:
#   1. Master Mini App → More → Автозапись loads.
#   2. Toggle on — backend gets enabled=true.
#   3. Tap Пн → sheet opens → add 10:00-14:00 interval → Save.
#   4. Slider cutoff to 12h — backend gets cutoff=12.
#   5. Date strip — tap a date → "Выходной" → Save → chip turns red.
#   6. Toggle off — other cards dim but stay clickable.
#   7. Reload page — settings persisted.
```

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/AutobookingPage.jsx
git commit -m "feat(miniapp): dim non-toggle cards when autobooking is off"
```

---

## Verification pass (after all tasks)

```bash
cd miniapp && npm run build
```
Expected: success.

```bash
cd miniapp && npx eslint src/master/pages/AutobookingPage.jsx src/master/components/autobooking/ src/master/hooks/
```
Expected: clean.

Backend regression (the API contract this UI consumes):
```bash
env BONUS_MEDIA_DIR=/tmp/mb_test/bm AVATARS_DIR=/tmp/mb_test/av \
    PORTFOLIO_DIR=/tmp/mb_test/pf PROMO_MEDIA_DIR=/tmp/mb_test/pm \
    BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test \
    python3.11 -m unittest discover -s tests
```
Expected: 130/130 OK (unchanged).

---

## Deploy

This is a **miniapp-only** change — backend stays at `6dac549`. Per project CLAUDE.md → Deploy Rules:

```bash
# Locally:
bash deploy_miniapp.sh
```

(Reminder from feedback-memory: deploy_miniapp.sh runs from the developer machine, not from VPS — Vite v8 is incompatible with VPS Node v18.)

After deploy, verify in production: open Mini App as a pilot master, check that More → Автозапись renders and persists changes.

---

## Out of scope (re-confirmed)

- Vitest/Jest/RTL setup
- TypeScript migration
- Drag-to-reorder of intervals
- Bulk schedule import
- Dedicated "self-bookings" tab in master Calendar (orders already appear in shared calendar)
- Settings preview ("what does the client see")

All listed in design doc §10.

---

## Risk register for implementation

1. **`<input type="time">` on iOS** may behave differently than Android. Caught at manual smoke — fallback is two `<select>` (hours, minutes), ~20 LOC change.
2. **`replaceWeeklySchedule` ships full bundle every save** — rapid edits hit the API multiple times. Acceptable on pilot scale (5 masters). Coalesce later if needed.
3. **MissingDurationWarning's 60-min heuristic** false-positives for "genuinely 60-min-everything" masters. They edit one service once → warning gone. Acceptable.
4. **Optimistic patch shape** in `useReplaceWeeklySchedule` assumes the server's `weekly` payload shape (`{id, weekday, start_time, end_time}`). If the actual response differs after invalidate-refetch, you'll see brief flicker. Verify shape at first manual smoke.
