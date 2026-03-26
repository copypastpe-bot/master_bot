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
  // dateStr: "2026-03-24"
  const d = new Date(dateStr + 'T00:00:00');
  const weekday = WEEKDAY_NAMES[d.getDay()];
  const day = d.getDate();
  const month = MONTH_NAMES_GENITIVE[d.getMonth()];
  return `${weekday}, ${day} ${month}`;
}

export default function DaySchedule({ dateStr, orders, loading, onOrderClick, onCreateOrder }) {
  const dateLabel = dateStr ? formatDate(dateStr) : '';

  const handleCreateOrder = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    if (onCreateOrder) onCreateOrder();
  };

  return (
    <div style={{ padding: '0 16px 100px' }}>
      {/* Date heading */}
      <div style={{
        padding: '16px 0 12px',
        fontSize: 15,
        fontWeight: 600,
        color: 'var(--tg-text)',
        opacity: loading ? 0.4 : 1,
        transition: 'opacity 0.2s',
      }}>
        {dateLabel}
      </div>

      {/* Orders list */}
      <div style={{
        opacity: loading ? 0.4 : 1,
        transition: 'opacity 0.2s',
      }}>
        {loading ? (
          // Skeleton placeholders
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
          <div style={{
            textAlign: 'center',
            paddingTop: 48,
            paddingBottom: 24,
          }}>
            <div style={{
              fontSize: 36,
              marginBottom: 12,
              opacity: 0.4,
            }}>
              📅
            </div>
            <div style={{
              color: 'var(--tg-hint)',
              fontSize: 14,
              marginBottom: 20,
            }}>
              Нет заказов
            </div>
            <button
              onClick={handleCreateOrder}
              style={{
                background: 'var(--tg-button)',
                color: 'var(--tg-button-text)',
                border: 'none',
                borderRadius: 10,
                padding: '10px 24px',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              + Создать
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
