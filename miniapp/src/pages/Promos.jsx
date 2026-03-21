import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getPromos } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

function formatActiveTo(dateStr) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  });
}

export default function Promos({ onNavigate }) {
  const qc = useQueryClient();
  const { data: promos = [], isLoading, error, refetch } = useQuery({
    queryKey: ['promos'],
    queryFn: getPromos,
  });

  if (error) return <ErrorScreen message={error.message} onRetry={refetch} />;

  return (
    <div style={{ padding: '16px 16px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Акции</h2>
        <button
          onClick={() => qc.invalidateQueries()}
          style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', cursor: 'pointer', fontSize: 20 }}
        >↻</button>
      </div>

      {isLoading ? (
        [...Array(2)].map((_, i) => (
          <Skeleton key={i} height={120} radius={16} style={{ marginBottom: 12 }} />
        ))
      ) : promos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🎁</div>
          <p style={{ fontWeight: 600, marginBottom: 8 }}>Акций пока нет.</p>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Следите за обновлениями!</p>
        </div>
      ) : (
        promos.map(promo => (
          <div key={promo.id} style={{
            background: 'var(--tg-surface)',
            borderRadius: 16, padding: '16px', marginBottom: 12,
          }}>
            <h3 style={{ marginBottom: 8 }}>{promo.title}</h3>
            {promo.text && (
              <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 8, lineHeight: 1.5 }}>
                {promo.text}
              </p>
            )}
            {promo.active_to && (
              <p style={{ fontSize: 12, color: 'var(--tg-accent)' }}>
                До {formatActiveTo(promo.active_to)}
              </p>
            )}
          </div>
        ))
      )}
    </div>
  );
}
