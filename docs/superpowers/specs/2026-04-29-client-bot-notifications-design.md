# Client Bot Notifications Design

Date: 2026-04-29

## Source

Primary task file:

- `prompts/files/PROMPT_CLIENT_BOT_NOTIFICATIONS.md`

Project rules:

- `CLAUDE.md`

## Goal

Simplify the client Telegram bot into a lightweight Mini App entry point and notification delivery channel.

The bot must keep:

- `/start` with invite registration and connected specialists list
- service commands `/support` and `/delete_me`
- existing post-order feedback flow for ratings 1-4
- client notifications with inline actions

The bot must remove old client-side navigation and request flows that now belong in the Mini App.

UI terminology uses `специалист`, not `мастер`, in client-facing bot messages.

## Runtime Scope

After implementation, the client bot runtime has these areas:

1. Start and invite registration.
2. Service commands: `/support`, `/delete_me`.
3. Post-order feedback rating callbacks.
4. Notification inline actions: confirm visit, show specialist contacts, open Mini App, leave review.
5. Scheduler setup and Telegram menu button setup.

The old client menu runtime is removed:

- bonuses screen
- history screen
- promos screen
- order request flow
- question flow
- photo/video flow
- master info screen
- notification settings screen in the bot
- specialist switching screen in the bot
- client-side reschedule and cancel flows from reminders

The notification settings live in the Mini App and remain controlled by:

- `notify_reminders`
- `notify_marketing`
- `notify_bonuses`

## Legacy Copy

Before cutting old runtime code, keep a local archive copy of the current client bot as `src/client_bot_legacy.py`.

This file is not imported by `main.py`, the dispatcher, tests, or production code. It exists only as a reference during this transition. Git history remains the authoritative rollback mechanism.

## Start Flow

`/start` keeps the current invite registration behavior:

- invalid invite token returns an error
- new client with invite token goes through consent, name, phone, birthday registration
- existing client with new invite token links to the specialist
- already linked client gets an already-connected notice
- registered client without token sees the Mini App entry message
- unregistered client without token is told to request an invite link

After successful registration or linking, the bot sends the simplified Mini App entry message:

```text
Привет, {имя клиента}!

Ваши специалисты:
— {Имя} · {Сфера} · {N} бонусов
— {Имя} · {Сфера} · {N} бонусов
```

If the client has no linked specialists:

```text
Привет, {имя клиента}!

У вас пока нет специалистов
```

The message includes one inline WebApp button:

- `Открыть приложение`

The Telegram menu button is always configured as a WebApp button to `CLIENT_MINIAPP_URL`.

## Notification Keyboards

Shared notification keyboard helpers should live close to notification formatting code.

Common buttons:

- `Открыть приложение`: WebApp button to `CLIENT_MINIAPP_URL`
- `Связаться`: callback button that updates the current message with specialist contacts
- `Подтвердить`: callback button for active order confirmation
- `Оставить отзыв`: WebApp button to the Mini App review entry for a specific order

Contact buttons:

- `Позвонить`: URL button `tel:{phone}`, only if specialist phone exists
- `Написать в TG`: URL button `https://t.me/{username}`, only if specialist Telegram username exists
- `Открыть приложение`: WebApp button

If both phone and Telegram username are missing, the contact message still shows available legacy contact text and the Mini App button. The implementation should not create a broken URL button.

## New Order Notification

Trigger: a specialist creates an order for a client from the master Mini App/API.

Send only when:

- client has `tg_id`
- `master_clients.notify_reminders = true`

Message:

```text
{Имя специалиста} записал(а) вас:

{Название услуги/услуг}
{Дата}, {Время}
{Адрес (если есть)}
```

Buttons:

- `Связаться`
- `Открыть приложение`

Implementation detail:

- `src/api/routers/master/orders.py` already calls `src.notifications.notify_order_created`.
- `notify_order_created` must receive or fetch the master-client notification setting before sending.

## 24h Reminder

Trigger: scheduler, approximately 24 hours before `orders.scheduled_at`.

Send only when:

- `master_clients.notify_reminders = true`
- order status is active: `new` or `confirmed`
- reminder was not already sent
- client has `tg_id`

Message:

```text
Напоминание:

{Название услуги/услуг}
Завтра, {Время} — {Имя специалиста}
{Адрес (если есть)}
```

Buttons:

- `Подтвердить`
- `Связаться`
- `Открыть приложение`

The old 24h reminder actions `Перенести` and `Отменить` are removed from client bot runtime.

The old 1h reminder job is removed from scheduler runtime because it is not part of the new client bot scope.

## Confirm Action

Callback: `confirm_order:{order_id}`.

Behavior:

1. Resolve order by `order_id` and `callback.from_user.id`.
2. If the order is already client-confirmed, show alert: `Запись уже подтверждена`.
3. If the order is cancelled, done, missing, or not owned by the client, show alert: `Запись больше не активна`.
4. For active orders, set `orders.client_confirmed = 1`. Keep the existing status architecture: status may remain `confirmed`; do not introduce a new status value.
5. Update the current message and remove the `Подтвердить` button.
6. Notify the specialist in the master bot.

Updated client message:

```text
Вы подтвердили запись:

{Название услуги/услуг}
{Дата}, {Время} — {Имя специалиста}
{Адрес (если есть)}

Ждём вас!
```

Updated buttons:

- `Связаться`
- `Открыть приложение`

Specialist notification:

```text
Клиент подтвердил запись:

{Имя клиента}
{Название услуги/услуг}
{Дата}, {Время}
```

## Contact Action

Callback: `contact_order:{order_id}`.

The action is order-scoped so the bot can verify ownership and fetch the exact specialist.

Behavior:

1. Resolve the specialist and verify the client is allowed to see these contacts.
2. Update the current message to contact information.
3. Show URL buttons only for available structured contacts.
4. Keep `Открыть приложение`.

Message:

```text
{Имя специалиста}

Телефон: {телефон}
Telegram: {username}
```

Fallback:

- If structured `phone` is empty, do not show `Позвонить`.
- If structured `telegram` is empty, do not show `Написать в TG`.
- If only legacy `contacts` exists, include it in the message as text and show no broken URL buttons.

## Feedback Flow

The existing rating request remains scheduler-driven and is sent regardless of notification settings.

Ratings 1-4 keep current behavior.

Rating 5 changes only the follow-up reply:

```text
Большое спасибо! Оставьте, пожалуйста, отзыв — это поможет специалисту.
```

Buttons:

- `Оставить отзыв`

The button opens the Mini App with an order-scoped start parameter. The Mini App must open the review UI for that `order_id`. If the current frontend does not support this start parameter, implementation includes a small review-entry handler.

Old master-configured `review_buttons` are not used for rating 5 in the client bot after this change.

## Broadcast And Promotions

Trigger: master sends a broadcast/publication from the master Mini App/API.

Send only when:

- recipient is returned by the existing `notify_marketing` filtered recipient query
- client has `tg_id`

Message:

```text
{Имя специалиста}:

{Заголовок (если есть)}
{Текст публикации}
```

If image media exists, send as photo with caption.

Buttons:

- `Открыть приложение`

The existing master broadcast endpoint already supports text and photo/video sending. Implementation should adapt text format and add the Mini App button. Video support may remain, but the acceptance requirement only requires photo-with-caption behavior.

## Manual Bonus Notification

Trigger: specialist manually adds bonuses from the master Mini App/API.

Send only when:

- `amount > 0`
- client has `tg_id`
- `master_clients.notify_bonuses = true`

Message:

```text
Начислено +{N} бонусов
{Комментарий}
от {Имя специалиста}

Ваш баланс: {итого} бонусов
```

No inline buttons.

Negative manual corrections do not send this notification because the requirement describes bonus accrual, not deduction.

Order-linked bonus accrual after completed visits remains part of existing order completion behavior and is outside this manual-bonus notification requirement.

## Files To Change In Implementation

Expected backend files:

- `src/client_bot.py`
- `src/client_bot_legacy.py`
- `src/notifications.py`
- `src/scheduler.py`
- `src/database.py`
- `src/keyboards.py`
- `src/states.py`
- `src/api/routers/master/orders.py`
- `src/api/routers/master/broadcast.py`
- `src/api/routers/master/clients.py`

Expected frontend file for review deep-link support:

- `miniapp/src/App.jsx`

Expected tests:

- database tests for notification setting checks and confirm edge cases
- import/compile tests for simplified client bot
- focused unit tests for notification keyboard formatting where practical
- API tests for manual bonus notification path where practical with a fake bot

## Acceptance Mapping

1. `/start` shows specialists, bonuses, and `Открыть приложение`.
2. Menu button opens the Mini App.
3. New order notification sends with `Связаться` and `Открыть приложение`.
4. 24h reminder sends with `Подтвердить`.
5. `Подтвердить` changes `client_confirmed`, updates the message, and notifies the specialist.
6. `Связаться` updates the message and shows valid contact buttons.
7. Feedback ratings 1-4 keep current behavior.
8. Feedback rating 5 shows `Оставить отзыв` to Mini App review entry.
9. Broadcasts/promotions respect `notify_marketing`.
10. Manual positive bonus notifications respect `notify_bonuses`.
11. Old navigation buttons and handlers are removed from runtime.
12. Repeated confirmation shows an alert instead of an error.
