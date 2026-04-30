# Client App UI V1 Design

## Goal

Implement `prompts/TZ_CLIENT_APP_UI_V1.md` for the client Telegram Mini App: compact expandable order cards shared by Home and History, and reliable notification toggles on Settings.

## Current Context

- `miniapp/src/components/OrderCard.jsx` is already shared by Home and History.
- `miniapp/src/pages/Home.jsx` already renders an Activity block with a History link and currently requests 3 items.
- `miniapp/src/pages/History.jsx` already renders the same `OrderCard` for order items and separate rows for standalone bonus events.
- `miniapp/src/pages/Settings.jsx` already loads and patches notification settings through `miniapp/src/api/client.js`.
- `src/api/routers/client_app.py` already exposes GET/PATCH settings endpoints.
- `src/database.py` already syncs `notify_reminders` with `notify_24h`/`notify_1h`, `notify_marketing` with `notify_promos`, and has a local `notify_bonuses` field path.

## Design

### Order Card

`OrderCard.jsx` keeps one reusable component with internal `expanded` state. The collapsed view shows status, date/time, amount, services with ellipsis, and a down chevron. Tapping the card toggles the expanded state with haptic feedback.

The expanded area shows optional address, bonus accrual and spending, review-left marker, and status-dependent action buttons. Button clicks call `stopPropagation()` so actions do not also collapse the card.

Action rules:

- `done`: show `Оставить отзыв` when `has_review` is false, always show `Повторить`.
- `confirmed`, `new`, `reminder`: show `Связаться`; keep existing confirm support for `reminder`.
- `cancelled`: show `Повторить`.

The card uses existing API fields from `orders o.*`: `address`, `amount_total`, `bonus_accrued`, `bonus_spent`, `has_review`, `services`, and `scheduled_at`. No backend response expansion is needed for this task.

### Home Activity

`Home.jsx` continues to use the shared order card and changes the Activity query limit from 3 to 4. The existing `Вся история` link remains the navigation path to History.

### Settings Toggles

`Settings.jsx` keeps the current GET/PATCH flow. It adds two hardening changes:

- Reset `loading` and `settings` when `activeMasterId` changes, so stale settings are not shown for another master.
- Ignore duplicate toggle changes while the same setting is saving.

The existing optimistic UI update remains: toggle immediately reflects the new value, then rolls back and emits error haptic feedback if the request fails.

### Styling

`miniapp/src/theme.css` makes the order card compact, keeps the dark theme, adds service ellipsis, and animates the expanded body with a smooth grid/opacity transition. Layout must fit 320-420px widths without text overlap.

## Testing

- Run existing focused backend tests for client app database/API behavior.
- Run `npm --prefix miniapp run lint`.
- Run `npm --prefix miniapp run build`.

No new backend endpoint is planned because the data required by the card is already selected through `o.*`.
