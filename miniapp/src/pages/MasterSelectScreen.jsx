import { useI18n } from '../i18n';

export default function MasterSelectScreen({ masters, onSelect }) {
  const { t, locale } = useI18n();

  return (
    <div className="client-page client-master-select-page">
      <header className="client-page-header client-master-select-header">
        <div>
          <h1 className="client-page-title">{t('masterSelect.title')}</h1>
          <p className="client-page-subtitle">{t('masterSelect.subtitle')}</p>
        </div>
      </header>

      <section className="client-contact-content client-master-select-content">
        <div className="client-master-select-list">
          {masters.map((m) => {
            const initial = (m.master_name || '?')[0].toUpperCase();
            const lastDate = m.last_visit
              ? new Date(m.last_visit).toLocaleDateString(locale, {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                })
              : null;

            return (
              <button
                key={m.master_id}
                type="button"
                className="client-card client-master-select-card"
                onClick={() => onSelect(m.master_id)}
              >
                <span className="client-master-select-avatar">{initial}</span>

                <span className="client-master-select-copy">
                  <span className="client-master-select-name">
                    {m.master_name}
                    {m.pending_count > 0 && (
                      <span className="client-master-badge">{m.pending_count}</span>
                    )}
                  </span>

                  {m.sphere && (
                    <span className="client-pill client-master-select-pill">{m.sphere}</span>
                  )}

                  <span className="client-master-select-meta">
                    <span>{t('masterSelect.bonus', { amount: m.bonus_balance ?? 0 })}</span>
                    <span>{t('masterSelect.visits', { count: m.order_count ?? 0 })}</span>
                  </span>

                  {lastDate && (
                    <span className="client-master-select-last">
                      {t('masterSelect.lastVisit', { date: lastDate })}
                    </span>
                  )}
                </span>

                <span className="client-master-select-chevron">›</span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
