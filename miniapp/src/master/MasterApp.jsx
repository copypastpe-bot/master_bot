import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import MasterNav from './components/MasterNav';
import { getMasterMe } from '../api/client';
import { Skeleton } from '../components/Skeleton';

function MasterHome({ master }) {
  return (
    <div style={{ padding: '24px 16px 100px' }}>
      <h2 style={{ color: 'var(--tg-text)', marginBottom: 8, fontSize: 20 }}>
        Добро пожаловать, {master?.name}!
      </h2>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 24 }}>
        {master?.sphere || 'Мастер'}
      </p>

      <div style={{
        background: 'var(--tg-surface)',
        borderRadius: 'var(--radius-card)',
        padding: '16px',
        marginBottom: 12,
      }}>
        <div style={{ color: 'var(--tg-hint)', fontSize: 12, marginBottom: 4 }}>Клиентов</div>
        <div style={{ color: 'var(--tg-text)', fontSize: 28, fontWeight: 600 }}>
          {master?.client_count ?? '—'}
        </div>
      </div>

      <div style={{
        background: 'var(--tg-surface)',
        borderRadius: 'var(--radius-card)',
        padding: '16px',
      }}>
        <div style={{ color: 'var(--tg-hint)', fontSize: 12, marginBottom: 4 }}>Бонусная программа</div>
        <div style={{ color: 'var(--tg-text)', fontSize: 15 }}>
          {master?.bonus_enabled
            ? `${master.bonus_rate}% от суммы`
            : 'Отключена'}
        </div>
      </div>
    </div>
  );
}

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

export default function MasterApp() {
  const [tab, setTab] = useState('home');

  const { data: master, isLoading, isError } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div style={{ padding: '24px 16px' }}>
        <Skeleton height={28} style={{ marginBottom: 12, width: '60%' }} />
        <Skeleton height={16} style={{ marginBottom: 24, width: '40%' }} />
        <Skeleton height={72} style={{ marginBottom: 12 }} />
        <Skeleton height={72} />
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 24px' }}>
        <p style={{ color: 'var(--tg-text)', marginBottom: 8 }}>Не удалось загрузить профиль</p>
        <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Попробуйте перезапустить приложение</p>
      </div>
    );
  }

  const renderTab = () => {
    switch (tab) {
      case 'home': return <MasterHome master={master} />;
      case 'calendar': return <PlaceholderTab label="Календарь" />;
      case 'marketing': return <PlaceholderTab label="Рассылки" />;
      case 'more': return <PlaceholderTab label="Ещё" />;
      default: return <MasterHome master={master} />;
    }
  };

  return (
    <div>
      {renderTab()}
      <MasterNav active={tab} onNavigate={setTab} />
    </div>
  );
}
