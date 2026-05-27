import { useState } from 'react';
import { useI18n } from '../../../i18n';

/**
 * Per-date radio-group sheet: "as usual" / "off" / "custom hours". The
 * parent receives ('delete', id) when the master wants to clear an
 * existing exception, or ('upsert', {existingId, body}) for create/edit.
 * Same-day type change goes through delete + create — simplest path that
 * keeps the backend transactional.
 */
export default function DateExceptionSheet({
  date,            // 'YYYY-MM-DD'
  existing,        // null or {id, kind, start_time, end_time}
  onClose,
  onSubmit,
}) {
  const { t } = useI18n();
  const initialKind = existing?.kind ?? null;
  const [kind, setKind] = useState(initialKind);
  const [start, setStart] = useState(existing?.start_time ?? '10:00');
  const [end, setEnd] = useState(existing?.end_time ?? '18:00');

  const save = () => {
    if (kind === null) {
      if (existing) onSubmit('delete', existing.id);
      else onClose();
      return;
    }
    onSubmit('upsert', {
      existingId: existing?.id ?? null,
      body: {
        date,
        kind,
        start: kind === 'override' ? start : null,
        end: kind === 'override' ? end : null,
      },
    });
  };

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
        <h3 style={{ margin: '0 0 12px' }}>{date}</h3>

        <label style={{ display: 'block', padding: '8px 0' }}>
          <input
            type="radio"
            name="exc-kind"
            checked={kind === null}
            onChange={() => setKind(null)}
          />{' '}
          {t('autobooking.exceptions.asUsual')}
        </label>
        <label style={{ display: 'block', padding: '8px 0' }}>
          <input
            type="radio"
            name="exc-kind"
            checked={kind === 'off'}
            onChange={() => setKind('off')}
          />{' '}
          {t('autobooking.exceptions.off')}
        </label>
        <label style={{ display: 'block', padding: '8px 0' }}>
          <input
            type="radio"
            name="exc-kind"
            checked={kind === 'override'}
            onChange={() => setKind('override')}
          />{' '}
          {t('autobooking.exceptions.override')}
        </label>

        {kind === 'override' && (
          <div style={{ display: 'flex', gap: 8, margin: '8px 0' }}>
            <input type="time" value={start} onChange={(e) => setStart(e.target.value)} />
            <span>—</span>
            <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 10 }}>
            {t('common.cancel')}
          </button>
          <button
            onClick={save}
            style={{ flex: 1, padding: 10, background: 'var(--tg-button-bg, #1a73e8)', color: '#fff', border: 'none' }}
          >
            {t('common.save')}
          </button>
        </div>
      </div>
    </div>
  );
}
