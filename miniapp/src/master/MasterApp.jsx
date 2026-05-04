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
import FeedbackSettings from './pages/FeedbackSettings';
import BonusMessageEditor from './pages/BonusMessageEditor';
import Services from './pages/Services';
import PromosList from './pages/PromosList';
import PromoCreate from './pages/PromoCreate';
import PromoCard from './pages/PromoCard';
import Reports from './pages/Reports';
import Requests from './pages/Requests';
import Subscription from './pages/Subscription';
import { useI18n } from '../i18n';
import AppHeader from './components/AppHeader';
import { resetViewportScroll } from '../utils/scroll';

const WebApp = window.Telegram?.WebApp;

export default function MasterApp() {
  const { t } = useI18n();
  const [tab, setTab] = useState('home');
  // navStack: array of { type, id?, ...params }
  // Empty stack = tab root. Push = navigate forward. Pop = back.
  const [navStack, setNavStack] = useState([]);
  const [requestsBadge, setRequestsBadge] = useState(0);

  const queryClient = useQueryClient();

  useEffect(() => {
    let ignore = false;
    getMasterRequestsUnreadCount()
      .then((data) => {
        if (!ignore) setRequestsBadge(data.count ?? 0);
      })
      .catch(() => {
        // badge is best-effort
      });
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    document.body.classList.add('typeui-enterprise-body');
    return () => {
      document.body.classList.remove('typeui-enterprise-body');
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Navigation helpers
  // ---------------------------------------------------------------------------
  const push = (type, params = {}) => {
    resetViewportScroll();
    setNavStack(prev => [...prev, { type, ...params }]);
  };

  const handleBack = useCallback(() => {
    resetViewportScroll();
    setNavStack(prev => prev.slice(0, -1));
  }, []);

  const switchTab = (newTab) => {
    resetViewportScroll();
    setNavStack([]);
    setTab(newTab);
  };

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
  }, [navStack.length, handleBack]);

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

  const titleMap = {
    order:         t('masterApp.titles.order'),
    create_order:  t('masterApp.titles.createOrder'),
    clients:       t('masterApp.titles.clients'),
    client:        t('masterApp.titles.client'),
    profile:       t('masterApp.titles.profile'),
    bonus:         t('masterApp.titles.bonus'),
    feedback_settings: t('masterApp.titles.feedbackSettings'),
    bonus_message: current?.kind === 'birthday'
                     ? t('masterApp.titles.bonusBirthday')
                     : t('masterApp.titles.bonusWelcome'),
    services:      t('masterApp.titles.services'),
    promos:        t('masterApp.titles.promos'),
    promo_new:     t('masterApp.titles.promoNew'),
    promo:         t('masterApp.titles.promo'),
    reports:       t('masterApp.titles.reports'),
    requests:      t('masterApp.titles.requests'),
    subscription:  t('masterApp.titles.subscription'),
    broadcast:     t('masterApp.titles.broadcast'),
  };

  const currentTitle = current ? (titleMap[current.type] ?? 'Master_bot') : 'Master_bot';

  if (current) {
    const { type, id } = current;

    if (type === 'order') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
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
          <AppHeader title={currentTitle} />
          <OrderCreate params={current} onBack={handleBack} onCreated={handleOrderCreated} />
        </div>
      );
    }

    if (type === 'clients') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <ClientsList onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'client') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
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
          <AppHeader title={currentTitle} />
          <Profile />
        </div>
      );
    }

    if (type === 'bonus') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <BonusSettings onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'feedback_settings') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <FeedbackSettings />
        </div>
      );
    }

    if (type === 'bonus_message') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <BonusMessageEditor kind={current.kind || 'welcome'} />
        </div>
      );
    }

    if (type === 'services') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <Services />
        </div>
      );
    }

    if (type === 'promos') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <PromosList onNavigate={(t, p) => push(t, p)} />
        </div>
      );
    }

    if (type === 'promo_new') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
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
            <AppHeader title={currentTitle} />
            <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
              {t('masterApp.promoNotFound')}
            </div>
          </div>
        );
      }
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <PromoCard promo={promo} onBack={handleBack} />
        </div>
      );
    }

    if (type === 'reports') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <Reports initialPeriod={current.period || 'month'} />
        </div>
      );
    }

    if (type === 'requests') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <Requests onNavigate={(t, p) => push(t, p)} onBadgeChange={setRequestsBadge} />
        </div>
      );
    }

    if (type === 'subscription') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <Subscription />
        </div>
      );
    }

    if (type === 'broadcast') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <Broadcast />
        </div>
      );
    }

    // Fallback
    return (
      <div className="master-shell" style={{ padding: '24px 16px', textAlign: 'center' }}>
        <AppHeader title={currentTitle} />
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
      <AppHeader title={currentTitle} />
      {renderTab()}
      <MasterNav active={tab} onNavigate={switchTab} requestsBadge={requestsBadge} />
    </div>
  );
}
