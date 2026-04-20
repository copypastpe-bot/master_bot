export default function StatCard({ icon, value, label, onClick }) {
  const isClickable = typeof onClick === 'function';

  return (
    <div
      onClick={isClickable ? onClick : undefined}
      style={{
        background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.025))',
        border: '1px solid var(--tg-enterprise-border)',
        boxShadow: 'var(--tg-enterprise-shadow)',
        borderRadius: 'var(--radius-card)',
        padding: '15px 13px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        minWidth: 0,
        cursor: isClickable ? 'pointer' : 'default',
        position: 'relative',
        transition: 'transform 140ms ease, box-shadow 140ms ease',
        WebkitTapHighlightColor: 'transparent',
        backdropFilter: 'blur(14px)',
        overflow: 'hidden',
      }}
    >
      <div style={{
        width: 36,
        height: 36,
        borderRadius: 12,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(79, 156, 249, 0.12)',
        color: 'var(--tg-accent)',
      }}>
        {icon}
      </div>
      <div style={{
        color: 'var(--tg-text)',
        fontSize: 18,
        fontWeight: 700,
        lineHeight: 1.2,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {value}
      </div>
      <div style={{
        color: 'var(--tg-hint)',
        fontSize: 12,
        lineHeight: 1.35,
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
