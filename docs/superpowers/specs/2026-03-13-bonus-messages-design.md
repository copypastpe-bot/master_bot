# Приветственный бонус, кастомные сообщения и часовой пояс

**Дата:** 2026-03-13
**Статус:** Утверждён

## Обзор

Расширение функционала бонусной системы:
1. Приветственный бонус при регистрации клиента
2. Настраиваемые тексты сообщений (приветствие + ДР)
3. Возможность прикрепить картинку к сообщениям
4. Выбор часового пояса мастера (для отправки ДР в 13:00 локального времени)

## Изменения в БД

### Миграция 002_bonus_messages.sql

```sql
ALTER TABLE masters ADD COLUMN bonus_welcome INTEGER DEFAULT 0;
ALTER TABLE masters ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow';
ALTER TABLE masters ADD COLUMN welcome_message TEXT;
ALTER TABLE masters ADD COLUMN welcome_photo_id TEXT;
ALTER TABLE masters ADD COLUMN birthday_message TEXT;
ALTER TABLE masters ADD COLUMN birthday_photo_id TEXT;
```

| Поле | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `bonus_welcome` | INTEGER | 0 | Сумма приветственного бонуса (0 = выключен) |
| `timezone` | TEXT | Europe/Moscow | Часовой пояс мастера |
| `welcome_message` | TEXT | NULL | Кастомный текст приветствия (NULL = дефолт) |
| `welcome_photo_id` | TEXT | NULL | Telegram file_id картинки приветствия |
| `birthday_message` | TEXT | NULL | Кастомный текст ДР (NULL = дефолт) |
| `birthday_photo_id` | TEXT | NULL | Telegram file_id картинки ДР |

## UI изменения

### Настройки → Бонусная программа

```
🎁 Бонусная программа
━━━━━━━━━━━━━━━
Статус: ✅ Включена
Начисление: 5% от суммы заказа
Макс. списание: 50% суммы заказа
━━━━━━━━━━━━━━━
🎉 Приветственный: 300 ₽
🎂 Бонус на ДР: 500 ₽
━━━━━━━━━━━━━━━

[% начисления] [% списания]
[🎉 Приветственный] [🎂 День рождения]
[Выключить ✅]
[← Назад]
```

### Подменю "Приветственный" / "День рождения"

```
🎉 Приветственный бонус
━━━━━━━━━━━━━━━
Сумма: 300 ₽
Текст: стандартный
Картинка: нет
━━━━━━━━━━━━━━━

[💰 Сумма] [✏️ Текст]
[🖼 Картинка] [👁 Предпросмотр]
[← Назад]
```

### Настройки → Профиль (добавить часовой пояс)

```
👤 Профиль
━━━━━━━━━━━━━━━
Имя: Анна
Сфера: Маникюр
Часовой пояс: Москва (UTC+3)
━━━━━━━━━━━━━━━

[✏️ Имя] [✏️ Сфера]
[🕐 Часовой пояс]
[← Назад]
```

### Регистрация мастера (новый шаг)

После ввода имени/сферы:

```
🕐 Выберите часовой пояс:

[Калининград (UTC+2)]
[Москва (UTC+3)]
[Самара (UTC+4)]
[Екатеринбург (UTC+5)]
[Новосибирск (UTC+7)]
[Владивосток (UTC+10)]
```

## Список часовых поясов

| Название | Код | UTC offset |
|----------|-----|------------|
| Калининград | Europe/Kaliningrad | +2 |
| Москва | Europe/Moscow | +3 |
| Самара | Europe/Samara | +4 |
| Екатеринбург | Asia/Yekaterinburg | +5 |
| Новосибирск | Asia/Novosibirsk | +7 |
| Владивосток | Asia/Vladivostok | +10 |

## Переменные в шаблонах

| Переменная | Описание | Доступна в |
|------------|----------|------------|
| `{имя}` | Имя клиента | welcome, birthday |
| `{бонус}` | Сумма бонуса | welcome, birthday |
| `{мастер}` | Имя мастера | welcome, birthday |
| `{баланс}` | Баланс после начисления | birthday |

## Тексты по умолчанию

### Приветственное сообщение

```
👋 Добро пожаловать, {имя}!

Ваш мастер {мастер} дарит вам приветственный бонус 🎁 {бонус} ₽

Используйте его при следующем заказе!
```

### Сообщение на ДР

```
🎂 С днём рождения, {имя}!

Ваш мастер {мастер} дарит вам 🎁 {бонус} бонусов!

💰 Ваш баланс: {баланс} ₽

Используйте бонусы при следующем заказе.
```

## Логика

### Приветственный бонус

```
client_bot.py: complete_registration()
    ↓
если master.bonus_welcome > 0 и bonus_enabled:
    ↓
accrue_welcome_bonus(master_id, client_id)
    ↓
render_message(template, переменные)
    ↓
если photo_id: send_photo() иначе send_message()
```

### ДР бонус (изменения в scheduler)

```
scheduler: каждый час в :00
    ↓
для каждого timezone:
    если в timezone сейчас 13:00:
        ↓
        найти мастеров с этим timezone
        ↓
        найти их именинников
        ↓
        начислить бонус и отправить сообщение
```

### Функция render_message

```python
def render_message(template: str | None, default: str, **kwargs) -> str:
    """Render message template with variables."""
    text = template if template else default
    return text.format(
        имя=kwargs.get("имя", ""),
        бонус=kwargs.get("бонус", 0),
        мастер=kwargs.get("мастер", ""),
        баланс=kwargs.get("баланс", 0),
    )
```

### Функция send_bonus_message

```python
async def send_bonus_message(
    bot: Bot,
    chat_id: int,
    text: str,
    photo_id: str | None = None
) -> None:
    """Send bonus message with optional photo."""
    if photo_id:
        await bot.send_photo(chat_id, photo_id, caption=text)
    else:
        await bot.send_message(chat_id, text)
```

## Затрагиваемые файлы

1. `migrations/002_bonus_messages.sql` — новая миграция
2. `src/models.py` — добавить поля в Master
3. `src/database.py` — функции для работы с новыми полями
4. `src/utils.py` — render_message, send_bonus_message
5. `src/keyboards.py` — клавиатуры для настроек
6. `src/states.py` — FSM состояния для редактирования
7. `src/master_bot.py` — UI настроек, регистрация
8. `src/client_bot.py` — отправка приветственного бонуса
9. `src/scheduler.py` — timezone-aware отправка ДР
