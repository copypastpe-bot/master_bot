import { useState, useRef } from 'react';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

/** Returns Monday of the week containing `d`. */
function getWeekStart(d) {
  const day = new Date(d);
  const dow = day.getDay(); // 0=Sun
  const diff = dow === 0 ? -6 : 1 - dow; // shift to Monday
  day.setDate(day.getDate() + diff);
  day.setHours(0, 0, 0, 0);
  return day;
}

/** Returns array of 7 Date objects for the week starting at `monday`. */
function getWeekDays(monday) {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function toYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const SWIPE_THRESHOLD = 50; // px

export default function WeekStrip({ selectedDate, onSelectDate, activeDates = [] }) {
  const { tr, locale } = useI18n();
  const activeDateSet = new Set(activeDates);
  const todayStr = toYMD(new Date());

  // weekStart is stored as ISO string to keep it serialisable
  const [weekStart, setWeekStart] = useState(() => toYMD(getWeekStart(new Date())));

  // Touch tracking
  const touchStartX = useRef(null);
  const touchCurrentX = useRef(null);
  const [swipeOffset, setSwipeOffset] = useState(0);
  const [animating, setAnimating] = useState(false);

  const days = getWeekDays(new Date(weekStart));

  const goToWeek = (direction) => {
    if (animating) return;

    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }

    // Animate out
    setAnimating(true);
    setSwipeOffset(direction === 'next' ? -100 : 100);

    setTimeout(() => {
      const current = new Date(weekStart);
      current.setDate(current.getDate() + direction * 7);
      setWeekStart(toYMD(current));
      // Snap to opposite side instantly (no transition), then slide in to 0
      setSwipeOffset(direction === 'next' ? 100 : -100);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setSwipeOffset(0);
          setAnimating(false);
        });
      });
    }, 200);
  };

  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
    touchCurrentX.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e) => {
    if (touchStartX.current === null) return;
    touchCurrentX.current = e.touches[0].clientX;
    const delta = touchCurrentX.current - touchStartX.current;
    setSwipeOffset((delta / window.innerWidth) * 100);
  };

  const handleTouchEnd = () => {
    if (touchStartX.current === null) return;
    const delta = touchCurrentX.current - touchStartX.current;
    touchStartX.current = null;
    touchCurrentX.current = null;

    if (Math.abs(delta) >= SWIPE_THRESHOLD) {
      // Reset offset before animated transition
      setSwipeOffset(0);
      goToWeek(delta < 0 ? 1 : -1);
    } else {
      setSwipeOffset(0);
    }
  };

  const handleSelectDay = (dayStr) => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onSelectDate(dayStr);
  };

  const goToToday = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    setWeekStart(toYMD(getWeekStart(new Date())));
    onSelectDate(todayStr);
  };

  // Check if "today" button is needed (current week shown already?)
  const currentWeekStartStr = toYMD(getWeekStart(new Date()));
  const isCurrentWeek = weekStart === currentWeekStartStr;

  return (
    <div style={{ background: 'var(--tg-surface)', paddingBottom: 8 }}>
      {/* Header row: week label + Today button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px 4px',
      }}>
        <span style={{ fontSize: 12, color: 'var(--tg-hint)' }}>
          {days[0].toLocaleDateString(locale, { month: 'long', year: 'numeric' })}
        </span>
        {!isCurrentWeek && (
          <button
            onClick={goToToday}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--tg-button)',
              fontSize: 13,
              cursor: 'pointer',
              padding: '2px 0',
              fontWeight: 500,
            }}
          >
            {tr('Сегодня', 'Today')}
          </button>
        )}
      </div>

      {/* Days row — swipeable */}
      <div
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onTouchCancel={() => {
          touchStartX.current = null;
          touchCurrentX.current = null;
          setSwipeOffset(0);
        }}
        style={{ overflow: 'hidden', touchAction: 'pan-y' }}
      >
        <div
          style={{
            display: 'flex',
            padding: '4px 8px',
            transform: `translateX(${swipeOffset}%)`,
            transition: animating ? 'transform 0.2s ease' : 'none',
          }}
        >
          {days.map((day, idx) => {
            const dayStr = toYMD(day);
            const isSelected = dayStr === selectedDate;
            const isToday = dayStr === todayStr;
            const hasOrders = activeDateSet.has(dayStr);

            return (
              <button
                key={dayStr}
                onClick={() => handleSelectDay(dayStr)}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                  padding: '6px 0',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  position: 'relative',
                }}
              >
                {/* Day label */}
                <span style={{
                  fontSize: 11,
                  color: isSelected
                    ? 'var(--tg-button)'
                    : isToday
                      ? 'var(--tg-button)'
                      : 'var(--tg-hint)',
                  fontWeight: isSelected || isToday ? 600 : 400,
                }}>
                  {day.toLocaleDateString(locale, { weekday: 'short' })}
                </span>

                {/* Day number with selection circle */}
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: isSelected ? 'var(--tg-button)' : 'transparent',
                }}>
                  <span style={{
                    fontSize: 14,
                    fontWeight: isSelected || isToday ? 700 : 400,
                    fontVariantNumeric: 'tabular-nums',
                    color: isSelected
                      ? 'var(--tg-button-text)'
                      : isToday
                        ? 'var(--tg-button)'
                        : 'var(--tg-text)',
                  }}>
                    {day.getDate()}
                  </span>
                </div>

                {/* Dot for days with orders */}
                <div style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: hasOrders ? 'var(--tg-button)' : 'transparent',
                }} />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
