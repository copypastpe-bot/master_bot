const WebApp = window.Telegram?.WebApp;

const HomeIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const MailIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
    <polyline points="22,6 12,13 2,6"/>
  </svg>
);

const StarIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
  </svg>
);

const GiftIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 12 20 22 4 22 4 12"/>
    <rect x="2" y="7" width="20" height="5"/>
    <line x1="12" y1="22" x2="12" y2="7"/>
    <path d="M12 7H7.5a2.5 2.5 0 010-5C11 2 12 7 12 7z"/>
    <path d="M12 7h4.5a2.5 2.5 0 000-5C13 2 12 7 12 7z"/>
  </svg>
);

const tabs = [
  { id: 'home', label: 'Главная', Icon: HomeIcon },
  { id: 'contact', label: 'Связаться', Icon: MailIcon },
  { id: 'bonuses', label: 'Бонусы', Icon: StarIcon },
  { id: 'promos', label: 'Акции', Icon: GiftIcon },
];

export default function BottomNav({ active, onNavigate = () => {} }) {
  const handleTab = (id) => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate(id);
  };

  return (
    <nav style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      background: 'var(--tg-surface)',
      borderTop: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      zIndex: 100,
      paddingBottom: 'env(safe-area-inset-bottom)',
    }}>
      {tabs.map(({ id, label, Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => handleTab(id)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
              padding: '10px 0',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: isActive ? 'var(--tg-accent)' : 'var(--tg-hint)',
              fontSize: 11,
              transition: 'color 0.15s',
            }}
          >
            <Icon />
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
