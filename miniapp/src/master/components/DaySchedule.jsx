import OrderCard from './OrderCard';

const WebApp = window.Telegram?.WebApp;

const WEEKDAY_NAMES = [
  'Воскресенье', 'Понедельник', 'Вторник', 'Среда',
  'Четверг', 'Пятница', 'Суббота',
];

const MONTH_NAMES_GENITIVE = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const weekday = WEEKDAY_NAMES[d.getDay()];
  const day = d.getDate();
  const month = MONTH_NAMES_GENITIVE[d.getMonth()];
  return `${weekday}, ${day} ${month}`;
}

function ordersWord(count) {
  const n = Math.abs(count) % 100;
  const n1 = n % 10;
  if (n > 10 && n < 20) return 'заказов';
  if (n1 > 1 && n1 < 5) return 'заказа';
  if (n1 === 1) return 'заказ';
  return 'заказов';
}

export default function DaySchedule({ dateStr, orders, loading, onOrderClick, onCreateOrder }) {
  const dateLabel = dateStr ? formatDate(dateStr) : '';
  const totalOrders = Array.isArray(orders) ? orders.length : 0;

  const handleCreateOrder = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    if (onCreateOrder) onCreateOrder();
  };

  return (
    <div style={{ padding: '4px 12px 100px' }}>
      <div
        style={{
          background: 'var(--tg-surface)',
          border: '1px solid var(--tg-enterprise-border)',
          borderRadius: 'var(--radius-card)',
          boxShadow: 'var(--tg-enterprise-shadow)',
          padding: '14px 14px 10px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            marginBottom: 8,
            opacity: loading ? 0.4 : 1,
            transition: 'opacity 0.2s',
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontSize: 17,
                fontWeight: 700,
                color: 'var(--tg-text)',
                lineHeight: 1.2,
              }}
            >
              {dateLabel}
            </div>
            <div
              style={{
                color: 'var(--tg-hint)',
                fontSize: 12,
                fontWeight: 600,
                marginTop: 3,
              }}
            >
              {loading ? 'Загрузка...' : `${totalOrders} ${ordersWord(totalOrders)}`}
            </div>
          </div>

          <button
            onClick={handleCreateOrder}
            style={{
              background: 'var(--tg-button)',
              color: 'var(--tg-button-text)',
              border: 'none',
              borderRadius: 11,
              padding: '10px 12px',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            + Запись
          </button>
        </div>

        <div style={{ opacity: loading ? 0.4 : 1, transition: 'opacity 0.2s' }}>
          {loading ? (
            [1, 2, 3].map((i) => (
              <div
                key={i}
                style={{
                  height: 52,
                  borderRadius: 8,
                  background: 'rgba(128,128,128,0.1)',
                  marginBottom: 8,
                  animation: 'skeleton-pulse 1.5s ease-in-out infinite',
                }}
              />
            ))
          ) : orders && orders.length > 0 ? (
            orders.map((order) => (
              <OrderCard
                key={order.id}
                order={order}
                onClick={(o) => onOrderClick && onOrderClick(o.id)}
              />
            ))
          ) : (
            <div style={{ textAlign: 'center', paddingTop: 38, paddingBottom: 20 }}>
              <div style={{ fontSize: 34, marginBottom: 10, opacity: 0.4 }}>
                📅
              </div>
              <div style={{ color: 'var(--tg-hint)', fontSize: 14 }}>
                На этот день заказов пока нет
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
