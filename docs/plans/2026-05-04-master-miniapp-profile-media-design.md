# Дизайн: профиль мастера + медиа в Mini App

**Дата:** 2026-05-04
**Контекст:** ТЗ `TZ_LANDING_AND_PROFILE_V2.md`, Задача 2.4 — UI управления профилем в Master Mini App.
**Статус:** approved

---

## Цель

Дать мастеру возможность прямо в Mini App:
- заполнить «О себе» (about)
- загрузить/удалить аватар
- управлять портфолио (до 10 фото, добавить/удалить)
- переключить «Показывать на минисайте» для каждой услуги

Бот остаётся только для уведомлений — никаких новых bot-хендлеров.

---

## Решение по хранению медиафайлов

Загруженные фото сохраняются на сервере как статика.
Поля `avatar_file_id` (masters) и `file_id` (master_portfolio) содержат либо:
- Telegram file_id (строка без `/`) — старые данные
- Локальный путь (начинается с `/`) — загруженные через Mini App

Функция `_photo_url` в `landing.py` и `public.py`:
```python
def _photo_url(file_id: str) -> str:
    if not file_id:
        return None
    if file_id.startswith('/'):
        return file_id          # уже URL, отдаём напрямую
    return f"/api/public/photo/{file_id}"   # Telegram proxy
```

Никаких изменений схемы БД не нужно.

---

## Backend

### `src/api/app.py`

Монтировать две статические директории (аналогично `/bonus-media`):
```python
AVATARS_DIR = Path(os.getenv("AVATARS_DIR", "/app/data/avatars"))
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")

PORTFOLIO_DIR = Path(os.getenv("PORTFOLIO_DIR", "/app/data/portfolio"))
PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/portfolio", StaticFiles(directory=str(PORTFOLIO_DIR)), name="portfolio")
```

### `src/api/routers/master/settings.py`

Три новых эндпоинта (multipart upload через `UploadFile`):

**`POST /api/master/avatar/upload`**
- Принимает `file: UploadFile`
- Валидация: content_type `image/*`, размер ≤ 10 MB
- Сохраняет в `/app/data/avatars/master_{master_id}{ext}`
- Записывает `/avatars/master_{master_id}{ext}` в `avatar_file_id`
- Возвращает `{"avatar_url": "/avatars/..."}`

**`DELETE /api/master/avatar`**
- Удаляет файл с диска (если локальный)
- Очищает `avatar_file_id = None`
- Возвращает `{"ok": true}`

**`POST /api/master/portfolio/upload`**
- Принимает `file: UploadFile`
- Валидация: content_type `image/*`, размер ≤ 10 MB
- Сохраняет в `/app/data/portfolio/master_{master_id}_{uuid4_short}{ext}`
- Вызывает `add_portfolio_photo(master.id, url)` где url = `/portfolio/...`
- Если `add_portfolio_photo` вернул `None` → 409 (лимит 10 фото)
- Возвращает `{"id": ..., "url": "/portfolio/..."}`

Существующие `GET /api/master/portfolio`, `DELETE /api/master/portfolio/{photo_id}` — без изменений.

---

## Frontend

### `miniapp/src/api/client.js`

Пять новых функций:
```js
uploadMasterAvatar(formData)     // POST /api/master/avatar/upload (multipart)
deleteMasterAvatar()             // DELETE /api/master/avatar
uploadPortfolioPhoto(formData)   // POST /api/master/portfolio/upload (multipart)
getMasterPortfolio()             // GET /api/master/portfolio
deletePortfolioPhoto(id)         // DELETE /api/master/portfolio/{id}
```

Для multipart: `axios.post(url, formData, { headers: { 'Content-Type': 'multipart/form-data' } })`.

### `miniapp/src/master/pages/Profile.jsx`

**Изменение 1 — «О себе»** в секции «Профиль»:
- Новая ячейка `Cell` с иконкой (FileText/Pencil)
- При клике открывает `TextEditSheet` с `multiline={true}`, `maxLength={1000}`
- Сохраняет через `profileMutation.mutate({ about: draft })`
- Поле `about` уже принимается `PUT /api/master/profile`

**Изменение 2 — секция «Минисайт»** (новая, ниже «Приглашения»):

Подсекция «Аватар»:
- Если `master.avatar_file_id` есть — показать `<img>` превью (60×60, круглый)
- Иначе — круг с инициалами (как в landing.html)
- Кнопка «Загрузить» → `<input type="file" accept="image/*">` (hidden, triggered by click)
  - onChange → `uploadMasterAvatar(formData)` → invalidate `['master-me']`
- Кнопка «Удалить» (только если аватар есть) → `deleteMasterAvatar()`

Подсекция «Портфолио»:
- Запрос `getMasterPortfolio()` (отдельный queryKey `['master-portfolio']`)
- Счётчик `{count}/10 фото`
- Горизонтальный скролл с превью фото + кнопка ✕ на каждой
- Кнопка «Добавить фото» (если < 10) → `<input type="file">` → `uploadPortfolioPhoto`
- Удаление: `deletePortfolioPhoto(id)` → invalidate `['master-portfolio']`

Стиль: `enterprise-cell-group` / `enterprise-section-title` — как везде в Profile.jsx.

### `miniapp/src/master/pages/Services.jsx`

В `ServiceSheet` — новый toggle «Показывать на минисайте»:
- Отдельный `useState` для `showOnLanding` (инициализируется из `initial?.show_on_landing ?? true`)
- При сохранении включается в payload: `{ ..., show_on_landing: showOnLanding }`
- Визуально: строка с лейблом + кнопка-переключатель (аналог toggles в Settings.jsx клиента)
- Подпись под toggle: «Услуга будет видна на вашем минисайте»

---

## Что НЕ меняем

- Схема БД (нет миграций)
- `landing.html` (изменений нет)
- `landing.py` — только 1 строка в `_photo_url`
- `public.py` — только 1 строка в `_photo_url`
- Bot-хендлеры

---

## Порядок реализации

1. Backend: mount статики + upload эндпоинты + `_photo_url` fix
2. Frontend API-клиент: 5 новых функций
3. Profile.jsx: «О себе» + секция «Минисайт»
4. Services.jsx: toggle show_on_landing
5. Build + lint + деплой
