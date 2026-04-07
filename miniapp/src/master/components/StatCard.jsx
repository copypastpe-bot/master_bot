export default function StatCard({ icon, value, label, onClick }) {
  const isClickable = typeof onClick === 'function';

  return (
    <div
      onClick={isClickable ? onClick : undefined}
      style={{
        background: 'var(--tg-surface)',
        border: '1px solid var(--tg-enterprise-border)',
        boxShadow: 'var(--tg-enterprise-shadow)',
        borderRadius: 'var(--radius-card)',
        padding: '14px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        minWidth: 0,
        cursor: isClickable ? 'pointer' : 'default',
        position: 'relative',
        transition: 'transform 140ms ease, box-shadow 140ms ease',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
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
      {isClickable && (
        <span style={{
          position: 'absolute',
          top: 10,
          right: 10,
          color: 'var(--tg-hint)',
          fontSize: 16,
          lineHeight: 1,
        }}>›</span>
      )}
    </div>
  );
}
