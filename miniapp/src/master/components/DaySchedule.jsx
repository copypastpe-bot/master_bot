import OrderCard from './OrderCard';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function formatDate(dateStr, locale) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' });
}

export default function DaySchedule({ dateStr, orders, loading, onOrderClick, onCreateOrder }) {
  const { tr, locale } = useI18n();
  const dateLabel = dateStr ? formatDate(dateStr, locale) : '';
  const totalOrders = Array.isArray(orders) ? orders.length : 0;
  const ordersLabel = tr(
    `${totalOrders} ${(() => {
      const n = Math.abs(totalOrders) % 100;
      const n1 = n % 10;
      if (n > 10 && n < 20) return 'заказов';
      if (n1 > 1 && n1 < 5) return 'заказа';
      if (n1 === 1) return 'заказ';
      return 'заказов';
    })()}`,
    `${totalOrders} ${totalOrders === 1 ? 'order' : 'orders'}`
  );

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
              {loading ? tr('Загрузка...', 'Loading...') : ordersLabel}
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
            {tr('+ Запись', '+ Booking')}
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
                {tr('На этот день заказов пока нет', 'No orders for this day yet')}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
