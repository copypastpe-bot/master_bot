import { useState } from 'react';
import { useI18n } from '../../../i18n';
import { useReplaceWeeklySchedule } from '../../hooks/useBookingSettings';
import DayIntervalsSheet from './DayIntervalsSheet';

function summarise(intervals, dayOffLabel) {
  if (!intervals.length) return dayOffLabel;
  return intervals.map((i) => `${i.start_time}-${i.end_time}`).join(', ');
}

/**
 * Card showing 7 day-rows. Tap any day → DayIntervalsSheet. On save, the
 * card builds the full 7-day array (keeping other days' intervals
 * untouched) and ships it via useReplaceWeeklySchedule, which does an
 * idempotent delete-all + insert on the backend.
 *
 * If "apply to weekdays" is checked while editing Mon-Fri, the saved
 * intervals override Mon-Fri all at once.
 */
export default function WeeklyScheduleCard({ settings }) {
  const { t } = useI18n();
  const replaceMut = useReplaceWeeklySchedule();
  const [editingDay, setEditingDay] = useState(null);

  const dayLabels = t('autobooking.weekly.dayShort') || ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  const dayOffLabel = t('autobooking.weekly.dayOff');

  const weekly = settings.weekly ?? [];
  const byDay = (d) => weekly.filter((i) => i.weekday === d);

  const handleSave = (rows, applyToWeekdays) => {
    // Build new full-7-day array. Keep other days' intervals untouched
    // (or overwrite Mon-Fri with `rows` if applyToWeekdays).
    const next = [];
    for (let d = 0; d < 7; d++) {
      const dayRows =
        applyToWeekdays && d < 5
          ? rows
          : d === editingDay
            ? rows
            : byDay(d).map((i) => ({ start: i.start_time, end: i.end_time }));
      dayRows.forEach((r) => next.push({ weekday: d, start: r.start, end: r.end }));
    }
    replaceMut.mutate(next);
    setEditingDay(null);
  };

  return (
    <section
      style={{
        background: 'var(--tg-card-bg, #fff)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}
    >
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{t('autobooking.weekly.title')}</h3>

      {dayLabels.map((label, d) => (
        <button
          key={d}
          onClick={() => setEditingDay(d)}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            width: '100%',
            background: 'transparent',
            border: 'none',
            padding: '10px 0',
            borderBottom: '1px solid #eee',
            fontSize: 14,
            cursor: 'pointer',
            color: 'inherit',
          }}
        >
          <span>{label}</span>
          <span style={{ color: byDay(d).length ? 'inherit' : 'var(--tg-hint, #888)' }}>
            {summarise(byDay(d), dayOffLabel)} ›
          </span>
        </button>
      ))}

      {editingDay !== null && (
        <DayIntervalsSheet
          weekday={editingDay}
          initialIntervals={byDay(editingDay).map((i) => ({
            start: i.start_time,
            end: i.end_time,
          }))}
          onClose={() => setEditingDay(null)}
          onSave={handleSave}
        />
      )}
    </section>
  );
}
