import { useQuery } from '@tanstack/react-query';
import { getMasterDashboard } from '../../api/client';
import { Skeleton } from '../../components/Skeleton';
import StatCard from '../components/StatCard';
import OrderCard from '../components/OrderCard';

const WebApp = window.Telegram?.WebApp;

const WEEKDAYS = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
const MONTHS = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];

function formatCurrency(amount) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'decimal',
    maximumFractionDigits: 0,
  }).format(amount) + ' ₽';
}

function formatDate(d) {
  const dayName = WEEKDAYS[d.getDay()];
  // Capitalise first letter
  const dayNameCap = dayName.charAt(0).toUpperCase() + dayName.slice(1);
  return `${dayNameCap}, ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

function OrdersSection({ title, orders, onNavigate }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
      }}>
        <h3 style={{
          color: 'var(--tg-text)',
          fontSize: 16,
          fontWeight: 600,
          margin: 0,
        }}>
          {title}
        </h3>
        <span style={{
          color: 'var(--tg-hint)',
          fontSize: 13,
        }}>
          {orders.length > 0 ? `${orders.length} зап.` : ''}
        </span>
      </div>

      {orders.length === 0 ? (
        <div style={{
          background: 'var(--tg-surface)',
          borderRadius: 'var(--radius-card)',
          padding: '14px 16px',
          color: 'var(--tg-hint)',
          fontSize: 14,
          textAlign: 'center',
        }}>
          Свободный день! 🎉
        </div>
      ) : (
        <div style={{
          background: 'var(--tg-surface)',
          borderRadius: 'var(--radius-card)',
          padding: '0 16px',
        }}>
          {orders.map((order, idx) => (
            <OrderCard
              key={order.id}
              order={order}
              onClick={() => onNavigate('order', order.id)}
              style={idx === orders.length - 1 ? { borderBottom: 'none' } : {}}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div style={{ padding: '16px 16px 100px' }}>
      <Skeleton height={24} style={{ width: '50%', marginBottom: 6 }} />
      <Skeleton height={14} style={{ width: '35%', marginBottom: 24 }} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 24 }}>
        <Skeleton height={80} />
        <Skeleton height={80} />
        <Skeleton height={80} />
        <Skeleton height={80} />
      </div>

      <Skeleton height={18} style={{ width: '30%', marginBottom: 10 }} />
      <Skeleton height={64} style={{ marginBottom: 24 }} />

      <Skeleton height={18} style={{ width: '30%', marginBottom: 10 }} />
      <Skeleton height={64} />
    </div>
  );
}

export default function Dashboard({ onNavigate }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['master-dashboard'],
    queryFn: getMasterDashboard,
    retry: 1,
    staleTime: 30_000,
  });

  if (isLoading) return <DashboardSkeleton />;

  if (isError) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 24px' }}>
        <p style={{ color: 'var(--tg-text)', marginBottom: 8 }}>
          Не удалось загрузить данные
        </p>
        <button
          onClick={() => {
            if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
              WebApp.HapticFeedback.impactOccurred('light');
            }
            refetch();
          }}
          style={{
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 10,
            padding: '10px 24px',
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          Повторить
        </button>
      </div>
    );
  }

  const stats = data?.stats || {};
  const today = new Date();

  const handleNewOrder = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('create_order');
  };

  const handleRequests = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('requests');
  };

  return (
    <div style={{ padding: '16px 16px 100px' }}>
      {/* Block 1: Greeting */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{
          color: 'var(--tg-text)',
          fontSize: 20,
          fontWeight: 700,
          margin: 0,
          marginBottom: 4,
        }}>
          Привет, {data?.master_name || ''}!
        </h2>
        <p style={{
          color: 'var(--tg-hint)',
          fontSize: 13,
          margin: 0,
        }}>
          {formatDate(today)}
        </p>
      </div>

      {/* Block 2: Stats 2x2 grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 8,
        marginBottom: 24,
      }}>
        <StatCard
          icon="💰"
          value={formatCurrency(stats.week_revenue || 0)}
          label="Выручка за неделю"
        />
        <StatCard
          icon="📅"
          value={formatCurrency(stats.month_revenue || 0)}
          label="Выручка за месяц"
        />
        <StatCard
          icon="✅"
          value={stats.week_orders || 0}
          label="Заказов за неделю"
        />
        <StatCard
          icon="👥"
          value={stats.total_clients || 0}
          label="Всего клиентов"
        />
      </div>

      {/* Block 3: Today's orders */}
      <OrdersSection
        title="Сегодня"
        orders={data?.today_orders || []}
        onNavigate={onNavigate}
      />

      {/* Block 4: Tomorrow's orders */}
      <OrdersSection
        title="Завтра"
        orders={data?.tomorrow_orders || []}
        onNavigate={onNavigate}
      />

      {/* Block 5: Quick actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button
          onClick={handleNewOrder}
          style={{
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            padding: '14px',
            fontSize: 15,
            fontWeight: 600,
            cursor: 'pointer',
            width: '100%',
          }}
        >
          + Новый заказ
        </button>

        {(stats.pending_requests || 0) > 0 && (
          <button
            onClick={handleRequests}
            style={{
              background: 'var(--tg-surface)',
              color: '#3390EC',
              border: '1.5px solid #3390EC',
              borderRadius: 12,
              padding: '14px',
              fontSize: 15,
              fontWeight: 600,
              cursor: 'pointer',
              width: '100%',
            }}
          >
            Новые заявки ({stats.pending_requests})
          </button>
        )}
      </div>
    </div>
  );
}
