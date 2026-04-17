import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getBonuses, getOrders } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';
import { useI18n } from '../i18n';

const BONUS_ICONS = {
  accrual: { icon: '+', color: '#4caf50' },
  spend: { icon: '−', color: '#f44336' },
  birthday: { icon: '★', color: '#ffd700' },
  manual: { icon: '✎', color: '#2196f3' },
  promo: { icon: '◆', color: '#9c27b0' },
};

const STATUS_ICONS = {
  done: { icon: '✅' },
  cancelled: { icon: '❌' },
  new: { icon: '📅' },
  confirmed: { icon: '📅' },
  moved: { icon: '🔄' },
};

function RefreshButton({ title, onClick }) {
  return (
    <button className="client-home-refresh-btn" onClick={onClick} title={title} aria-label={title}>
      ↻
    </button>
  );
}

export default function Bonuses() {
  const { t, locale } = useI18n();
  const [tab, setTab] = useState('bonuses');
  const qc = useQueryClient();

  const { data: bonuses, isLoading: bLoading, error: bError, refetch: refetchB } = useQuery({
    queryKey: ['bonuses'],
    queryFn: getBonuses,
  });
  const { data: orders = [], isLoading: oLoading, error: oError, refetch: refetchO } = useQuery({
    queryKey: ['orders'],
    queryFn: getOrders,
  });

  if (bError) return <ErrorScreen message={bError.message} onRetry={refetchB} />;
  if (oError) return <ErrorScreen message={oError.message} onRetry={refetchO} />;

  const log = bonuses?.log || [];

  return (
    <div className="client-page client-bonuses-page">
      <header className="client-page-header client-bonuses-header">
        <div>
          <h1 className="client-page-title">{t('bonuses.title')}</h1>
          <p className="client-page-subtitle">{t('bonuses.balance')}</p>
        </div>
        <RefreshButton title={t('common.refresh')} onClick={() => qc.invalidateQueries()} />
      </header>

      <section className="client-contact-content client-bonuses-content">
        <div className="client-card client-bonuses-tabs">
          {[
            ['bonuses', t('bonuses.tabs.bonuses')],
            ['history', t('bonuses.tabs.history')],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`client-bonuses-tab${tab === id ? ' is-active' : ''}`}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'bonuses' && (
          <>
            <section className="client-card client-bonuses-balance-card">
              <p className="client-home-kicker">{t('bonuses.balance')}</p>
              {bLoading ? (
                <Skeleton width={140} height={52} style={{ margin: '8px auto 0' }} />
              ) : (
                <p className="client-bonuses-balance-value">{bonuses?.balance ?? 0} ₽</p>
              )}
            </section>

            <p className="client-section-title">{t('home.recentOperations')}</p>
            {bLoading ? (
              <div className="client-card client-bonuses-list-card">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} height={54} style={{ marginBottom: i < 2 ? 10 : 0 }} />
                ))}
              </div>
            ) : log.length === 0 ? (
              <div className="client-card client-bonuses-empty-card">
                <p className="client-home-empty-title">{t('bonuses.noOperations')}</p>
              </div>
            ) : (
              <section className="client-card client-bonuses-list-card">
                {log.map((op, i) => {
                  const { icon, color } = BONUS_ICONS[op.type] || { icon: '•', color: 'var(--tg-hint)' };
                  const sign = op.amount > 0 ? '+' : '';
                  return (
                    <div
                      key={op.id ?? i}
                      className={`client-bonuses-row${i < log.length - 1 ? ' has-border' : ''}`}
                    >
                      <div className="client-bonuses-row-meta">
                        <span className="client-bonuses-row-icon" style={{ color, backgroundColor: `${color}20` }}>
                          {icon}
                        </span>
                        <div>
                          <p className="client-bonuses-row-title">{op.comment || op.type}</p>
                          <p className="client-bonuses-row-subtitle">
                            {op.created_at
                              ? new Date(op.created_at).toLocaleDateString(locale, {
                                  day: 'numeric',
                                  month: 'long',
                                })
                              : ''}
                          </p>
                        </div>
                      </div>
                      <span className="client-bonuses-row-amount" style={{ color }}>
                        {sign}
                        {op.amount} ₽
                      </span>
                    </div>
                  );
                })}
              </section>
            )}
          </>
        )}

        {tab === 'history' && (
          <>
            <p className="client-section-title">{t('bonuses.tabs.history')}</p>
            {oLoading ? (
              <div className="client-card client-bonuses-list-card">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} height={62} style={{ marginBottom: i < 2 ? 10 : 0 }} />
                ))}
              </div>
            ) : orders.length === 0 ? (
              <div className="client-card client-bonuses-empty-card">
                <p className="client-home-empty-title">{t('bonuses.noOrders')}</p>
              </div>
            ) : (
              <section className="client-card client-bonuses-list-card">
                {orders.map((order, i) => {
                  const { icon } = STATUS_ICONS[order.status] || { icon: '•' };
                  return (
                    <div
                      key={order.id}
                      className={`client-bonuses-row${i < orders.length - 1 ? ' has-border' : ''}`}
                    >
                      <div className="client-bonuses-row-meta">
                        <span className="client-bonuses-row-icon is-order">{icon}</span>
                        <div>
                          <p className="client-bonuses-row-title">
                            {order.scheduled_at
                              ? new Date(order.scheduled_at).toLocaleDateString(locale, {
                                  day: 'numeric',
                                  month: 'short',
                                })
                              : t('common.dash')}
                            {' · '}
                            {order.services || t('bonuses.serviceDefault')}
                          </p>
                          {order.amount_total != null && (
                            <p className="client-bonuses-row-subtitle">{order.amount_total} ₽</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </section>
            )}
          </>
        )}
      </section>
    </div>
  );
}
