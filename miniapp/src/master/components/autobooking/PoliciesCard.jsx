import { useEffect, useRef, useState } from 'react';
import { useI18n } from '../../../i18n';
import { useUpdateBookingSettings } from '../../hooks/useBookingSettings';

/**
 * Two range sliders for booking policies — cancel cutoff (1-48h) and
 * booking horizon (7-60 days). Drag is debounced 500ms so a single PUT
 * lands per gesture instead of one per onChange tick.
 *
 * Local state mirrors props for the live readout next to each slider
 * while the master drags; the debounced effect fires the mutation,
 * which optimistically patches the bundle.
 */
export default function PoliciesCard({ settings }) {
  const { t } = useI18n();
  const updateMut = useUpdateBookingSettings();
  // Local state initialised once. Cross-device editing during a single
  // session is out of scope for the pilot — if it ever becomes a concern,
  // switch to the React 19 setState-during-render pattern for derived
  // state. The optimistic mutation already keeps the cache in sync.
  const [cutoff, setCutoff] = useState(settings.cancel_cutoff_hours);
  const [horizon, setHorizon] = useState(settings.horizon_days);

  const timer = useRef(null);
  const queueSave = (nextCutoff, nextHorizon) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      updateMut.mutate({
        enabled: settings.enabled,
        cancel_cutoff_hours: nextCutoff,
        horizon_days: nextHorizon,
      });
    }, 500);
  };

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  return (
    <section
      style={{
        background: 'var(--tg-card-bg, #fff)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}
    >
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{t('autobooking.policies.title')}</h3>

      <label style={{ display: 'block', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span>{t('autobooking.policies.cutoffLabel')}</span>
          <span>{cutoff} {t('autobooking.policies.cutoffUnit')}</span>
        </div>
        <input
          type="range"
          min={1}
          max={48}
          step={1}
          value={cutoff}
          onChange={(e) => {
            const v = Number(e.target.value);
            setCutoff(v);
            queueSave(v, horizon);
          }}
          style={{ width: '100%' }}
        />
      </label>

      <label style={{ display: 'block' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span>{t('autobooking.policies.horizonLabel')}</span>
          <span>{horizon} {t('autobooking.policies.horizonUnit')}</span>
        </div>
        <input
          type="range"
          min={7}
          max={60}
          step={1}
          value={horizon}
          onChange={(e) => {
            const v = Number(e.target.value);
            setHorizon(v);
            queueSave(cutoff, v);
          }}
          style={{ width: '100%' }}
        />
      </label>
    </section>
  );
}
