import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import MasterNav from './components/MasterNav';
import Dashboard from './pages/Dashboard';
import Calendar from './pages/Calendar';
import OrderDetail from './pages/OrderDetail';
import OrderCreate from './pages/OrderCreate';
import Broadcast from './pages/Broadcast';
import More from './pages/More';
import ClientsList from './pages/ClientsList';
import ClientCard from './pages/ClientCard';
import Profile from './pages/Profile';
import BonusSettings from './pages/BonusSettings';
import Services from './pages/Services';
import PromosList from './pages/PromosList';
import PromoCreate from './pages/PromoCreate';
import PromoCard from './pages/PromoCard';
import Reports from './pages/Reports';

const WebApp = window.Telegram?.WebApp;

// ---------------------------------------------------------------------------
// Screen-title map for Back button context
// ---------------------------------------------------------------------------
const SCREEN_TITLES = {
  order: 'Заказ',
  create_order: 'Новый заказ',
  clients: 'Клиенты',
  client: 'Клиент',
  profile: 'Профиль',
  bonus: 'Бонусная программа',
  services: 'Услуги',
  promos: 'Акции',
  promo_new: 'Новая акция',
  promo: 'Акция',
  reports: 'Аналитика',
};

export default function MasterApp() {
  const [tab, setTab] = useState('home');
  // navStack: array of { type, id?, ...params }
  // Empty stack = tab root. Push = navigate forward. Pop = back.
  const [navStack, setNavStack] = useState([]);

  const queryClient = useQueryClient();

  // ---------------------------------------------------------------------------
  // Telegram BackButton integration
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const BackButton = WebApp?.BackButton;
    if (!BackButton) return;

    if (navStack.length > 0) {
      BackButton.show();
      const handler = () => handleBack();
      BackButton.onClick(handler);
      return () => BackButton.offClick(handler);
    } else {
      BackButton.hide();
    }
  }, [navStack]);

  // ---------------------------------------------------------------------------
  // Navigation helpers
  // ---------------------------------------------------------------------------
  const push = (type, params = {}) => {
    setNavStack(prev => [...prev, { type, ...params }]);
  };

  const handleBack = () => {
    setNavStack(prev => prev.slice(0, -1));
  };

  const switchTab = (newTab) => {
    setNavStack([]);
    setTab(newTab);
  };

  // ---------------------------------------------------------------------------
  // React Query invalidation helpers
  // ---------------------------------------------------------------------------
  const invalidateOrders = () => {
    queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['master-calendar'] });
    queryClient.invalidateQueries({ queryKey: ['master-orders'] });
    queryClient.invalidateQueries({ queryKey: ['master-reports'] });
  };

  const handleOrderUpdated = () => invalidateOrders();

  const handleOrderCreated = (order) => {
    invalidateOrders();
    setNavStack([]);
    if (order?.scheduled_at?.slice(0, 10)) {
      setTab('calendar');
    }
  };

  // ---------------------------------------------------------------------------
  // Render current screen based on navStack top
  // ---------------------------------------------------------------------------
  const current = navStack[navStack.length - 1];

  if (current) {
    const { type, id, ...rest } = current;

    if (type === 'order') {
      return (
        <OrderDetail orderId={id} onBack={handleBack} onUpdated={handleOrderUpdated} />
      );
    }

    if (type === 'create_order') {
      return (
        <OrderCreate params={current} onBack={handleBack} onCreated={handleOrderCreated} />
      );
    }

    if (type === 'clients') {
      return (
        <div>
          <PageHeader title="Клиенты" onBack={handleBack} />
          <ClientsList onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'client') {
      return (
        <div>
          <PageHeader title="Клиент" onBack={handleBack} />
          <ClientCard
            clientId={id}
            onBack={handleBack}
            onNavigate={(t, p) => push(t, p)}
          />
        </div>
      );
    }

    if (type === 'profile') {
      return (
        <div>
          <PageHeader title="Профиль мастера" onBack={handleBack} />
          <Profile />
        </div>
      );
    }

    if (type === 'bonus') {
      return (
        <div>
          <PageHeader title="Бонусная программа" onBack={handleBack} />
          <BonusSettings />
        </div>
      );
    }

    if (type === 'services') {
      return (
        <div>
          <PageHeader title="Справочник услуг" onBack={handleBack} />
          <Services />
        </div>
      );
    }

    if (type === 'promos') {
      return (
        <div>
          <PageHeader title="Акции" onBack={handleBack} />
          <PromosList onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'promo_new') {
      return (
        <div>
          <PageHeader title="Новая акция" onBack={handleBack} />
          <PromoCreate onBack={handleBack} onCreated={() => { handleBack(); }} />
        </div>
      );
    }

    if (type === 'promo') {
      // Find promo data from query cache or pass id
      const promosData = queryClient.getQueryData(['master-promos']);
      const allPromos = [...(promosData?.active || []), ...(promosData?.past || [])];
      const promo = allPromos.find(p => p.id === id);
      if (!promo) {
        return (
          <div>
            <PageHeader title="Акция" onBack={handleBack} />
            <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
              Не найдено
            </div>
          </div>
        );
      }
      return (
        <div>
          <PageHeader title="Акция" onBack={handleBack} />
          <PromoCard promo={promo} onBack={handleBack} />
        </div>
      );
    }

    if (type === 'reports') {
      return (
        <div>
          <PageHeader title="Аналитика" onBack={handleBack} />
          <Reports initialPeriod={current.period || 'month'} />
        </div>
      );
    }

    // Fallback
    return (
      <div style={{ padding: '24px 16px' }}>
        <button onClick={handleBack} style={{ background: 'none', border: 'none', color: 'var(--tg-accent)', fontSize: 15, cursor: 'pointer', padding: 0, marginBottom: 16 }}>
          ← Назад
        </button>
        <p style={{ color: 'var(--tg-hint)', textAlign: 'center', marginTop: 48 }}>Скоро</p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Tab root screens
  // ---------------------------------------------------------------------------
  const renderTab = () => {
    switch (tab) {
      case 'home':
        return <Dashboard onNavigate={(t, p) => push(t, p)} />;
      case 'calendar':
        return <Calendar onNavigate={(t, p) => push(t, p)} />;
      case 'marketing':
        return <Broadcast />;
      case 'more':
        return <More onNavigate={(t, p) => push(t, p)} />;
      default:
        return <Dashboard onNavigate={(t, p) => push(t, p)} />;
    }
  };

  return (
    <div>
      {renderTab()}
      <MasterNav active={tab} onNavigate={switchTab} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Simple page header with back button (shown when WebApp BackButton unavailable)
// ---------------------------------------------------------------------------
function PageHeader({ title, onBack }) {
  const hasBackButton = typeof WebApp?.BackButton?.show === 'function';
  if (hasBackButton) {
    // Telegram BackButton handles navigation — show just the title
    return (
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--tg-secondary-bg)',
        fontSize: 17,
        fontWeight: 600,
        color: 'var(--tg-text)',
        background: 'var(--tg-bg)',
      }}>
        {title}
      </div>
    );
  }
  // Fallback: show manual back button
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '12px 16px',
      borderBottom: '1px solid var(--tg-secondary-bg)',
      background: 'var(--tg-bg)',
    }}>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--tg-accent)', fontSize: 20, cursor: 'pointer', padding: '0 4px 0 0', lineHeight: 1 }}>‹</button>
      <div style={{ fontSize: 17, fontWeight: 600, color: 'var(--tg-text)' }}>{title}</div>
    </div>
  );
}
