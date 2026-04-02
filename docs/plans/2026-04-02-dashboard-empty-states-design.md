# Design: Dashboard Empty States, Navigation Update, Broadcast Empty State

**Date:** 2026-04-02
**Scope:** Parts A (Dashboard), B (Navigation), C (Broadcast empty state)

---

## Overview

После внедрения онбординга у новых мастеров нет выполненных заказов. Текущий Dashboard показывает KPI-карточки с нулями и "Свободный день! 🎉" — это не подходит для нового пользователя. Также нужно обновить навигацию и добавить empty state для рассылок.

---

## Part A — Dashboard Empty States

### Логика

Ключевое условие: `total_done_orders` (COUNT * WHERE status='done').

- `== 0` → новый мастер, показать motivational UX
- `>= 1` → опытный мастер, показать KPI как сейчас

### Изменения бэкенда

**`GET /api/master/dashboard`** — добавить два поля:

```json
{
  "total_done_orders": 0,
  "onboarding_banner": {
    "show": true,
    "skipped_first_client": true,
    "banner_shown": false
  }
}
```

- `total_done_orders`: `COUNT(*) FROM orders WHERE master_id=? AND status='done'`
- `onboarding_banner.show`: `skipped_first_client == true AND banner_shown == false`
- `skipped_first_client` и `banner_shown` — поля из таблицы masters (добавлены в онбординге)

### Изменения фронтенда

**KPI-блок:**
- `total_done_orders == 0` → скрыть 4 StatCard, показать мотивационную карточку:
  - Иконка 📊, текст "Выполни первый заказ и увидишь показатели своей работы в цифрах"
  - Стиль: `--tg-secondary-bg`, мягкий border-radius

**Секции "Сегодня"/"Завтра" — empty states:**
- Нет заказов вообще (`today_orders.length == 0` и `tomorrow_orders.length == 0`):
  - "Пока записей нет" + кнопка "＋ Добавить первую запись" → `push('create_order')`
- Есть заказы, но не на сегодня (`today_orders.length == 0`, `tomorrow_orders.length > 0`):
  - "Записей на сегодня нет" (нейтральный текст, без эмодзи)
- Стандартный пустой день (опытный мастер):
  - "Свободный день! 🎉" — как сейчас

**Онбординг-баннер:**
- Условие: `onboarding_banner.show == true`
- Позиция: самый верх Dashboard, над приветствием
- Layout: текст + кнопка "Добавить →" + кнопка-крестик ×
- При нажатии "Добавить" или "×":
  - `PUT /api/master/profile { onboarding_banner_shown: true }`
  - Скрыть баннер (invalidate query или local state)

---

## Part B — Navigation

**Файл:** `MasterNav.jsx`

Единственное изменение: иконка вкладки "Рассылки" — `Megaphone` → `Mail` (из lucide-react).

Порядок вкладок остаётся: Главная / Календарь / Рассылки / Ещё.

---

## Part C — Broadcast Empty State

### Новый эндпоинт

**`GET /api/master/broadcast/can-send`**

```json
{
  "can_send": false,
  "clients_with_telegram": 0,
  "invite_link": "t.me/client_bot?start=abc123"
}
```

- `clients_with_telegram`: COUNT клиентов мастера с `tg_id IS NOT NULL`
- `invite_link`: из таблицы masters (поле `invite_token` или аналог)
- `can_send`: `clients_with_telegram > 0`

### Изменения фронтенда (Broadcast.jsx)

- Добавить `useQuery('broadcast-can-send')` при загрузке экрана
- Если `can_send == false` → вместо 4-шагового wizard показать empty state:
  - Большая иконка конверта (центр)
  - Заголовок: "Массовые рассылки"
  - Текст: "Добавьте клиентов, чтобы делать массовые рассылки"
  - Разделитель
  - Блок с инвайт-ссылкой:
    - Заголовок: "Ссылка-приглашение для клиентов"
    - Подпись: "Отправьте ссылку, чтобы пригласить клиента"
    - Отображение ссылки + кнопка "Копировать ссылку" (Clipboard API)

---

## Критерии проверки

1. Новый мастер (0 done-заказов) → KPI скрыты, мотивационный блок видён
2. "Пока записей нет" + кнопка → ведёт на OrderCreate
3. Баннер онбординга виден если `onboarding_banner.show == true`
4. Баннер скрывается навсегда после "Добавить" или "×"
5. Мастер с 1+ done-заказом → KPI показываются, баннер скрыт
6. "Записей на сегодня нет" — нейтральный текст (без 🎉)
7. Навигация: вкладка "Рассылки" с иконкой конверта (Mail)
8. 0 клиентов с TG → empty state рассылок с инвайт-ссылкой
9. 1+ клиент с TG → обычный wizard рассылок
10. Кнопка "Копировать ссылку" работает
11. `npm run build` без ошибок
