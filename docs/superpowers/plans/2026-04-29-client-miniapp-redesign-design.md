# Design: Client Mini App Redesign (Frontend)

**Date:** 2026-04-29
**Status:** approved
**Approach:** Variant A — targeted file replacement within existing `miniapp/src/` structure

---

## Context

Client Telegram Mini App is being redesigned. Backend API is already deployed (`f8514ca`). This document covers the frontend-only pass.

### Key clarifications vs TZ

1. **`confirmed_by_client` status** — backend does not use this as a `status` string. Instead it sets `orders.client_confirmed=true`. The backend computes `display_status` via `_client_display_status()` and returns it in every order object. Frontend uses `display_status` directly — no client-side status computation needed.

2. **Navigation model** — flat extended `setPage(pageId, params?)`. No stack. Sub-screens (`create_order`, `ask_question`, `landing`) hide BottomNav and show Telegram BackButton. Master select is a separate state flag.

3. **Invite flow** — when `start_param=invite_TOKEN`, show public landing first (load `/api/public/master/{token}`). User clicks «Подключиться» → `linkToMaster(token)` → reload masters → go to `home`. If already linked (409) — go to `home` directly.

4. **"Do not rewrite" screens** — `Contact.jsx` (BookingForm + QuestionForm) is the booking/question flow. Kept as-is with one minimal addition: `preselectedService` prop on `BookingForm`.

5. **`reminder_sent` field** — available as `display_status='reminder'` in order objects. Frontend switches on `display_status` string directly.

---

## Navigation Architecture

### ClientApp state

```js
state:
  tab: 'home' | 'history' | 'news' | 'settings'   // active bottom tab
  page: tab | 'create_order' | 'ask_question' | 'landing' | 'master_select'
  pageParams: { service?, masterId?, inviteToken? }
```

- `navigate(pageId, params?)` replaces current `setPage()`
- When `page` is a sub-screen (`create_order`, `ask_question`, `landing`): BottomNav hidden, Telegram BackButton shown → back to last tab
- Master select: `page='master_select'` → shows existing `MasterSelectScreen`
- Header shows current master name (tappable) → `navigate('master_select')`

### BottomNav tabs

| id | Label | Icon |
|----|-------|------|
| `home` | Главная | HomeIcon |
| `history` | История | ClockIcon |
| `news` | Новости | BellIcon |
| `settings` | Настройки | GearIcon |

Active tab tap → scroll to top. Tab switch → preserve scroll position per tab.

### App.jsx invite flow change

```
start_param = 'invite_TOKEN'
  ↓
role loaded → masters loaded
  ↓
show MasterLanding(mode='public', inviteToken=token)
  ↓ user clicks «Подключиться»
linkToMaster(token)
  ↓
reload masters → navigate('home')

if 409 (already linked) → navigate('home') directly
```

---

## Data Layer (`api/client.js` additions)

New functions added alongside existing ones:

```js
// Per-master client endpoints
getClientMasterProfile(masterId)
getClientMasterActivity(masterId, limit = 3)
getClientMasterServices(masterId)
getClientMasterNews(masterId)
getClientMasterHistory(masterId, limit, offset)
getClientMasterPublications(masterId, limit, offset)
getClientMasterSettings(masterId)
patchClientMasterSettings(masterId, patch)
getClientMasterReviews(masterId, limit, offset)

// Order actions
confirmClientOrder(orderId)
createClientOrderReview(orderId, { text, rating? })

// Public (no X-Init-Data header)
getPublicMasterProfile(inviteToken)

// Account
deleteClientProfile()
```

Existing functions (`getMe`, `getOrders`, `getBonuses`, `getServices`, `getPromos`, etc.) are preserved — used by master flow and `Contact.jsx`.

---

## Screens

### `pages/Home.jsx` (full rewrite)

Parallel load on mount: `profile`, `activity?limit=3`, `services`, `news?limit=1`.

Blocks top to bottom:
1. **Profile header card** — avatar (initials/photo), name, specialization, bonus balance, bio, «Подробнее» → `navigate('landing', { masterId })`
2. **Action buttons** (2-col grid) — «Записаться» → `navigate('create_order')`, «Задать вопрос» → `navigate('ask_question')`
3. **Activity** — title + «Вся история» link → switch tab to `history`. Last 3 orders via `OrderCard`
4. **Services accordion** — collapsed: name + price. Expanded: description + «Записаться» → `navigate('create_order', { service })`
5. **News preview** — last publication card, tap → switch tab to `news`

### `pages/History.jsx` (new)

Load `history?limit=20&offset=0`. Lazy load on scroll (offset += 20).

Header: «История» left, «Баланс: N бонусов» right.

Two item types:
- `type='order'` → `OrderCard` with full data and action buttons
- `type='bonus'` → compact row, grey background, amount green(+) / red(-)

### `pages/News.jsx` (new)

Load `publications?limit=20&offset=0`. Lazy load on scroll.

Cards with type badge:
- `promo` → «Акция» (coral) + «Записаться» button
- `announcement` → «Объявление» (yellow) + no button
- `free_slot` → «Свободное окно» (green) + «Записаться» button
- `portfolio` → no badge + «Хочу так же» button → `navigate('create_order')`

### `pages/Settings.jsx` (new)

Load `settings` on mount.

Groups:
- **Уведомления**: 3 toggles — `notify_reminders`, `notify_marketing`, `notify_bonuses`. Each toggle → immediate `PATCH /settings`
- **Поддержка**: «Написать в поддержку» → `tg://` link
- **О приложении**: version string, privacy policy link
- **Аккаунт**: «Удалить профиль» (red) → confirmation screen → `DELETE /client/profile` → reset app state

### `pages/MasterLanding.jsx` (new)

Two modes via prop:
- `mode='private'` (masterId) — load `profile` + `reviews` with auth
- `mode='public'` (inviteToken) — load `/api/public/master/{token}` without auth

Layout top to bottom:
1. Avatar 80px, name, specialization, metrics («N отзывов»)
2. Action buttons: private → «Записаться» + «Задать вопрос»; public → «Подключиться к специалисту» (full width)
3. «О специалисте» section
4. Full services price list (not accordion)
5. Contacts — phone (`tel:`), Telegram (`tg://resolve`), Instagram, website, address
6. Work format
7. Reviews (last 5-10), name shortened: «Анна М.»
8. «Поделиться специалистом» → `tg://msg_url` with invite link

### `pages/Contact.jsx` (minimal change)

`BookingForm` receives optional `preselectedService?: { id, name, price }` prop. If provided, service is pre-selected on mount.

---

## Shared Components

### `components/OrderCard.jsx` (new)

Props: `{ order, onConfirm, onReview, onRepeat, onContact }`

Uses `order.display_status` directly (computed by backend):

| `display_status` | Badge | Buttons |
|---|---|---|
| `new` | «Новая запись» yellow | Связаться |
| `reminder` | «Напоминание» yellow | Подтвердить, Связаться |
| `confirmed` | «Подтверждён» blue | Связаться |
| `done` + `has_review=false` | «Выполнен» green | Оставить отзыв, Повторить |
| `done` + `has_review=true` | «Выполнен» grey | «Отзыв оставлен» (text) |
| `cancelled` | «Отменён» red | — |

«Подтвердить» → calls `onConfirm(orderId)` → optimistic update via `useQueryClient.setQueryData` (no full reload).

### `components/ReviewModal.jsx` (new)

Bottom sheet. Title «Отзыв о визите», subtitle: service + date from order. Textarea (min 10 chars). Submit → `POST /api/client/orders/{id}/review`. On success: close, fire `onSuccess(orderId)` callback → parent updates order card.

### `components/ContactSheet.jsx` (new)

Bottom sheet with master contacts. Phone → `tel:`, Telegram → `tg://resolve?domain=`. Close on swipe or overlay tap.

---

## Files Changed

| File | Change |
|------|--------|
| `src/App.jsx` | invite flow + new ClientApp with 4 tabs |
| `src/components/BottomNav.jsx` | 4 new tabs |
| `src/api/client.js` | add new API functions |
| `src/pages/Contact.jsx` | add `preselectedService` prop to BookingForm |
| `src/pages/Home.jsx` | full rewrite |
| `src/pages/History.jsx` | new file |
| `src/pages/News.jsx` | new file |
| `src/pages/Settings.jsx` | new file |
| `src/pages/MasterLanding.jsx` | new file |
| `src/components/OrderCard.jsx` | new file |
| `src/components/ReviewModal.jsx` | new file |
| `src/components/ContactSheet.jsx` | new file |
| `src/i18n/dictionaries/ru.js` | new keys |
| `src/i18n/dictionaries/en.js` | new keys |
| `src/pages/Bonuses.jsx` | delete |
| `src/pages/Promos.jsx` | delete |
| `src/pages/Booking.jsx` | delete |

---

## Styling

- Follow existing CSS variable system: `var(--tg-theme-bg-color)`, `var(--tg-theme-text-color)`, etc.
- Use existing `client-*` CSS class naming convention
- Dark theme primary (Telegram Mini App)
- Cards: `border-radius: 12px`, padding `12-16px`
- New CSS classes added to `theme.css` following existing `client-*` pattern
- No inline styles except where unavoidable (dynamic values)

---

## Out of Scope

- Client-bot notification inline actions redesign (only `/start` entry, already done)
- Backend changes (all endpoints deployed)
- i18n English translations (keys added with Russian values, English can be filled later)
