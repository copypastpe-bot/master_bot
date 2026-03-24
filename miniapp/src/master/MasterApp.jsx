import { useState } from 'react';
import MasterNav from './components/MasterNav';
import Dashboard from './pages/Dashboard';
import Calendar from './pages/Calendar';

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

  const handleNavigate = (type, id) => {
    setScreen({ type, id });
  };

  const handleBack = () => {
    setScreen(null);
  };

  // Nested screens (over tab content)
  if (screen) {
    if (screen.type === 'order') {
      return <PlaceholderScreen label={`Заказ #${screen.id} (скоро)`} onBack={handleBack} />;
    }
    if (screen.type === 'create_order') {
      return <PlaceholderScreen label="Создание заказа (скоро)" onBack={handleBack} />;
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
        return <PlaceholderTab label="Рассылки" />;
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
