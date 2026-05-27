import { useQuery } from '@tanstack/react-query';
import { getMasterServices } from '../../../api/client';
import { useI18n } from '../../../i18n';

/**
 * Heuristic: if at least one service exists and ALL of them sit at exactly
 * 60 minutes, treat it as "no master has touched durations yet" and nudge
 * them to the Services screen. After even a single explicit edit, the
 * warning self-resolves. A master who genuinely runs only 60-min services
 * can ignore the prompt — no harm done.
 */
export default function MissingDurationWarning({ onGotoServices }) {
  const { t } = useI18n();
  const { data: services } = useQuery({
    queryKey: ['master-services'],
    queryFn: getMasterServices,
    staleTime: 15_000,
  });

  const needsAttention =
    services &&
    services.length > 0 &&
    services.every((s) => (s.duration_minutes ?? 60) === 60);

  if (!needsAttention) return null;

  return (
    <section
      style={{
        background: '#fff7e0',
        borderRadius: 12,
        padding: 12,
        marginBottom: 12,
        fontSize: 13,
      }}
    >
      <strong>⚠ {t('autobooking.missingDuration.title')}</strong>
      <p style={{ margin: '6px 0' }}>{t('autobooking.missingDuration.body')}</p>
      <button
        onClick={onGotoServices}
        style={{
          background: 'transparent',
          border: 'none',
          color: '#1a73e8',
          padding: 0,
          fontSize: 13,
          cursor: 'pointer',
        }}
      >
        {t('autobooking.missingDuration.cta')} →
      </button>
    </section>
  );
}
