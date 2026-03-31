# Design: Клиентский Mini App — мультимастерность (Подход C)

**Date:** 2026-03-31
**Scope:** Поддержка нескольких мастеров в клиентском Mini App. Backward-compatible: клиент с 1 мастером не видит никаких изменений.

---

## Архитектура

### Хранение активного master_id

**Проблема:** localStorage не работает в Telegram Mini App. React state недоступен из `client.js`.

**Решение:** Module-level переменная в `client.js`:
```js
let _activeMasterId = null;
export const setActiveMasterId = (id) => { _activeMasterId = id; };
```
При перезапуске Mini App — `App.jsx` определяет мастера заново через `/api/client/masters`.

### Поток App.jsx при role='client'

```
getAuthRole() → 'client'
  ↓
getClientMasters()
  ↓
count === 0 → "Нет мастеров"
count === 1 → setActiveMasterId(masters[0].id) → ClientApp
count > 1   → MasterSelectScreen (или сразу ClientApp, если start_param обрабатывается)
```

### API запросы с master_id

Все клиентские функции в `client.js` добавляют `?master_id` когда `_activeMasterId` задан:
```js
export const getMe = () => api.get('/api/me', { params: _activeMasterId ? { master_id: _activeMasterId } : {} });
```
Backward compat: при 1 мастере `_activeMasterId` всегда задан, API получает `?master_id=X`. Бэкенд поддерживает это (уже реализовано в Промпте 2).

### React Query invalidation при смене мастера

При смене мастера: `setActiveMasterId(newId)` + `queryClient.invalidateQueries()` — все кеши сбрасываются, данные перезапрашиваются с новым `master_id`.

Важно: queryKey остаётся `['me']`, `['orders']` и т.д. — invalidation достаточно, усложнять не нужно.

---

## Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `miniapp/src/api/client.js` | `_activeMasterId`, `setActiveMasterId`, `getClientMasters`, `linkToMaster`, обновить `getMe/getOrders/getBonuses/getPromos/getServices/createOrderRequest` |
| `miniapp/src/App.jsx` | Fetch masters при role='client', передать props, deep link обработка |
| `miniapp/src/pages/MasterSelectScreen.jsx` | Новый файл — экран выбора мастера |
| `miniapp/src/pages/Home.jsx` | Переключатель мастера в шапке + bottom sheet (если masters.length > 1) |

---

## Компоненты

### MasterSelectScreen
- Список карточек (аватар-круг с первой буквой, имя, сфера, баланс, визиты, дата)
- Тап → `setActiveMasterId` → callback к родителю → показать ClientApp

### Bottom sheet в Home
- Кондиционно: `if (masters.length > 1)` — показать имя мастера + ▼ в шапке
- Тап → inline bottom sheet с backdrop + список мастеров
- Выбор → `setActiveMasterId` + `qc.invalidateQueries()`

### Deep link (start_param)
- В `App.jsx` при role='client', после загрузки мастеров
- `WebApp.initDataUnsafe?.start_param` начинается с `invite_` → `linkToMaster(token)`
- Успех → добавить в список → перейти на Home с новым мастером
- 409 → toast "Уже подключены"

---

## Backward compatibility

- Клиент с 1 мастером: `_activeMasterId` задаётся автоматически, переключатель не рендерится, MasterSelectScreen не показывается
- Все существующие queryKey неизменны — invalidation подхватывает новый master_id из замыкания
