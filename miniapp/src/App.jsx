import { useState, useEffect, lazy, Suspense } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import Home from './pages/Home';
import History from './pages/History';
import News from './pages/News';
import Settings from './pages/Settings';
import MasterLanding from './pages/MasterLanding';
import Contact from './pages/Contact';
import BottomNav from './components/BottomNav';
import { Skeleton } from './components/Skeleton';
import { getAuthRole, getClientMasters, setActiveMasterId } from './api/client';
import MasterOnboarding from './master/pages/MasterOnboarding';
import MasterSelectScreen from './pages/MasterSelectScreen';
import MasterTypeUIProvider from './master/components/MasterTypeUIProvider';
import { useI18n } from './i18n';
const WebApp = window.Telegram?.WebApp;

// Lazy-load master bundle — clients never download it
const MasterApp = lazy(() => import('./master/MasterApp'));

const SUB_SCREENS = new Set(['create_order', 'ask_question', 'landing']);

function ClientApp({ masters, activeMasterId, onMasterChange, initialInviteToken }) {
  const [tab, setTab] = useState('home');
  const [page, setPage] = useState(initialInviteToken ? 'landing' : 'home');
  const [pageParams, setPageParams] = useState(initialInviteToken ? { inviteToken: initialInviteToken, mode: 'public' } : {});
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [masterProfile, setMasterProfile] = useState(null);
  const qc = useQueryClient();

  useEffect(() => {
    document.body.classList.add('typeui-client-body');
    return () => document.body.classList.remove('typeui-client-body');
  }, []);

  // Telegram BackButton
  useEffect(() => {
    if (!WebApp?.BackButton) return;
    const isSubScreen = SUB_SCREENS.has(page) || page === 'master_select';
    if (isSubScreen) {
      WebApp.BackButton.show();
      const handler = () => navigate(tab);
      WebApp.BackButton.onClick(handler);
      return () => WebApp.BackButton.offClick(handler);
    } else {
      WebApp.BackButton.hide();
    }
  }, [page, tab]);

  // Hide BottomNav when keyboard open
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const handler = () => setKeyboardOpen(window.innerHeight - vv.height > 150);
    vv.addEventListener('resize', handler);
    return () => vv.removeEventListener('resize', handler);
  }, []);

  const navigate = (pageId, params = {}) => {
    if (pageId === 'home' || pageId === 'history' || pageId === 'news' || pageId === 'settings') {
      setTab(pageId);
      setPage(pageId);
      setPageParams({});
    } else {
      setPage(pageId);
      setPageParams(params);
    }
  };

  const handleTabNav = (tabId) => {
    if (tabId === tab && !SUB_SCREENS.has(page) && page !== 'master_select') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      navigate(tabId);
    }
  };

  const handleMasterSelectDone = (masterId) => {
    onMasterChange(masterId);
    qc.invalidateQueries();
    navigate(tab);
  };

  const handleLinked = () => {
    window.location.reload();
  };

  const isSubScreen = SUB_SCREENS.has(page) || page === 'master_select';
  const activeMaster = masters.find(m => m.master_id === activeMasterId);

  const renderContent = () => {
    if (!activeMasterId && page !== 'landing') {
      return <MasterSelectScreen masters={masters} onSelect={handleMasterSelectDone} />;
    }

    if (page === 'master_select') {
      return <MasterSelectScreen masters={masters} onSelect={handleMasterSelectDone} />;
    }

    if (page === 'landing') {
      return (
        <MasterLanding
          mode={pageParams.mode || 'private'}
          masterId={pageParams.masterId || activeMasterId}
          inviteToken={pageParams.inviteToken}
          navigate={navigate}
          onLinked={handleLinked}
        />
      );
    }

    if (page === 'create_order') {
      return (
        <Contact
          onNavigate={(p) => navigate(p)}
          keyboardOpen={keyboardOpen}
          preselectedService={pageParams.service}
          initialMode="booking"
        />
      );
    }

    if (page === 'ask_question') {
      return (
        <Contact
          onNavigate={(p) => navigate(p)}
          keyboardOpen={keyboardOpen}
          initialMode="question"
        />
      );
    }

    if (tab === 'home') return (
      <Home
        activeMasterId={activeMasterId}
        navigate={navigate}
        masterName={activeMaster?.master_name}
        onProfileLoaded={setMasterProfile}
      />
    );
    if (tab === 'history') return (
      <History
        activeMasterId={activeMasterId}
        navigate={navigate}
        masterProfile={masterProfile}
      />
    );
    if (tab === 'news') return (
      <News activeMasterId={activeMasterId} navigate={navigate} />
    );
    if (tab === 'settings') return (
      <Settings
        activeMasterId={activeMasterId}
        onProfileDeleted={() => window.location.reload()}
      />
    );

    return null;
  };

  return (
    <div className="client-shell">
      <div className="client-shell-content">
        {/* Specialist switcher header — shown on tab screens when multi-master */}
        {!isSubScreen && activeMasterId && masters.length > 1 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '8px 16px 0' }}>
            <button className="client-header-specialist-btn" onClick={() => navigate('master_select')}>
              <span>{activeMaster?.master_name}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
          </div>
        )}
        {renderContent()}
      </div>
      {!isSubScreen && activeMasterId && !keyboardOpen && (
        <BottomNav active={tab} onNavigate={handleTabNav} />
      )}
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

  // Extract invite token at component level so it's available for ClientApp
  const startParam = WebApp?.initDataUnsafe?.start_param;
  const inviteToken = startParam?.startsWith('invite_') ? startParam.slice(7) : null;

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
    // Invite linking is now handled by MasterLanding — just load masters here
    const load = async () => {
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

    // If no masters but invite token present — show landing so user can connect
    if (masters.length === 0 && !inviteToken) {
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

    return (
      <ClientApp
        masters={masters}
        activeMasterId={activeMasterId}
        onMasterChange={handleMasterChange}
        initialInviteToken={inviteToken}
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
