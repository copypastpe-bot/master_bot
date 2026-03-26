import { useState, useEffect, lazy, Suspense } from 'react';
const WebApp = window.Telegram?.WebApp;
import Home from './pages/Home';
import Booking from './pages/Booking';
import Bonuses from './pages/Bonuses';
import Promos from './pages/Promos';
import BottomNav from './components/BottomNav';
import { Skeleton } from './components/Skeleton';
import { getAuthRole } from './api/client';

// Lazy-load master bundle — clients never download it
const MasterApp = lazy(() => import('./master/MasterApp'));

const clientPages = { home: Home, booking: Booking, bonuses: Bonuses, promos: Promos };

function ClientApp() {
  const [page, setPage] = useState('home');

  // Telegram BackButton — show on all pages except home
  useEffect(() => {
    if (!WebApp?.BackButton) return;
    if (page === 'home') {
      WebApp.BackButton.hide();
    } else {
      WebApp.BackButton.show();
      const handler = () => setPage('home');
      WebApp.BackButton.onClick(handler);
      return () => WebApp.BackButton.offClick(handler);
    }
  }, [page]);

  const Page = clientPages[page];

  return (
    <div>
      <Page onNavigate={setPage} />
      <BottomNav active={page} onNavigate={setPage} />
    </div>
  );
}

function UnknownRoleScreen() {
  return (
    <div style={{ textAlign: 'center', padding: '64px 24px' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>👋</div>
      <p style={{ color: 'var(--tg-text)', fontSize: 18, marginBottom: 8 }}>
        Вы не зарегистрированы
      </p>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>
        Зарегистрируйтесь через бота, чтобы открыть приложение
      </p>
    </div>
  );
}

function RoleSkeleton() {
  return (
    <div style={{ padding: '24px 16px' }}>
      <Skeleton height={28} style={{ marginBottom: 12, width: '50%' }} />
      <Skeleton height={16} style={{ marginBottom: 24, width: '35%' }} />
      <Skeleton height={80} style={{ marginBottom: 12 }} />
      <Skeleton height={80} />
    </div>
  );
}

export default function App() {
  const [role, setRole] = useState(null); // null = loading, 'master'|'client'|'unknown'

  useEffect(() => {
    getAuthRole()
      .then(data => setRole(data.role))
      .catch(() => setRole('unknown'));
  }, []);

  if (role === null) {
    return <RoleSkeleton />;
  }

  if (role === 'master') {
    return (
      <Suspense fallback={<RoleSkeleton />}>
        <MasterApp />
      </Suspense>
    );
  }

  if (role === 'client') {
    return <ClientApp />;
  }

  return <UnknownRoleScreen />;
}
