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
import MonthCalendar from '../components/MonthCalendar';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

// ─── Formatters ──────────────────────────────────────────────────────────────

function formatCurrency(n, locale) {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(n) + ' ₽';
}

function formatYAxis(n) {
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'K';
  return n;
}

function formatXAxisTick(dateStr, totalDays, locale) {
  const d = new Date(dateStr + 'T00:00:00');
  if (totalDays > 30 && d.getDay() !== 1) return '';
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
}

function formatTooltipDate(dateStr, locale) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatInputDate(ymd, locale, tr) {
  if (!ymd) return tr('Выбрать дату', 'Pick date');
  try {
    return new Date(ymd + 'T00:00:00').toLocaleDateString(locale);
  } catch {
    return ymd;
  }
}

const ELEVATED_CARD_STYLE = {
  background: 'var(--tg-surface)',
  border: '1px solid var(--tg-enterprise-border, var(--tg-secondary-bg))',
  borderRadius: 'var(--radius-card)',
  boxShadow: 'var(--tg-enterprise-shadow, 0 6px 18px rgba(0,0,0,0.06))',
};

// ─── KPI card ─────────────────────────────────────────────────────────────────

function KpiCard({ icon, value, label }) {
  return (
    <div style={{
      ...ELEVATED_CARD_STYLE,
      padding: '14px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      minHeight: 92,
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
      <div style={{ color: 'var(--tg-hint)', fontSize: 11, lineHeight: 1.3, fontWeight: 500 }}>
        {label}
      </div>
    </div>
  );
}

// ─── Chart tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label, locale }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--tg-surface)',
      border: '1px solid var(--tg-secondary-bg)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 13,
    }}>
      <div style={{ color: 'var(--tg-hint)', marginBottom: 2 }}>{formatTooltipDate(label, locale)}</div>
      <div style={{ color: 'var(--tg-text)', fontWeight: 600 }}>
        {formatCurrency(payload[0].value, locale)}
      </div>
    </div>
  );
}

// ─── Revenue chart ────────────────────────────────────────────────────────────

function RevenueChart({ data, locale, tr }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ color: 'var(--tg-hint)', fontSize: 14, textAlign: 'center', padding: '32px 0' }}>
        {tr('Нет данных для графика', 'No chart data')}
      </div>
    );
  }

  if (data.length === 1) {
    const dayRevenue = data[0].revenue;
    return (
      <div style={{ textAlign: 'center', padding: '32px 0' }}>
        <div style={{ color: 'var(--tg-text)', fontSize: 22, fontWeight: 700 }}>
          {formatCurrency(dayRevenue, locale)}
        </div>
        <div style={{ color: 'var(--tg-hint)', fontSize: 13, marginTop: 4 }}>
          {tr('за', 'for')} {formatTooltipDate(data[0].date, locale)}
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
          tickFormatter={(v) => formatXAxisTick(v, totalDays, locale)}
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
        <Tooltip content={<CustomTooltip locale={locale} />} />
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

function TopServices({ services, tr }) {
  if (!services || services.length === 0) return null;
  const max = services[0].count;

  return (
    <div style={{ ...ELEVATED_CARD_STYLE, marginTop: 16, padding: '14px 14px 12px' }}>
      <h3 style={{ color: 'var(--tg-text)', fontSize: 16, fontWeight: 700, margin: '0 0 12px' }}>
        {tr('Топ услуг', 'Top services')}
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {services.slice(0, 5).map((s, i) => (
          <div key={i} style={{ padding: '8px 6px', borderRadius: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, gap: 8 }}>
              <span style={{ color: 'var(--tg-text)', fontSize: 13, fontWeight: 500 }}>{s.name}</span>
              <span style={{ color: 'var(--tg-hint)', fontSize: 13, fontWeight: 600 }}>{s.count}</span>
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

function PeriodTabs({ active, onSwitch, customLabel, periods }) {
  return (
    <div style={{
      ...ELEVATED_CARD_STYLE,
      padding: 6,
      marginBottom: 20,
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
        gap: 6,
      }}>
      {periods.map(({ key, label }) => {
        const isActive = active === key;
        return (
          <button
            key={key}
            onClick={() => onSwitch(key)}
            style={{
              width: '100%',
              minWidth: 0,
              padding: '8px 14px',
              borderRadius: 20,
              border: isActive ? 'none' : '1px solid transparent',
              fontSize: 13,
              fontWeight: isActive ? 700 : 500,
              background: isActive ? 'var(--tg-button)' : 'transparent',
              color: isActive ? 'var(--tg-button-text)' : 'var(--tg-hint)',
              cursor: 'pointer',
              transition: 'background 0.15s, color 0.15s',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {label}
          </button>
        );
      })}
      </div>
      {active === 'custom' && customLabel && (
        <div
          style={{
            marginTop: 8,
            padding: '0 8px 2px',
            fontSize: 12,
            fontWeight: 600,
            color: 'var(--tg-hint)',
            textAlign: 'center',
          }}
        >
          {customLabel}
        </div>
      )}
    </div>
  );
}

// ─── Custom period bottom sheet ───────────────────────────────────────────────

function CustomPeriodSheet({ onApply, onClose, locale, tr }) {
  const today = new Date().toISOString().slice(0, 10);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [error, setError] = useState('');
  const [pickerField, setPickerField] = useState(null); // 'from' | 'to' | null
  const [viewYear, setViewYear] = useState(new Date().getFullYear());
  const [viewMonth, setViewMonth] = useState(new Date().getMonth() + 1);

  const handleApply = () => {
    if (!from || !to) { setError(tr('Укажите обе даты', 'Specify both dates')); return; }
    if (to < from) { setError(tr('Конец должен быть не раньше начала', 'End date must not be earlier than start date')); return; }
    const diff = (new Date(to) - new Date(from)) / 86400000;
    if (diff > 365) { setError(tr('Максимум 365 дней', 'Maximum 365 days')); return; }
    onApply(from, to);
  };

  const inputStyle = {
    width: '100%',
    minWidth: 0,
    boxSizing: 'border-box',
    border: '1px solid var(--tg-secondary-bg)',
    borderRadius: 8,
    padding: '10px 12px',
    background: 'var(--tg-surface)',
    color: 'var(--tg-text)',
    fontSize: 14,
    textAlign: 'left',
    cursor: 'pointer',
  };

  const openPicker = (field) => {
    const base = (field === 'from' ? from : to) || today;
    const y = parseInt(base.slice(0, 4), 10);
    const m = parseInt(base.slice(5, 7), 10);
    setViewYear(Number.isFinite(y) ? y : new Date().getFullYear());
    setViewMonth(Number.isFinite(m) ? m : new Date().getMonth() + 1);
    setPickerField(field);
  };

  const handleSelectDate = (value) => {
    if (pickerField === 'from') setFrom(value);
    if (pickerField === 'to') setTo(value);
    setPickerField(null);
    setError('');
  };

  const goPrevMonth = () => {
    if (viewMonth === 1) {
      setViewMonth(12);
      setViewYear(y => y - 1);
    } else {
      setViewMonth(m => m - 1);
    }
  };

  const goNextMonth = () => {
    if (viewMonth === 12) {
      setViewMonth(1);
      setViewYear(y => y + 1);
    } else {
      setViewMonth(m => m + 1);
    }
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
          {tr('Произвольный период', 'Custom range')}
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: 10,
            marginBottom: 12,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>{tr('Начало', 'Start')}</div>
            <button
              type="button"
              onClick={() => openPicker('from')}
              style={inputStyle}
            >
              {formatInputDate(from, locale, tr)}
            </button>
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>{tr('Конец', 'End')}</div>
            <button
              type="button"
              onClick={() => openPicker('to')}
              style={inputStyle}
            >
              {formatInputDate(to, locale, tr)}
            </button>
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
          {tr('Показать', 'Apply')}
        </button>
      </div>

      {pickerField && (
        <>
          <div
            onClick={() => setPickerField(null)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 120 }}
          />
          <div
            style={{
              position: 'fixed',
              left: 12,
              right: 12,
              top: 96,
              zIndex: 121,
              borderRadius: 16,
              overflow: 'hidden',
              border: '1px solid var(--tg-secondary-bg)',
              background: 'var(--tg-bg)',
              boxShadow: '0 12px 30px rgba(0,0,0,0.22)',
            }}
          >
            <MonthCalendar
              selectedDate={pickerField === 'from' ? from || today : to || today}
              onSelectDate={handleSelectDate}
              viewYear={viewYear}
              viewMonth={viewMonth}
              onPrevMonth={goPrevMonth}
              onNextMonth={goNextMonth}
              onGoToToday={() => {
                const t = new Date();
                setViewYear(t.getFullYear());
                setViewMonth(t.getMonth() + 1);
              }}
              activeDates={[]}
              todayStr={today}
            />
          </div>
        </>
      )}
    </>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Reports({ initialPeriod = 'month' }) {
  const { tr, locale } = useI18n();
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
        const fmt = (s) => new Date(s + 'T00:00:00').toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: '2-digit' });
        return `${fmt(customRange.from)} – ${fmt(customRange.to)}`;
      })()
    : undefined;

  if (isLoading) return <ReportsSkeleton />;

  if (isError) {
    return (
      <div style={{ padding: '16px 16px 100px', maxWidth: 760, margin: '0 auto' }}>
        <PeriodTabs active={activePeriod} onSwitch={handlePeriodSwitch} customLabel={customLabel} periods={periods} />
        <div style={{ textAlign: 'center', padding: '48px 0' }}>
          <p style={{ color: 'var(--tg-hint)', marginBottom: 12 }}>{tr('Не удалось загрузить данные', 'Failed to load data')}</p>
          <button onClick={refetch} style={{
            background: 'var(--tg-button)', color: 'var(--tg-button-text)',
            border: 'none', borderRadius: 10, padding: '10px 24px', fontSize: 14, cursor: 'pointer',
          }}>{tr('Повторить', 'Retry')}</button>
        </div>
      </div>
    );
  }

  const kpi = data?.kpi || {};
  const hasData = (kpi.order_count || 0) > 0;

  return (
    <div style={{ padding: '16px 16px 100px', maxWidth: 760, margin: '0 auto' }}>
      <PeriodTabs active={activePeriod} onSwitch={handlePeriodSwitch} customLabel={customLabel} periods={periods} />

      {!hasData ? (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--tg-hint)', fontSize: 15 }}>
          {tr('За этот период данных нет', 'No data for this period')}
        </div>
      ) : (
        <>
          {/* KPI grid 2×3 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
            <KpiCard icon="💰" value={formatCurrency(kpi.revenue || 0, locale)} label={tr('Выручка', 'Revenue')} />
            <KpiCard icon="🛒" value={kpi.order_count || 0} label={tr('Заказов', 'Orders')} />
            <KpiCard icon="👥" value={kpi.new_clients || 0} label={tr('Новых клиентов', 'New clients')} />
            <KpiCard icon="🔄" value={kpi.repeat_clients || 0} label={tr('Повторных', 'Repeat')} />
            <KpiCard icon="🧾" value={formatCurrency(kpi.avg_check || 0, locale)} label={tr('Средний чек', 'Average check')} />
            <KpiCard icon="📋" value={kpi.total_clients || 0} label={tr('Всего в базе', 'Total clients')} />
          </div>

          {/* Revenue chart */}
          <div style={{
            ...ELEVATED_CARD_STYLE,
            padding: '16px 8px 8px',
            marginTop: 6,
          }}>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--tg-text)',
              marginBottom: 8,
              paddingLeft: 8,
            }}>
              {tr('Выручка по дням', 'Revenue by day')}
            </div>
            <RevenueChart data={data?.chart_data} locale={locale} tr={tr} />
          </div>

          {/* Top services */}
          <TopServices services={data?.top_services} tr={tr} />
        </>
      )}

      {showCustomSheet && (
        <CustomPeriodSheet
          onApply={handleCustomApply}
          onClose={() => setShowCustomSheet(false)}
          locale={locale}
          tr={tr}
        />
      )}
    </div>
  );
}
  const periods = [
    { key: 'today', label: tr('Сегодня', 'Today') },
    { key: 'week', label: tr('Неделя', 'Week') },
    { key: 'month', label: tr('Месяц', 'Month') },
    { key: 'custom', label: tr('Период', 'Range') },
  ];
