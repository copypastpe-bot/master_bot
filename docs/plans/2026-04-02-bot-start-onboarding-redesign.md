# Bot /start + Onboarding Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Сделать бота точкой входа (баннер + кнопка Mini App) и убрать FSM-регистрацию; переделать онбординг Mini App на 3 шага (имя → ниша → первый клиент).

**Architecture:** Бот отключается от всех навигационных роутеров в `setup_dispatcher`; старый код комментируется, не удаляется. Онбординг Mini App переписывается с нуля в `MasterOnboarding.jsx`. Мастер создаётся в БД после Шага 2 (имя + ниша вместе). Шаг 3 использует уже существующие API.

**Tech Stack:** Python/aiogram 3, FastAPI, React (Vite), aiosqlite, Pillow

---

### Task 1: Сгенерировать welcome_banner.png

**Files:**
- Create: `scripts/generate_banner.py`
- Create: `assets/welcome_banner.png` (результат скрипта)

**Step 1: Создать скрипт генерации баннера**

```python
# scripts/generate_banner.py
"""Generate welcome banner for Master Bot /start command."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
img = Image.new("RGB", (W, H), color=(30, 30, 46))

draw = ImageDraw.Draw(img)

# Gradient overlay (top-left blue → bottom-right purple)
for y in range(H):
    for x in range(W):
        r = int(30 + (80 - 30) * x / W + (60 - 30) * y / H)
        g = int(30 + (10 - 30) * x / W)
        b = int(46 + (120 - 46) * x / W + (80 - 46) * y / H)
        draw.point((x, y), fill=(min(r, 255), max(g, 0), min(b, 255)))

# Text: CRMfit (large)
try:
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 100)
    font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
except:
    font_big = ImageFont.load_default()
    font_sub = font_big

draw.text((W // 2, H // 2 - 60), "CRMfit", font=font_big, fill="white", anchor="mm")
draw.text((W // 2, H // 2 + 60), "CRM для мастеров в Telegram", font=font_sub, fill=(200, 200, 220), anchor="mm")

out = Path(__file__).parent.parent / "assets" / "welcome_banner.png"
out.parent.mkdir(exist_ok=True)
img.save(out)
print(f"Banner saved: {out}")
```

**Step 2: Запустить скрипт**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
pip install pillow  # если не установлен
python scripts/generate_banner.py
```

Ожидаемый вывод: `Banner saved: .../assets/welcome_banner.png`

**Step 3: Проверить файл**

```bash
ls -lh assets/welcome_banner.png
# Ожидание: файл ~100-500KB
```

**Step 4: Commit**

```bash
git add scripts/generate_banner.py assets/welcome_banner.png
git commit -m "feat(bot): add welcome banner asset"
```

---

### Task 2: DB migration + models

**Files:**
- Create: `migrations/001_onboarding_flags.sql`
- Modify: `src/models.py` (добавить 2 поля в Master)
- Modify: `src/database.py` (ALLOWED_MASTER_FIELDS + _parse_master_row)

**Step 1: Создать папку migrations и файл миграции**

```bash
mkdir -p /Users/evgenijpastusenko/Projects/Master_bot/migrations
```

Файл `migrations/001_onboarding_flags.sql`:
```sql
ALTER TABLE masters ADD COLUMN onboarding_skipped_first_client BOOLEAN DEFAULT FALSE;
ALTER TABLE masters ADD COLUMN onboarding_banner_shown BOOLEAN DEFAULT FALSE;
```

**Step 2: Обновить `src/models.py` — добавить поля в Master**

После строки `home_message_id: Optional[int] = None` добавить:
```python
    onboarding_skipped_first_client: bool = False
    onboarding_banner_shown: bool = False
```

**Step 3: Обновить `src/database.py` — ALLOWED_MASTER_FIELDS**

В `ALLOWED_MASTER_FIELDS` добавить два ключа:
```python
ALLOWED_MASTER_FIELDS = frozenset({
    "name", "sphere", "socials", "contacts", "work_hours", "invite_token",
    "bonus_enabled", "bonus_rate", "bonus_max_spend", "bonus_birthday",
    "gc_connected", "gc_credentials",
    "bonus_welcome", "timezone", "welcome_message", "welcome_photo_id",
    "birthday_message", "birthday_photo_id", "home_message_id", "currency",
    "onboarding_skipped_first_client", "onboarding_banner_shown",  # NEW
})
```

**Step 4: Обновить `_parse_master_row` — добавить парсинг новых полей**

После строки `home_message_id=row["home_message_id"] if "home_message_id" in row.keys() else None,` добавить:
```python
        onboarding_skipped_first_client=bool(row["onboarding_skipped_first_client"]) if "onboarding_skipped_first_client" in row.keys() else False,
        onboarding_banner_shown=bool(row["onboarding_banner_shown"]) if "onboarding_banner_shown" in row.keys() else False,
```

**Step 5: Проверить, что миграция применяется**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "import asyncio; from src.database import init_db; asyncio.run(init_db()); print('OK')"
```

Ожидание: `OK` без ошибок.

**Step 6: Commit**

```bash
git add migrations/001_onboarding_flags.sql src/models.py src/database.py
git commit -m "feat(db): add onboarding flags to Master model and migration"
```

---

### Task 3: Отключить роутеры в master_bot.py

**Files:**
- Modify: `src/master_bot.py`

**Step 1: Обновить `setup_dispatcher()`**

Текущий код:
```python
from src.handlers import common, registration, orders, clients, marketing, reports, settings

def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(common.HomeButtonMiddleware())
    dp.include_router(common.router)
    dp.include_router(registration.router)
    dp.include_router(orders.router)
    dp.include_router(clients.router)
    dp.include_router(marketing.router)
    dp.include_router(reports.router)
    dp.include_router(settings.router)
    return dp
```

Заменить на:
```python
from src.handlers import common  # registration, orders, clients, marketing, reports, settings — disabled

def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # HomeButtonMiddleware disabled — bot is entry point only, no navigation
    # dp.message.outer_middleware(common.HomeButtonMiddleware())

    dp.include_router(common.router)

    # Navigation routers disabled — all functionality moved to Mini App
    # dp.include_router(registration.router)
    # dp.include_router(orders.router)
    # dp.include_router(clients.router)
    # dp.include_router(marketing.router)
    # dp.include_router(reports.router)
    # dp.include_router(settings.router)

    return dp
```

**Step 2: Проверить синтаксис**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "from src.master_bot import setup_dispatcher; print('OK')"
```

Ожидание: `OK`

**Step 3: Commit**

```bash
git add src/master_bot.py
git commit -m "feat(bot): disable navigation routers — bot is entry point only"
```

---

### Task 4: Новый cmd_start и cmd_home в common.py

**Files:**
- Modify: `src/handlers/common.py`

**Step 1: Обновить импорты**

Текущие импорты:
```python
from src.database import get_master_by_tg_id, get_orders_today, save_master_home_message_id
from src.keyboards import home_master_kb, home_reply_kb
from src.states import MasterRegistration
```

Заменить на:
```python
from src.database import get_master_by_tg_id
from src.config import MINIAPP_URL
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, FSInputFile
```

**Step 2: Закомментировать старый код**

Закомментировать следующие блоки (оставить в файле, не удалять):
- `HomeButtonMiddleware` (весь класс, строки 28-56)
- `build_home_text()` (строки 63-90)
- `show_home()` (строки 93-132)
- `edit_home_message()` (строки 135-140)
- `cb_home` хендлер (строки 189-202)
- Константы `MONTHS_RU` и `MONTHS_RU_NOM` (строки 17-25)

Обернуть каждый блок в `# --- DISABLED: moved to Mini App ---` и `# --- END DISABLED ---`.

**Step 3: Заменить `cmd_start`**

```python
BANNER_PATH = "assets/welcome_banner.png"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start — show banner with Mini App button."""
    await state.clear()

    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if master:
        caption = (
            f"Привет, {master.name}! 👋\n\n"
            "Открой приложение, чтобы продолжить работу."
        )
    else:
        caption = (
            "Привет! Помогу вести запись клиентов, напоминать им "
            "о визите и вести учёт финансов.\n\n"
            "Всё в Telegram — никаких лишних приложений."
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть приложение →",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )]
    ])

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=FSInputFile(BANNER_PATH),
        caption=caption,
        reply_markup=keyboard,
    )
```

**Step 4: Заменить `cmd_home`**

```python
@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /home — same as /start."""
    await state.clear()

    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if master:
        caption = (
            f"Привет, {master.name}! 👋\n\n"
            "Открой приложение, чтобы продолжить работу."
        )
    else:
        caption = (
            "Привет! Помогу вести запись клиентов, напоминать им "
            "о визите и вести учёт финансов.\n\n"
            "Всё в Telegram — никаких лишних приложений."
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть приложение →",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )]
    ])

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=FSInputFile(BANNER_PATH),
        caption=caption,
        reply_markup=keyboard,
    )
```

**Step 5: Проверить синтаксис**

```bash
python -c "from src.handlers.common import router; print('OK')"
```

Ожидание: `OK`

**Step 6: Commit**

```bash
git add src/handlers/common.py
git commit -m "feat(bot): replace /start with banner+miniapp button, disable home screen"
```

---

### Task 5: Разрешить заказы без услуг в API

**Files:**
- Modify: `src/api/routers/master/orders.py:107-108`

**Step 1: Удалить проверку на пустой список услуг**

Текущий код (строки 107-108):
```python
    if not body.services:
        raise HTTPException(status_code=400, detail="At least one service is required")
```

Удалить эти две строки полностью.

После удаления следующая активная строка должна быть:
```python
    # Validate client belongs to this master
    mc = await get_master_client(master.id, body.client_id)
```

**Step 2: Убедиться что `amount_total = 0` при пустом списке**

Строка `amount_total = sum(item["price"] for item in order_items)` уже корректно вернёт `0` при `order_items = []`. Ничего менять не нужно.

**Step 3: Проверить синтаксис**

```bash
python -c "from src.api.routers.master.orders import router; print('OK')"
```

**Step 4: Commit**

```bash
git add src/api/routers/master/orders.py
git commit -m "fix(api): allow creating orders without services (amount_total=0)"
```

---

### Task 6: Переписать MasterOnboarding.jsx — Шаги 1 и 2

**Files:**
- Modify: `miniapp/src/master/pages/MasterOnboarding.jsx` (полная замена)

**Step 1: Написать новый компонент (Steps 1-2 + каркас)**

Полностью заменить содержимое файла:

```jsx
import { useState, useEffect, useRef } from 'react';
import { registerMaster, createMasterClient, createMasterOrder, updateMasterProfile } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

// ─── Styles ────────────────────────────────────────────────────────────────

const S = {
  wrap: { padding: '32px 20px', maxWidth: 420, margin: '0 auto' },
  dots: { display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 36 },
  dot: (active) => ({
    width: 8, height: 8, borderRadius: '50%',
    background: active ? 'var(--tg-button)' : 'var(--tg-hint)',
    opacity: active ? 1 : 0.35,
    transition: 'all 0.2s',
  }),
  h1: { fontSize: 26, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 6 },
  sub: { fontSize: 14, color: 'var(--tg-hint)', marginBottom: 28 },
  label: { fontSize: 13, color: 'var(--tg-hint)', display: 'block', marginBottom: 6 },
  input: {
    width: '100%', padding: '12px 14px', borderRadius: 12,
    border: '1.5px solid var(--tg-hint)', background: 'var(--tg-bg)',
    color: 'var(--tg-text)', fontSize: 16, outline: 'none', boxSizing: 'border-box',
  },
  btnPrimary: (disabled) => ({
    width: '100%', padding: '14px', borderRadius: 12, border: 'none',
    background: 'var(--tg-button)', color: 'var(--tg-button-text)',
    fontSize: 16, fontWeight: 600, cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  }),
  btnSecondary: {
    width: '100%', padding: '12px', borderRadius: 12,
    border: '1.5px solid var(--tg-hint)', background: 'transparent',
    color: 'var(--tg-hint)', fontSize: 15, cursor: 'pointer', marginTop: 10,
  },
  error: { color: '#e53935', fontSize: 13, marginBottom: 12 },
};

// ─── Niches ─────────────────────────────────────────────────────────────────

const NICHES = [
  'Клининг',
  'Химчистка мебели и ковров',
  'Парикмахер и барбер',
  'Маникюр и бьюти-услуги',
  'Груминг и животные',
  'Массаж',
  'Ремонт бытовой техники',
  'Мастер на час, мелкий ремонт',
  'Репетитор',
  'Фотограф и видеограф',
  'Психолог',
  'Садовник',
  'Другое',
];

// ─── Utils ───────────────────────────────────────────────────────────────────

function tomorrowDate() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0];
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function MasterOnboarding({ onRegistered }) {
  const [step, setStep] = useState(1);

  // Step 1
  const [name, setName] = useState('');

  // Step 2
  const [selectedNiche, setSelectedNiche] = useState(null);
  const [customNiche, setCustomNiche] = useState('');

  // Step 3
  const [clientName, setClientName] = useState('');
  const [clientPhone, setClientPhone] = useState('');
  const [clientDate, setClientDate] = useState(tomorrowDate());
  const [clientTime, setClientTime] = useState('10:00');
  const [clientAdded, setClientAdded] = useState(false);

  // Shared
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const autoAdvanceTimer = useRef(null);

  // ── Cleanup timer on unmount
  useEffect(() => () => clearTimeout(autoAdvanceTimer.current), []);

  // ── Step 2 → register master after niche selected
  const handleNicheSelect = async (niche) => {
    if (loading) return;
    setSelectedNiche(niche);
    WebApp?.HapticFeedback?.selectionChanged();

    if (niche !== 'Другое') {
      autoAdvanceTimer.current = setTimeout(() => doRegister(niche), 300);
    }
  };

  const doRegister = async (sphere) => {
    setLoading(true);
    setError('');
    try {
      await registerMaster({ name: name.trim(), sphere });
      setStep(3);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Ошибка регистрации. Попробуйте ещё раз.';
      // 409 = already registered — still proceed
      if (err?.response?.status === 409) {
        setStep(3);
      } else {
        setError(msg);
        setSelectedNiche(null);
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Step 3 → add first client
  const handleAddClient = async () => {
    setLoading(true);
    setError('');
    try {
      const client = await createMasterClient({ name: clientName.trim(), phone: clientPhone.trim() });
      await createMasterOrder({
        client_id: client.id,
        scheduled_date: clientDate,
        scheduled_time: clientTime,
        services: [],
      });
      setClientAdded(true);
      setStep(4);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Не удалось добавить клиента.');
    } finally {
      setLoading(false);
    }
  };

  const handleSkipClient = async () => {
    setLoading(true);
    try {
      await updateMasterProfile({ onboarding_skipped_first_client: true });
    } catch (_) {
      // non-critical
    } finally {
      setLoading(false);
      setClientAdded(false);
      setStep(4);
    }
  };

  // ── Final screen → Telegram MainButton
  useEffect(() => {
    if (step !== 4 || !WebApp?.MainButton) return;
    const handleStart = () => { WebApp.MainButton.hide(); onRegistered(); };
    WebApp.MainButton.setText('Начать работу');
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleStart);
    return () => { WebApp.MainButton.offClick(handleStart); WebApp.MainButton.hide(); };
  }, [step]);

  const step3Ready = clientName.trim() && clientPhone.trim() && clientDate && clientTime;

  return (
    <div style={S.wrap}>
      {/* Progress dots — 3 visible steps */}
      <div style={S.dots}>
        {[1, 2, 3].map((n) => <div key={n} style={S.dot(step === n || (step === 4 && n === 3))} />)}
      </div>

      {/* ── Step 1: Name ─────────────────────────────── */}
      {step === 1 && (
        <>
          <div style={S.h1}>Как тебя зовут?</div>
          <div style={S.sub}>Будем обращаться по имени</div>
          <div style={{ marginBottom: 24 }}>
            <label style={S.label}>Имя</label>
            <input
              style={S.input}
              placeholder="Например: Анна"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <button
            style={S.btnPrimary(!name.trim())}
            disabled={!name.trim()}
            onClick={() => setStep(2)}
          >
            Продолжить
          </button>
        </>
      )}

      {/* ── Step 2: Niche ─────────────────────────────── */}
      {step === 2 && (
        <>
          <div style={S.h1}>Чем занимаешься?</div>
          <div style={S.sub}>Настроим шаблоны напоминаний под тебя</div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
            {NICHES.map((niche) => (
              <button
                key={niche}
                disabled={loading}
                onClick={() => handleNicheSelect(niche)}
                style={{
                  padding: '8px 14px',
                  borderRadius: 20,
                  border: `1.5px solid ${selectedNiche === niche ? 'var(--tg-button)' : 'var(--tg-hint)'}`,
                  background: selectedNiche === niche ? 'var(--tg-button)' : 'transparent',
                  color: selectedNiche === niche ? 'var(--tg-button-text)' : 'var(--tg-text)',
                  fontSize: 14,
                  cursor: loading ? 'default' : 'pointer',
                  transition: 'all 0.15s',
                  opacity: loading && selectedNiche !== niche ? 0.5 : 1,
                }}
              >
                {niche}
              </button>
            ))}
          </div>

          {selectedNiche === 'Другое' && (
            <div style={{ marginBottom: 16 }}>
              <input
                style={S.input}
                placeholder="Напишите вашу нишу"
                value={customNiche}
                onChange={(e) => setCustomNiche(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {error && <div style={S.error}>{error}</div>}

          {selectedNiche === 'Другое' && (
            <button
              style={S.btnPrimary(!customNiche.trim() || loading)}
              disabled={!customNiche.trim() || loading}
              onClick={() => doRegister(customNiche.trim())}
            >
              {loading ? 'Сохраняем...' : 'Продолжить'}
            </button>
          )}

          {loading && selectedNiche !== 'Другое' && (
            <div style={{ textAlign: 'center', color: 'var(--tg-hint)', fontSize: 14, marginTop: 8 }}>
              Сохраняем...
            </div>
          )}
        </>
      )}

      {/* ── Step 3: First Client ───────────────────────── */}
      {step === 3 && (
        <>
          <div style={S.h1}>Добавим первого клиента?</div>
          <div style={S.sub}>Увидишь как придёт напоминание — это главная фишка</div>

          {[
            { label: 'Имя клиента', type: 'text', value: clientName, set: setClientName, placeholder: 'Например: Мария' },
            { label: 'Телефон', type: 'tel', value: clientPhone, set: setClientPhone, placeholder: '+7 999 123 45 67' },
          ].map(({ label, type, value, set, placeholder }) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <label style={S.label}>{label}</label>
              <input style={S.input} type={type} placeholder={placeholder} value={value} onChange={(e) => set(e.target.value)} />
            </div>
          ))}

          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <div style={{ flex: 1 }}>
              <label style={S.label}>Дата записи</label>
              <input style={S.input} type="date" value={clientDate} onChange={(e) => setClientDate(e.target.value)} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={S.label}>Время</label>
              <input style={S.input} type="time" value={clientTime} onChange={(e) => setClientTime(e.target.value)} />
            </div>
          </div>

          {error && <div style={S.error}>{error}</div>}

          <button
            style={S.btnPrimary(!step3Ready || loading)}
            disabled={!step3Ready || loading}
            onClick={handleAddClient}
          >
            {loading ? 'Сохраняем...' : 'Добавить и продолжить'}
          </button>
          <button style={S.btnSecondary} disabled={loading} onClick={handleSkipClient}>
            Пропустить
          </button>
        </>
      )}

      {/* ── Step 4: Final ─────────────────────────────── */}
      {step === 4 && (
        <>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ fontSize: 64, animation: 'popIn 0.4s cubic-bezier(0.175,0.885,0.32,1.275)' }}>✅</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--tg-text)', marginTop: 16 }}>
              Всё готово, {name}!
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginTop: 8 }}>
              {clientAdded
                ? 'Напоминание отправится клиенту автоматически — можешь проверить'
                : 'Добавь первого клиента — это займёт 30 секунд'}
            </div>
          </div>

          {!WebApp?.MainButton && (
            <button style={S.btnPrimary(false)} onClick={onRegistered}>
              Начать работу
            </button>
          )}
        </>
      )}

      <style>{`
        @keyframes popIn {
          0% { transform: scale(0); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
```

**Step 2: Проверить сборку**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build
```

Ожидание: завершается без ошибок.

**Step 3: Commit**

```bash
git add miniapp/src/master/pages/MasterOnboarding.jsx
git commit -m "feat(miniapp): rewrite onboarding — name→niche chips→first client→final"
```

---

### Task 7: Финальная проверка по критериям

**Step 1: Проверить бот локально**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -m src.master_bot
```

Проверить вручную в Telegram:
- `/start` → баннер + кнопка «Открыть приложение →»
- `/start` повторно → то же самое
- Кнопка «🏠 Домой» → **не должна появляться**
- Произвольный текст → бот не реагирует

**Step 2: Проверить API**

```bash
# Проверить, что сервер запускается
python -m uvicorn src.api.app:app --port 8081
```

**Step 3: Проверить сборку Mini App**

```bash
cd miniapp && npm run build
```

Ожидание: `✓ built in X.XXs`

**Step 4: Финальный commit**

```bash
git add -A
git commit -m "chore: final verification — bot entry-point + onboarding redesign complete"
```

---

## Checklist критериев (из дизайн-дока)

- [ ] `/start` → баннер + кнопка (одинаково для всех)
- [ ] `/start` повторно — не ломается
- [ ] Кнопка «Домой» не появляется
- [ ] FSM регистрации не запускается
- [ ] Онбординг: имя → ниша → автопереход 300ms → шаг 3 → финал
- [ ] «Другое» → поле ввода → кнопка «Продолжить»
- [ ] Клиент + заказ создаются без услуг (amount=0)
- [ ] `onboarding_skipped_first_client` сохраняется в БД
- [ ] `npm run build` без ошибок
