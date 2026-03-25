import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import MasterNav from './components/MasterNav';
import Dashboard from './pages/Dashboard';
import Calendar from './pages/Calendar';
import OrderDetail from './pages/OrderDetail';
import OrderCreate from './pages/OrderCreate';
import Broadcast from './pages/Broadcast';

function PlaceholderTab({ label }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '60vh',
      color: 'var(--tg-hint)',
      fontSize: 16,
    }}>
      {label} — скоро
    </div>
  );
}

function PlaceholderScreen({ label, onBack }) {
  return (
    <div style={{ padding: '24px 16px' }}>
      <button
        onClick={onBack}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--tg-button)',
          fontSize: 15,
          cursor: 'pointer',
          padding: 0,
          marginBottom: 16,
        }}
      >
        ← Назад
      </button>
      <p style={{ color: 'var(--tg-hint)', textAlign: 'center', marginTop: 48 }}>{label}</p>
    </div>
  );
}

export default function MasterApp() {
  const [tab, setTab] = useState('home');
  const [screen, setScreen] = useState(null); // { type: 'order'|'create_order', id? }
  const queryClient = useQueryClient();

  const handleNavigate = (type, params) => {
    setScreen({ type, ...( typeof params === 'object' ? params : { id: params }) });
  };

  const handleBack = () => {
    setScreen(null);
  };

  const handleOrderUpdated = () => {
    queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['master-calendar'] });
    queryClient.invalidateQueries({ queryKey: ['master-orders'] });
  };

  const handleOrderCreated = (order) => {
    queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['master-calendar'] });
    queryClient.invalidateQueries({ queryKey: ['master-orders'] });
    // Navigate to calendar showing the new order's date
    setScreen(null);
    const orderDate = order?.scheduled_at?.slice(0, 10) || null;
    if (orderDate) {
      // Switch to calendar tab with the date
      setTab('calendar');
    }
  };

  // Nested screens (over tab content)
  if (screen) {
    if (screen.type === 'order') {
      return (
        <OrderDetail
          orderId={screen.id}
          onBack={handleBack}
          onUpdated={handleOrderUpdated}
        />
      );
    }
    if (screen.type === 'create_order') {
      return (
        <OrderCreate
          params={screen}
          onBack={handleBack}
          onCreated={handleOrderCreated}
        />
      );
    }
    return <PlaceholderScreen label="Скоро" onBack={handleBack} />;
  }

  const renderTab = () => {
    switch (tab) {
      case 'home':
        return <Dashboard onNavigate={handleNavigate} />;
      case 'calendar':
        return <Calendar onNavigate={handleNavigate} />;
      case 'marketing':
        return <Broadcast />;
      case 'more':
        return <PlaceholderTab label="Ещё" />;
      default:
        return <Dashboard onNavigate={handleNavigate} />;
    }
  };

  return (
    <div>
      {renderTab()}
      <MasterNav active={tab} onNavigate={setTab} />
    </div>
  );
}
