# Master Mini App UI Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify all master Mini App screens visually — remove "разрезающие полосы", add missing page headers, fix OrderCreate UX with immediate client list.

**Architecture:** Extend existing `enterprise-*` CSS system. No new design systems, no backend changes. Each task is one screen or component — commit after each.

**Tech Stack:** React 19, Vite, lucide-react (new), CSS in `miniapp/src/theme.css`, @tanstack/react-query

---

## Task 1: Install lucide-react and replace emoji icons in Dashboard StatCards

**Files:**
- Modify: `miniapp/package.json`
- Modify: `miniapp/src/master/pages/Dashboard.jsx`
- Modify: `miniapp/src/master/components/StatCard.jsx`

**Step 1: Install lucide-react**

Run in `miniapp/` directory:
```bash
cd miniapp && npm install lucide-react
```

Expected: `package.json` gains `"lucide-react": "^X.Y.Z"` in dependencies.

**Step 2: Update StatCard to handle SVG icon sizing**

In `StatCard.jsx` the icon wrapper div currently has `fontSize: 18` which sizes emoji. SVG icons use `size` prop, not fontSize. Remove `fontSize` from the icon wrapper and set `display: inline-flex; alignItems: center; justifyContent: center` (already present). Replace:

```jsx
// OLD — line 34-36 in StatCard.jsx
  background: 'rgba(79, 156, 249, 0.12)',
  color: 'var(--tg-accent)',
  fontSize: 18,
  lineHeight: 1,
```

with:

```jsx
  background: 'rgba(79, 156, 249, 0.12)',
  color: 'var(--tg-accent)',
```

**Step 3: Replace emoji strings with Lucide icons in Dashboard.jsx**

Add import at top of `Dashboard.jsx`:
```jsx
import { TrendingUp, CalendarDays, CheckCircle2, Users } from 'lucide-react';
```

In `DashboardContent` replace the four `<StatCard icon="...">` calls (around line 258–261):

```jsx
<StatCard icon={<TrendingUp size={20} />} value={formatCurrency(stats.week_revenue || 0, locale)} label={tr('Выручка за неделю', 'Revenue this week')} onClick={handleReportsWeek} />
<StatCard icon={<CalendarDays size={20} />} value={formatCurrency(stats.month_revenue || 0, locale)} label={tr('Выручка за месяц', 'Revenue this month')} onClick={handleReportsMonth} />
<StatCard icon={<CheckCircle2 size={20} />} value={stats.week_orders || 0} label={tr('Заказов за неделю', 'Orders this week')} />
<StatCard icon={<Users size={20} />} value={stats.total_clients || 0} label={tr('Всего клиентов', 'Total clients')} onClick={handleClients} />
```

**Step 4: Verify build**

```bash
cd miniapp && npm run build
```

Expected: Build completes. No errors about missing imports.

**Step 5: Commit**

```bash
git add miniapp/package.json miniapp/package-lock.json miniapp/src/master/pages/Dashboard.jsx miniapp/src/master/components/StatCard.jsx
git commit -m "Replace emoji icons with lucide-react in dashboard stat cards"
```

---

## Task 2: Fix ClientsList — remove dividers, wrap in enterprise card

**Files:**
- Modify: `miniapp/src/master/pages/ClientsList.jsx`

**Step 1: Remove borderBottom from sticky search wrapper**

In `ClientsList.jsx` around line 133–140, find the sticky wrapper div:
```jsx
<div style={{
  position: 'sticky',
  top: 0,
  zIndex: 10,
  background: 'var(--tg-bg)',
  padding: '12px 16px',
  borderBottom: '1px solid rgba(255,255,255,0.06)',   // ← REMOVE this line
}}>
```

Remove the `borderBottom` line entirely. Keep everything else.

**Step 2: Replace bare list container with enterprise-cell-group**

Find around line 207–208:
```jsx
<div style={{ background: 'var(--tg-section-bg)' }}>
```

Replace with:
```jsx
<div className="enterprise-cell-group" style={{ margin: '0 12px' }}>
```

Note: `enterprise-cell-group` already has `margin: 0 12px` from the theme, but inline override is needed because the sticky search is `padding: 12px 16px` — keep consistent. Actually just use className only:

```jsx
<div className="enterprise-cell-group">
```

**Step 3: Remove inline borderBottom from each client row**

Find the `clients.map(...)` render block around line 209. Each row div has:
```jsx
borderBottom: idx < clients.length - 1
  ? '1px solid var(--tg-secondary-bg)'
  : 'none',
```

Remove the `borderBottom` prop entirely. The `enterprise-cell-group` CSS handles separators via `::after` pseudo-elements on the inner content, but since we have a plain `<div>` (not `enterprise-cell` class), add `className` to each row div:

Replace the row's outer `<div onClick=... style=...>` with:
```jsx
<div
  key={client.id}
  onClick={() => handleClientClick(client)}
  className="enterprise-cell is-interactive"
  style={{ cursor: 'pointer' }}
>
```

Remove from the inline style: `display`, `alignItems`, `padding`, `cursor`, `borderBottom`, `gap` — these are now handled by `enterprise-cell`. Keep only what `enterprise-cell` doesn't cover (nothing extra is needed).

The inner structure (avatar + info div + balance) stays unchanged.

**Step 4: Verify build**

```bash
cd miniapp && npm run build
```

Expected: Build passes. ClientsList renders without style errors.

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/ClientsList.jsx
git commit -m "Fix clients list — remove dividers, use enterprise card"
```

---

## Task 3: Fix Calendar — add page header

**Files:**
- Modify: `miniapp/src/master/pages/Calendar.jsx`

**Step 1: Add a formatted month title helper**

At the top of `Calendar.jsx` (after existing helpers), add:

```jsx
function formatMonthTitle(year, month, locale) {
  return new Date(year, month - 1, 1)
    .toLocaleDateString(locale, { month: 'long', year: 'numeric' });
}
```

**Step 2: Replace root div inline styles with enterprise-page class**

Find the root return (line 81):
```jsx
return (
  <div style={{ paddingBottom: 88, minHeight: '100vh', background: 'var(--tg-bg)' }}>
```

Replace with:
```jsx
return (
  <div className="enterprise-page" style={{ paddingBottom: 0 }}>
```

The `enterprise-page` class provides `padding: 18px 0 108px`. Override `paddingBottom: 0` because `DaySchedule` already has its own bottom spacing.

**Step 3: Add page header before the sticky calendar block**

Insert a header block between the root div opening tag and the sticky calendar comment:

```jsx
{/* Page header */}
<div className="enterprise-page-inner" style={{ marginBottom: 14 }}>
  <h2 className="enterprise-page-title">{tr('Календарь', 'Calendar')}</h2>
  <p className="enterprise-page-subtitle">
    {formatMonthTitle(viewYear, viewMonth, locale)}
  </p>
</div>
```

This requires `locale` in scope. `Calendar` component doesn't currently use `useI18n`. Add at the top of `Calendar`:
```jsx
const { tr, locale } = useI18n();
```

`useI18n` is already imported in the file (used by child components like `DaySchedule`). Add the import if missing:
```jsx
import { useI18n } from '../../i18n';
```

**Step 4: Remove background from sticky wrapper**

The sticky calendar wrapper currently has explicit `background: 'var(--tg-bg)'`. This is now unnecessary because the page header sits above it. Keep the `position: sticky` but the background can stay for scroll overlap — no change needed here.

**Step 5: Verify build**

```bash
cd miniapp && npm run build
```

Expected: Build passes. No undefined variable errors.

**Step 6: Commit**

```bash
git add miniapp/src/master/pages/Calendar.jsx
git commit -m "Add page header to calendar screen"
```

---

## Task 4: Fix Requests — page header, remove visual stripe

**Files:**
- Modify: `miniapp/src/master/pages/Requests.jsx`
- Modify: `miniapp/src/theme.css`

**Step 1: Remove sticky + gradient from requests-filter-wrap**

The `requests-filter-wrap` uses `position: sticky; top: 0` with a gradient background — this creates the visible horizontal stripe. Since the filter has only 3 options and doesn't need to stick (users don't scroll past it before seeing content), remove stickiness.

In `theme.css`, find `.requests-filter-wrap` (line 2685):
```css
body.typeui-enterprise-body .requests-filter-wrap {
  position: sticky;
  top: 0;
  z-index: 20;
  margin: 0 -12px;
  padding: 4px 12px 12px;
  background: linear-gradient(180deg, rgba(11, 22, 34, 0.96), rgba(11, 22, 34, 0.76) 70%, rgba(11, 22, 34, 0));
  backdrop-filter: blur(14px);
}
```

Replace with:
```css
body.typeui-enterprise-body .requests-filter-wrap {
  margin: 0 0 12px;
  padding: 0;
}
```

**Step 2: Increase requests-page top padding**

In `theme.css`, find `.requests-page` (line 2656):
```css
body.typeui-enterprise-body .requests-page {
  padding: 14px 12px 94px;
}
```

Replace with:
```css
body.typeui-enterprise-body .requests-page {
  padding: 18px 12px 108px;
}
```

**Step 3: Update requests-header to use enterprise-page-title style**

In `Requests.jsx`, find the `requests-header` block (line ~429):
```jsx
<div className="requests-header">
  <h1>{tr('Заявки', 'Requests')}</h1>
  {unreadCount > 0 && <span className="requests-unread-pill">...</span>}
</div>
```

Replace with:
```jsx
<div className="requests-header">
  <h2 className="enterprise-page-title">{tr('Заявки', 'Requests')}</h2>
  {unreadCount > 0 && <span className="requests-unread-pill">{tr('Новых', 'New')}: {unreadCount}</span>}
</div>
```

Also update `.requests-header h1` in `theme.css` since we switched to `h2.enterprise-page-title`. The CSS rule at line 2667 can be removed (or kept harmlessly):
```css
/* Remove this rule — enterprise-page-title handles styling now */
body.typeui-enterprise-body .requests-header h1 { ... }
```

**Step 4: Verify build**

```bash
cd miniapp && npm run build
```

Expected: Build passes.

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/Requests.jsx miniapp/src/theme.css
git commit -m "Fix requests page header and remove filter stripe"
```

---

## Task 5: Fix OrderCreate — immediate client list, no autoFocus, search+button row

**Files:**
- Modify: `miniapp/src/master/pages/OrderCreate.jsx`

**Step 1: Import getMasterClients**

At the top of `OrderCreate.jsx`, add `getMasterClients` to the existing import:
```jsx
import {
  searchMasterClients,
  getMasterClients,      // ← add this
  getMasterServices,
  ...
} from '../../api/client';
```

**Step 2: Remove autoFocus and add initial client query in StepClient**

In `StepClient` function (line 89), add a query for the initial client list:
```jsx
const { data: allClientsData, isFetching: allClientsFetching } = useQuery({
  queryKey: ['master-clients-all-order'],
  queryFn: () => getMasterClients('', 1),
  staleTime: 60_000,
});
```

**Step 3: Derive visible clients**

After the existing `const clients = data?.clients || [];` line, add:

```jsx
const allClients = [...(allClientsData?.clients || [])].sort((a, b) =>
  a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })
);

const searchClients = [...clients].sort((a, b) =>
  a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })
);

const visibleClients = debouncedQuery.length > 0 ? searchClients : allClients;
const isLoadingClients = debouncedQuery.length > 0 ? isFetching : allClientsFetching;
```

**Step 4: Remove autoFocus from input**

In `StepClient` return, find the `<input ... autoFocus ...>` (line 126) and remove the `autoFocus` prop.

**Step 5: Put search and "+ Новый клиент" button on one row**

Replace the current layout (hint text → full-width input → full-width "+ Новый клиент" button) with:

```jsx
return (
  <div style={{ padding: '0 16px 16px' }}>
    {/* Search + add-client row */}
    <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder={tr('Поиск клиента...', 'Search client...')}
        style={{
          flex: 1,
          padding: '10px 12px',
          fontSize: 15,
          background: 'var(--tg-secondary-bg)',
          color: 'var(--tg-text)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 10,
          outline: 'none',
        }}
      />
      {!selected && (
        <button
          type="button"
          onClick={() => { haptic(); setShowAddSheet(true); }}
          style={{
            flexShrink: 0,
            padding: '10px 14px',
            background: 'none',
            border: '1.5px solid var(--tg-button)',
            borderRadius: 10,
            color: 'var(--tg-button)',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {tr('+ Клиент', '+ Client')}
        </button>
      )}
    </div>

    {/* Selected client chip */}
    {selected && (
      <div style={{
        marginBottom: 12,
        padding: '10px 12px',
        background: 'var(--tg-button)',
        color: 'var(--tg-button-text)',
        borderRadius: 10,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{selected.name}</div>
          <div style={{ fontSize: 12, opacity: 0.85 }}>{selected.phone}</div>
        </div>
        <button
          type="button"
          onClick={() => { haptic(); onSelect(null); }}
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            color: 'var(--tg-button-text)',
            borderRadius: 6,
            padding: '4px 8px',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          {tr('Изменить', 'Change')}
        </button>
      </div>
    )}

    {/* Client list */}
    {!selected && (
      <div className="enterprise-cell-group" style={{ marginBottom: 16 }}>
        {isLoadingClients && (
          <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13 }}>
            {tr('Загрузка...', 'Loading...')}
          </div>
        )}
        {!isLoadingClients && visibleClients.length === 0 && (
          <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13 }}>
            {debouncedQuery
              ? tr('Клиенты не найдены', 'No clients found')
              : tr('Нет клиентов', 'No clients')}
          </div>
        )}
        {visibleClients.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => { haptic(); onSelect(c); }}
            className="enterprise-cell is-interactive"
          >
            <div style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: 'var(--tg-accent)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: 14,
              flexShrink: 0,
            }}>
              {(c.name || '?')[0].toUpperCase()}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--tg-hint)' }}>{c.phone}</div>
            </div>
          </button>
        ))}
      </div>
    )}

    {/* Next button */}
    <button
      type="button"
      onClick={() => { haptic(); onNext(); }}
      disabled={!selected}
      className="enterprise-btn-primary"
      style={!selected ? { opacity: 0.45, cursor: 'not-allowed' } : {}}
    >
      {tr('Далее →', 'Next ->')}
    </button>

    {showAddSheet && (
      <ClientAddSheet
        onSuccess={(client) => {
          haptic();
          setShowAddSheet(false);
          onSelect(client);
          onNext();
        }}
        onClose={() => setShowAddSheet(false)}
      />
    )}
  </div>
);
```

**Step 6: Verify build**

```bash
cd miniapp && npm run build
```

Expected: Build passes. No missing variable errors.

**Step 7: Commit**

```bash
git add miniapp/src/master/pages/OrderCreate.jsx
git commit -m "Rework order create step 1 — immediate client list, no autofocus"
```

---

## Task 6: Final build verification

**Step 1: Full clean build**

```bash
cd miniapp && npm run build
```

Expected: Build succeeds with no errors. Note: `npm run lint` may have pre-existing warnings — these are known and out of scope.

**Step 2: Check working tree**

```bash
git status --short
```

Expected: Clean tree after all task commits.

**Step 3: Manual QA checklist**

Open the Mini App in Telegram and verify:

1. Dashboard — stat cards show Lucide icons (not emoji), cards look the same
2. Clients list — list is inside a rounded card, no horizontal dividers on bare background
3. Calendar — page title "Календарь" with month subtitle visible above the calendar card
4. Requests — title "Заявки" with proper top spacing, no gradient stripe above filter tabs
5. New order → step 1 — keyboard does NOT open automatically; all clients visible in scrollable list sorted alphabetically; search and "+ Клиент" on one line; tapping search opens keyboard

---

## Self-review

- No backend changes
- No new CSS systems — only `enterprise-*` classes already in `theme.css`
- 5 focused commits, one per screen
- `npm run build` gate after every task
- `lucide-react` is the only new dependency (well-maintained, tree-shakeable)
