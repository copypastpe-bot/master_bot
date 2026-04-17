import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMe, getOrders, getBonuses } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';
import { useI18n } from '../i18n';

function relativeDate(dateStr, t) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((date - now) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return t('home.relative.today');
  if (diffDays === 1) return t('home.relative.tomorrow');
  if (diffDays > 1) return t('home.relative.inDays', { count: diffDays });
  return '';
}

function formatDate(dateStr, locale) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString(locale, {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const BONUS_ICONS = {
  accrual: { icon: '+', color: '#4caf50' },
  spend: { icon: '−', color: '#f44336' },
  birthday: { icon: '★', color: '#ffd700' },
  manual: { icon: '✎', color: '#2196f3' },
  promo: { icon: '◆', color: '#9c27b0' },
};

function RefreshButton({ title, onClick }) {
  return (
    <button className="client-home-refresh-btn" onClick={onClick} title={title} aria-label={title}>
      ↻
    </button>
  );
}

export default function Home({ masters = [], activeMasterId, onMasterChange }) {
  const { t, locale } = useI18n();
  const qc = useQueryClient();
  const [showMasterPicker, setShowMasterPicker] = useState(false);

  const { data: me, isLoading: meLoading, error: meError, refetch: refetchMe } = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
  });
  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: getOrders,
  });
  const { data: bonuses, isLoading: bonusesLoading } = useQuery({
    queryKey: ['bonuses'],
    queryFn: getBonuses,
  });

  if (meError) return <ErrorScreen message={meError.message} onRetry={refetchMe} />;

  const now = new Date();
  const upcoming = orders
    .filter((o) => (o.status === 'new' || o.status === 'confirmed') && new Date(o.scheduled_at) > now)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];

  const recentBonuses = bonuses?.log?.slice(0, 3) || [];
  const initials = me?.client?.name
    ? me.client.name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';
  const masterName = me?.master?.name || t('common.dash');
  const multiMaster = masters.length > 1;

  return (
    <div className="client-page client-home-page">
      <header className="client-page-header client-home-header">
        <div>
          <p className="client-page-subtitle">{t('home.welcome')}</p>
          {meLoading ? (
            <Skeleton width={160} height={28} style={{ marginTop: 6 }} />
          ) : (
            <h1 className="client-page-title">{me?.client?.name || t('common.dash')}</h1>
          )}
        </div>

        <div className="client-home-header-actions">
          <RefreshButton title={t('common.refresh')} onClick={() => qc.invalidateQueries()} />
          <div className="client-home-avatar">{initials}</div>
        </div>
      </header>

      <section className="client-card client-home-hero-card">
        <div className="client-home-balance-row">
          <div>
            <p className="client-home-kicker">{t('home.bonusBalance')}</p>
            {bonusesLoading ? (
              <Skeleton width={132} height={44} style={{ marginTop: 8 }} />
            ) : (
              <p className="client-home-balance-value">{bonuses?.balance ?? 0} ₽</p>
            )}
          </div>
          <div className="client-home-balance-badge">CRM</div>
        </div>

        {meLoading ? (
          <Skeleton width={190} height={18} style={{ marginTop: 18 }} />
        ) : (
          <button
            className={`client-home-master-row${multiMaster ? ' is-interactive' : ''}`}
            onClick={multiMaster ? () => setShowMasterPicker(true) : undefined}
            type="button"
          >
            <span className="client-home-master-label">{t('home.masterPrefix', { name: masterName })}</span>
            {multiMaster && <span className="client-home-master-chevron">▼</span>}
          </button>
        )}

        {me?.master?.sphere && (
          <div className="client-home-tags">
            <span className="client-pill">{me.master.sphere}</span>
          </div>
        )}
      </section>

      <p className="client-section-title">{t('home.upcoming')}</p>
      {ordersLoading ? (
        <div className="client-card client-home-upcoming-card">
          <Skeleton height={84} radius={18} />
        </div>
      ) : upcoming ? (
        <section className="client-card client-home-upcoming-card">
          <div className="client-home-upcoming-topline">
            <span className="client-home-upcoming-date">📅 {formatDate(upcoming.scheduled_at, locale)}</span>
            <span className="client-home-upcoming-relative">{relativeDate(upcoming.scheduled_at, t)}</span>
          </div>
          <h2 className="client-home-upcoming-title">{upcoming.services || t('home.serviceNotSpecified')}</h2>
          {upcoming.address && <p className="client-home-upcoming-address">{upcoming.address}</p>}
        </section>
      ) : (
        <div className="client-card client-home-empty-card">
          <p className="client-home-empty-title">{t('home.serviceNotSpecified')}</p>
          <p className="client-home-empty-subtitle">{t('app.noMasters.subtitle')}</p>
        </div>
      )}

      {recentBonuses.length > 0 && (
        <>
          <p className="client-section-title">{t('home.recentOperations')}</p>
          <section className="client-card client-home-log-card">
            {recentBonuses.map((op, i) => {
              const { icon, color } = BONUS_ICONS[op.type] || { icon: '•', color: 'var(--tg-hint)' };
              const sign = op.amount > 0 ? '+' : '';
              return (
                <div
                  key={op.id ?? i}
                  className={`client-home-log-item${i < recentBonuses.length - 1 ? ' has-border' : ''}`}
                >
                  <div className="client-home-log-meta">
                    <span className="client-home-log-icon" style={{ color, backgroundColor: `${color}20` }}>
                      {icon}
                    </span>
                    <div>
                      <p className="client-home-log-title">{op.comment || op.type}</p>
                      <p className="client-home-log-date">
                        {op.created_at
                          ? new Date(op.created_at).toLocaleDateString(locale, { day: 'numeric', month: 'long' })
                          : ''}
                      </p>
                    </div>
                  </div>
                  <div className="client-home-log-amount" style={{ color }}>
                    {sign}
                    {op.amount} ₽
                  </div>
                </div>
              );
            })}
          </section>
        </>
      )}

      {showMasterPicker && (
        <div className="client-home-sheet-overlay" onClick={() => setShowMasterPicker(false)}>
          <div className="client-home-sheet" onClick={(e) => e.stopPropagation()}>
            <p className="client-home-sheet-title">{t('home.switchMaster')}</p>
            <div className="client-home-sheet-list">
              {masters.map((m) => (
                <button
                  key={m.master_id}
                  type="button"
                  className={`client-home-sheet-item${m.master_id === activeMasterId ? ' is-active' : ''}`}
                  onClick={() => {
                    onMasterChange(m.master_id);
                    qc.invalidateQueries();
                    setShowMasterPicker(false);
                  }}
                >
                  <span className="client-home-sheet-avatar">{(m.master_name || '?')[0].toUpperCase()}</span>
                  <span className="client-home-sheet-copy">
                    <span className="client-home-sheet-name">{m.master_name}</span>
                    {m.sphere && <span className="client-home-sheet-sphere">{m.sphere}</span>}
                  </span>
                  {m.master_id === activeMasterId && <span className="client-home-sheet-check">✓</span>}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
