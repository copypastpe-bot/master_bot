# Feedback Request Feature — Design

date: 2026-04-17
status: approved

## Goal

After a master completes an order, automatically send the client a rating request (1–5) via client_bot. Route the response to the right follow-up action and alert the master when needed.

## Approach

Polling scheduler (Variant A) — same pattern as existing 24h/1h reminders in `src/scheduler.py`. Every 30 minutes, scan `orders` for rows where `status='done'`, `feedback_sent=FALSE`, and `done_at + feedback_delay_hours * 3600 ≤ now()`. Send inline keyboard, mark flag.

## Database Changes — migration `013_feedback.sql`

### `orders` table
```sql
ALTER TABLE orders ADD COLUMN feedback_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN rating INTEGER;
```

### `masters` table
```sql
ALTER TABLE masters ADD COLUMN feedback_delay_hours INTEGER DEFAULT 3;
ALTER TABLE masters ADD COLUMN feedback_message TEXT;   -- initial message template
ALTER TABLE masters ADD COLUMN feedback_reply_5 TEXT;   -- reply-on-5 template
ALTER TABLE masters ADD COLUMN review_buttons TEXT;     -- JSON: [{label, url}, ...]  max 3
```

Template variables available in `feedback_message` and `feedback_reply_5`:
- `{master_name}` — master display name
- `{service}` — comma-joined service names from order_items

## Components

### 1. DB functions (`src/database.py`)
- `get_orders_for_feedback()` — returns orders meeting trigger criteria (join masters for delay + tg_id)
- `mark_feedback_sent(order_id)` — sets `feedback_sent=TRUE`
- `save_order_rating(order_id, rating)` — writes `rating` column
- `get_master_feedback_settings(master_id)` — returns delay, message templates, review_buttons

### 2. Scheduler job (`src/scheduler.py`)
New function `send_feedback_requests(client_bot: Bot)`, registered at 30-minute interval.

Sends client a message (default or custom `feedback_message`) with inline keyboard:
```
[ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ]
```
callback_data: `feedback:{order_id}:{rating}`

### 3. Client bot callback handler (`src/client_bot.py`)
Handles `feedback:*` callbacks.

| Rating | Client response | Master alert |
|--------|----------------|--------------|
| 5 | `feedback_reply_5` text + up to 3 inline URL buttons from `review_buttons` | — |
| 4 | "Расскажите, что можно улучшить?" | Notify: "Клиент [name] поставил 4" |
| ≤ 3 | "Мы свяжемся с вами в ближайшее время" | ⚠️ "Клиент [name] недоволен, оценка [N]" |

After any press: save rating, edit message to remove inline keyboard.

### 4. Backend API (`src/api/routers/master/settings.py`)
New endpoint: `PUT /master/settings/feedback`

Request body:
```json
{
  "feedback_delay_hours": 3,
  "feedback_message": "Как прошёл визит у {master_name}?",
  "feedback_reply_5": "Спасибо! Рады видеть вас снова 🙏",
  "review_buttons": [
    {"label": "Яндекс Карты", "url": "https://..."},
    {"label": "Google Maps", "url": "https://..."}
  ]
}
```

Validation: `feedback_delay_hours` 1–72, `review_buttons` max 3 items, each URL must be http/https.

### 5. Mini App UI
New section in master settings page (existing `Settings` screen or dedicated tab):
- Number input: "Через сколько часов спрашивать отзыв" (1–72, default 3)
- Textarea: "Текст сообщения клиенту" (with placeholder showing default)
- Textarea: "Ответ при оценке 5" (with placeholder showing default)
- Up to 3 button rows: label input + URL input (add/remove)

## Default Templates

```
feedback_message (default):
"Спасибо, что записались к {master_name}! Как прошёл визит?\nОцените от 1 до 5:"

feedback_reply_5 (default):
"Спасибо за высокую оценку! Будем рады видеть вас снова 🙏"
```

## Out of Scope (deferred)

- Dashboard widget showing average rating per master
- Rating history in client card
- Reply collection for rating 4 (free-text follow-up)
