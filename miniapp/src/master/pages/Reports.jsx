import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
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

function formatXAxisTick(dateStr, totalDays) {
  const d = new Date(dateStr + 'T00:00:00');
  if (totalDays > 30 && d.getDay() !== 1) return '';
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

// ─── KPI card ─────────────────────────────────────────────────────────────────

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

// ─── Chart tooltip ────────────────────────────────────────────────────────────

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

// ─── Revenue chart ────────────────────────────────────────────────────────────

function RevenueChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ color: 'var(--tg-hint)', fontSize: 14, textAlign: 'center', padding: '32px 0' }}>
        Нет данных для графика
      </div>
    );
  }

  if (data.length === 1) {
    const dayRevenue = data[0].revenue;
    return (
      <div style={{ textAlign: 'center', padding: '32px 0' }}>
        <div style={{ color: 'var(--tg-text)', fontSize: 22, fontWeight: 700 }}>
          {formatCurrency(dayRevenue)}
        </div>
        <div style={{ color: 'var(--tg-hint)', fontSize: 13, marginTop: 4 }}>
          за {formatTooltipDate(data[0].date)}
        </div>
      </div>
    );
  }

  const totalDays = data.length;
  const tickInterval = totalDays > 30 ? 6 : totalDays > 14 ? 2 : 0;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#5288c1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#5288c1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tickFormatter={(v) => formatXAxisTick(v, totalDays)}
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

// ─── Top services ─────────────────────────────────────────────────────────────

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

// ─── Skeleton ─────────────────────────────────────────────────────────────────

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

  const inputStyle = {
    width: '100%',
    boxSizing: 'border-box',
    border: '1px solid var(--tg-secondary-bg)',
    borderRadius: 8,
    padding: '10px 12px',
    background: 'var(--tg-surface)',
    color: 'var(--tg-text)',
    fontSize: 14,
  };

  return (
    <>
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100 }}
      />
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
              style={inputStyle}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>Конец</div>
            <input
              type="date"
              value={to}
              max={today}
              onChange={e => { setTo(e.target.value); setError(''); }}
              style={inputStyle}
            />
          </div>
        </div>
        {error && (
          <div style={{ color: '#e53935', fontSize: 13, marginBottom: 10 }}>{error}</div>
        )}
        <button
          onClick={handleApply}
          style={{
            width: '100%',
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            padding: '14px',
            fontSize: 15,
            fontWeight: 600,
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

  const customLabel = customRange
    ? (() => {
        const fmt = (s) => new Date(s + 'T00:00:00').toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' });
        return `${fmt(customRange.from)} – ${fmt(customRange.to)}`;
      })()
    : undefined;

  if (isLoading) return <ReportsSkeleton />;

  if (isError) {
    return (
      <div style={{ padding: '16px 16px 100px' }}>
        <PeriodTabs active={activePeriod} onSwitch={handlePeriodSwitch} customLabel={customLabel} />
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
      <PeriodTabs active={activePeriod} onSwitch={handlePeriodSwitch} customLabel={customLabel} />

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
          }}>
            <div style={{
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--tg-text)',
              marginBottom: 8,
              paddingLeft: 8,
            }}>
              Выручка по дням
            </div>
            <RevenueChart data={data?.chart_data} />
          </div>

          {/* Top services */}
          <TopServices services={data?.top_services} />
        </>
      )}

      {showCustomSheet && (
        <CustomPeriodSheet
          onApply={handleCustomApply}
          onClose={() => setShowCustomSheet(false)}
        />
      )}
    </div>
  );
}
