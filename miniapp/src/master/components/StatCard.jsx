export default function StatCard({ icon, value, label }) {
  return (
    <div style={{
      background: 'var(--tg-surface)',
      borderRadius: 'var(--radius-card)',
      padding: '14px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      minWidth: 0,
    }}>
      <div style={{ fontSize: 20, lineHeight: 1 }}>{icon}</div>
      <div style={{
        color: 'var(--tg-text)',
        fontSize: 18,
        fontWeight: 700,
        lineHeight: 1.2,
        marginTop: 4,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {value}
      </div>
      <div style={{
        color: 'var(--tg-hint)',
        fontSize: 11,
        lineHeight: 1.3,
      }}>
        {label}
      </div>
    </div>
  );
}
