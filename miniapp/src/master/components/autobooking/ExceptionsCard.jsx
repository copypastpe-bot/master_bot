import { useState } from 'react';
import { useI18n } from '../../../i18n';
import {
  useAddScheduleException,
  useRemoveScheduleException,
} from '../../hooks/useBookingSettings';
import DateExceptionSheet from './DateExceptionSheet';

// Hand-rolled date math — no library. YYYY-MM-DD in local TZ for the
// strip; backend stores the same string verbatim.
function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function buildDates(horizonDays) {
  const out = [];
  const today = new Date();
  for (let i = 0; i < horizonDays; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    out.push({ iso: isoDate(d), label: `${d.getDate()}.${d.getMonth() + 1}` });
  }
  return out;
}

/**
 * Horizontal date strip showing today + the next `horizon_days` chips.
 * Plain background = no exception. Red tint = off. Blue tint = override.
 * Tap chip → DateExceptionSheet. Below the strip is a sorted list of
 * saved exceptions with a per-row ✕ for one-tap removal.
 */
export default function ExceptionsCard({ settings }) {
  const { t } = useI18n();
  const [picking, setPicking] = useState(null); // 'YYYY-MM-DD' or null
  const addMut = useAddScheduleException();
  const removeMut = useRemoveScheduleException();

  const exceptions = settings.exceptions ?? [];
  const byIso = Object.fromEntries(exceptions.map((e) => [e.date, e]));
  const dates = buildDates(settings.horizon_days || 30);

  const submit = (action, payload) => {
    if (action === 'delete') {
      removeMut.mutate(payload);
    } else if (action === 'upsert') {
      // Existing same-day exception of any kind → delete+add for simplicity.
      if (payload.existingId) removeMut.mutate(payload.existingId);
      addMut.mutate(payload.body);
    }
    setPicking(null);
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
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{t('autobooking.exceptions.title')}</h3>

      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '4px 0' }}>
        {dates.map((d) => {
          const exc = byIso[d.iso];
          const bg = !exc ? '#f3f4f6' : exc.kind === 'off' ? '#fee2e2' : '#dbeafe';
          return (
            <button
              key={d.iso}
              onClick={() => setPicking(d.iso)}
              style={{
                flex: '0 0 auto',
                padding: '6px 10px',
                borderRadius: 8,
                border: '1px solid #ddd',
                background: bg,
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              {d.label}
            </button>
          );
        })}
      </div>

      {exceptions.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, marginTop: 12, fontSize: 13 }}>
          {[...exceptions]
            .sort((a, b) => a.date.localeCompare(b.date))
            .map((e) => (
              <li
                key={e.id}
                style={{
                  padding: '6px 0',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>
                  {e.date} —{' '}
                  {e.kind === 'off'
                    ? t('autobooking.exceptions.off')
                    : `${e.start_time}–${e.end_time}`}
                </span>
                <button
                  onClick={() => removeMut.mutate(e.id)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                  aria-label="remove"
                >
                  ✕
                </button>
              </li>
            ))}
        </ul>
      )}

      {picking && (
        <DateExceptionSheet
          date={picking}
          existing={byIso[picking] ?? null}
          onClose={() => setPicking(null)}
          onSubmit={submit}
        />
      )}
    </section>
  );
}
