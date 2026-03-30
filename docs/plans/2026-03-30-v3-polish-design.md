# V3 Polish — Design Doc

**Date:** 2026-03-30
**Scope:** Финальная полировка после реализации Отчётов, ClientAdd и Broadcast с медиа.

---

## Что уже готово (не трогаем)

- Reports маршрут в MasterApp + навигация через Dashboard StatCards
- ClientsList → handleClientAdded → перейти на карточку нового клиента
- OrderCreate → ClientAddSheet → onSelect(client) + onNext()
- staleTime: Reports 60s, Broadcast segments 60s
- Broadcast 413 — проверка размера на фронте до отправки

---

## Что реализуем

### 1. Reports — пустой период
**Файл:** `miniapp/src/master/pages/Reports.jsx`

Если `days` пуст или все `revenue === 0` — вместо пустого графика показывать:
```
"За этот период данных нет"
```
Пустой блок с hint-цветом, без графика.

### 2. ClientAddSheet — ошибка 409
**Файл:** `miniapp/src/master/components/ClientAddSheet.jsx`

При `err.response?.status === 409` показывать понятное сообщение:
```
"Клиент с таким номером уже существует"
```
Вместо текущего общего текста ошибки.

### 3. Broadcast — timeout
**Файл:** `miniapp/src/master/pages/Broadcast.jsx`

В `sendMutation.onError`:
- `err.code === 'ECONNABORTED'` (axios timeout) или `status >= 504`
→ alert: "Рассылка заняла больше времени — проверьте результат позже"
- Всё остальное → прежнее поведение (`err.response.data.detail`)

### 4. Reports — инвалидация после заказа
**Файл:** `miniapp/src/master/MasterApp.jsx`

В `invalidateOrders()` добавить:
```js
queryClient.invalidateQueries({ queryKey: ['master-reports'] });
```
Обеспечивает обновление данных Reports при следующем открытии после проведения/отмены заказа.

### 5. CLAUDE.md — актуализация
Добавить:
- Новые файлы: `Reports.jsx`, `ClientAddSheet.jsx`, `src/api/routers/master/reports.py`
- Новые API: `GET /api/master/reports`, `POST /api/master/clients`
- Обновлённый `broadcast/send` (multipart/form-data)
- `get_daily_revenue()` в `database.py`
- Статус Reports и ClientAdd как ✅ Реализовано

---

## Критерии готовности

1. Reports с данными → графики отображаются
2. Reports без данных → "За этот период данных нет"
3. ClientAdd с дублирующим телефоном → понятная ошибка
4. Broadcast с большим файлом → ошибка до отправки (уже есть)
5. Broadcast timeout → специальный текст
6. Провести заказ → открыть Reports → данные свежие
7. `npm run build` без ошибок
8. CLAUDE.md актуален
