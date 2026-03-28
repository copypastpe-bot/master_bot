# Reports Screen Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить экран аналитики с KPI-карточками, линейным графиком выручки и топом услуг; сделать StatCard на Dashboard кликабельными для навигации к отчётам.

**Architecture:** Новый FastAPI роутер `/api/master/reports` возвращает KPI + chart_data (выручка по дням). Фронтенд — `Reports.jsx` с recharts LineChart; навигация к нему — через клик по StatCard на Dashboard (period=week/month), без изменения MoreMenu.

**Tech Stack:** Python/FastAPI + aiosqlite (бэкенд), React + recharts + @tanstack/react-query (фронтенд), Telegram Mini App CSS vars.

---

### Task 1: `get_daily_revenue()` в database.py

**Files:**
- Modify: `src/database.py` — после функции `get_reports()`

**Step 1: Написать функцию**

Добавить после блока `get_reports()` (около строки 1350):

```python
async def get_daily_revenue(
    master_id: int, date_from: date, date_to: date
) -> list[dict]:
    """Get revenue by day for chart. Fills missing days with 0."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT date(done_at) as day, COALESCE(SUM(amount_total), 0) as revenue
            FROM orders
            WHERE master_id = ?
              AND status = 'done'
              AND date(done_at) >= ?
              AND date(done_at) <= ?
            GROUP BY date(done_at)
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()

    # Index results by date string
    by_day = {row["day"]: row["revenue"] for row in rows}

    # Fill every day in range (including zeros)
    result = []
    current = date_from
    while current <= date_to:
        day_str = current.isoformat()
        result.append({"date": day_str, "revenue": by_day.get(day_str, 0)})
        current += timedelta(days=1)

    return result
```

Убедиться что `timedelta` уже импортирован вверху файла (вместе с `date`).

**Step 2: Ручная проверка импорта**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "from src.database import get_daily_revenue; print('OK')"
```
Ожидание: `OK`

**Step 3: Commit**

```bash
git add src/database.py
git commit -m "feat(db): add get_daily_revenue for chart data"
```

---

### Task 2: Роутер `src/api/routers/master/reports.py`

**Files:**
- Create: `src/api/routers/master/reports.py`

**Step 1: Создать файл**

```python
"""Master reports endpoint."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from src.api.dependencies import get_current_master
from src.database import get_reports, get_daily_revenue
from src.models import Master

router = APIRouter(tags=["master"])

MONTH_NAMES = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def _resolve_period(
    period: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
) -> tuple[date, date, str]:
    """Return (date_from, date_to, label). Raises HTTPException on bad input."""
    today = date.today()

    if date_from and date_to:
        if date_to < date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        if (date_to - date_from).days > 365:
            raise HTTPException(400, "Period cannot exceed 365 days")
        label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
        return date_from, date_to, label

    if period == "today":
        return today, today, "Сегодня"
    if period == "week":
        date_from = today - timedelta(days=today.weekday())  # Monday
        return date_from, today, "Эта неделя"
    # default: month
    date_from = today.replace(day=1)
    label = f"{MONTH_NAMES[today.month]} {today.year}"
    return date_from, today, label


@router.get("/master/reports")
async def get_master_reports(
    period: Optional[str] = Query(None, regex="^(today|week|month)$"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    master: Master = Depends(get_current_master),
):
    """Get KPI + chart data for a period."""
    d_from, d_to, label = _resolve_period(period, date_from, date_to)

    kpi_raw = await get_reports(master.id, d_from, d_to)
    chart = await get_daily_revenue(master.id, d_from, d_to)

    return {
        "period": {
            "from": d_from.isoformat(),
            "to": d_to.isoformat(),
            "label": label,
        },
        "kpi": {
            "revenue": kpi_raw["revenue"],
            "order_count": kpi_raw["order_count"],
            "new_clients": kpi_raw["new_clients"],
            "repeat_clients": kpi_raw["repeat_clients"],
            "avg_check": kpi_raw["avg_check"],
            "total_clients": kpi_raw["total_clients"],
        },
        "top_services": kpi_raw.get("top_services", [])[:5],
        "chart_data": chart,
    }
```

> ⚠️ Проверить структуру ответа `get_reports()` в `src/database.py` — убедиться, что ключи `revenue`, `order_count`, `new_clients`, `repeat_clients`, `avg_check`, `total_clients` совпадают с тем, что возвращает функция.

**Step 2: Зарегистрировать роутер в `src/api/app.py`**

Добавить в блок импортов (рядом с другими master-роутерами):
```python
from src.api.routers.master import reports as master_reports
```

Добавить в блок `include_router`:
```python
app.include_router(master_reports.router, prefix="/api")
```

**Step 3: Проверка импорта**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "from src.api.app import app; print('OK')"
```
Ожидание: `OK`

**Step 4: Commit**

```bash
git add src/api/routers/master/reports.py src/api/app.py
git commit -m "feat(api): add GET /master/reports endpoint"
```

---

### Task 3: API функция на фронтенде

**Files:**
- Modify: `miniapp/src/api/client.js`

**Step 1: Добавить функцию**

В конец файла `miniapp/src/api/client.js` добавить:

```javascript
// params: { period: 'week'|'month'|'today' } or { date_from: 'YYYY-MM-DD', date_to: 'YYYY-MM-DD' }
export const getMasterReports = (params) =>
  api.get('/api/master/reports', { params }).then(r => r.data);
```

**Step 2: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(api-client): add getMasterReports"
```

---

### Task 4: Установить recharts

**Files:**
- Modify: `miniapp/package.json` (автоматически через npm)

**Step 1: Установить**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm install recharts
```

**Step 2: Проверка**

```bash
grep '"recharts"' package.json
```
Ожидание: строка вида `"recharts": "^2.x.x"`

**Step 3: Commit**

```bash
git add miniapp/package.json miniapp/package-lock.json
git commit -m "chore(deps): add recharts for revenue chart"
```

---

### Task 5: StatCard — поддержка onClick

**Files:**
- Modify: `miniapp/src/master/components/StatCard.jsx`

**Step 1: Обновить компонент**

Текущий `StatCard` не принимает `onClick`. Заменить полностью:

```jsx
export default function StatCard({ icon, value, label, onClick }) {
  const isClickable = typeof onClick === 'function';

  return (
    <div
      onClick={isClickable ? onClick : undefined}
      style={{
        background: 'var(--tg-surface)',
        borderRadius: 'var(--radius-card)',
        padding: '14px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        minWidth: 0,
        cursor: isClickable ? 'pointer' : 'default',
        position: 'relative',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      <div style={{ fontSize: 20, lineHeight: 1 }}>{icon}</div>
      <div style={{
        color: 'var(--tg-text)',
        fontSize: 18,
        fontWeight: 700,
        lineHeight: 1.2,
        marginTop: 4,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {value}
      </div>
      <div style={{
        color: 'var(--tg-hint)',
        fontSize: 11,
        lineHeight: 1.3,
      }}>
        {label}
      </div>
      {isClickable && (
        <span style={{
          position: 'absolute',
          top: 10,
          right: 10,
          color: 'var(--tg-hint)',
          fontSize: 16,
          lineHeight: 1,
        }}>›</span>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/master/components/StatCard.jsx
git commit -m "feat(StatCard): add optional onClick with chevron indicator"
```

---

### Task 6: Dashboard — кликабельные карточки

**Files:**
- Modify: `miniapp/src/master/pages/Dashboard.jsx`

**Step 1: Добавить handlers и onClick**

В функции `Dashboard` (после `handleRequests`) добавить два хэндлера:

```javascript
const handleReportsWeek = () => {
  WebApp?.HapticFeedback?.impactOccurred('light');
  onNavigate('reports', { period: 'week' });
};

const handleReportsMonth = () => {
  WebApp?.HapticFeedback?.impactOccurred('light');
  onNavigate('reports', { period: 'month' });
};

const handleClients = () => {
  WebApp?.HapticFeedback?.impactOccurred('light');
  onNavigate('clients');
};
```

**Step 2: Привязать к StatCard**

В блоке "Stats 2x2 grid" обновить четыре карточки:

```jsx
<StatCard
  icon="💰"
  value={formatCurrency(stats.week_revenue || 0)}
  label="Выручка за неделю"
  onClick={handleReportsWeek}
/>
<StatCard
  icon="📅"
  value={formatCurrency(stats.month_revenue || 0)}
  label="Выручка за месяц"
  onClick={handleReportsMonth}
/>
<StatCard
  icon="✅"
  value={stats.week_orders || 0}
  label="Заказов за неделю"
  // TODO: onClick={() => onNavigate('orders_week')} — список выполненных заказов
/>
<StatCard
  icon="👥"
  value={stats.total_clients || 0}
  label="Всего клиентов"
  onClick={handleClients}
/>
```

**Step 3: Commit**

```bash
git add miniapp/src/master/pages/Dashboard.jsx
git commit -m "feat(dashboard): make stat cards navigate to reports/clients"
```

---

### Task 7: Создать `Reports.jsx`

**Files:**
- Create: `miniapp/src/master/pages/Reports.jsx`

**Step 1: Создать файл**

```jsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer, LineChart, Line,
  XAxis, YAxis, Tooltip, Area, AreaChart,
} from 'recharts';
import { getMasterReports } from '../../api/client';
import { Skeleton } from '../../components/Skeleton';

const WebApp = window.Telegram?.WebApp;

// ─── Formatters ──────────────────────────────────────────────────────────────

const MONTH_SHORT = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];

function formatCurrency(n) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(n) + ' ₽';
}

function formatYAxis(n) {
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'K';
  return n;
}

function formatXAxis(dateStr, totalDays) {
  const d = new Date(dateStr + 'T00:00:00');
  if (totalDays > 30) {
    // Show only weekly ticks
    if (d.getDay() !== 1) return '';
  }
  return `${d.getDate()} ${MONTH_SHORT[d.getMonth()]}`;
}

function formatTooltipDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return `${d.getDate()} ${MONTH_SHORT[d.getMonth()]} ${d.getFullYear()}`;
}

// ─── Period tabs ──────────────────────────────────────────────────────────────

const PERIODS = [
  { key: 'today', label: 'Сегодня' },
  { key: 'week',  label: 'Неделя'  },
  { key: 'month', label: 'Месяц'   },
  { key: 'custom',label: 'Период'  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function KpiCard({ icon, value, label }) {
  return (
    <div style={{
      background: 'var(--tg-surface)',
      borderRadius: 'var(--radius-card)',
      padding: '14px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      <div style={{ fontSize: 18, lineHeight: 1 }}>{icon}</div>
      <div style={{
        color: 'var(--tg-text)',
        fontSize: 18,
        fontWeight: 700,
        lineHeight: 1.2,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        marginTop: 4,
      }}>
        {value}
      </div>
      <div style={{ color: 'var(--tg-hint)', fontSize: 11, lineHeight: 1.3 }}>
        {label}
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--tg-surface)',
      border: '1px solid var(--tg-secondary-bg)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 13,
    }}>
      <div style={{ color: 'var(--tg-hint)', marginBottom: 2 }}>{formatTooltipDate(label)}</div>
      <div style={{ color: 'var(--tg-text)', fontWeight: 600 }}>
        {formatCurrency(payload[0].value)}
      </div>
    </div>
  );
}

function RevenueChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ color: 'var(--tg-hint)', fontSize: 14, textAlign: 'center', padding: '32px 0' }}>
        Нет данных для графика
      </div>
    );
  }

  if (data.length === 1) {
    return (
      <div style={{ color: 'var(--tg-hint)', fontSize: 14, textAlign: 'center', padding: '32px 0' }}>
        График доступен для периода от 2 дней
      </div>
    );
  }

  const totalDays = data.length;
  // Determine tick interval for X axis
  const tickInterval = totalDays > 30 ? 6 : totalDays > 14 ? 2 : 0;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--tg-button)" stopOpacity={0.25} />
            <stop offset="95%" stopColor="var(--tg-button)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tickFormatter={(v) => formatXAxis(v, totalDays)}
          interval={tickInterval}
          tick={{ fontSize: 10, fill: 'var(--tg-hint)' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatYAxis}
          tick={{ fontSize: 10, fill: 'var(--tg-hint)' }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="revenue"
          stroke="var(--tg-button)"
          strokeWidth={2}
          fill="url(#revenueGradient)"
          dot={false}
          activeDot={{ r: 4, fill: 'var(--tg-button)' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function TopServices({ services }) {
  if (!services || services.length === 0) return null;
  const max = services[0].count;

  return (
    <div style={{ marginTop: 24 }}>
      <h3 style={{ color: 'var(--tg-text)', fontSize: 16, fontWeight: 600, margin: '0 0 12px' }}>
        Топ услуг
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {services.slice(0, 5).map((s, i) => (
          <div key={i}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ color: 'var(--tg-text)', fontSize: 13 }}>{s.name}</span>
              <span style={{ color: 'var(--tg-hint)', fontSize: 13 }}>{s.count}</span>
            </div>
            <div style={{ background: 'var(--tg-secondary-bg)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                borderRadius: 4,
                background: 'var(--tg-button)',
                opacity: 1 - i * 0.15,
                width: `${Math.round((s.count / max) * 100)}%`,
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReportsSkeleton() {
  return (
    <div style={{ padding: '16px 16px 100px' }}>
      <Skeleton height={36} style={{ marginBottom: 20, borderRadius: 20 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
        {[...Array(6)].map((_, i) => <Skeleton key={i} height={80} />)}
      </div>
      <Skeleton height={200} style={{ borderRadius: 12 }} />
    </div>
  );
}

// ─── Custom period bottom sheet ───────────────────────────────────────────────

function CustomPeriodSheet({ onApply, onClose }) {
  const today = new Date().toISOString().slice(0, 10);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [error, setError] = useState('');

  const handleApply = () => {
    if (!from || !to) { setError('Укажите обе даты'); return; }
    if (to < from) { setError('Конец должен быть не раньше начала'); return; }
    const diff = (new Date(to) - new Date(from)) / 86400000;
    if (diff > 365) { setError('Максимум 365 дней'); return; }
    onApply(from, to);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100 }}
      />
      {/* Sheet */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 101,
        background: 'var(--tg-bg)',
        borderRadius: '16px 16px 0 0',
        padding: '20px 16px 32px',
      }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 16 }}>
          Произвольный период
        </div>
        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>Начало</div>
            <input
              type="date"
              value={from}
              max={today}
              onChange={e => { setFrom(e.target.value); setError(''); }}
              style={{
                width: '100%', boxSizing: 'border-box',
                border: '1px solid var(--tg-secondary-bg)',
                borderRadius: 8, padding: '10px 12px',
                background: 'var(--tg-surface)', color: 'var(--tg-text)',
                fontSize: 14,
              }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>Конец</div>
            <input
              type="date"
              value={to}
              max={today}
              onChange={e => { setTo(e.target.value); setError(''); }}
              style={{
                width: '100%', boxSizing: 'border-box',
                border: '1px solid var(--tg-secondary-bg)',
                borderRadius: 8, padding: '10px 12px',
                background: 'var(--tg-surface)', color: 'var(--tg-text)',
                fontSize: 14,
              }}
            />
          </div>
        </div>
        {error && (
          <div style={{ color: '#e53935', fontSize: 13, marginBottom: 10 }}>{error}</div>
        )}
        <button
          onClick={handleApply}
          style={{
            width: '100%', background: 'var(--tg-button)', color: 'var(--tg-button-text)',
            border: 'none', borderRadius: 12, padding: '14px', fontSize: 15, fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Показать
        </button>
      </div>
    </>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Reports({ initialPeriod = 'month' }) {
  const [activePeriod, setActivePeriod] = useState(initialPeriod);
  const [showCustomSheet, setShowCustomSheet] = useState(false);
  const [customRange, setCustomRange] = useState(null); // { from, to }

  const queryParams = activePeriod === 'custom' && customRange
    ? { date_from: customRange.from, date_to: customRange.to }
    : { period: activePeriod === 'custom' ? 'month' : activePeriod };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['master-reports', queryParams],
    queryFn: () => getMasterReports(queryParams),
    staleTime: 60_000,
    enabled: activePeriod !== 'custom' || !!customRange,
  });

  const handlePeriodSwitch = (key) => {
    WebApp?.HapticFeedback?.impactOccurred('light');
    if (key === 'custom') {
      setShowCustomSheet(true);
    } else {
      setActivePeriod(key);
      setCustomRange(null);
    }
  };

  const handleCustomApply = (from, to) => {
    setCustomRange({ from, to });
    setActivePeriod('custom');
    setShowCustomSheet(false);
    WebApp?.HapticFeedback?.notificationOccurred('success');
  };

  if (isLoading) return <ReportsSkeleton />;

  if (isError) {
    return (
      <div style={{ padding: '16px 16px 100px' }}>
        <PeriodTabs active={activePeriod} onSwitch={handlePeriodSwitch} />
        <div style={{ textAlign: 'center', padding: '48px 0' }}>
          <p style={{ color: 'var(--tg-hint)', marginBottom: 12 }}>Не удалось загрузить данные</p>
          <button onClick={refetch} style={{
            background: 'var(--tg-button)', color: 'var(--tg-button-text)',
            border: 'none', borderRadius: 10, padding: '10px 24px', fontSize: 14, cursor: 'pointer',
          }}>Повторить</button>
        </div>
      </div>
    );
  }

  const kpi = data?.kpi || {};
  const hasData = (kpi.order_count || 0) > 0;

  return (
    <div style={{ padding: '16px 16px 100px' }}>
      <PeriodTabs active={activePeriod} onSwitch={handlePeriodSwitch} customLabel={customRange
        ? `${customRange.from.slice(5).replace('-', '.')} – ${customRange.to.slice(5).replace('-', '.')}`
        : undefined}
      />

      {!hasData ? (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--tg-hint)', fontSize: 15 }}>
          За этот период данных нет
        </div>
      ) : (
        <>
          {/* KPI grid 2×3 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
            <KpiCard icon="💰" value={formatCurrency(kpi.revenue || 0)} label="Выручка" />
            <KpiCard icon="🛒" value={kpi.order_count || 0} label="Заказов" />
            <KpiCard icon="👥" value={kpi.new_clients || 0} label="Новых клиентов" />
            <KpiCard icon="🔄" value={kpi.repeat_clients || 0} label="Повторных" />
            <KpiCard icon="🧾" value={formatCurrency(kpi.avg_check || 0)} label="Средний чек" />
            <KpiCard icon="📋" value={kpi.total_clients || 0} label="Всего в базе" />
          </div>

          {/* Revenue chart */}
          <div style={{
            background: 'var(--tg-surface)',
            borderRadius: 'var(--radius-card)',
            padding: '16px 8px 8px',
            marginBottom: 0,
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 8, paddingLeft: 8 }}>
              Выручка по дням
            </div>
            <RevenueChart data={data?.chart_data} />
          </div>

          {/* Top services */}
          <TopServices services={data?.top_services} />
        </>
      )}

      {showCustomSheet && (
        <CustomPeriodSheet onApply={handleCustomApply} onClose={() => setShowCustomSheet(false)} />
      )}
    </div>
  );
}

// ─── Period tabs ──────────────────────────────────────────────────────────────

function PeriodTabs({ active, onSwitch, customLabel }) {
  return (
    <div style={{
      display: 'flex',
      gap: 6,
      marginBottom: 20,
      overflowX: 'auto',
      WebkitOverflowScrolling: 'touch',
      scrollbarWidth: 'none',
    }}>
      {PERIODS.map(({ key, label }) => {
        const isActive = active === key;
        const displayLabel = key === 'custom' && customLabel ? customLabel : label;
        return (
          <button
            key={key}
            onClick={() => onSwitch(key)}
            style={{
              flexShrink: 0,
              padding: '7px 14px',
              borderRadius: 20,
              border: 'none',
              fontSize: 13,
              fontWeight: isActive ? 600 : 400,
              background: isActive ? 'var(--tg-button)' : 'var(--tg-surface)',
              color: isActive ? 'var(--tg-button-text)' : 'var(--tg-text)',
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}
          >
            {displayLabel}
          </button>
        );
      })}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/master/pages/Reports.jsx
git commit -m "feat(reports): add Reports screen with KPI cards, chart, top services"
```

---

### Task 8: Подключить Reports в MasterApp.jsx

**Files:**
- Modify: `miniapp/src/master/MasterApp.jsx`

**Step 1: Добавить импорт**

В блок импортов (после `PromoCard`):
```javascript
import Reports from './pages/Reports';
```

**Step 2: Добавить в SCREEN_TITLES**

```javascript
reports: 'Аналитика',
```

**Step 3: Добавить case в рендер**

После блока `if (type === 'promo')` и перед `// Fallback`:

```javascript
if (type === 'reports') {
  return (
    <div>
      <PageHeader title="Аналитика" onBack={handleBack} />
      <Reports initialPeriod={current.period || 'month'} />
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add miniapp/src/master/MasterApp.jsx
git commit -m "feat(nav): register reports screen in MasterApp"
```

---

### Task 9: Финальная проверка сборки

**Step 1: Запустить сборку**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build
```
Ожидание: `✓ built in X.Xs` без ошибок.

**Step 2: Если есть ошибки TypeScript/lint**

Исправить по сообщению ошибки. Типичные проблемы:
- recharts не найден → `npm install` не выполнен
- `var(--tg-button)` в LinearGradient — SVG не поддерживает CSS vars в некоторых движках; fallback: заменить на `#5288c1` (Telegram синий)

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: verify build passes after reports feature"
```
