# Mini App React Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Создать React + Vite SPA в папке `miniapp/` — клиентский интерфейс Telegram Mini App с 4 экранами и полной интеграцией Telegram WebApp API.

**Architecture:** useState-навигация в App.jsx (без react-router), React Query для data fetching, Telegram CSS-переменные для темы. Dev bypass в FastAPI: если `APP_ENV=development` и `X-Init-Data: "dev"` — возвращать тестового клиента без HMAC.

**Tech Stack:** React 18, Vite, @twa-dev/sdk, @tanstack/react-query, axios, FastAPI (бэкенд уже готов на порту 8081)

---

## Task 1: Backend dev bypass

**Files:**
- Modify: `src/config.py`
- Modify: `src/api/dependencies.py`
- Modify: `.env.example`

**Step 1: Добавить APP_ENV в config.py**

В конец файла `src/config.py` добавить:
```python
# Environment (development / production)
APP_ENV: str = os.getenv("APP_ENV", "production")
```

**Step 2: Добавить dev bypass в dependencies.py**

Заменить содержимое `src/api/dependencies.py`:
```python
"""FastAPI dependencies for Mini App API."""

from fastapi import Header, HTTPException

from src.database import (
    get_client_by_tg_id,
    get_master_client_by_client_tg_id,
    get_master_by_id,
    get_masters,
)
from src.api.auth import validate_init_data, extract_tg_id
from src.config import CLIENT_BOT_TOKEN, APP_ENV
from src.models import Client, Master, MasterClient


async def _get_dev_client() -> tuple[Client, Master, MasterClient]:
    """Return first client in DB for development testing."""
    masters = await get_masters()
    if not masters:
        raise HTTPException(status_code=404, detail="No masters in DB for dev mode")
    master = masters[0]

    # Get first client linked to this master
    # Use master_id=1, tg_id=0 hack: just grab any client
    # Actually we need to find any client. Let's use a known approach:
    # get_master_client_by_client_tg_id needs tg_id — but in dev we pick master's own tg_id
    # Simplest: use master as a fake client proxy
    fake_client = Client(
        id=0,
        tg_id=master.tg_id,
        name="Dev User",
        phone="+79991234567",
        birthday=None,
    )
    fake_master_client = MasterClient(
        id=0,
        master_id=master.id,
        client_id=0,
        bonus_balance=450,
        notifications_enabled=True,
        notes=None,
    )
    return fake_client, master, fake_master_client


async def get_current_client(
    x_init_data: str = Header(..., alias="X-Init-Data")
) -> tuple[Client, Master, MasterClient]:
    """
    Dependency - validate initData and return (client, master, master_client).
    In development mode with X-Init-Data: "dev" — returns first DB client without HMAC check.
    Raises 401 if invalid, 404 if client not found in DB.
    """
    # Dev bypass
    if APP_ENV == "development" and x_init_data == "dev":
        return await _get_dev_client()

    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")

    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")

    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")

    master_client = await get_master_client_by_client_tg_id(tg_id)
    if not master_client:
        raise HTTPException(status_code=404, detail="Master not linked")

    master = await get_master_by_id(master_client.master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    return client, master, master_client
```

**Step 3: Проверить что get_masters существует в database.py**

```bash
grep -n "def get_masters" src/database.py
```

Если не существует — добавить в `src/database.py`:
```python
async def get_masters() -> list[dict]:
    """Get all masters."""
    async with get_connection() as db:
        async with db.execute("SELECT * FROM masters LIMIT 10") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return []
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
```

И в зависимостях исправить импорт — `get_masters` возвращает `list[dict]`, поэтому `_get_dev_client` нужно адаптировать:
```python
async def _get_dev_client() -> tuple[Client, Master, MasterClient]:
    """Return first master's data for development testing."""
    masters = await get_masters()
    if not masters:
        raise HTTPException(status_code=404, detail="No masters in DB for dev mode")
    m = masters[0]
    master = Master(**{k: m[k] for k in Master.__dataclass_fields__ if k in m})
    fake_client = Client(
        id=0,
        tg_id=master.tg_id,
        name="Dev User",
        phone="+79991234567",
        birthday=None,
    )
    fake_master_client = MasterClient(
        id=0,
        master_id=master.id,
        client_id=0,
        bonus_balance=450,
        notifications_enabled=True,
        notes=None,
    )
    return fake_client, master, fake_master_client
```

**Step 4: Добавить APP_ENV в .env.example**

```
# Environment (development / production)
APP_ENV=production
```

**Step 5: Проверить быстро**

```bash
curl -s http://localhost:8081/health
# Ожидаем: {"status":"ok"}
# Если сервер не запущен локально — пропустить, проверим после Task 2
```

**Step 6: Commit**

```bash
git add src/config.py src/api/dependencies.py .env.example
git commit -m "feat: add dev bypass for Mini App API (APP_ENV=development)"
```

---

## Task 2: Инициализация Vite-проекта

**Files:**
- Create: `miniapp/` (весь проект)

**Step 1: Инициализировать проект**

```bash
cd /путь/к/miniapp
npm create vite@latest . -- --template react
# Ответить yes если спросит overwrite
```

**Step 2: Установить зависимости**

```bash
npm install
npm install @twa-dev/sdk @tanstack/react-query axios
```

**Step 3: Убедиться что dev запускается**

```bash
npm run dev
# Должен запустить на http://localhost:5173
# Ctrl+C после проверки
```

**Step 4: Удалить дефолтный мусор Vite**

```bash
rm -f src/App.css src/index.css
# Файлы src/assets/ можно оставить или удалить
```

**Step 5: Commit**

```bash
cd .. && git add miniapp/ && git commit -m "feat: init vite react project for Mini App"
```

---

## Task 3: Конфигурация проекта

**Files:**
- Modify: `miniapp/vite.config.js`
- Create: `miniapp/.env.development`
- Create: `miniapp/.env.production`
- Create: `miniapp/src/theme.css`

**Step 1: Написать vite.config.js**

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8081'
    }
  },
  build: {
    outDir: 'dist',
  }
});
```

**Step 2: Создать .env.development**

```
VITE_API_URL=http://localhost:8081
```

**Step 3: Создать .env.production**

```
VITE_API_URL=https://api.crmfit.ru
```

**Step 4: Создать src/theme.css**

```css
:root {
  --tg-bg: var(--tg-theme-bg-color, #0f1923);
  --tg-surface: var(--tg-theme-secondary-bg-color, #162030);
  --tg-text: var(--tg-theme-text-color, #ffffff);
  --tg-hint: var(--tg-theme-hint-color, #8b9bb4);
  --tg-link: var(--tg-theme-link-color, #4f9cf9);
  --tg-button: var(--tg-theme-button-color, #4f9cf9);
  --tg-button-text: var(--tg-theme-button-text-color, #ffffff);
  --tg-accent: var(--tg-theme-accent-text-color, #4f9cf9);

  --radius-card: 16px;
  --radius-btn: 12px;
  --gap: 12px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
}

body {
  background: var(--tg-bg);
  color: var(--tg-text);
  font-family: -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif;
  font-size: 16px;
  line-height: 1.5;
  overflow-x: hidden;
  padding-bottom: 80px;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

**Step 5: Commit**

```bash
git add miniapp/ && git commit -m "feat: configure vite, env files, telegram theme css"
```

---

## Task 4: API клиент

**Files:**
- Create: `miniapp/src/api/client.js`

**Step 1: Создать src/api/client.js**

```javascript
import axios from 'axios';
import WebApp from '@twa-dev/sdk';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  // Dev bypass: в режиме разработки отправляем "dev" вместо реального initData
  config.headers['X-Init-Data'] = import.meta.env.DEV ? 'dev' : WebApp.initData;
  return config;
});

export const getMe = () => api.get('/api/me').then(r => r.data);
export const getOrders = () => api.get('/api/orders').then(r => r.data);
export const getBonuses = () => api.get('/api/bonuses').then(r => r.data);
export const getPromos = () => api.get('/api/promos').then(r => r.data);
export const getServices = () => api.get('/api/services').then(r => r.data);
export const createOrderRequest = (data) =>
  api.post('/api/orders/request', data).then(r => r.data);
```

**Step 2: Commit**

```bash
git add miniapp/src/api/ && git commit -m "feat: add api client with dev bypass"
```

---

## Task 5: Компонент Skeleton

**Files:**
- Create: `miniapp/src/components/Skeleton.jsx`

**Step 1: Создать Skeleton.jsx**

```jsx
export const Skeleton = ({ width = '100%', height = 16, radius = 8, style = {} }) => (
  <div style={{
    width,
    height,
    borderRadius: radius,
    background: 'var(--tg-surface)',
    animation: 'skeleton-pulse 1.5s ease-in-out infinite',
    ...style
  }} />
);
```

**Step 2: Commit**

```bash
git add miniapp/src/components/Skeleton.jsx && git commit -m "feat: add Skeleton component"
```

---

## Task 6: Компонент ErrorScreen

**Files:**
- Create: `miniapp/src/components/ErrorScreen.jsx`

**Step 1: Создать ErrorScreen.jsx**

```jsx
export default function ErrorScreen({ message, onRetry }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 24px' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <p style={{ color: 'var(--tg-text)', marginBottom: 8 }}>Что-то пошло не так</p>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 24 }}>{message}</p>
      <button
        onClick={onRetry}
        style={{
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 'var(--radius-btn)',
          padding: '12px 24px',
          fontSize: 16,
          cursor: 'pointer'
        }}
      >
        Попробовать снова
      </button>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/components/ErrorScreen.jsx && git commit -m "feat: add ErrorScreen component"
```

---

## Task 7: Компонент BottomNav

**Files:**
- Create: `miniapp/src/components/BottomNav.jsx`

**Step 1: Создать BottomNav.jsx**

```jsx
import WebApp from '@twa-dev/sdk';

const HomeIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const CalendarIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

const StarIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
  </svg>
);

const GiftIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 12 20 22 4 22 4 12"/>
    <rect x="2" y="7" width="20" height="5"/>
    <line x1="12" y1="22" x2="12" y2="7"/>
    <path d="M12 7H7.5a2.5 2.5 0 010-5C11 2 12 7 12 7z"/>
    <path d="M12 7h4.5a2.5 2.5 0 000-5C13 2 12 7 12 7z"/>
  </svg>
);

const tabs = [
  { id: 'home', label: 'Главная', Icon: HomeIcon },
  { id: 'booking', label: 'Запись', Icon: CalendarIcon },
  { id: 'bonuses', label: 'Бонусы', Icon: StarIcon },
  { id: 'promos', label: 'Акции', Icon: GiftIcon },
];

export default function BottomNav({ active, onNavigate }) {
  const handleTab = (id) => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate(id);
  };

  return (
    <nav style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      background: 'var(--tg-surface)',
      borderTop: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      zIndex: 100,
      paddingBottom: 'env(safe-area-inset-bottom)',
    }}>
      {tabs.map(({ id, label, Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => handleTab(id)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
              padding: '10px 0',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: isActive ? 'var(--tg-accent)' : 'var(--tg-hint)',
              fontSize: 11,
              transition: 'color 0.15s',
            }}
          >
            <Icon />
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/components/BottomNav.jsx && git commit -m "feat: add BottomNav with inline SVG icons"
```

---

## Task 8: main.jsx и App.jsx

**Files:**
- Modify: `miniapp/src/main.jsx`
- Modify: `miniapp/src/App.jsx`

**Step 1: Написать main.jsx**

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import WebApp from '@twa-dev/sdk';
import App from './App';
import './theme.css';

// Инициализация Telegram WebApp
if (typeof WebApp?.ready === 'function') {
  WebApp.ready();
}
if (typeof WebApp?.expand === 'function') {
  WebApp.expand();
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30000 }
  }
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
```

**Step 2: Написать App.jsx**

```jsx
import { useState, useEffect } from 'react';
import WebApp from '@twa-dev/sdk';
import Home from './pages/Home';
import Booking from './pages/Booking';
import Bonuses from './pages/Bonuses';
import Promos from './pages/Promos';
import BottomNav from './components/BottomNav';

const pages = { home: Home, booking: Booking, bonuses: Bonuses, promos: Promos };

export default function App() {
  const [page, setPage] = useState('home');

  // Telegram BackButton — показывать на всех страницах кроме home
  useEffect(() => {
    if (!WebApp?.BackButton) return;
    if (page === 'home') {
      WebApp.BackButton.hide();
    } else {
      WebApp.BackButton.show();
      const handler = () => setPage('home');
      WebApp.BackButton.onClick(handler);
      return () => WebApp.BackButton.offClick(handler);
    }
  }, [page]);

  const Page = pages[page];

  return (
    <div>
      <Page onNavigate={setPage} />
      <BottomNav active={page} onNavigate={setPage} />
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add miniapp/src/main.jsx miniapp/src/App.jsx && git commit -m "feat: add main entry and app routing with BackButton"
```

---

## Task 9: Home страница

**Files:**
- Create: `miniapp/src/pages/Home.jsx`

**Step 1: Хелпер для даты "через N дней"**

В начале файла Home.jsx определить хелпер:

```javascript
function relativeDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date - now;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Сегодня';
  if (diffDays === 1) return 'Завтра';
  if (diffDays > 1) return `Через ${diffDays} дн.`;
  return '';
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('ru-RU', {
    day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit'
  });
}

const BONUS_ICONS = {
  accrual: { icon: '+', color: '#4caf50' },
  spend:   { icon: '−', color: '#f44336' },
  birthday:{ icon: '★', color: '#ffd700' },
  manual:  { icon: '✎', color: '#2196f3' },
  promo:   { icon: '◆', color: '#9c27b0' },
};
```

**Step 2: Написать Home.jsx**

```jsx
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMe, getOrders, getBonuses } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

// ... (хелперы из Step 1 выше)

export default function Home({ onNavigate }) {
  const qc = useQueryClient();
  const { data: me, isLoading: meLoading, error: meError, refetch: refetchMe } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const { data: orders = [], isLoading: ordersLoading } = useQuery({ queryKey: ['orders'], queryFn: getOrders });
  const { data: bonuses, isLoading: bonusesLoading } = useQuery({ queryKey: ['bonuses'], queryFn: getBonuses });

  if (meError) return <ErrorScreen message={meError.message} onRetry={refetchMe} />;

  // Ближайшая запись
  const now = new Date();
  const upcoming = orders
    .filter(o => (o.status === 'new' || o.status === 'confirmed') && new Date(o.scheduled_at) > now)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];

  // Последние 3 бонусных операции
  const recentBonuses = bonuses?.log?.slice(0, 3) || [];

  // Инициалы
  const initials = me?.name
    ? me.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  return (
    <div style={{ padding: '16px 16px 0' }}>
      {/* Шапка */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Добро пожаловать</p>
          {meLoading
            ? <Skeleton width={140} height={22} style={{ marginTop: 4 }} />
            : <h2 style={{ fontSize: 20, fontWeight: 700 }}>{me?.name || '—'}</h2>
          }
        </div>
        {/* Кнопка обновления + аватар */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => qc.invalidateQueries()}
            style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
            title="Обновить"
          >↻</button>
          <div style={{
            width: 42, height: 42, borderRadius: '50%',
            background: 'var(--tg-button)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--tg-button-text)', fontWeight: 700, fontSize: 16
          }}>
            {initials}
          </div>
        </div>
      </div>

      {/* Карточка баланса */}
      <div style={{
        background: 'var(--tg-surface)',
        borderRadius: 20,
        padding: '20px',
        marginBottom: 16,
      }}>
        <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 4 }}>Бонусный баланс</p>
        {bonusesLoading
          ? <Skeleton width={100} height={36} style={{ marginBottom: 8 }} />
          : <p style={{ fontSize: 36, fontWeight: 800, color: 'var(--tg-accent)', lineHeight: 1.1 }}>
              {bonuses?.balance ?? 0} ₽
            </p>
        }
        {meLoading
          ? <Skeleton width={160} height={16} style={{ marginTop: 8 }} />
          : <>
              <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginTop: 8 }}>
                Мастер: {me?.master_name || '—'}
              </p>
              {me?.master_specialty && (
                <span style={{
                  display: 'inline-block', marginTop: 6,
                  background: 'rgba(79,156,249,0.15)', color: 'var(--tg-accent)',
                  borderRadius: 20, padding: '2px 10px', fontSize: 12
                }}>
                  {me.master_specialty}
                </span>
              )}
            </>
        }
      </div>

      {/* Ближайшая запись */}
      {ordersLoading
        ? <Skeleton height={80} radius={16} style={{ marginBottom: 16 }} />
        : upcoming && (
          <div style={{
            background: 'var(--tg-surface)',
            borderRadius: 16, padding: '16px',
            marginBottom: 16,
            borderLeft: '3px solid var(--tg-accent)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 13, color: 'var(--tg-accent)' }}>
                📅 {formatDate(upcoming.scheduled_at)}
              </span>
              <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
                {relativeDate(upcoming.scheduled_at)}
              </span>
            </div>
            <p style={{ fontWeight: 600 }}>{upcoming.services || 'Услуга не указана'}</p>
            {upcoming.address && (
              <p style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 2 }}>{upcoming.address}</p>
            )}
          </div>
        )
      }

      {/* Последние бонусные операции */}
      {recentBonuses.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 10 }}>Последние операции</p>
          {recentBonuses.map((op, i) => {
            const { icon, color } = BONUS_ICONS[op.type] || { icon: '•', color: 'var(--tg-hint)' };
            const sign = op.amount > 0 ? '+' : '';
            return (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0',
                borderBottom: i < recentBonuses.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ color, fontSize: 18, width: 20, textAlign: 'center' }}>{icon}</span>
                  <span style={{ fontSize: 14 }}>{op.description || op.type}</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color, fontWeight: 600 }}>{sign}{op.amount} ₽</span>
                  <p style={{ fontSize: 12, color: 'var(--tg-hint)' }}>
                    {op.created_at ? new Date(op.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' }) : ''}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

**Step 3: Проверить что /api/me возвращает master_name**

```bash
curl -s -H "X-Init-Data: dev" http://localhost:8081/api/me
```

Если в ответе нет `master_name` — проверить `src/api/routers/client.py` и добавить поля мастера в ответ.

**Step 4: Commit**

```bash
git add miniapp/src/pages/Home.jsx && git commit -m "feat: add Home page with balance, upcoming order, bonus log"
```

---

## Task 10: Booking страница

**Files:**
- Create: `miniapp/src/pages/Booking.jsx`

**Step 1: Написать Booking.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import WebApp from '@twa-dev/sdk';
import { getServices, createOrderRequest } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

export default function Booking({ onNavigate }) {
  const [selectedService, setSelectedService] = useState(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [validationError, setValidationError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: services = [], isLoading, error, refetch } = useQuery({
    queryKey: ['services'],
    queryFn: getServices
  });

  // MainButton управление
  useEffect(() => {
    if (!WebApp?.MainButton) return;
    if (submitted) {
      WebApp.MainButton.hide();
      return;
    }
    WebApp.MainButton.setText('Отправить заявку');
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleSubmit);
    return () => {
      WebApp.MainButton.offClick(handleSubmit);
      WebApp.MainButton.hide();
    };
  }, [selectedService, comment, submitted]);

  async function handleSubmit() {
    if (!selectedService) {
      setValidationError(true);
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('error');
      }
      return;
    }
    setIsSubmitting(true);
    try {
      await createOrderRequest({ service_name: selectedService.name, comment });
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
      setSubmitted(true);
    } catch (e) {
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('error');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (error) return <ErrorScreen message={error.message} onRetry={refetch} />;

  // Экран успеха
  if (submitted) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 24px' }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>✓</div>
        <h2 style={{ marginBottom: 12 }}>Заявка отправлена!</h2>
        <p style={{ color: 'var(--tg-hint)', marginBottom: 32 }}>
          Мастер свяжется с вами в ближайшее время.
        </p>
        <button
          onClick={() => onNavigate('home')}
          style={{
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 'var(--radius-btn)',
            padding: '14px 32px',
            fontSize: 16,
            cursor: 'pointer',
          }}
        >
          На главную
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px 16px 0' }}>
      <h2 style={{ marginBottom: 20 }}>Запись к мастеру</h2>

      {/* Сетка услуг */}
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gap)', marginBottom: 20 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} height={80} radius={16} />)}
        </div>
      ) : (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: 'var(--gap)', marginBottom: 20,
          border: validationError && !selectedService ? '1px solid #f44336' : 'none',
          borderRadius: 16, padding: validationError && !selectedService ? 8 : 0,
        }}>
          {services.map(service => {
            const isSelected = selectedService?.id === service.id;
            return (
              <button
                key={service.id}
                onClick={() => {
                  setSelectedService(service);
                  setValidationError(false);
                  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
                    WebApp.HapticFeedback.impactOccurred('light');
                  }
                }}
                style={{
                  background: 'var(--tg-surface)',
                  border: isSelected ? '2px solid var(--tg-accent)' : '2px solid transparent',
                  borderRadius: 16,
                  padding: '16px 12px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  color: 'var(--tg-text)',
                }}
              >
                <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{service.name}</p>
                {service.price && (
                  <p style={{ color: 'var(--tg-accent)', fontSize: 13 }}>{service.price} ₽</p>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Комментарий */}
      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Адрес, пожелания..."
        rows={3}
        style={{
          width: '100%',
          background: 'var(--tg-surface)',
          border: 'none',
          borderRadius: 'var(--radius-card)',
          padding: '12px 16px',
          color: 'var(--tg-text)',
          fontSize: 15,
          resize: 'none',
          fontFamily: 'inherit',
          outline: 'none',
        }}
      />

      {/* Кнопка-запасной вариант если MainButton недоступен */}
      {!WebApp?.MainButton && (
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          style={{
            marginTop: 16,
            width: '100%',
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 'var(--radius-btn)',
            padding: '14px',
            fontSize: 16,
            cursor: 'pointer',
          }}
        >
          {isSubmitting ? 'Отправка...' : 'Отправить заявку'}
        </button>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/pages/Booking.jsx && git commit -m "feat: add Booking page with service selection and order request"
```

---

## Task 11: Bonuses страница

**Files:**
- Create: `miniapp/src/pages/Bonuses.jsx`

**Step 1: Написать Bonuses.jsx**

```jsx
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getBonuses, getOrders } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

const BONUS_ICONS = {
  accrual:  { icon: '+', color: '#4caf50' },
  spend:    { icon: '−', color: '#f44336' },
  birthday: { icon: '★', color: '#ffd700' },
  manual:   { icon: '✎', color: '#2196f3' },
  promo:    { icon: '◆', color: '#9c27b0' },
};

const STATUS_ICONS = {
  done:      { icon: '✅', color: '#4caf50' },
  cancelled: { icon: '❌', color: '#f44336' },
  new:       { icon: '📅', color: '#2196f3' },
  confirmed: { icon: '📅', color: '#2196f3' },
};

export default function Bonuses({ onNavigate }) {
  const [tab, setTab] = useState('bonuses');
  const qc = useQueryClient();

  const { data: bonuses, isLoading: bLoading, error: bError, refetch: refetchB } = useQuery({ queryKey: ['bonuses'], queryFn: getBonuses });
  const { data: orders = [], isLoading: oLoading, error: oError, refetch: refetchO } = useQuery({ queryKey: ['orders'], queryFn: getOrders });

  if (bError) return <ErrorScreen message={bError.message} onRetry={refetchB} />;
  if (oError) return <ErrorScreen message={oError.message} onRetry={refetchO} />;

  const log = bonuses?.log || [];

  return (
    <div style={{ padding: '16px 16px 0' }}>
      {/* Заголовок с кнопкой обновления */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Бонусы</h2>
        <button
          onClick={() => qc.invalidateQueries()}
          style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
        >↻</button>
      </div>

      {/* Переключатель вкладок */}
      <div style={{
        display: 'flex', background: 'var(--tg-surface)',
        borderRadius: 12, padding: 3, marginBottom: 20
      }}>
        {[['bonuses', 'Бонусы'], ['history', 'История']].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              flex: 1, padding: '9px', border: 'none', borderRadius: 10,
              background: tab === id ? 'var(--tg-button)' : 'transparent',
              color: tab === id ? 'var(--tg-button-text)' : 'var(--tg-hint)',
              cursor: 'pointer', fontSize: 14, fontWeight: tab === id ? 600 : 400,
              transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Вкладка Бонусы */}
      {tab === 'bonuses' && (
        <>
          {/* Карточка баланса */}
          <div style={{
            background: 'var(--tg-surface)',
            borderRadius: 20, padding: '20px', marginBottom: 20,
            textAlign: 'center'
          }}>
            <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 4 }}>Баланс</p>
            {bLoading
              ? <Skeleton width={120} height={44} style={{ margin: '0 auto' }} />
              : <p style={{ fontSize: 44, fontWeight: 800, color: 'var(--tg-accent)' }}>
                  {bonuses?.balance ?? 0} ₽
                </p>
            }
          </div>

          {/* Лог операций */}
          {bLoading
            ? [...Array(3)].map((_, i) => <Skeleton key={i} height={50} style={{ marginBottom: 8 }} />)
            : log.length === 0
              ? <p style={{ color: 'var(--tg-hint)', textAlign: 'center', padding: '24px 0' }}>Операций нет</p>
              : log.map((op, i) => {
                  const { icon, color } = BONUS_ICONS[op.type] || { icon: '•', color: 'var(--tg-hint)' };
                  const sign = op.amount > 0 ? '+' : '';
                  return (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 0',
                      borderBottom: i < log.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{
                          color, fontSize: 20, width: 28, height: 28,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          background: color + '20', borderRadius: '50%'
                        }}>{icon}</span>
                        <div>
                          <p style={{ fontSize: 14 }}>{op.description || op.type}</p>
                          <p style={{ fontSize: 12, color: 'var(--tg-hint)' }}>
                            {op.created_at ? new Date(op.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' }) : ''}
                          </p>
                        </div>
                      </div>
                      <span style={{ color, fontWeight: 700 }}>{sign}{op.amount} ₽</span>
                    </div>
                  );
                })
          }
        </>
      )}

      {/* Вкладка История заказов */}
      {tab === 'history' && (
        <>
          {oLoading
            ? [...Array(3)].map((_, i) => <Skeleton key={i} height={60} style={{ marginBottom: 8 }} />)
            : orders.length === 0
              ? <p style={{ color: 'var(--tg-hint)', textAlign: 'center', padding: '24px 0' }}>Заказов нет</p>
              : orders.map((order, i) => {
                  const { icon } = STATUS_ICONS[order.status] || { icon: '•' };
                  return (
                    <div key={order.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 0',
                      borderBottom: i < orders.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none'
                    }}>
                      <div>
                        <p style={{ fontSize: 14, fontWeight: 500 }}>
                          {order.scheduled_at
                            ? new Date(order.scheduled_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
                            : '—'}
                          {'  '}{order.services || 'Услуга'}
                        </p>
                        <p style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
                          {order.amount_total ? `${order.amount_total} ₽` : ''}
                        </p>
                      </div>
                      <span style={{ fontSize: 18 }}>{icon}</span>
                    </div>
                  );
                })
          }
        </>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/pages/Bonuses.jsx && git commit -m "feat: add Bonuses page with log and order history tabs"
```

---

## Task 12: Promos страница

**Files:**
- Create: `miniapp/src/pages/Promos.jsx`

**Step 1: Написать Promos.jsx**

```jsx
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getPromos } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

function formatActiveTo(dateStr) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

export default function Promos({ onNavigate }) {
  const qc = useQueryClient();
  const { data: promos = [], isLoading, error, refetch } = useQuery({ queryKey: ['promos'], queryFn: getPromos });

  if (error) return <ErrorScreen message={error.message} onRetry={refetch} />;

  return (
    <div style={{ padding: '16px 16px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Акции</h2>
        <button
          onClick={() => qc.invalidateQueries()}
          style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
        >↻</button>
      </div>

      {isLoading ? (
        [...Array(2)].map((_, i) => <Skeleton key={i} height={120} radius={16} style={{ marginBottom: 12 }} />)
      ) : promos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🎁</div>
          <p style={{ fontWeight: 600, marginBottom: 8 }}>Акций пока нет.</p>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Следите за обновлениями!</p>
        </div>
      ) : (
        promos.map(promo => (
          <div key={promo.id} style={{
            background: 'var(--tg-surface)',
            borderRadius: 16, padding: '16px',
            marginBottom: 12,
          }}>
            <h3 style={{ marginBottom: 8 }}>{promo.title}</h3>
            {promo.text && (
              <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 8 }}>{promo.text}</p>
            )}
            {promo.active_to && (
              <p style={{ fontSize: 12, color: 'var(--tg-accent)' }}>
                До {formatActiveTo(promo.active_to)}
              </p>
            )}
          </div>
        ))
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/pages/Promos.jsx && git commit -m "feat: add Promos page with empty state"
```

---

## Task 13: Финальная проверка

**Files:** нет изменений

**Step 1: Проверить что /api/me возвращает нужные поля**

```bash
curl -s -H "X-Init-Data: dev" http://localhost:8081/api/me | python3 -m json.tool
```

Ожидаемый формат:
```json
{
  "name": "...",
  "phone": "...",
  "bonus_balance": 0,
  "master_name": "...",
  "master_specialty": "..."
}
```

Если поля `master_name` / `master_specialty` отсутствуют — добавить их в `src/api/routers/client.py`.

**Step 2: npm run dev — проверить все страницы**

```bash
cd miniapp && npm run dev
```

Открыть http://localhost:5173 и проверить:
- [ ] Home загружается, skeleton виден при старте
- [ ] Booking: услуги отображаются карточками
- [ ] Bonuses: обе вкладки переключаются
- [ ] Promos: пустой стейт или карточки

**Step 3: npm run build — собрать без ошибок**

```bash
npm run build
# Ожидаем: vite vX.X.X building for production...
# dist/ index.html + assets/
```

**Step 4: Commit финальный**

```bash
git add -A && git commit -m "feat: Mini App React frontend complete"
```

---

## Контрольный список критериев

| # | Критерий | Команда проверки |
|---|---|---|
| 1 | `npm run dev` без ошибок | `npm run dev` |
| 2 | `npm run build` → `dist/` | `npm run build` |
| 3 | Home: имя, баланс, мастер | Открыть в браузере |
| 4 | Ближайшая запись если есть | Проверить в браузере |
| 5 | Последние 3 бонуса на Home | Проверить в браузере |
| 6 | Booking: услуги карточками | Проверить в браузере |
| 7 | Booking: POST request работает | Dev tools → Network |
| 8 | Bonuses: 2 вкладки | Проверить в браузере |
| 9 | Promos: empty state | Проверить в браузере |
| 10 | Skeleton на загрузке | Отключить сеть → обновить |
| 11 | Тема от CSS переменных | Работает без Telegram тоже |
