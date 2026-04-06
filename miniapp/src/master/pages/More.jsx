import { useQuery } from '@tanstack/react-query';
import { getMasterMe, getMasterInvite } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

function SectionTitle({ children }) {
  return (
    <div style={{
      padding: '20px 16px 6px',
      fontSize: 12,
      fontWeight: 600,
      color: 'var(--tg-hint)',
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
    }}>
      {children}
    </div>
  );
}

function Cell({ icon, label, value, onClick }) {
  return (
    <div
      onClick={onClick ? () => { haptic(); onClick(); } : undefined}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '13px 16px',
        background: 'var(--tg-section-bg)',
        borderBottom: '1px solid var(--tg-secondary-bg)',
        cursor: onClick ? 'pointer' : 'default',
        gap: 12,
      }}
    >
      {icon && (
        <span style={{ fontSize: 20, flexShrink: 0, width: 24, textAlign: 'center' }}>{icon}</span>
      )}
      <span style={{ flex: 1, fontSize: 15, color: 'var(--tg-text)' }}>{label}</span>
      {value && <span style={{ fontSize: 14, color: 'var(--tg-hint)' }}>{value}</span>}
      {onClick && <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>}
    </div>
  );
}

export default function More({ onNavigate }) {
  const { data: master } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 60_000,
  });

  const { data: inviteData, isLoading: inviteLoading } = useQuery({
    queryKey: ['master-invite'],
    queryFn: getMasterInvite,
    staleTime: 5 * 60_000,
  });

  const handleCopyInvite = () => {
    const link = inviteData?.invite_link;
    if (!link) return;
    haptic();
    if (typeof navigator?.clipboard?.writeText === 'function') {
      navigator.clipboard.writeText(link);
    }
    if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup({ title: 'Ссылка скопирована', message: link, buttons: [{ type: 'ok' }] });
    }
  };

  const handleSupport = () => {
    haptic();
    if (typeof WebApp?.openTelegramLink === 'function') {
      WebApp.openTelegramLink('https://t.me/crmfit_support');
    }
  };

  return (
    <div style={{ paddingBottom: 80 }}>
      <SectionTitle>Клиенты</SectionTitle>
      <div style={{ overflow: 'hidden' }}>
        <Cell icon="👥" label="Список клиентов" onClick={() => onNavigate('clients')} />
        <Cell
          icon="🔗"
          label="Пригласить клиента"
          value={inviteLoading ? '...' : undefined}
          onClick={inviteData?.invite_link ? handleCopyInvite : undefined}
        />
      </div>

      <SectionTitle>Маркетинг</SectionTitle>
      <div style={{ overflow: 'hidden' }}>
        <Cell icon="📨" label="Рассылки" onClick={() => onNavigate('broadcast')} />
        <Cell icon="📣" label="Акции" onClick={() => onNavigate('promos')} />
      </div>

      <SectionTitle>Настройки</SectionTitle>
      <div style={{ overflow: 'hidden' }}>
        <Cell icon="⚙️" label="Профиль мастера" onClick={() => onNavigate('profile')} />
        <Cell icon="🎁" label="Бонусная программа" onClick={() => onNavigate('bonus')} />
        <Cell icon="🛠" label="Справочник услуг" onClick={() => onNavigate('services')} />
      </div>

      <SectionTitle>Поддержка</SectionTitle>
      <div style={{ overflow: 'hidden' }}>
        <Cell icon="💬" label="Написать в поддержку" onClick={handleSupport} />
      </div>

      <SectionTitle>О приложении</SectionTitle>
      <div style={{ overflow: 'hidden' }}>
        <Cell label="Версия" value="2.0.0" />
        <Cell label="crmfit.ru" />
      </div>
    </div>
  );
}
