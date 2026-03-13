# Приветственный бонус и кастомные сообщения — План реализации

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить приветственный бонус при регистрации, кастомные тексты сообщений с картинками, выбор часового пояса.

**Architecture:** Расширяем таблицу masters новыми полями, добавляем UI в настройках бонусов и профиля, модифицируем scheduler для timezone-aware отправки.

**Tech Stack:** Python 3.11, aiogram 3.x, SQLite, APScheduler

**Spec:** `docs/superpowers/specs/2026-03-13-bonus-messages-design.md`

---

## Структура файлов

| Действие | Файл | Ответственность |
|----------|------|-----------------|
| Create | `migrations/002_bonus_messages.sql` | Новые поля в masters |
| Modify | `src/models.py` | Добавить поля в Master dataclass |
| Modify | `src/database.py` | Функции для новых полей |
| Modify | `src/utils.py` | render_message, send_bonus_message |
| Modify | `src/keyboards.py` | Клавиатуры настроек |
| Modify | `src/states.py` | FSM состояния |
| Modify | `src/master_bot.py` | UI настроек, регистрация |
| Modify | `src/client_bot.py` | Отправка приветственного бонуса |
| Modify | `src/scheduler.py` | Timezone-aware ДР |

---

## Chunk 1: База данных и модели

### Task 1: Миграция БД

**Files:**
- Create: `migrations/002_bonus_messages.sql`

- [ ] **Step 1: Создать файл миграции**

```sql
-- Migration 002: Bonus messages and timezone
-- Adds welcome bonus, custom messages, and timezone support

ALTER TABLE masters ADD COLUMN bonus_welcome INTEGER DEFAULT 0;
ALTER TABLE masters ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow';
ALTER TABLE masters ADD COLUMN welcome_message TEXT;
ALTER TABLE masters ADD COLUMN welcome_photo_id TEXT;
ALTER TABLE masters ADD COLUMN birthday_message TEXT;
ALTER TABLE masters ADD COLUMN birthday_photo_id TEXT;
```

- [ ] **Step 2: Commit**

```bash
git add migrations/002_bonus_messages.sql
git commit -m "feat(db): add migration for bonus messages and timezone"
```

---

### Task 2: Обновить модель Master

**Files:**
- Modify: `src/models.py`

- [ ] **Step 1: Прочитать текущую модель Master**

- [ ] **Step 2: Добавить новые поля в dataclass**

```python
# Добавить после bonus_birthday:
bonus_welcome: int = 0
timezone: str = "Europe/Moscow"
welcome_message: Optional[str] = None
welcome_photo_id: Optional[str] = None
birthday_message: Optional[str] = None
birthday_photo_id: Optional[str] = None
```

- [ ] **Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat(models): add bonus message fields to Master"
```

---

### Task 3: Обновить парсер Master в database.py

**Files:**
- Modify: `src/database.py`

- [ ] **Step 1: Найти функцию _parse_master_row**

- [ ] **Step 2: Добавить новые поля в парсер**

```python
# Добавить в _parse_master_row:
bonus_welcome=row["bonus_welcome"],
timezone=row["timezone"],
welcome_message=row["welcome_message"],
welcome_photo_id=row["welcome_photo_id"],
birthday_message=row["birthday_message"],
birthday_photo_id=row["birthday_photo_id"],
```

- [ ] **Step 3: Commit**

```bash
git add src/database.py
git commit -m "feat(db): parse new bonus message fields"
```

---

## Chunk 2: Утилиты для сообщений

### Task 4: Константы часовых поясов

**Files:**
- Modify: `src/utils.py`

- [ ] **Step 1: Добавить константы timezone**

```python
# Часовые пояса для выбора
TIMEZONES = [
    ("Europe/Kaliningrad", "Калининград", "UTC+2"),
    ("Europe/Moscow", "Москва", "UTC+3"),
    ("Europe/Samara", "Самара", "UTC+4"),
    ("Asia/Yekaterinburg", "Екатеринбург", "UTC+5"),
    ("Asia/Novosibirsk", "Новосибирск", "UTC+7"),
    ("Asia/Vladivostok", "Владивосток", "UTC+10"),
]

def get_timezone_display(tz_code: str) -> str:
    """Get display name for timezone code."""
    for code, name, utc in TIMEZONES:
        if code == tz_code:
            return f"{name} ({utc})"
    return tz_code
```

- [ ] **Step 2: Commit**

```bash
git add src/utils.py
git commit -m "feat(utils): add timezone constants"
```

---

### Task 5: Функции для рендеринга сообщений

**Files:**
- Modify: `src/utils.py`

- [ ] **Step 1: Добавить дефолтные тексты**

```python
DEFAULT_WELCOME_MESSAGE = """👋 Добро пожаловать, {имя}!

Ваш мастер {мастер} дарит вам приветственный бонус 🎁 {бонус} ₽

Используйте его при следующем заказе!"""

DEFAULT_BIRTHDAY_MESSAGE = """🎂 С днём рождения, {имя}!

Ваш мастер {мастер} дарит вам 🎁 {бонус} бонусов!

💰 Ваш баланс: {баланс} ₽

Используйте бонусы при следующем заказе."""
```

- [ ] **Step 2: Добавить функцию render_message**

```python
def render_bonus_message(
    template: Optional[str],
    default: str,
    client_name: str,
    master_name: str,
    bonus_amount: int,
    balance: int = 0,
) -> str:
    """Render bonus message with variable substitution."""
    text = template if template else default
    return text.format(
        имя=client_name,
        мастер=master_name,
        бонус=bonus_amount,
        баланс=balance,
    )
```

- [ ] **Step 3: Commit**

```bash
git add src/utils.py
git commit -m "feat(utils): add render_bonus_message function"
```

---

## Chunk 3: Клавиатуры

### Task 6: Клавиатура выбора timezone

**Files:**
- Modify: `src/keyboards.py`

- [ ] **Step 1: Добавить импорт TIMEZONES**

```python
from src.utils import TIMEZONES
```

- [ ] **Step 2: Добавить клавиатуру timezone**

```python
def timezone_kb() -> InlineKeyboardMarkup:
    """Keyboard for timezone selection."""
    buttons = []
    for code, name, utc in TIMEZONES:
        buttons.append([
            InlineKeyboardButton(
                text=f"{name} ({utc})",
                callback_data=f"set_timezone:{code}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

- [ ] **Step 3: Commit**

```bash
git add src/keyboards.py
git commit -m "feat(kb): add timezone selection keyboard"
```

---

### Task 7: Клавиатуры настроек бонусов

**Files:**
- Modify: `src/keyboards.py`

- [ ] **Step 1: Добавить клавиатуру подменю приветственного/ДР бонуса**

```python
def bonus_message_kb(bonus_type: str, back_to: str = "settings:bonus") -> InlineKeyboardMarkup:
    """Keyboard for welcome/birthday bonus submenu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Сумма", callback_data=f"bonus:{bonus_type}:amount"),
            InlineKeyboardButton(text="✏️ Текст", callback_data=f"bonus:{bonus_type}:text"),
        ],
        [
            InlineKeyboardButton(text="🖼 Картинка", callback_data=f"bonus:{bonus_type}:photo"),
            InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"bonus:{bonus_type}:preview"),
        ],
        [InlineKeyboardButton(text="← Назад", callback_data=back_to)],
    ])
```

- [ ] **Step 2: Обновить settings_bonus_kb — добавить кнопки**

Найти `settings_bonus_kb` и добавить кнопки:
```python
[
    InlineKeyboardButton(text="🎉 Приветственный", callback_data="bonus:welcome"),
    InlineKeyboardButton(text="🎂 День рождения", callback_data="bonus:birthday"),
],
```

- [ ] **Step 3: Commit**

```bash
git add src/keyboards.py
git commit -m "feat(kb): add bonus message settings keyboards"
```

---

## Chunk 4: FSM состояния

### Task 8: Добавить состояния для редактирования

**Files:**
- Modify: `src/states.py`

- [ ] **Step 1: Добавить класс BonusMessageEdit**

```python
class BonusMessageEdit(StatesGroup):
    """States for editing bonus message settings."""
    waiting_amount = State()      # Ожидание ввода суммы
    waiting_text = State()        # Ожидание ввода текста
    waiting_photo = State()       # Ожидание фото
```

- [ ] **Step 2: Добавить состояние для timezone в регистрации**

Найти класс Registration и добавить:
```python
timezone = State()  # Выбор часового пояса
```

- [ ] **Step 3: Commit**

```bash
git add src/states.py
git commit -m "feat(states): add BonusMessageEdit and timezone states"
```

---

## Chunk 5: Функции БД для бонусов

### Task 9: Функция начисления приветственного бонуса

**Files:**
- Modify: `src/database.py`

- [ ] **Step 1: Добавить accrue_welcome_bonus**

```python
async def accrue_welcome_bonus(master_id: int, client_id: int) -> int:
    """Accrue welcome bonus to client. Returns new balance."""
    conn = await get_connection()
    try:
        # Get master settings
        cursor = await conn.execute(
            "SELECT bonus_welcome, bonus_enabled FROM masters WHERE id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        if not row or not row["bonus_enabled"] or row["bonus_welcome"] <= 0:
            return 0

        bonus_amount = row["bonus_welcome"]

        # Update balance
        await conn.execute(
            "UPDATE master_clients SET bonus_balance = bonus_balance + ? WHERE master_id = ? AND client_id = ?",
            (bonus_amount, master_id, client_id)
        )

        # Log bonus
        await conn.execute(
            """INSERT INTO bonus_log (master_id, client_id, type, amount, comment)
               VALUES (?, ?, 'welcome', ?, 'Приветственный бонус')""",
            (master_id, client_id, bonus_amount)
        )

        await conn.commit()

        # Get new balance
        cursor = await conn.execute(
            "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        return row["bonus_balance"] if row else 0
    finally:
        await conn.close()
```

- [ ] **Step 2: Commit**

```bash
git add src/database.py
git commit -m "feat(db): add accrue_welcome_bonus function"
```

---

### Task 10: Функции обновления настроек бонусов

**Files:**
- Modify: `src/database.py`

- [ ] **Step 1: Добавить update_master_bonus_settings**

```python
async def update_master_bonus_setting(master_id: int, field: str, value) -> None:
    """Update a single bonus setting field."""
    allowed_fields = [
        "bonus_welcome", "timezone",
        "welcome_message", "welcome_photo_id",
        "birthday_message", "birthday_photo_id",
    ]
    if field not in allowed_fields:
        raise ValueError(f"Invalid field: {field}")

    conn = await get_connection()
    try:
        await conn.execute(
            f"UPDATE masters SET {field} = ? WHERE id = ?",
            (value, master_id)
        )
        await conn.commit()
    finally:
        await conn.close()
```

- [ ] **Step 2: Commit**

```bash
git add src/database.py
git commit -m "feat(db): add update_master_bonus_setting function"
```

---

## Chunk 6: UI настроек бонусов (master_bot.py)

### Task 11: Обновить отображение настроек бонусов

**Files:**
- Modify: `src/master_bot.py`

- [ ] **Step 1: Найти cb_settings_bonus и обновить текст**

Добавить отображение приветственного бонуса:
```python
welcome_status = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"

text = (
    "🎁 Бонусная программа\n"
    "━━━━━━━━━━━━━━━\n"
    f"Статус: {'✅ Включена' if master.bonus_enabled else '❌ Выключена'}\n"
    f"Начисление: {master.bonus_rate}% от суммы заказа\n"
    f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
    "━━━━━━━━━━━━━━━\n"
    f"🎉 Приветственный: {welcome_status}\n"
    f"🎂 Бонус на ДР: {master.bonus_birthday} ₽\n"
    "━━━━━━━━━━━━━━━"
)
```

- [ ] **Step 2: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(ui): show welcome bonus in settings"
```

---

### Task 12: Обработчик подменю приветственного бонуса

**Files:**
- Modify: `src/master_bot.py`

- [ ] **Step 1: Добавить обработчик bonus:welcome**

```python
@router.callback_query(F.data == "bonus:welcome")
async def cb_bonus_welcome(callback: CallbackQuery) -> None:
    """Show welcome bonus settings."""
    await callback.answer()
    master = await get_master_by_tg_id(callback.from_user.id)

    amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
    text_str = "свой" if master.welcome_message else "стандартный"
    photo_str = "есть" if master.welcome_photo_id else "нет"

    text = (
        "🎉 Приветственный бонус\n"
        "━━━━━━━━━━━━━━━\n"
        f"Сумма: {amount_str}\n"
        f"Текст: {text_str}\n"
        f"Картинка: {photo_str}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, bonus_message_kb("welcome"))
```

- [ ] **Step 2: Аналогичный обработчик bonus:birthday**

```python
@router.callback_query(F.data == "bonus:birthday")
async def cb_bonus_birthday(callback: CallbackQuery) -> None:
    """Show birthday bonus settings."""
    await callback.answer()
    master = await get_master_by_tg_id(callback.from_user.id)

    text_str = "свой" if master.birthday_message else "стандартный"
    photo_str = "есть" if master.birthday_photo_id else "нет"

    text = (
        "🎂 Бонус на день рождения\n"
        "━━━━━━━━━━━━━━━\n"
        f"Сумма: {master.bonus_birthday} ₽\n"
        f"Текст: {text_str}\n"
        f"Картинка: {photo_str}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, bonus_message_kb("birthday"))
```

- [ ] **Step 3: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(ui): add welcome/birthday bonus submenus"
```

---

### Task 13: Обработчики редактирования суммы/текста/фото

**Files:**
- Modify: `src/master_bot.py`

- [ ] **Step 1: Обработчик ввода суммы**

```python
@router.callback_query(F.data.startswith("bonus:") & F.data.endswith(":amount"))
async def cb_bonus_amount(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for bonus amount."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]  # welcome or birthday

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_amount)

    text = "💰 Введите сумму бонуса (0 = выключить):"
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.message(BonusMessageEdit.waiting_amount)
async def on_bonus_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save bonus amount."""
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    try:
        amount = int(message.text.strip())
        if amount < 0:
            raise ValueError()
    except ValueError:
        # Show error briefly
        error_msg = await bot.send_message(message.chat.id, "❌ Введите число >= 0")
        await asyncio.sleep(2)
        try:
            await error_msg.delete()
        except:
            pass
        return

    field = "bonus_welcome" if bonus_type == "welcome" else "bonus_birthday"
    await update_master_bonus_setting(master.id, field, amount)
    await state.clear()

    # Return to bonus submenu
    # ... (trigger cb_bonus_welcome or cb_bonus_birthday)
```

- [ ] **Step 2: Обработчик ввода текста**

```python
@router.callback_query(F.data.startswith("bonus:") & F.data.endswith(":text"))
async def cb_bonus_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for custom message text."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_text)

    variables = "{имя}, {мастер}, {бонус}" + (", {баланс}" if bonus_type == "birthday" else "")
    text = (
        f"✏️ Введите текст сообщения.\n\n"
        f"Переменные: {variables}\n\n"
        f"Отправьте «сброс» для возврата к стандартному тексту."
    )
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.message(BonusMessageEdit.waiting_text)
async def on_bonus_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save custom message text."""
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    text = message.text.strip()
    value = None if text.lower() == "сброс" else text

    field = "welcome_message" if bonus_type == "welcome" else "birthday_message"
    await update_master_bonus_setting(master.id, field, value)
    await state.clear()
```

- [ ] **Step 3: Обработчик загрузки фото**

```python
@router.callback_query(F.data.startswith("bonus:") & F.data.endswith(":photo"))
async def cb_bonus_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for photo upload."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_photo)

    text = "🖼 Отправьте картинку или «удалить» для удаления текущей."
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.message(BonusMessageEdit.waiting_photo, F.photo)
async def on_bonus_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save photo file_id."""
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    photo_id = message.photo[-1].file_id

    field = "welcome_photo_id" if bonus_type == "welcome" else "birthday_photo_id"
    await update_master_bonus_setting(master.id, field, photo_id)
    await state.clear()


@router.message(BonusMessageEdit.waiting_photo)
async def on_bonus_photo_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle text in photo state (for 'удалить')."""
    try:
        await message.delete()
    except:
        pass

    if message.text and message.text.strip().lower() == "удалить":
        data = await state.get_data()
        bonus_type = data.get("bonus_type")
        master = await get_master_by_tg_id(message.from_user.id)

        field = "welcome_photo_id" if bonus_type == "welcome" else "birthday_photo_id"
        await update_master_bonus_setting(master.id, field, None)

    await state.clear()
```

- [ ] **Step 4: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(ui): add bonus amount/text/photo editing handlers"
```

---

### Task 14: Обработчик предпросмотра

**Files:**
- Modify: `src/master_bot.py`

- [ ] **Step 1: Добавить обработчик preview**

```python
@router.callback_query(F.data.startswith("bonus:") & F.data.endswith(":preview"))
async def cb_bonus_preview(callback: CallbackQuery, bot: Bot) -> None:
    """Send preview of bonus message."""
    await callback.answer("Отправляю предпросмотр...")
    bonus_type = callback.data.split(":")[1]
    master = await get_master_by_tg_id(callback.from_user.id)

    if bonus_type == "welcome":
        template = master.welcome_message
        default = DEFAULT_WELCOME_MESSAGE
        amount = master.bonus_welcome
        photo_id = master.welcome_photo_id
        balance = 0
    else:
        template = master.birthday_message
        default = DEFAULT_BIRTHDAY_MESSAGE
        amount = master.bonus_birthday
        photo_id = master.birthday_photo_id
        balance = 1500  # Example balance

    text = render_bonus_message(
        template=template,
        default=default,
        client_name="Анна",
        master_name=master.name,
        bonus_amount=amount,
        balance=balance,
    )

    try:
        if photo_id:
            await bot.send_photo(callback.from_user.id, photo_id, caption=text)
        else:
            await bot.send_message(callback.from_user.id, text)
    except Exception as e:
        await bot.send_message(callback.from_user.id, f"❌ Ошибка: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(ui): add bonus message preview"
```

---

## Chunk 7: Часовой пояс в профиле и регистрации

### Task 15: Timezone в настройках профиля

**Files:**
- Modify: `src/master_bot.py`

- [ ] **Step 1: Обновить отображение профиля**

Найти обработчик профиля и добавить timezone:
```python
from src.utils import get_timezone_display

tz_display = get_timezone_display(master.timezone)

text = (
    "👤 Профиль\n"
    "━━━━━━━━━━━━━━━\n"
    f"Имя: {master.name}\n"
    f"Сфера: {master.sphere or '—'}\n"
    f"Часовой пояс: {tz_display}\n"
    "━━━━━━━━━━━━━━━"
)
```

- [ ] **Step 2: Добавить кнопку timezone в клавиатуру профиля**

- [ ] **Step 3: Добавить обработчик выбора timezone**

```python
@router.callback_query(F.data == "profile:timezone")
async def cb_profile_timezone(callback: CallbackQuery) -> None:
    """Show timezone selection."""
    await callback.answer()
    text = "🕐 Выберите часовой пояс:"
    await edit_home_message(callback, text, timezone_kb())


@router.callback_query(F.data.startswith("set_timezone:"))
async def cb_set_timezone(callback: CallbackQuery) -> None:
    """Save selected timezone."""
    await callback.answer("Сохранено!")
    tz_code = callback.data.split(":")[1]
    master = await get_master_by_tg_id(callback.from_user.id)

    await update_master_bonus_setting(master.id, "timezone", tz_code)

    # Return to profile
    # ... (trigger profile display)
```

- [ ] **Step 4: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(ui): add timezone selection in profile"
```

---

### Task 16: Timezone при регистрации мастера

**Files:**
- Modify: `src/master_bot.py`

- [ ] **Step 1: Найти flow регистрации и добавить шаг timezone**

После ввода сферы, перед завершением:
```python
# В обработчике после сферы:
await state.set_state(Registration.timezone)
text = "🕐 Выберите часовой пояс:"
await message.answer(text, reply_markup=timezone_kb())
```

- [ ] **Step 2: Добавить обработчик выбора timezone в регистрации**

```python
@router.callback_query(Registration.timezone, F.data.startswith("set_timezone:"))
async def reg_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    """Save timezone during registration."""
    await callback.answer()
    tz_code = callback.data.split(":")[1]
    await state.update_data(timezone=tz_code)

    # Continue to next step or complete registration
    # ...
```

- [ ] **Step 3: Сохранить timezone при создании мастера**

- [ ] **Step 4: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(reg): add timezone selection during master registration"
```

---

## Chunk 8: Приветственный бонус при регистрации клиента

### Task 17: Отправка приветственного бонуса

**Files:**
- Modify: `src/client_bot.py`

- [ ] **Step 1: Добавить импорты**

```python
from src.database import accrue_welcome_bonus
from src.utils import render_bonus_message, DEFAULT_WELCOME_MESSAGE
```

- [ ] **Step 2: В complete_registration добавить отправку бонуса**

После создания client и link:
```python
# Welcome bonus
master = await get_master_by_id(master_id)
if master.bonus_enabled and master.bonus_welcome > 0:
    new_balance = await accrue_welcome_bonus(master_id, client_id)

    if new_balance > 0:
        text = render_bonus_message(
            template=master.welcome_message,
            default=DEFAULT_WELCOME_MESSAGE,
            client_name=client_name,
            master_name=master.name,
            bonus_amount=master.bonus_welcome,
        )

        try:
            if master.welcome_photo_id:
                await bot.send_photo(tg_id, master.welcome_photo_id, caption=text)
            else:
                await bot.send_message(tg_id, text)
        except Exception as e:
            logger.error(f"Failed to send welcome bonus: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add src/client_bot.py
git commit -m "feat(client): send welcome bonus on registration"
```

---

## Chunk 9: Timezone-aware ДР в scheduler

### Task 18: Обновить scheduler для timezone

**Files:**
- Modify: `src/scheduler.py`

- [ ] **Step 1: Добавить импорты**

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from src.utils import render_bonus_message, DEFAULT_BIRTHDAY_MESSAGE, TIMEZONES
```

- [ ] **Step 2: Создать функцию get_timezones_at_hour**

```python
def get_timezones_at_hour(hour: int) -> list[str]:
    """Return timezone codes where current local time is the given hour."""
    now_utc = datetime.now(ZoneInfo("UTC"))
    result = []
    for tz_code, _, _ in TIMEZONES:
        local_time = now_utc.astimezone(ZoneInfo(tz_code))
        if local_time.hour == hour:
            result.append(tz_code)
    return result
```

- [ ] **Step 3: Обновить get_clients_with_birthday_today**

Добавить фильтр по timezone:
```python
async def get_clients_with_birthday_today(timezones: list[str]) -> list[dict]:
    """Get clients with birthday today for masters in given timezones."""
    # ... SQL with WHERE m.timezone IN (...)
```

- [ ] **Step 4: Обновить send_birthday_bonuses**

```python
async def send_birthday_bonuses(client_bot: Bot) -> None:
    """Send birthday bonuses for timezones where it's 13:00."""
    logger.info("Running birthday bonus task")

    # Find timezones where it's currently 13:00
    active_timezones = get_timezones_at_hour(13)
    if not active_timezones:
        logger.info("No timezones at 13:00, skipping")
        return

    logger.info(f"Active timezones at 13:00: {active_timezones}")

    clients = await get_clients_with_birthday_today(active_timezones)
    # ... rest of logic with render_bonus_message and photo support
```

- [ ] **Step 5: Commit**

```bash
git add src/scheduler.py src/database.py
git commit -m "feat(scheduler): timezone-aware birthday bonus sending"
```

---

## Chunk 10: Финальная интеграция

### Task 19: Обновить отправку ДР с фото и кастомным текстом

**Files:**
- Modify: `src/scheduler.py`

- [ ] **Step 1: Обновить цикл отправки**

```python
for client in clients:
    try:
        new_balance = await accrue_birthday_bonus(
            client["master_id"],
            client["client_id"]
        )

        if new_balance == client["bonus_balance"]:
            continue  # Already accrued

        text = render_bonus_message(
            template=client.get("birthday_message"),
            default=DEFAULT_BIRTHDAY_MESSAGE,
            client_name=client.get("client_name") or "—",
            master_name=client.get("master_name") or "—",
            bonus_amount=client["bonus_birthday"],
            balance=new_balance,
        )

        photo_id = client.get("birthday_photo_id")
        if photo_id:
            await client_bot.send_photo(client["client_tg_id"], photo_id, caption=text)
        else:
            await client_bot.send_message(client["client_tg_id"], text)

        logger.info(f"Sent birthday bonus to client {client['client_id']}")

    except TelegramForbiddenError:
        logger.warning(f"Client blocked bot: {client['client_tg_id']}")
    except Exception as e:
        logger.error(f"Error sending birthday bonus: {e}")
```

- [ ] **Step 2: Обновить SQL запрос для получения birthday_message и photo_id**

- [ ] **Step 3: Commit**

```bash
git add src/scheduler.py src/database.py
git commit -m "feat(scheduler): use custom message and photo for birthday"
```

---

### Task 20: Тестирование и финальный коммит

- [ ] **Step 1: Запустить бота локально**

```bash
python run_master.py
```

- [ ] **Step 2: Проверить flow**
- Настройки → Бонусы → Приветственный → редактировать
- Настройки → Профиль → Часовой пояс
- Регистрация нового клиента (должен получить приветственный бонус)

- [ ] **Step 3: Финальный коммит**

```bash
git add .
git commit -m "feat: complete bonus messages and timezone feature"
```

---

## Итого: 20 задач, ~15 коммитов

| Chunk | Задачи | Коммиты |
|-------|--------|---------|
| 1. БД и модели | 1-3 | 3 |
| 2. Утилиты | 4-5 | 2 |
| 3. Клавиатуры | 6-7 | 2 |
| 4. FSM | 8 | 1 |
| 5. Функции БД | 9-10 | 2 |
| 6. UI бонусов | 11-14 | 4 |
| 7. Timezone | 15-16 | 2 |
| 8. Welcome bonus | 17 | 1 |
| 9. Scheduler | 18 | 1 |
| 10. Интеграция | 19-20 | 2 |
