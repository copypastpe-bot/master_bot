const WebApp = window.Telegram?.WebApp;

const HomeIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const CalendarIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

const BellIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
);

const MoreIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="1"/>
    <circle cx="19" cy="12" r="1"/>
    <circle cx="5" cy="12" r="1"/>
  </svg>
);

const tabs = [
  { id: 'home', label: 'Главная', Icon: HomeIcon },
  { id: 'calendar', label: 'Календарь', Icon: CalendarIcon },
  { id: 'requests', label: 'Заявки', Icon: BellIcon },
  { id: 'more', label: 'Ещё', Icon: MoreIcon },
];

export default function MasterNav({ active, onNavigate = () => {}, requestsBadge = 0 }) {
  const handleTab = (id) => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate(id);
  };

  return (
    <nav className="master-nav">
      {tabs.map(({ id, label, Icon }) => {
        const isActive = active === id;
        const badge = id === 'requests' && requestsBadge > 0 ? requestsBadge : 0;
        return (
          <button
            key={id}
            onClick={() => handleTab(id)}
            className={`master-nav-button${isActive ? ' is-active' : ''}`}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="master-nav-icon-wrap">
              <Icon />
              {badge > 0 && (
                <span className="master-nav-badge">
                  {badge > 99 ? '99+' : badge}
                </span>
              )}
            </span>
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
