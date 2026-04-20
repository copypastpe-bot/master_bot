# Master Mini App UI Unification — Design Doc

**Date:** 2026-04-20  
**Status:** Approved  
**Approach:** Variant B — enterprise-class unification

---

## Goal

Bring all master Mini App screens into a consistent visual style using the existing `enterprise-*` CSS system. Remove "разрезающие полосы" (horizontal dividers on bare backgrounds), add missing page headers, unify the Requests filter, improve OrderCreate UX.

---

## Scope

Five areas of change. The "Ещё" screen is excluded — user confirmed it is already correct.

---

## Section 1 — Icons (Dashboard StatCards)

Install `lucide-react` as a production dependency. Replace emoji strings in `StatCard` icon prop with Lucide JSX components:

| Metric | Icon |
|--------|------|
| Выручка за неделю | `<TrendingUp size={22} />` |
| Выручка за месяц | `<CalendarDays size={22} />` |
| Заказов за неделю | `<CheckCircle2 size={22} />` |
| Всего клиентов | `<Users size={22} />` |

`StatCard` already accepts `icon` as a prop — no structural changes needed.

---

## Section 2 — ClientsList

**Problem:** client rows sit on bare `var(--tg-section-bg)` with inline `borderBottom` — looks like raw dividers.

**Fix:**
- Wrap the client list in `enterprise-cell-group` (rounded card, internal separators handled by CSS)
- Remove inline `borderBottom` from each client row
- Remove `borderBottom` from sticky search wrapper — replace with `paddingBottom` only

No logic changes. Infinite scroll and search stay intact.

---

## Section 3 — Calendar

**Problem:** no page header, first calendar card starts immediately after the Telegram system zone.

**Fix:**
- Add a page header above the sticky calendar block using `enterprise-page-inner` + `enterprise-page-title` + `enterprise-page-subtitle`
- Title: "Календарь"
- Subtitle: current month/year formatted string (derived from `viewYear`/`viewMonth` state)
- Sticky calendar block keeps its behavior, just no longer at y=0

---

## Section 4 — Requests

**Problem:** "Заявки" title is at the raw top edge; filter tabs (`requests-filter`) are flat and create a visual stripe.

**Fix:**
- Wrap title in `enterprise-page-inner` / `enterprise-page-title` pattern (same as Dashboard greeting)
- Replace `requests-filter-wrap` + `requests-filter` with an `enterprise-cell-group` containing three `enterprise-cell` buttons
- Active tab: highlighted with `enterprise-btn-primary` accent style
- Empty state card: use `enterprise-cell-group` + `enterprise-orders-empty` for consistency

---

## Section 5 — OrderCreate

**Problem:** keyboard auto-opens on entry; no client list visible; "+ Новый клиент" occupies full width; no alphabetical list.

**Fix:**
- Remove `autoFocus` from search input
- Load all clients immediately on step 1 mount via `getMasterClients('', 1)`; sort alphabetically by name
- Search input and "+ Новый клиент" button share one row (flexbox: input `flex:1`, button fixed width ~120px)
- Visible scrollable client list below the search row, always shown
- Search filters the loaded list client-side (for the initial page); debounced API search kicks in for queries > 1 char
- Remove top divider/stripe (same bare `borderBottom` pattern as ClientsList)

---

## Files Affected

| File | Change |
|------|--------|
| `miniapp/package.json` | add `lucide-react` |
| `miniapp/src/master/components/StatCard.jsx` | accept Lucide icon JSX, style icon wrapper |
| `miniapp/src/master/pages/Dashboard.jsx` | pass Lucide icons to StatCard |
| `miniapp/src/master/pages/ClientsList.jsx` | enterprise-cell-group wrapper, remove inline borderBottom |
| `miniapp/src/master/pages/Calendar.jsx` | add page header, remove inline styles |
| `miniapp/src/master/pages/Requests.jsx` | page header + enterprise filter tabs |
| `miniapp/src/master/pages/OrderCreate.jsx` | immediate client list, search+button row, no autoFocus |
| `miniapp/src/theme.css` | minor additions if new utility classes needed |

---

## Constraints

- No backend changes
- No new design systems — only extend existing `enterprise-*` classes
- Each screen change is a self-contained commit
- `npm run build` must pass after each commit
