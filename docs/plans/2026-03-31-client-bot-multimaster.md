# client_bot Multi-Master Scenarios Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Закрыть три недостающих сценария мультимастерности в `client_bot.py`: привязка существующего клиента к новому мастеру через токен, сообщение "уже привязан", и авто-выбор best_master при `/start` без токена.

**Architecture:** Два изменения в одном файле. (1) `get_client_context` — однострочный фикс fallback на `masters[0]` вместо `(client, None, None)`. (2) `cmd_start` — реструктурировать порядок проверок: сначала извлечь токен и загрузить клиента, затем разделить на две ветки (с токеном / без токена).

**Tech Stack:** Python, aiogram 3.x, aiosqlite. Тестов нет — верификация через `python3 -c "from src.client_bot import router; print('OK')"`.

---

### Task 1: Исправить `get_client_context` — fallback на latest last_visit

**Files:**
- Modify: `src/client_bot.py` (~строка 175-177)

**Контекст:** Функция `get_client_masters` в `database.py` возвращает мастеров, отсортированных по `last_visit DESC NULLS LAST`. Значит `masters[0]` — всегда самый "свежий" мастер. Нужно использовать его как fallback вместо возврата `None`.

**Step 1: Найти строки для замены**

В `src/client_bot.py` найти блок (~строка 173-177):
```python
    elif len(masters) == 1:
        master_id = masters[0]["master_id"]
    else:
        # Multiple masters, no selection — caller must handle
        return client, None, None
```

**Step 2: Заменить на fallback**

```python
    else:
        master_id = masters[0]["master_id"]  # latest last_visit (sorted by DB)
```

Полный `else`-блок теперь покрывает и `len == 1`, и `len > 1`. Строку `elif len(masters) == 1:` тоже убрать, заменив двумя случаями одним `else`:

Итоговый фрагмент `get_client_context` после строки `if master_id:`:
```python
    if master_id:
        entry = next((m for m in masters if m["master_id"] == master_id), None)
        if not entry:
            return client, None, None
    else:
        master_id = masters[0]["master_id"]  # latest last_visit (sorted by DB)
```

**Step 3: Также обновить docstring**

```python
async def get_client_context(tg_id: int, master_id: int = None) -> tuple:
    """Get client, master, and master_client for a user.

    If master_id specified → use that master.
    Otherwise → master with latest last_visit (masters[0], sorted by DB).
    Returns (None, None, None) if client not found or has no masters.
    """
```

**Step 4: Проверить синтаксис**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python3 -c "from src.client_bot import router; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 5: Commit**

```bash
git add src/client_bot.py
git commit -m "fix(bot): get_client_context falls back to latest-last_visit master"
```

---

### Task 2: Реструктурировать `cmd_start`

**Files:**
- Modify: `src/client_bot.py` (~строка 246-311)

**Контекст:** Текущая проблема — код проверяет "уже зарегистрирован" ДО извлечения токена. Из-за этого токен игнорируется для существующих клиентов. Нужно: сначала загрузить клиента и токен, затем — два чётких if-ветки.

**Уже импортированы** (проверить, не дублировать):
- `get_client_by_tg_id`, `get_master_by_invite_token`, `get_master_client`
- `link_existing_client_to_master`, `accrue_welcome_bonus`
- `_active_masters` (module-level dict)

**Step 1: Найти текущую функцию**

Найти строку `@router.message(CommandStart())` (~строка 246). Функция заканчивается на строке ~311 (`await state.set_state(ClientRegistration.consent)`).

**Step 2: Заменить тело функции целиком**

```python
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start command."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    tg_id = message.from_user.id

    # Extract token early (before any DB calls)
    args = message.text.split(maxsplit=1)
    invite_token = args[1].strip() if len(args) >= 2 else None

    # Load client (without master — token determines which master)
    client = await get_client_by_tg_id(tg_id)

    # ── Branch A: invite token present ────────────────────────────────────────
    if invite_token:
        master = await get_master_by_invite_token(invite_token)
        if not master:
            await bot.send_message(
                message.chat.id,
                "❌ Ссылка недействительна.\n\n"
                "Попросите мастера отправить вам актуальную ссылку."
            )
            return

        if not client:
            # New client → full registration FSM (unchanged)
            await state.update_data(master_id=master.id)
            await bot.send_message(
                message.chat.id,
                "Привет 👋\n\n"
                "Для регистрации нам нужно ваше согласие на обработку персональных данных.\n\n"
                "Мы собираем: имя, телефон, дату рождения (опционально).\n"
                "Данные используются только для записи и бонусной программы.\n\n"
                '📜 <a href="https://crmfit.ru/privacy">Политика конфиденциальности</a>',
                reply_markup=consent_kb(),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await state.set_state(ClientRegistration.consent)
            return

        # Existing client — check if already linked
        existing_link = await get_master_client(master.id, client.id)
        if existing_link:
            # Scenario 3: already linked to this master
            _active_masters[tg_id] = master.id
            await state.clear()
            await bot.send_message(
                message.chat.id,
                f"✅ Вы уже записаны к мастеру {master.name}"
            )
            await show_home(bot, client, master, existing_link, message.chat.id, force_new=True)
        else:
            # Scenario 2: existing client, new master
            await link_existing_client_to_master(client.id, master.id)
            await accrue_welcome_bonus(master.id, client.id)
            _active_masters[tg_id] = master.id
            master_client = await get_master_client(master.id, client.id)
            await state.clear()
            await bot.send_message(
                message.chat.id,
                f"✅ Вы подключились к мастеру {master.name}!"
            )
            await show_home(bot, client, master, master_client, message.chat.id, force_new=True)
        return

    # ── Branch B: no token ────────────────────────────────────────────────────
    if not client:
        await bot.send_message(
            message.chat.id,
            "👋 Добро пожаловать!\n\n"
            "Для регистрации нужна ссылка от вашего мастера.\n"
            "Попросите мастера отправить вам персональную ссылку.",
            reply_markup=home_reply_kb()
        )
        return

    # Registered client, no token → show Home (get_client_context picks best master)
    await state.clear()
    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if master:
        await show_home(bot, client, master, master_client, message.chat.id, force_new=True)
    else:
        await bot.send_message(
            message.chat.id,
            "👋 Для начала работы нужна ссылка от мастера.",
            reply_markup=home_reply_kb()
        )
```

**Step 3: Проверить синтаксис**

```bash
python3 -c "from src.client_bot import router; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 4: Commit**

```bash
git add src/client_bot.py
git commit -m "feat(bot): restructure cmd_start for multi-master scenarios 2, 3, 5"
```

---

### Task 3: Финальная проверка

**Step 1: Проверить все импорты**

```bash
python3 -c "
from src.client_bot import router, get_client_context, _active_masters, show_master_select
from src.keyboards import home_client_kb
print('All imports OK')
"
```

Ожидаемый вывод: `All imports OK`

**Step 2: Проверить app запускается**

```bash
python3 -c "from src.api.app import app; print('API OK')"
```

Ожидаемый вывод: `API OK`

**Step 3: Финальный commit (если нужны правки)**

```bash
git add src/client_bot.py
git commit -m "fix(bot): <описание>"
```

---

## Итог: затронутые файлы

| Файл | Изменение |
|------|-----------|
| `src/client_bot.py` | `get_client_context` fallback + `cmd_start` реструктуризация |

## Backward compatibility

- Новый клиент + токен → регистрация как раньше (FSM не тронут)
- Клиент с 1 мастером + без токена → Home как раньше
- master_bot и мастерский Mini App — не затронуты
