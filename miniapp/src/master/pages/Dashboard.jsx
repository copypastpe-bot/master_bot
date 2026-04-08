import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterDashboard,
  getMasterSubscription,
  trackMasterReferralLinkCopied,
  updateMasterProfile,
} from '../../api/client';
import { Skeleton } from '../../components/Skeleton';
import StatCard from '../components/StatCard';
import OrderCard from '../components/OrderCard';
import SubscriptionPaywallSheet from '../components/SubscriptionPaywallSheet';

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

function OrdersSection({ title, orders, onNavigate, emptyContent }) {
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
          {emptyContent ?? 'Свободный день! 🎉'}
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
              onClick={() => onNavigate('order', { id: order.id })}
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
  const { data: subscription } = useQuery({
    queryKey: ['master-subscription'],
    queryFn: getMasterSubscription,
    retry: 1,
    staleTime: 20_000,
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

  return <DashboardContent data={data} subscription={subscription} onNavigate={onNavigate} />;
}

function DashboardContent({ data, subscription, onNavigate }) {
  const queryClient = useQueryClient();
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [paywallOpen, setPaywallOpen] = useState(false);

  const dismissBannerMutation = useMutation({
    mutationFn: () => updateMasterProfile({ onboarding_banner_shown: true }),
    onSuccess: () => {
      setBannerDismissed(true);
      queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    },
  });

  const stats = data?.stats || {};
  const today = new Date();
  const totalDoneOrders = data?.total_done_orders ?? 0;
  const todayOrders = data?.today_orders || [];
  const tomorrowOrders = data?.tomorrow_orders || [];
  const showBanner = !bannerDismissed && (data?.onboarding_banner?.show === true);
  const isSubscriptionActive = subscription?.is_active ?? true;

  const handleNewOrder = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    if (!isSubscriptionActive) {
      setPaywallOpen(true);
      return;
    }
    onNavigate('create_order');
  };

  const handlePaywallPay = () => {
    setPaywallOpen(false);
    onNavigate('subscription');
  };

  const handlePaywallInvite = async () => {
    const link = subscription?.referral_link || queryClient.getQueryData(['master-subscription'])?.referral_link;
    if (!link) {
      setPaywallOpen(false);
      onNavigate('subscription');
      return;
    }
    try {
      if (typeof navigator?.clipboard?.writeText === 'function') {
        await navigator.clipboard.writeText(link);
      }
    } catch (_) {
      // non-critical
    }
    trackMasterReferralLinkCopied('dashboard-paywall').catch(() => {});
    if (typeof WebApp?.showAlert === 'function') {
      WebApp.showAlert('Ссылка скопирована');
    }
    setPaywallOpen(false);
  };

  const handleRequests = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('requests');
  };

  const handleReportsWeek = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('reports', { period: 'week' });
  };

  const handleReportsMonth = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('reports', { period: 'month' });
  };

  const handleClients = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('clients');
  };

  const handleBannerDismiss = () => {
    dismissBannerMutation.mutate();
  };

  const handleBannerAdd = () => {
    handleNewOrder();
    dismissBannerMutation.mutate();
  };

  return (
    <div style={{ padding: '16px 16px 100px' }}>
      {/* Onboarding banner */}
      {showBanner && (
        <div style={{
          background: 'var(--tg-secondary-bg)',
          border: '1px solid var(--tg-enterprise-border)',
          borderRadius: 'var(--radius-card)',
          padding: '12px 14px',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <p style={{
            flex: 1,
            color: 'var(--tg-text)',
            fontSize: 13,
            margin: 0,
            lineHeight: 1.4,
          }}>
            Добавь первого клиента, чтобы увидеть как работают напоминания
          </p>
          <button
            onClick={handleBannerAdd}
            style={{
              background: 'var(--tg-button)',
              color: 'var(--tg-button-text)',
              border: 'none',
              borderRadius: 8,
              padding: '7px 12px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Добавить →
          </button>
          <button
            onClick={handleBannerDismiss}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--tg-hint)',
              fontSize: 18,
              cursor: 'pointer',
              padding: '0 2px',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Block 1: Greeting */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <h2 style={{
            color: 'var(--tg-text)',
            fontSize: 20,
            fontWeight: 700,
            margin: 0,
          }}>
            Привет, {data?.master_name || ''}!
          </h2>
          <span style={{ color: isSubscriptionActive ? '#2f74d2' : '#888888', fontSize: 24, lineHeight: 1 }}>
            ★
          </span>
        </div>
        <p style={{
          color: 'var(--tg-hint)',
          fontSize: 13,
          margin: 0,
        }}>
          {formatDate(today)}
        </p>
      </div>

      {/* Block 2: KPI or motivational block */}
      {totalDoneOrders > 0 ? (
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
            onClick={handleReportsWeek}
          />
          <StatCard
            icon="📅"
            value={formatCurrency(stats.month_revenue || 0)}
            label="Выручка за месяц"
            onClick={handleReportsMonth}
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
            onClick={handleClients}
          />
        </div>
      ) : (
        <div style={{
          background: 'var(--tg-secondary-bg)',
          border: '1px solid var(--tg-enterprise-border)',
          borderRadius: 'var(--radius-card)',
          padding: '16px',
          marginBottom: 24,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
        }}>
          <span style={{ fontSize: 24, lineHeight: 1 }}>📊</span>
          <p style={{
            color: 'var(--tg-hint)',
            fontSize: 14,
            margin: 0,
            lineHeight: 1.4,
          }}>
            Выполни первый заказ и увидишь показатели своей работы в цифрах
          </p>
        </div>
      )}

      {/* Block 3: Today's orders */}
      <OrdersSection
        title="Сегодня"
        orders={todayOrders}
        onNavigate={onNavigate}
        emptyContent={
          totalDoneOrders === 0 && todayOrders.length === 0 && tomorrowOrders.length === 0
            ? (
              <div>
                <p style={{ margin: '0 0 10px', color: 'var(--tg-hint)' }}>
                  Пока записей нет
                </p>
                <button
                  onClick={handleNewOrder}
                  style={{
                    background: isSubscriptionActive ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                    color: isSubscriptionActive ? 'var(--tg-button-text)' : 'var(--tg-hint)',
                    border: isSubscriptionActive ? 'none' : '1px solid var(--tg-enterprise-border)',
                    borderRadius: 8,
                    padding: '8px 16px',
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  + Добавить первую запись
                </button>
              </div>
            )
            : todayOrders.length === 0
              ? 'Записей на сегодня нет'
              : null
        }
      />

      {/* Block 4: Tomorrow's orders */}
      <OrdersSection
        title="Завтра"
        orders={tomorrowOrders}
        onNavigate={onNavigate}
        emptyContent="Записей на завтра нет"
      />

      {/* Block 5: Quick actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button
          onClick={handleNewOrder}
          style={{
            background: isSubscriptionActive ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
            color: isSubscriptionActive ? 'var(--tg-button-text)' : 'var(--tg-hint)',
            border: isSubscriptionActive ? 'none' : '1px solid var(--tg-enterprise-border)',
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
              color: 'var(--tg-button)',
              border: '1.5px solid var(--tg-button)',
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

      <SubscriptionPaywallSheet
        open={paywallOpen}
        onClose={() => setPaywallOpen(false)}
        onPay={handlePaywallPay}
        onInvite={handlePaywallInvite}
      />
    </div>
  );
}
