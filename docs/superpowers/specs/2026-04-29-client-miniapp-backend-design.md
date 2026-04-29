# Client Mini App Backend Design

Date: 2026-04-29
Status: approved for backend-first implementation

## Goal

Prepare the backend and minimal client-bot entry point for the redesigned client Telegram Mini App. The Mini App becomes the primary client UI; `client_bot.py` remains a welcome, notification, and inline-action channel.

## Scope

This implementation covers the first/backend part of the task:

- New client-facing API endpoints required by `prompts/files/PROMPT_CLIENT_APP_CODEX.md`.
- Data support for text reviews and bonus notification preferences.
- Compatibility responses for the upcoming frontend task described in `prompts/files/PROMPT_CLIENT_APP_CLAUDE_CODE.md`.
- A simplified `/start` experience in `client_bot.py`: greeting, connected specialists with bonus balances, and an inline Mini App button.

This implementation does not redesign the React client Mini App screens. It also does not rebuild the full client-bot notification system beyond preserving existing notifications and keeping future inline Mini App actions possible.

## Existing Architecture Decisions

The Claude-written TЗ is treated as product intent, not implementation authority. Where it conflicts with this repository, the repository architecture wins unless explicitly approved otherwise.

### Order Confirmation

Do not add or use an `orders.status = 'confirmed_by_client'` value.

The project already stores client confirmation as `orders.client_confirmed BOOLEAN`, with supporting migrations and code. New API endpoints must use this existing model and return a client-facing display state derived from:

- `orders.status`
- `orders.client_confirmed`
- reminder flags such as `reminder_24h_sent`
- review presence for completed orders

### Reviews

Use a hybrid feedback model:

- Keep `orders.rating` as the quick 1-5 rating collected from bot feedback notifications.
- Add a separate `reviews` table for public text reviews submitted from the Mini App.
- For ratings below 5, existing bot behavior remains conceptually unchanged in a later notification pass.
- For high ratings, the future bot flow can lead users to the Mini App review form.
- Done order cards in the future Mini App can also show "Оставить отзыв" when no review exists.

### Publications / News

Do not add a `publications` table in this backend pass.

The current product already has `campaigns` and working promo flows. New client "news/publications" endpoints should read active promo campaigns and return them in a publication-shaped response:

- `type: "promo"`
- `title`
- `text`
- `created_at`
- `active_from`
- `active_to`
- no image for now

This keeps the API shape ready for future announcement, free-slot, and portfolio types after the master-side creation UI is designed.

### Notification Settings

The new client settings UI has three toggles:

- `notify_reminders`
- `notify_marketing`
- `notify_bonuses`

Add `notify_bonuses` to `master_clients`.

Keep existing detailed fields for backward compatibility:

- `notify_24h`
- `notify_1h`
- `notify_promos`

When the new API updates `notify_reminders`, synchronize `notify_24h` and `notify_1h` to the same value so existing reminder sending keeps respecting the new setting.

When the new API updates `notify_marketing`, synchronize `notify_promos` to the same value so current promo and broadcast behavior keeps respecting the new setting.

## API Design

Create a new router for the redesigned client app, likely `src/api/routers/client_app.py`, included under `/api`.

All authenticated endpoints validate Telegram initData with the existing client auth flow and verify that the requested `master_id` is linked to the current client.

### Specialist Selection

`GET /api/client/masters`

Return the existing linked-specialist list, enriched and normalized for the new UI:

- `master_id`
- `name`
- `master_name` for backward compatibility
- `sphere`
- `bonus_balance`
- `visit_count`
- `order_count` for backward compatibility
- `last_visit`

### Specialist Profile

`GET /api/client/master/{master_id}/profile`

Return connected-client profile context:

- specialist identity and contact fields
- sphere and work format fields
- bonus balance
- visit count
- review count
- years on platform
- invite token or share URL if safe to expose to connected clients

The UI says "специалист"; backend fields may remain named `master`.

### Activity And History

`GET /api/client/master/{master_id}/activity?limit=3`

Return recent mixed activity for the home screen.

`GET /api/client/master/{master_id}/history?limit=20&offset=0`

Return a paginated mixed feed of:

- order items
- bonus-log items without an `order_id`

Bonus operations linked to an order are not duplicated as standalone feed items, because the order card already carries accrued/spent bonus data.

Order items must include:

- `id`
- `type: "order"`
- raw `status`
- `client_confirmed`
- client-facing `display_status`
- `scheduled_at`
- `amount_total`
- `bonus_accrued`
- `bonus_spent`
- service names
- address
- `has_review`

### Services

`GET /api/client/master/{master_id}/services`

Return active services with:

- `id`
- `name`
- `price`
- `description`

### News / Publications

`GET /api/client/master/{master_id}/news?limit=1`

`GET /api/client/master/{master_id}/publications?limit=20&offset=0`

Read current promo campaigns and return a publication-shaped response. Include `total` for paginated endpoints.

### Settings

`GET /api/client/master/{master_id}/settings`

Return:

- `notify_reminders`
- `notify_marketing`
- `notify_bonuses`

`PATCH /api/client/master/{master_id}/settings`

Accept any subset of the three fields. Reject non-boolean values through Pydantic validation. Apply the synchronization rules for legacy notification fields.

### Order Actions

`POST /api/client/orders/{order_id}/confirm`

Verify the order belongs to the current Telegram client. Use the existing confirmation model by setting `client_confirmed = 1`. Do not introduce a new order status. Return:

- `ok: true`
- `client_confirmed: true`
- `display_status: "confirmed"`

### Reviews

`POST /api/client/orders/{order_id}/review`

Create a text review for a completed order that belongs to the current client. Enforce:

- text length at least 10 characters
- rating optional, 1-5 if present
- one review per order

`GET /api/client/master/{master_id}/reviews?limit=20&offset=0`

Return visible reviews with shortened client names.

### Public Profile

`GET /api/public/master/{invite_token}`

No auth required. Return public specialist profile, services, visible reviews, review count, and years on platform.

The public endpoint must not expose private client data or internal notes.

### Profile Deletion

`DELETE /api/client/profile`

Use existing anonymization behavior for the current client:

- set name to `Удалённый клиент`
- clear phone, birthday, and `tg_id`
- keep historical order data for specialist accounting

Do not physically delete orders or bonus logs.

## Client Bot Entry Point

Update `client_bot.py` only for the simplified entry experience:

- `/start` greets the client.
- If the client has connected specialists, show each specialist with sphere and bonus balance.
- Include an inline WebApp button to open `CLIENT_MINIAPP_URL`.
- If the user opens via invite token, preserve the existing linking behavior.
- Do not keep old bot navigation as the primary client UI.

Full notification redesign is out of scope for this backend pass unless a separate TЗ is provided.

## Testing Strategy

Use TDD for behavior changes:

- migration/init test for new `reviews` and `notify_bonuses`
- database tests for settings sync, review creation, review uniqueness, confirmation using `client_confirmed`
- API tests for auth-linked master checks, settings, history/activity shaping, publications from campaigns, public profile
- a focused test or manual check for simplified `/start` rendering if bot handlers are changed in a way that is practical to test

Verification before completion must include at minimum:

- targeted Python tests added for this work
- import/app startup check for FastAPI router inclusion
- `git status --short`

## Open Constraints

- Existing dirty worktree files are unrelated and must not be reverted or included accidentally.
- Frontend implementation from `PROMPT_CLIENT_APP_CLAUDE_CODE.md` is a later step.
- Bot notification inline actions beyond `/start` are a later step.
