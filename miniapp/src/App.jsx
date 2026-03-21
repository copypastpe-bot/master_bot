import { useState, useEffect } from 'react';
import WebApp from '@twa-dev/sdk';
import Home from './pages/Home';
import Booking from './pages/Booking';
import Bonuses from './pages/Bonuses';
import Promos from './pages/Promos';
import BottomNav from './components/BottomNav';

const pages = { home: Home, booking: Booking, bonuses: Bonuses, promos: Promos };

export default function App() {
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

  const Page = pages[page];

  return (
    <div>
      <Page onNavigate={setPage} />
      <BottomNav active={page} onNavigate={setPage} />
    </div>
  );
}
