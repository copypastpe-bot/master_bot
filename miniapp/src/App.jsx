import { useState, useEffect, lazy, Suspense } from 'react';
import Home from './pages/Home';
import Contact from './pages/Contact';
import Bonuses from './pages/Bonuses';
import Promos from './pages/Promos';
import BottomNav from './components/BottomNav';
import { Skeleton } from './components/Skeleton';
import { getAuthRole, getClientMasters, linkToMaster, setActiveMasterId } from './api/client';
import MasterOnboarding from './master/pages/MasterOnboarding';
import MasterSelectScreen from './pages/MasterSelectScreen';
import MasterTypeUIProvider from './master/components/MasterTypeUIProvider';
import { useI18n } from './i18n';
const WebApp = window.Telegram?.WebApp;

// Lazy-load master bundle — clients never download it
const MasterApp = lazy(() => import('./master/MasterApp'));

const clientPages = { home: Home, contact: Contact, bonuses: Bonuses, promos: Promos };

function ClientApp({ masters, activeMasterId, onMasterChange }) {
  const [page, setPage] = useState('home');
  const [keyboardOpen, setKeyboardOpen] = useState(false);

  useEffect(() => {
    document.body.classList.add('typeui-client-body');
    return () => {
      document.body.classList.remove('typeui-client-body');
    };
  }, []);

  // Telegram BackButton — show on all pages except home
  useEffect(() => {
    if (!WebApp?.BackButton) return;
    if (page === 'home' || page === 'contact') {
      WebApp.BackButton.hide();
    } else {
      WebApp.BackButton.show();
      const handler = () => setPage('home');
      WebApp.BackButton.onClick(handler);
      return () => WebApp.BackButton.offClick(handler);
    }
  }, [page]);

  // Hide BottomNav when keyboard is open
  // visualViewport.height shrinks on iOS when keyboard opens; window.innerHeight stays the same
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const handler = () => {
      setKeyboardOpen(window.innerHeight - vv.height > 150);
    };
    vv.addEventListener('resize', handler);
    return () => vv.removeEventListener('resize', handler);
  }, []);

  const Page = clientPages[page];

  return (
    <div className="client-shell">
      <div className="client-shell-content">
        <Page
          onNavigate={setPage}
          masters={masters}
          activeMasterId={activeMasterId}
          onMasterChange={onMasterChange}
          keyboardOpen={keyboardOpen}
        />
      </div>
      {!keyboardOpen && <BottomNav active={page} onNavigate={setPage} />}
    </div>
  );
}


function RoleSkeleton() {
  return (
    <div className="client-shell">
      <div className="client-shell-content">
        <div className="client-page">
          <div style={{ padding: '24px 16px' }}>
            <Skeleton height={28} style={{ marginBottom: 12, width: '50%' }} />
            <Skeleton height={16} style={{ marginBottom: 24, width: '35%' }} />
            <Skeleton height={80} style={{ marginBottom: 12 }} />
            <Skeleton height={80} />
          </div>
        </div>
      </div>
    </div>
  );
}

function extractReferralCode(startParamRaw) {
  const startParam = (startParamRaw || '').trim();
  if (!startParam) return null;

  if (startParam.startsWith('ref_')) return startParam.slice(4).toUpperCase();
  if (startParam.startsWith('referral_')) return startParam.slice(9).toUpperCase();
  if (startParam.startsWith('REF_')) return startParam.toUpperCase();

  return null;
}

function getForcedRole() {
  try {
    const params = new URLSearchParams(window.location.search);
    const app = (params.get('app') || params.get('role') || '').trim().toLowerCase();
    if (app === 'client' || app === 'master') return app;
  } catch {
    // ignore invalid location state
  }
  return null;
}

export default function App() {
  const { t } = useI18n();
  const [role, setRole] = useState(null); // null = loading
  const [masters, setMasters] = useState(null); // null = not yet loaded
  const [activeMasterId, setActiveMasterIdState] = useState(null);
  const referralCode = extractReferralCode(WebApp?.initDataUnsafe?.start_param);
  const forcedRole = getForcedRole();

  useEffect(() => {
    getAuthRole()
      .then((data) => {
        const resolvedRole = data?.role || 'unknown';
        if (resolvedRole === 'unknown' && forcedRole) {
          setRole(forcedRole);
          return;
        }
        setRole(resolvedRole);
      })
      .catch(() => setRole(forcedRole || 'unknown'));
  }, [forcedRole]);

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
        <MasterTypeUIProvider>
          <MasterApp />
        </MasterTypeUIProvider>
      </Suspense>
    );
  }

  if (role === 'client') {
    if (masters === null) return <RoleSkeleton />;

    if (masters.length === 0) {
      return (
        <div className="client-shell">
          <div className="client-shell-content">
            <div className="client-page">
              <div className="client-screen-state" style={{ marginTop: 60 }}>
                <p style={{ fontSize: 40, marginBottom: 16 }}>👋</p>
                <p className="client-screen-state-title">{t('app.noMasters.title')}</p>
                <p className="client-screen-state-subtitle">
                  {t('app.noMasters.subtitle')}
                </p>
              </div>
            </div>
          </div>
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

  if (forcedRole === 'client') {
    return (
      <div className="client-shell">
        <div className="client-shell-content">
          <div className="client-page">
            <div className="client-screen-state" style={{ marginTop: 60 }}>
              <p style={{ fontSize: 40, marginBottom: 16 }}>📱</p>
              <p className="client-screen-state-title">{t('app.noMasters.title')}</p>
              <p className="client-screen-state-subtitle">
                {t('app.noMasters.subtitle')}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <MasterOnboarding referralCode={referralCode} onRegistered={() => setRole('master')} />;
}
