import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMe, getOrders, getBonuses } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';
import { useI18n } from '../i18n';
const WebApp = window.Telegram?.WebApp;

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
    day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit'
  });
}

const BONUS_ICONS = {
  accrual:  { icon: '+', color: '#4caf50' },
  spend:    { icon: '−', color: '#f44336' },
  birthday: { icon: '★', color: '#ffd700' },
  manual:   { icon: '✎', color: '#2196f3' },
  promo:    { icon: '◆', color: '#9c27b0' },
};

export default function Home({ onNavigate, masters = [], activeMasterId, onMasterChange }) {
  const { t, locale } = useI18n();
  const qc = useQueryClient();
  const [showMasterPicker, setShowMasterPicker] = useState(false);

  const { data: me, isLoading: meLoading, error: meError, refetch: refetchMe } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const { data: orders = [], isLoading: ordersLoading } = useQuery({ queryKey: ['orders'], queryFn: getOrders });
  const { data: bonuses, isLoading: bonusesLoading } = useQuery({ queryKey: ['bonuses'], queryFn: getBonuses });

  if (meError) return <ErrorScreen message={meError.message} onRetry={refetchMe} />;

  const now = new Date();
  const upcoming = orders
    .filter(o => (o.status === 'new' || o.status === 'confirmed') && new Date(o.scheduled_at) > now)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];

  const recentBonuses = bonuses?.log?.slice(0, 3) || [];

  const initials = me?.client?.name
    ? me.client.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  const multiMaster = masters.length > 1;

  return (
    <div style={{ padding: '16px 16px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>{t('home.welcome')}</p>
          {meLoading
            ? <Skeleton width={140} height={22} style={{ marginTop: 4 }} />
            : <h2 style={{ fontSize: 20, fontWeight: 700 }}>{me?.client?.name || t('common.dash')}</h2>
          }
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => qc.invalidateQueries()}
            style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
            title={t('common.refresh')}
          >↻</button>
          <div style={{
            width: 42, height: 42, borderRadius: '50%',
            background: 'var(--tg-button)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--tg-button-text)', fontWeight: 700, fontSize: 16,
            flexShrink: 0,
          }}>
            {initials}
          </div>
        </div>
      </div>

      {/* Balance card */}
      <div style={{
        background: 'var(--tg-surface)',
        borderRadius: 20,
        padding: '20px',
        marginBottom: 16,
      }}>
        <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 4 }}>{t('home.bonusBalance')}</p>
        {bonusesLoading
          ? <Skeleton width={100} height={36} style={{ marginBottom: 8 }} />
          : <p style={{ fontSize: 36, fontWeight: 800, color: 'var(--tg-accent)', lineHeight: 1.1 }}>
              {bonuses?.balance ?? 0} ₽
            </p>
        }
        {meLoading
          ? <Skeleton width={160} height={16} style={{ marginTop: 8 }} />
          : <>
              {/* Clickable master name if multi-master */}
              <div
                onClick={multiMaster ? () => setShowMasterPicker(true) : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  marginTop: 8,
                  cursor: multiMaster ? 'pointer' : 'default',
                }}
              >
                <p style={{ color: 'var(--tg-hint)', fontSize: 13 }}>
                  {t('home.masterPrefix', { name: me?.master?.name || t('common.dash') })}
                </p>
                {multiMaster && (
                  <span style={{ color: 'var(--tg-hint)', fontSize: 11 }}>▼</span>
                )}
              </div>
              {me?.master?.sphere && (
                <span style={{
                  display: 'inline-block', marginTop: 6,
                  background: 'rgba(79,156,249,0.15)', color: 'var(--tg-accent)',
                  borderRadius: 20, padding: '2px 10px', fontSize: 12
                }}>
                  {me.master.sphere}
                </span>
              )}
            </>
        }
      </div>

      {/* Upcoming order */}
      {ordersLoading
        ? <Skeleton height={80} radius={16} style={{ marginBottom: 16 }} />
        : upcoming && (
          <div style={{
            background: 'var(--tg-surface)',
            borderRadius: 16, padding: '16px',
            marginBottom: 16,
            borderLeft: '3px solid var(--tg-accent)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 13, color: 'var(--tg-accent)' }}>
                📅 {formatDate(upcoming.scheduled_at, locale)}
              </span>
              <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
                {relativeDate(upcoming.scheduled_at, t)}
              </span>
            </div>
            <p style={{ fontWeight: 600 }}>{upcoming.services || t('home.serviceNotSpecified')}</p>
            {upcoming.address && (
              <p style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 2 }}>{upcoming.address}</p>
            )}
          </div>
        )
      }

      {/* Recent bonus operations */}
      {recentBonuses.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 10 }}>{t('home.recentOperations')}</p>
          {recentBonuses.map((op, i) => {
            const { icon, color } = BONUS_ICONS[op.type] || { icon: '•', color: 'var(--tg-hint)' };
            const sign = op.amount > 0 ? '+' : '';
            return (
              <div key={op.id ?? i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0',
                borderBottom: i < recentBonuses.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ color, fontSize: 18, width: 20, textAlign: 'center' }}>{icon}</span>
                  <span style={{ fontSize: 14 }}>{op.comment || op.type}</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color, fontWeight: 600 }}>{sign}{op.amount} ₽</span>
                  <p style={{ fontSize: 12, color: 'var(--tg-hint)' }}>
                    {op.created_at
                      ? new Date(op.created_at).toLocaleDateString(locale, { day: 'numeric', month: 'long' })
                      : ''}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Master picker bottom sheet */}
      {showMasterPicker && (
        <div
          onClick={() => setShowMasterPicker(false)}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex', alignItems: 'flex-end',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: 'var(--tg-bg)',
              width: '100%',
              borderRadius: '16px 16px 0 0',
              padding: '20px 16px 40px',
            }}
          >
            <p style={{ fontWeight: 700, fontSize: 16, marginBottom: 16 }}>{t('home.switchMaster')}</p>
            {masters.map((m, i) => (
              <div
                key={m.master_id}
                onClick={() => {
                  onMasterChange(m.master_id);
                  qc.invalidateQueries();
                  setShowMasterPicker(false);
                }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 0',
                  borderBottom: i < masters.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                  cursor: 'pointer',
                }}
              >
                <div style={{
                  width: 36, height: 36, borderRadius: '50%',
                  background: m.master_id === activeMasterId ? 'var(--tg-button)' : 'var(--tg-surface)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: m.master_id === activeMasterId ? 'var(--tg-button-text)' : 'var(--tg-text)',
                  fontWeight: 700, fontSize: 15,
                  flexShrink: 0,
                }}>
                  {(m.master_name || '?')[0].toUpperCase()}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: m.master_id === activeMasterId ? 700 : 400 }}>
                    {m.master_name}
                  </p>
                  {m.sphere && (
                    <p style={{ fontSize: 12, color: 'var(--tg-hint)' }}>{m.sphere}</p>
                  )}
                </div>
                {m.master_id === activeMasterId && (
                  <span style={{ color: 'var(--tg-accent)', fontSize: 18 }}>✓</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
