import { useState } from 'react';
import { useI18n } from '../../../i18n';

/**
 * Bottom-sheet for editing a single weekday's intervals. The master can
 * add/remove multiple intervals (split shifts like 10:00-14:00 + 16:00-20:00),
 * and optionally apply this exact set to all weekdays (Mon-Fri) with a
 * checkbox. Save returns (intervals, applyToWeekdays) to the parent card,
 * which then builds the full 7-day array and ships it to the API.
 */
export default function DayIntervalsSheet({
  weekday,           // 0..6
  initialIntervals,  // [{start,end}, ...]
  onClose,
  onSave,
}) {
  const { t } = useI18n();
  const dayLabels = t('autobooking.weekly.dayShort') || ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

  // Empty initial state = master can quickly add their first interval.
  const [rows, setRows] = useState(
    initialIntervals.length ? initialIntervals : [{ start: '10:00', end: '18:00' }]
  );
  const [applyAll, setApplyAll] = useState(false);

  const setRow = (i, k, v) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, [k]: v } : r)));
  const removeRow = (i) => setRows((rs) => rs.filter((_, idx) => idx !== i));
  const addRow = () => setRows((rs) => [...rs, { start: '10:00', end: '18:00' }]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'flex-end',
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--tg-card-bg, #fff)',
          width: '100%',
          borderRadius: '16px 16px 0 0',
          padding: 16,
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 12px' }}>{dayLabels[weekday]}</h3>

        {rows.map((r, i) => (
          <div
            key={i}
            style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}
          >
            <input
              type="time"
              value={r.start}
              onChange={(e) => setRow(i, 'start', e.target.value)}
            />
            <span>—</span>
            <input
              type="time"
              value={r.end}
              onChange={(e) => setRow(i, 'end', e.target.value)}
            />
            <button
              onClick={() => removeRow(i)}
              style={{ marginLeft: 'auto', background: 'transparent', border: 'none', fontSize: 18 }}
              aria-label="remove"
            >
              ✕
            </button>
          </div>
        ))}

        <button
          onClick={addRow}
          style={{ marginTop: 8, background: 'transparent', border: '1px dashed #ccc', padding: '8px 12px', width: '100%' }}
        >
          + {t('autobooking.weekly.intervalAdd')}
        </button>

        {weekday < 5 && (
          <label style={{ display: 'block', marginTop: 16, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={applyAll}
              onChange={(e) => setApplyAll(e.target.checked)}
            />{' '}
            {t('autobooking.weekly.applyToWeekdays')}
          </label>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 10 }}>
            {t('common.cancel')}
          </button>
          <button
            onClick={() => onSave(rows, applyAll)}
            style={{ flex: 1, padding: 10, background: 'var(--tg-button-bg, #1a73e8)', color: '#fff', border: 'none' }}
          >
            {t('common.save')}
          </button>
        </div>
      </div>
    </div>
  );
}
