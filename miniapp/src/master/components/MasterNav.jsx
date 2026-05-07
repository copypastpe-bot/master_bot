import { useI18n } from '../../i18n';
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

const PlanetIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <path d="M3 12c2.5-4 6.5-6 12-6" />
    <path d="M21 12c-2.5 4-6.5 6-12 6" />
    <path d="M4 15c5 3 11 3 16-1" />
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
  { id: 'home', key: 'nav.master.home', Icon: HomeIcon },
  { id: 'calendar', key: 'nav.master.calendar', Icon: CalendarIcon },
  { id: 'minisite', key: 'nav.master.minisite', Icon: PlanetIcon },
  { id: 'more', key: 'nav.master.more', Icon: MoreIcon },
];

export default function MasterNav({ active, onNavigate = () => {} }) {
  const { t } = useI18n();
  const handleTab = (id) => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate(id);
  };

  return (
    <nav className="master-nav">
      {tabs.map(({ id, key, Icon }) => {
        const isActive = active === id;
        const icon = Icon();
        return (
          <button
            key={id}
            onClick={() => handleTab(id)}
            className={`master-nav-button${isActive ? ' is-active' : ''}`}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="master-nav-icon-wrap">
              {icon}
            </span>
            <span>{t(key)}</span>
          </button>
        );
      })}
    </nav>
  );
}
