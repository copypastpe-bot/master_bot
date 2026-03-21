import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getBonuses, getOrders } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

const BONUS_ICONS = {
  accrual:  { icon: '+', color: '#4caf50' },
  spend:    { icon: '−', color: '#f44336' },
  birthday: { icon: '★', color: '#ffd700' },
  manual:   { icon: '✎', color: '#2196f3' },
  promo:    { icon: '◆', color: '#9c27b0' },
};

const STATUS_ICONS = {
  done:      { icon: '✅' },
  cancelled: { icon: '❌' },
  new:       { icon: '📅' },
  confirmed: { icon: '📅' },
  moved:     { icon: '🔄' },
};

export default function Bonuses({ onNavigate }) {
  const [tab, setTab] = useState('bonuses');
  const qc = useQueryClient();

  const { data: bonuses, isLoading: bLoading, error: bError, refetch: refetchB } = useQuery({ queryKey: ['bonuses'], queryFn: getBonuses });
  const { data: orders = [], isLoading: oLoading, error: oError, refetch: refetchO } = useQuery({ queryKey: ['orders'], queryFn: getOrders });

  if (bError) return <ErrorScreen message={bError.message} onRetry={refetchB} />;
  if (oError) return <ErrorScreen message={oError.message} onRetry={refetchO} />;

  const log = bonuses?.log || [];

  return (
    <div style={{ padding: '16px 16px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Бонусы</h2>
        <button
          onClick={() => qc.invalidateQueries()}
          style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
        >↻</button>
      </div>

      {/* Tab switcher */}
      <div style={{
        display: 'flex', background: 'var(--tg-surface)',
        borderRadius: 12, padding: 3, marginBottom: 20,
      }}>
        {[['bonuses', 'Бонусы'], ['history', 'История']].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              flex: 1, padding: '9px', border: 'none', borderRadius: 10,
              background: tab === id ? 'var(--tg-button)' : 'transparent',
              color: tab === id ? 'var(--tg-button-text)' : 'var(--tg-hint)',
              cursor: 'pointer', fontSize: 14, fontWeight: tab === id ? 600 : 400,
              transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Bonuses tab */}
      {tab === 'bonuses' && (
        <>
          <div style={{
            background: 'var(--tg-surface)',
            borderRadius: 20, padding: '20px', marginBottom: 20, textAlign: 'center',
          }}>
            <p style={{ color: 'var(--tg-hint)', fontSize: 13, marginBottom: 4 }}>Баланс</p>
            {bLoading
              ? <Skeleton width={120} height={44} style={{ margin: '0 auto' }} />
              : <p style={{ fontSize: 44, fontWeight: 800, color: 'var(--tg-accent)' }}>
                  {bonuses?.balance ?? 0} ₽
                </p>
            }
          </div>

          {bLoading
            ? [...Array(3)].map((_, i) => <Skeleton key={i} height={50} style={{ marginBottom: 8 }} />)
            : log.length === 0
              ? <p style={{ color: 'var(--tg-hint)', textAlign: 'center', padding: '24px 0' }}>Операций нет</p>
              : log.map((op, i) => {
                  const { icon, color } = BONUS_ICONS[op.type] || { icon: '•', color: 'var(--tg-hint)' };
                  const sign = op.amount > 0 ? '+' : '';
                  return (
                    <div key={op.id ?? i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 0',
                      borderBottom: i < log.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{
                          color, fontSize: 18, width: 30, height: 30,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          background: color + '20', borderRadius: '50%', flexShrink: 0,
                        }}>{icon}</span>
                        <div>
                          <p style={{ fontSize: 14 }}>{op.comment || op.type}</p>
                          <p style={{ fontSize: 12, color: 'var(--tg-hint)' }}>
                            {op.created_at
                              ? new Date(op.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
                              : ''}
                          </p>
                        </div>
                      </div>
                      <span style={{ color, fontWeight: 700, flexShrink: 0 }}>{sign}{op.amount} ₽</span>
                    </div>
                  );
                })
          }
        </>
      )}

      {/* History tab */}
      {tab === 'history' && (
        <>
          {oLoading
            ? [...Array(3)].map((_, i) => <Skeleton key={i} height={60} style={{ marginBottom: 8 }} />)
            : orders.length === 0
              ? <p style={{ color: 'var(--tg-hint)', textAlign: 'center', padding: '24px 0' }}>Заказов нет</p>
              : orders.map((order, i) => {
                  const { icon } = STATUS_ICONS[order.status] || { icon: '•' };
                  return (
                    <div key={order.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 0',
                      borderBottom: i < orders.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                    }}>
                      <div>
                        <p style={{ fontSize: 14, fontWeight: 500 }}>
                          {order.scheduled_at
                            ? new Date(order.scheduled_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
                            : '—'}
                          {'  '}{order.services || 'Услуга'}
                        </p>
                        {order.amount_total != null && (
                          <p style={{ fontSize: 13, color: 'var(--tg-hint)' }}>{order.amount_total} ₽</p>
                        )}
                      </div>
                      <span style={{ fontSize: 18 }}>{icon}</span>
                    </div>
                  );
                })
          }
        </>
      )}
    </div>
  );
}
