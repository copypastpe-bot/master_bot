import { useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import MasterNav from './components/MasterNav';
import { getMasterRequestsUnreadCount } from '../api/client';
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
import BonusMessageEditor from './pages/BonusMessageEditor';
import Services from './pages/Services';
import PromosList from './pages/PromosList';
import PromoCreate from './pages/PromoCreate';
import PromoCard from './pages/PromoCard';
import Reports from './pages/Reports';
import Requests from './pages/Requests';
import Subscription from './pages/Subscription';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

export default function MasterApp() {
  const { t } = useI18n();
  const [tab, setTab] = useState('home');
  // navStack: array of { type, id?, ...params }
  // Empty stack = tab root. Push = navigate forward. Pop = back.
  const [navStack, setNavStack] = useState([]);
  const [requestsBadge, setRequestsBadge] = useState(0);

  const queryClient = useQueryClient();

  const refreshBadge = useCallback(async () => {
    try {
      const data = await getMasterRequestsUnreadCount();
      setRequestsBadge(data.count ?? 0);
    } catch {
      // badge is best-effort
    }
  }, []);

  useEffect(() => { refreshBadge(); }, []);

  useEffect(() => {
    document.body.classList.add('typeui-enterprise-body');
    return () => {
      document.body.classList.remove('typeui-enterprise-body');
    };
  }, []);

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
    queryClient.invalidateQueries({ queryKey: ['masterOrderDates'] });
    queryClient.invalidateQueries({ queryKey: ['masterOrders'] });
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
        <div className="master-shell">
          <OrderDetail
            orderId={id}
            onBack={handleBack}
            onUpdated={handleOrderUpdated}
            onNavigate={(t, p) => push(t, p)}
          />
        </div>
      );
    }

    if (type === 'create_order') {
      return (
        <div className="master-shell">
          <OrderCreate params={current} onBack={handleBack} onCreated={handleOrderCreated} />
        </div>
      );
    }

    if (type === 'clients') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.clients')} onBack={handleBack} />
          <ClientsList onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'client') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.client')} onBack={handleBack} />
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
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.profile')} onBack={handleBack} />
          <Profile />
        </div>
      );
    }

    if (type === 'bonus') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.bonus')} onBack={handleBack} />
          <BonusSettings onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'bonus_message') {
      const title = current.kind === 'birthday'
        ? t('masterApp.titles.bonusBirthday')
        : t('masterApp.titles.bonusWelcome');
      return (
        <div className="master-shell">
          <PageHeader title={title} onBack={handleBack} />
          <BonusMessageEditor kind={current.kind || 'welcome'} />
        </div>
      );
    }

    if (type === 'services') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.services')} onBack={handleBack} />
          <Services />
        </div>
      );
    }

    if (type === 'promos') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.promos')} onBack={handleBack} />
          <PromosList onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'promo_new') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.promoNew')} onBack={handleBack} />
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
          <div className="master-shell">
            <PageHeader title={t('masterApp.titles.promo')} onBack={handleBack} />
            <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
              {t('masterApp.promoNotFound')}
            </div>
          </div>
        );
      }
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.promo')} onBack={handleBack} />
          <PromoCard promo={promo} onBack={handleBack} />
        </div>
      );
    }

    if (type === 'reports') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.reports')} onBack={handleBack} />
          <Reports initialPeriod={current.period || 'month'} />
        </div>
      );
    }

    if (type === 'requests') {
      return (
        <div className="master-shell">
          <Requests onNavigate={(t, p) => push(t, p)} onBadgeChange={setRequestsBadge} />
        </div>
      );
    }

    if (type === 'subscription') {
      return (
        <div className="master-shell">
          <PageHeader title={t('masterApp.titles.subscription')} onBack={handleBack} />
          <Subscription />
        </div>
      );
    }

    if (type === 'broadcast') {
      return (
        <div className="master-shell">
          <Broadcast />
        </div>
      );
    }

    // Fallback
    return (
      <div className="master-shell" style={{ padding: '24px 16px', textAlign: 'center' }}>
        <p style={{ color: 'var(--tg-hint)', marginTop: 48 }}>{t('masterApp.inDevelopment')}</p>
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
      case 'requests':
        return <Requests onNavigate={(t, p) => push(t, p)} onBadgeChange={setRequestsBadge} />;
      case 'more':
        return <More onNavigate={(t, p) => push(t, p)} />;
      default:
        return <Dashboard onNavigate={(t, p) => push(t, p)} />;
    }
  };

  return (
    <div className="master-shell">
      {renderTab()}
      <MasterNav active={tab} onNavigate={switchTab} requestsBadge={requestsBadge} />
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
      <div className="master-page-header">
        {title}
      </div>
    );
  }
  // Fallback: show manual back button
  return (
    <div className="master-page-header master-page-header-back">
      <button className="master-page-back-btn" onClick={onBack}>‹</button>
      <div className="master-page-header-title">{title}</div>
    </div>
  );
}
