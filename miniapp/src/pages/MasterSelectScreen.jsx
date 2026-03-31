export default function MasterSelectScreen({ masters, onSelect }) {
  return (
    <div style={{ padding: '16px 16px 24px' }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Выберите мастера</h2>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 20 }}>
        Вы подключены к нескольким мастерам
      </p>
      {masters.map((m) => {
        const initial = (m.master_name || '?')[0].toUpperCase();
        const lastDate = m.last_visit
          ? new Date(m.last_visit).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
          : null;
        return (
          <div
            key={m.master_id}
            onClick={() => onSelect(m.master_id)}
            style={{
              background: 'var(--tg-surface)',
              borderRadius: 16,
              padding: '16px',
              marginBottom: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              cursor: 'pointer',
            }}
          >
            <div style={{
              width: 48, height: 48, borderRadius: '50%',
              background: 'var(--tg-button)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--tg-button-text)', fontWeight: 700, fontSize: 20,
              flexShrink: 0,
            }}>
              {initial}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontWeight: 600, fontSize: 16 }}>{m.master_name}</p>
              {m.sphere && (
                <span style={{
                  display: 'inline-block', marginTop: 4,
                  background: 'rgba(79,156,249,0.15)', color: 'var(--tg-accent)',
                  borderRadius: 20, padding: '2px 8px', fontSize: 12,
                }}>
                  {m.sphere}
                </span>
              )}
              <div style={{ display: 'flex', gap: 16, marginTop: 6 }}>
                <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
                  💎 {m.bonus_balance ?? 0} ₽
                </span>
                <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
                  📋 {m.order_count ?? 0} визитов
                </span>
              </div>
              {lastDate && (
                <p style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
                  Последний визит: {lastDate}
                </p>
              )}
            </div>
            <span style={{ color: 'var(--tg-hint)', fontSize: 20 }}>›</span>
          </div>
        );
      })}
    </div>
  );
}
