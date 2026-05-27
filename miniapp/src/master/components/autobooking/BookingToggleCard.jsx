import { useI18n } from '../../../i18n';
import { useUpdateBookingSettings } from '../../hooks/useBookingSettings';

/**
 * Master-level on/off switch for self-booking. The toggle is the gatekeeper:
 * when off, the public /m/{slug}/book page hides its "Записаться" CTA.
 * Optimistic update via useUpdateBookingSettings — flips instantly, rolls
 * back on server error.
 */
export default function BookingToggleCard({ settings }) {
  const { t } = useI18n();
  const updateMut = useUpdateBookingSettings();

  const toggle = () => {
    updateMut.mutate({
      enabled: !settings.enabled,
      cancel_cutoff_hours: settings.cancel_cutoff_hours,
      horizon_days: settings.horizon_days,
    });
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
      <label
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
        }}
      >
        <span style={{ fontSize: 15 }}>{t('autobooking.toggle.label')}</span>
        <input
          type="checkbox"
          checked={!!settings.enabled}
          onChange={toggle}
        />
      </label>
      <p style={{ fontSize: 13, color: 'var(--tg-hint, #888)', marginTop: 8 }}>
        {t('autobooking.toggle.hint')}
      </p>
    </section>
  );
}
