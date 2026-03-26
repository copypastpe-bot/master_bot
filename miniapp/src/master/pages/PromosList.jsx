import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMasterPromos } from '../../api/client';

const WebApp = window.Telegram?.WebApp;
function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

function fmtDate(str) {
  if (!str) return '—';
  try {
    const d = new Date(str + 'T00:00:00');
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
  } catch { return str; }
}

function PromoCard({ promo, active, onClick }) {
  return (
    <div
      onClick={() => { haptic(); onClick(promo.id); }}
      style={{
        padding: '14px 16px',
        background: 'var(--tg-section-bg)',
        marginBottom: 1,
        cursor: 'pointer',
        opacity: active ? 1 : 0.6,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--tg-text)', marginBottom: 4 }}>
            {promo.title}
          </div>
          <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
            {fmtDate(promo.active_from)} — {fmtDate(promo.active_to)}
          </div>
          {promo.sent_count > 0 && (
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 4 }}>
              Уведомлено: {promo.sent_count} кл.
            </div>
          )}
        </div>
        <span style={{
          fontSize: 11, fontWeight: 600,
          color: active ? '#4caf50' : 'var(--tg-hint)',
          background: active ? '#4caf5022' : 'var(--tg-secondary-bg)',
          padding: '3px 8px', borderRadius: 6, flexShrink: 0,
        }}>
          {active ? 'Активна' : 'Завершена'}
        </span>
      </div>
    </div>
  );
}

export default function PromosList({ onNavigate }) {
  const [pastExpanded, setPastExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['master-promos'],
    queryFn: getMasterPromos,
    staleTime: 30_000,
  });

  if (isLoading) {
    return <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>Загрузка...</div>;
  }
  if (error) {
    return <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>Ошибка загрузки</div>;
  }

  const active = data?.active || [];
  const past = data?.past || [];

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Create button */}
      <div style={{ padding: '16px' }}>
        <button
          onClick={() => { haptic(); onNavigate('promo_new'); }}
          style={{
            width: '100%', padding: '13px',
            background: 'var(--tg-accent)', color: '#fff',
            borderRadius: 12, fontSize: 15, fontWeight: 600,
            border: 'none', cursor: 'pointer',
          }}
        >
          + Создать акцию
        </button>
      </div>

      {/* Active promos */}
      {active.length === 0 ? (
        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
          Нет активных акций
        </div>
      ) : (
        <div>
          <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
            Активные ({active.length})
          </div>
          {active.map(p => (
            <PromoCard key={p.id} promo={p} active={true} onClick={(id) => onNavigate('promo', { id })} />
          ))}
        </div>
      )}

      {/* Past promos */}
      {past.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div
            onClick={() => { haptic(); setPastExpanded(e => !e); }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', background: 'var(--tg-section-bg)',
              borderBottom: '1px solid var(--tg-secondary-bg)', cursor: 'pointer',
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-hint)' }}>
              Прошедшие ({past.length})
            </div>
            <span style={{
              color: 'var(--tg-hint)', fontSize: 16,
              transform: pastExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s',
            }}>▶</span>
          </div>
          {pastExpanded && past.map(p => (
            <PromoCard key={p.id} promo={p} active={false} onClick={(id) => onNavigate('promo', { id })} />
          ))}
        </div>
      )}
    </div>
  );
}
