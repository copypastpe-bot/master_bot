import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TrendingUp, CalendarDays, CheckCircle2, Users, BarChart3 } from 'lucide-react';
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
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function formatCurrency(amount, locale) {
  return new Intl.NumberFormat(locale, {
    style: 'decimal',
    maximumFractionDigits: 0,
  }).format(amount) + ' ₽';
}

function formatDate(d, locale) {
  return d.toLocaleDateString(locale, { weekday: 'short', day: 'numeric', month: 'long' });
}

function OrdersSection({ title, orders, onNavigate, emptyContent, tr }) {
  return (
    <div className="enterprise-orders-section">
      <div className="enterprise-orders-header">
        <div className="enterprise-orders-title">{title}</div>
        {orders.length > 0 && (
          <span className="enterprise-orders-count">
            {tr(`${orders.length} зап.`, `${orders.length} bookings`)}
          </span>
        )}
      </div>

      {orders.length === 0 ? (
        <div className="enterprise-orders-card">
          <div className="enterprise-orders-empty">
            {emptyContent ?? tr('Свободный день! 🎉', 'Free day! 🎉')}
          </div>
        </div>
      ) : (
        <div className="enterprise-orders-card">
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
    <div className="enterprise-page">
      <div className="enterprise-page-inner" style={{ marginBottom: 20 }}>
        <Skeleton height={24} style={{ width: '55%', marginBottom: 6 }} />
        <Skeleton height={14} style={{ width: '35%' }} />
      </div>
      <div className="enterprise-stat-grid">
        <Skeleton height={80} />
        <Skeleton height={80} />
        <Skeleton height={80} />
        <Skeleton height={80} />
      </div>
      <div className="enterprise-section-title" style={{ visibility: 'hidden' }}>—</div>
      <div className="enterprise-cell-group" style={{ marginBottom: 20 }}>
        <Skeleton height={64} />
      </div>
      <div className="enterprise-section-title" style={{ visibility: 'hidden' }}>—</div>
      <div className="enterprise-cell-group">
        <Skeleton height={64} />
      </div>
    </div>
  );
}

export default function Dashboard({ onNavigate }) {
  const { tr } = useI18n();
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
      <div className="enterprise-page">
        <div className="enterprise-page-inner" style={{ textAlign: 'center', paddingTop: 48 }}>
          <p style={{ color: 'var(--tg-text)', marginBottom: 8 }}>
            {tr('Не удалось загрузить данные', 'Failed to load data')}
          </p>
          <button
            className="enterprise-btn-primary"
            onClick={() => { WebApp?.HapticFeedback?.impactOccurred?.('light'); refetch(); }}
          >
            {tr('Повторить', 'Retry')}
          </button>
        </div>
      </div>
    );
  }

  return <DashboardContent data={data} subscription={subscription} onNavigate={onNavigate} />;
}

function DashboardContent({ data, subscription, onNavigate }) {
  const { tr, locale } = useI18n();
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
      WebApp.showAlert(tr('Ссылка скопирована', 'Link copied'));
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
    <div className="enterprise-page">
      {/* Onboarding banner */}
      {showBanner && (
        <div className="enterprise-info-card" style={{ alignItems: 'center', gap: 10 }}>
          <p style={{ flex: 1, color: 'var(--tg-text)', fontSize: 13, margin: 0, lineHeight: 1.4 }}>
            {tr('Добавь первого клиента, чтобы увидеть как работают напоминания', 'Add your first client to see how reminders work')}
          </p>
          <button
            onClick={handleBannerAdd}
            className="enterprise-btn-banner-action"
          >
            {tr('Добавить →', 'Add ->')}
          </button>
          <button
            onClick={handleBannerDismiss}
            className="enterprise-btn-dismiss"
          >
            ×
          </button>
        </div>
      )}

      {/* Greeting */}
      <div className="enterprise-page-inner" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <h2 className="enterprise-page-title">
            {tr('Привет', 'Hello')}, {data?.master_name || ''}!
          </h2>
          <span style={{ color: isSubscriptionActive ? '#2f74d2' : '#888888', fontSize: 24, lineHeight: 1 }}>★</span>
        </div>
        <p className="enterprise-page-subtitle">{formatDate(today, locale)}</p>
      </div>

      {/* Stats */}
      {totalDoneOrders > 0 ? (
        <div className="enterprise-stat-grid">
          <StatCard icon={<TrendingUp size={20} />} value={formatCurrency(stats.week_revenue || 0, locale)} label={tr('Выручка за неделю', 'Revenue this week')} onClick={handleReportsWeek} />
          <StatCard icon={<CalendarDays size={20} />} value={formatCurrency(stats.month_revenue || 0, locale)} label={tr('Выручка за месяц', 'Revenue this month')} onClick={handleReportsMonth} />
          <StatCard icon={<CheckCircle2 size={20} />} value={stats.week_orders || 0} label={tr('Заказов за неделю', 'Orders this week')} />
          <StatCard icon={<Users size={20} />} value={stats.total_clients || 0} label={tr('Всего клиентов', 'Total clients')} onClick={handleClients} />
        </div>
      ) : (
        <div className="enterprise-info-card">
          <span style={{ color: 'var(--tg-hint)', display: 'inline-flex' }}><BarChart3 size={24} /></span>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: 0, lineHeight: 1.4 }}>
            {tr('Выполни первый заказ и увидишь показатели своей работы в цифрах', 'Complete your first order to see your performance in numbers')}
          </p>
        </div>
      )}

      {/* Today's orders */}
      <OrdersSection
        title={tr('Сегодня', 'Today')}
        orders={todayOrders}
        onNavigate={onNavigate}
        tr={tr}
        emptyContent={
          totalDoneOrders === 0 && todayOrders.length === 0 && tomorrowOrders.length === 0
            ? (
              <div>
                <p style={{ margin: '0 0 10px', color: 'var(--tg-hint)' }}>
                  {tr('Пока записей нет', 'No bookings yet')}
                </p>
                <button
                  onClick={handleNewOrder}
                  style={{
                    background: isSubscriptionActive ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                    color: isSubscriptionActive ? 'var(--tg-button-text)' : 'var(--tg-hint)',
                    border: isSubscriptionActive ? 'none' : '1px solid var(--tg-enterprise-border)',
                    borderRadius: 8, padding: '8px 16px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  {tr('+ Добавить первую запись', '+ Add first booking')}
                </button>
              </div>
            )
            : todayOrders.length === 0
              ? tr('Записей на сегодня нет', 'No bookings for today')
              : null
        }
      />

      {/* Tomorrow's orders */}
      <OrdersSection
        title={tr('Завтра', 'Tomorrow')}
        orders={tomorrowOrders}
        onNavigate={onNavigate}
        tr={tr}
        emptyContent={tr('Записей на завтра нет', 'No bookings for tomorrow')}
      />

      {/* Actions */}
      <div className="enterprise-actions">
        <button
          className="enterprise-btn-primary"
          onClick={handleNewOrder}
          style={!isSubscriptionActive ? { background: 'var(--tg-secondary-bg)', color: 'var(--tg-hint)', border: '1px solid var(--tg-enterprise-border)' } : {}}
        >
          {tr('+ Новый заказ', '+ New order')}
        </button>

        {(stats.pending_requests || 0) > 0 && (
          <button
            onClick={handleRequests}
            className="enterprise-btn-outline"
          >
            {tr(`Новые заявки (${stats.pending_requests})`, `New requests (${stats.pending_requests})`)}
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
