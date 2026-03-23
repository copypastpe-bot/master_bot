import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMe, getOrders, getBonuses } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';
const WebApp = window.Telegram?.WebApp;

function relativeDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((date - now) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Сегодня';
  if (diffDays === 1) return 'Завтра';
  if (diffDays > 1) return `Через ${diffDays} дн.`;
  return '';
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('ru-RU', {
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

export default function Home({ onNavigate }) {
  const qc = useQueryClient();
  const { data: me, isLoading: meLoading, error: meError, refetch: refetchMe } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const { data: orders = [], isLoading: ordersLoading } = useQuery({ queryKey: ['orders'], queryFn: getOrders });
  const { data: bonuses, isLoading: bonusesLoading } = useQuery({ queryKey: ['bonuses'], queryFn: getBonuses });

  // DEBUG: show initData status (remove after debugging)
  const initDataLen = WebApp?.initData?.length ?? 0;

  if (meError) return (
    <>
      <div style={{ background: '#222', color: '#fff', padding: '8px 16px', fontSize: 12, fontFamily: 'monospace' }}>
        DEBUG: initData.length={initDataLen} | error={meError.message}
      </div>
      <ErrorScreen message={meError.message} onRetry={refetchMe} />
    </>
  );

  // Nearest upcoming order
  const now = new Date();
  const upcoming = orders
    .filter(o => (o.status === 'new' || o.status === 'confirmed') && new Date(o.scheduled_at) > now)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];

  // Last 3 bonus operations
  const recentBonuses = bonuses?.log?.slice(0, 3) || [];

  // Avatar initials from client name
  const initials = me?.client?.name
    ? me.client.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  return (
    <div style={{ padding: '16px 16px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Добро пожаловать</p>
          {meLoading
            ? <Skeleton width={140} height={22} style={{ marginTop: 4 }} />
            : <h2 style={{ fontSize: 20, fontWeight: 700 }}>{me?.client?.name || '—'}</h2>
          }
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => qc.invalidateQueries()}
            style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
            title="Обновить"
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
        <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 4 }}>Бонусный баланс</p>
        {bonusesLoading
          ? <Skeleton width={100} height={36} style={{ marginBottom: 8 }} />
          : <p style={{ fontSize: 36, fontWeight: 800, color: 'var(--tg-accent)', lineHeight: 1.1 }}>
              {bonuses?.balance ?? 0} ₽
            </p>
        }
        {meLoading
          ? <Skeleton width={160} height={16} style={{ marginTop: 8 }} />
          : <>
              <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginTop: 8 }}>
                Мастер: {me?.master?.name || '—'}
              </p>
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
                📅 {formatDate(upcoming.scheduled_at)}
              </span>
              <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
                {relativeDate(upcoming.scheduled_at)}
              </span>
            </div>
            <p style={{ fontWeight: 600 }}>{upcoming.services || 'Услуга не указана'}</p>
            {upcoming.address && (
              <p style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 2 }}>{upcoming.address}</p>
            )}
          </div>
        )
      }

      {/* Recent bonus operations */}
      {recentBonuses.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 10 }}>Последние операции</p>
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
                      ? new Date(op.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
                      : ''}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
