import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getPromos } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';
import { useI18n } from '../i18n';

function formatActiveTo(dateStr, locale) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function RefreshButton({ title, onClick }) {
  return (
    <button className="client-home-refresh-btn" onClick={onClick} title={title} aria-label={title}>
      ↻
    </button>
  );
}

export default function Promos() {
  const { t, locale } = useI18n();
  const qc = useQueryClient();
  const { data: promos = [], isLoading, error, refetch } = useQuery({
    queryKey: ['promos'],
    queryFn: getPromos,
  });

  if (error) return <ErrorScreen message={error.message} onRetry={refetch} />;

  return (
    <div className="client-page client-promos-page">
      <header className="client-page-header client-promos-header">
        <div>
          <h1 className="client-page-title">{t('promos.title')}</h1>
          <p className="client-page-subtitle">{t('promos.empty.subtitle')}</p>
        </div>
        <RefreshButton title={t('common.refresh')} onClick={() => qc.invalidateQueries()} />
      </header>

      <section className="client-contact-content client-promos-content">
        {isLoading ? (
          <div className="client-promos-list">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="client-card client-promos-card">
                <Skeleton height={18} width="54%" style={{ marginBottom: 12 }} />
                <Skeleton height={14} style={{ marginBottom: 8 }} />
                <Skeleton height={14} width="82%" />
              </div>
            ))}
          </div>
        ) : promos.length === 0 ? (
          <div className="client-card client-promos-empty-card">
            <div className="client-promos-empty-icon">🎁</div>
            <p className="client-home-empty-title">{t('promos.empty.title')}</p>
            <p className="client-home-empty-subtitle">{t('promos.empty.subtitle')}</p>
          </div>
        ) : (
          <div className="client-promos-list">
            {promos.map((promo) => (
              <article key={promo.id} className="client-card client-promos-card">
                <div className="client-promos-card-topline">
                  <span className="client-pill">{t('promos.title')}</span>
                  {promo.active_to && (
                    <span className="client-promos-card-date">
                      {t('promos.activeTo', { date: formatActiveTo(promo.active_to, locale) })}
                    </span>
                  )}
                </div>

                <h2 className="client-promos-card-title">{promo.title}</h2>

                {promo.text && (
                  <p className="client-promos-card-text">{promo.text}</p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
