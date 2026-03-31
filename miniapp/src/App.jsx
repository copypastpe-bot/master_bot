import { useState, useEffect, lazy, Suspense } from 'react';
const WebApp = window.Telegram?.WebApp;
import Home from './pages/Home';
import Booking from './pages/Booking';
import Bonuses from './pages/Bonuses';
import Promos from './pages/Promos';
import BottomNav from './components/BottomNav';
import { Skeleton } from './components/Skeleton';
import { getAuthRole, getClientMasters, linkToMaster, setActiveMasterId } from './api/client';
import MasterOnboarding from './master/pages/MasterOnboarding';
import MasterSelectScreen from './pages/MasterSelectScreen';

// Lazy-load master bundle — clients never download it
const MasterApp = lazy(() => import('./master/MasterApp'));

const clientPages = { home: Home, booking: Booking, bonuses: Bonuses, promos: Promos };

function ClientApp({ masters, activeMasterId, onMasterChange }) {
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
      <Page
        onNavigate={setPage}
        masters={masters}
        activeMasterId={activeMasterId}
        onMasterChange={onMasterChange}
      />
      <BottomNav active={page} onNavigate={setPage} />
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
  const [role, setRole] = useState(null); // null = loading
  const [masters, setMasters] = useState(null); // null = not yet loaded
  const [activeMasterId, setActiveMasterIdState] = useState(null);

  useEffect(() => {
    getAuthRole()
      .then(data => setRole(data.role))
      .catch(() => setRole('unknown'));
  }, []);

  useEffect(() => {
    if (role !== 'client') return;

    // Deep link: start_param = "invite_TOKEN"
    const startParam = WebApp?.initDataUnsafe?.start_param;
    const token = startParam?.startsWith('invite_') ? startParam.slice(7) : null;

    const load = async () => {
      if (token) {
        try {
          await linkToMaster(token);
        } catch (e) {
          // 409 = already linked — not an error, continue
          if (e?.response?.status !== 409) {
            console.error('linkToMaster failed', e);
          }
        }
      }
      const data = await getClientMasters();
      setMasters(data.masters || []);
    };

    load().catch(() => setMasters([]));
  }, [role]);

  // Auto-select when exactly 1 master
  useEffect(() => {
    if (!masters || masters.length !== 1) return;
    const id = masters[0].master_id;
    setActiveMasterId(id);       // module var in client.js
    setActiveMasterIdState(id);  // React state for re-render
  }, [masters]);

  const handleMasterChange = (masterId) => {
    setActiveMasterId(masterId);      // module var
    setActiveMasterIdState(masterId); // React state
  };

  if (role === null) return <RoleSkeleton />;

  if (role === 'master') {
    return (
      <Suspense fallback={<RoleSkeleton />}>
        <MasterApp />
      </Suspense>
    );
  }

  if (role === 'client') {
    if (masters === null) return <RoleSkeleton />;

    if (masters.length === 0) {
      return (
        <div style={{ padding: '24px 16px', textAlign: 'center', marginTop: 60 }}>
          <p style={{ fontSize: 40, marginBottom: 16 }}>👋</p>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Нет мастеров</p>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14, lineHeight: 1.5 }}>
            Попросите мастера отправить вам ссылку для подключения
          </p>
        </div>
      );
    }

    // 2+ masters, none selected yet → show selection screen
    if (!activeMasterId) {
      return (
        <MasterSelectScreen
          masters={masters}
          onSelect={handleMasterChange}
        />
      );
    }

    return (
      <ClientApp
        masters={masters}
        activeMasterId={activeMasterId}
        onMasterChange={handleMasterChange}
      />
    );
  }

  return <MasterOnboarding onRegistered={() => setRole('master')} />;
}
