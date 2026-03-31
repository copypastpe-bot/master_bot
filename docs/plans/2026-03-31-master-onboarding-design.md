# Design: Регистрация мастера через Mini App

**Дата:** 2026-03-31
**Ветка:** feature/lite-hybrid

## Контекст

Сейчас мастер регистрируется только через `/start` в master_bot (FSM в `src/handlers/registration.py`). При открытии Mini App незарегистрированный пользователь видит экран "Зарегистрируйтесь через бота".

Цель: добавить онбординг прямо в Mini App. Бот остаётся как альтернативный путь.

## Архитектура

### Бэкенд

**Новый файл:** `src/api/routers/master/auth.py`

```
POST /api/master/register
Header: X-Init-Data (обязательно)
Body: { name: str, sphere?: str, contacts?: str, work_hours?: str }

Response 200:
{
  "id": int,
  "name": str,
  "invite_token": str,
  "invite_link": str,   # https://t.me/<MASTER_BOT_USERNAME>?start=<token>
  "role": "master"
}
Response 409: мастер с таким tg_id уже существует
Response 401: невалидный X-Init-Data
```

Логика:
1. Без dev-bypass — вернуть 401 если `X-Init-Data == "dev"`
2. `validate_init_data(x_init_data, MASTER_BOT_TOKEN)` → 401 если невалидно
3. `extract_tg_id()` → 401 если нет user
4. `get_master_by_tg_id(tg_id)` → 409 если уже существует
5. `generate_invite_token()` + `create_master(tg_id, name, invite_token, sphere, contacts, work_hours)`
6. Вернуть ответ с `invite_link = f"https://t.me/{MASTER_BOT_USERNAME}?start={invite_token}"`

**Изменения конфига:** `src/config.py` — добавить:
```python
MASTER_BOT_USERNAME: str = os.getenv("MASTER_BOT_USERNAME", "")
```

**Подключение в `app.py`:**
```python
from src.api.routers.master import auth as master_auth
app.include_router(master_auth.router, prefix="/api")
```

### Фронтенд

**Новый файл:** `miniapp/src/master/pages/MasterOnboarding.jsx`

Мульти-степ форма, состояние:
```js
{ step: 1, name: '', sphere: '', contacts: '', work_hours: '', result: null }
```

**Шаг 1 — Имя:**
- Заголовок "Добро пожаловать в CRMfit!"
- Подзаголовок "Настроим ваш профиль за 1 минуту"
- Поле "Ваше имя или псевдоним" (обязательное)
- Кнопка "Далее" (задизейблена пока поле пустое)

**Шаг 2 — Детали (опционально):**
- Поле "Сфера деятельности" (placeholder: "Например: клининг, парикмахер, репетитор")
- Поле "Контакты для клиентов" (placeholder: "Телефон, мессенджеры")
- Поле "Режим работы" (placeholder: "Например: Пн-Пт 9:00-18:00")
- Кнопка "Далее" (primary) + кнопка "Пропустить" (secondary)
- При "Пропустить" — отправить запрос только с `name`

**Шаг 3 — Успех:**
- Анимированная галочка (CSS keyframes, без внешних пакетов)
- "Профиль создан!"
- Инвайт-ссылка с кнопкой копирования (`WebApp.copyToClipboard` если доступно, иначе `navigator.clipboard`)
- Haptic: `WebApp.HapticFeedback.notificationOccurred('success')`
- Telegram MainButton "Начать работу" → вызывает `props.onRegistered()`

**Прогресс-бар:** 3 точки сверху, CSS, текущий шаг подсвечен.

**Новая функция в `client.js`:**
```js
export const registerMaster = (data) =>
  api.post('/master/register', data).then(r => r.data);
```

**Изменения `App.jsx`:**
```jsx
// Убрать UnknownRoleScreen
// Добавить:
if (role === 'unknown') {
  return <MasterOnboarding onRegistered={() => setRole('master')} />;
}
```
`MasterOnboarding` импортировать напрямую (не lazy — маленький компонент, только для новых пользователей).

## Затронутые файлы

| Файл | Действие |
|------|----------|
| `src/config.py` | Добавить `MASTER_BOT_USERNAME` |
| `src/api/routers/master/auth.py` | Создать новый |
| `src/api/app.py` | Подключить новый роутер |
| `miniapp/src/api/client.js` | Добавить `registerMaster` |
| `miniapp/src/master/pages/MasterOnboarding.jsx` | Создать новый |
| `miniapp/src/App.jsx` | Заменить `UnknownRoleScreen` на `MasterOnboarding` |

## Критерии приёмки

1. Новый пользователь → видит онбординг (не "Зарегистрируйтесь через бота")
2. Заполняет имя → опционально детали → профиль создан
3. После регистрации → видит Dashboard
4. Инвайт-ссылка корректная (клиент может по ней зарегистрироваться)
5. Повторный `/start` в боте → бот распознаёт мастера, показывает Home
6. Повторная попытка регистрации → 409
7. `npm run build` без ошибок

## Что НЕ входит в эту задачу

- Соцсети в онбординге (можно добавить позже в профиле)
- Выбор timezone/currency при регистрации (дефолты: Europe/Moscow / RUB)
- Регистрация клиентов через Mini App
