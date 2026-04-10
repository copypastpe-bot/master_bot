import { useMemo } from 'react';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function pad(n) { return String(n).padStart(2, '0'); }
function toYMD(y, m, d) { return `${y}-${pad(m)}-${pad(d)}`; }
function getDaysInMonth(y, m) { return new Date(y, m, 0).getDate(); }

/** Monday-based start offset: how many cells to fill from prev month */
function startOffset(y, m) {
  const dow = new Date(y, m - 1, 1).getDay(); // 0=Sun
  return dow === 0 ? 6 : dow - 1;
}

function buildGrid(year, month) {
  const daysNow = getDaysInMonth(year, month);
  const offset = startOffset(year, month);

  const prevMonth = month === 1 ? 12 : month - 1;
  const prevYear  = month === 1 ? year - 1 : year;
  const daysInPrev = getDaysInMonth(prevYear, prevMonth);

  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear  = month === 12 ? year + 1 : year;

  const cells = [];

  // Fill from previous month
  for (let i = offset; i > 0; i--) {
    cells.push({ dateStr: toYMD(prevYear, prevMonth, daysInPrev - i + 1), current: false });
  }

  // Current month
  for (let d = 1; d <= daysNow; d++) {
    cells.push({ dateStr: toYMD(year, month, d), current: true });
  }

  // Fill to complete last row
  const tail = cells.length % 7;
  if (tail > 0) {
    for (let d = 1; d <= 7 - tail; d++) {
      cells.push({ dateStr: toYMD(nextYear, nextMonth, d), current: false });
    }
  }

  return cells;
}

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function MonthCalendar({
  selectedDate,
  onSelectDate,
  viewYear,
  viewMonth,
  onPrevMonth,
  onNextMonth,
  onGoToToday,
  activeDates = [],
  todayStr,
}) {
  const { tr, locale } = useI18n();
  const activeDateSet = new Set(activeDates);
  const cells = useMemo(() => buildGrid(viewYear, viewMonth), [viewYear, viewMonth]);
  const monthLabel = useMemo(
    () => new Date(viewYear, viewMonth - 1, 1).toLocaleDateString(locale, { month: 'long', year: 'numeric' }),
    [viewYear, viewMonth, locale]
  );
  const dayLabels = useMemo(() => {
    const monday = new Date(2024, 0, 1); // Monday
    return Array.from({ length: 7 }, (_, idx) =>
      new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + idx)
        .toLocaleDateString(locale, { weekday: 'short' })
    );
  }, [locale]);

  const isCurrentMonth =
    viewYear === parseInt(todayStr.slice(0, 4)) &&
    viewMonth === parseInt(todayStr.slice(5, 7));

  return (
    <div style={{ background: 'var(--tg-surface)', paddingBottom: 6 }}>

      {/* Month navigation */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 4px 6px',
      }}>
        <button
          onClick={() => { haptic(); onPrevMonth(); }}
          style={navBtn}
          aria-label={tr('Предыдущий месяц', 'Previous month')}
        >
          ‹
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--tg-text)' }}>
            {monthLabel}
          </span>
          {!isCurrentMonth && (
            <button
              onClick={() => { haptic(); onGoToToday(); }}
              style={todayBtn}
            >
              {tr('Сегодня', 'Today')}
            </button>
          )}
        </div>

        <button
          onClick={() => { haptic(); onNextMonth(); }}
          style={navBtn}
          aria-label={tr('Следующий месяц', 'Next month')}
        >
          ›
        </button>
      </div>

      {/* Day-of-week labels */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        padding: '0 8px',
        marginBottom: 2,
      }}>
        {dayLabels.map(d => (
          <div key={d} style={{
            textAlign: 'center',
            fontSize: 11,
            color: 'var(--tg-hint)',
            padding: '2px 0',
          }}>
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        padding: '0 4px',
        gap: '2px 0',
      }}>
        {cells.map(cell => {
          const isSelected  = cell.dateStr === selectedDate;
          const isToday     = cell.dateStr === todayStr;
          const hasOrders   = activeDateSet.has(cell.dateStr);
          const dayNum      = parseInt(cell.dateStr.slice(8), 10);

          return (
            <button
              key={cell.dateStr}
              onClick={() => { haptic(); onSelectDate(cell.dateStr); }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 2,
                padding: '3px 0',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              {/* Number circle */}
              <div style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: isSelected ? 'var(--tg-button)' : 'transparent',
                border: isToday && !isSelected ? '1.5px solid var(--tg-button)' : 'none',
                boxSizing: 'border-box',
              }}>
                <span style={{
                  fontSize: 14,
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: isSelected || isToday ? 700 : 400,
                  color: isSelected
                    ? 'var(--tg-button-text)'
                    : isToday
                      ? 'var(--tg-button)'
                      : cell.current
                        ? 'var(--tg-text)'
                        : 'var(--tg-hint)',
                }}>
                  {dayNum}
                </span>
              </div>

              {/* Order dot */}
              <div style={{
                width: 4,
                height: 4,
                borderRadius: '50%',
                background: hasOrders
                  ? (isSelected ? 'var(--tg-button-text)' : 'var(--tg-button)')
                  : 'transparent',
              }} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const navBtn = {
  background: 'none',
  border: 'none',
  color: 'var(--tg-button)',
  fontSize: 28,
  cursor: 'pointer',
  padding: '0 14px',
  lineHeight: 1,
  fontWeight: 300,
};

const todayBtn = {
  background: 'none',
  border: '1px solid var(--tg-button)',
  borderRadius: 10,
  color: 'var(--tg-button)',
  fontSize: 12,
  fontWeight: 500,
  cursor: 'pointer',
  padding: '2px 8px',
};
