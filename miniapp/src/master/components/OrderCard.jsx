const WebApp = window.Telegram?.WebApp;

// Status colors follow Telegram's semantic palette; these are Telegram's own accent values
const STATUS_COLORS = {
  new: '#3390EC',
  confirmed: '#31B545',
  done: '#999999',
  cancelled: '#E53935',
};

export default function OrderCard({ order, onClick, style }) {
  const statusColor = STATUS_COLORS[order.status] || '#999999';

  const handleClick = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    if (onClick) onClick(order);
  };

  return (
    <div
      onClick={handleClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 0',
        borderBottom: '1px solid rgba(128,128,128,0.1)',
        cursor: 'pointer',
        userSelect: 'none',
        ...style,
      }}
    >
      {/* Time */}
      <div style={{
        minWidth: 40,
        color: 'var(--tg-text)',
        fontSize: 14,
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        flexShrink: 0,
      }}>
        {order.time || '—'}
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          color: 'var(--tg-text)',
          fontSize: 14,
          fontWeight: 500,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {order.client_name}
        </div>
        {order.services ? (
          <div style={{
            color: 'var(--tg-hint)',
            fontSize: 12,
            marginTop: 2,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {order.services}
          </div>
        ) : null}
      </div>

      {/* Status dot */}
      <div style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: statusColor,
        flexShrink: 0,
      }} />
    </div>
  );
}
