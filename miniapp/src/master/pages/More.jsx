import { useQuery } from '@tanstack/react-query';
import { getMasterMe, getMasterInviteLink } from '../../api/client';

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

function Cell({ label, value, onClick, destructive }) {
  return (
    <div
      onClick={onClick ? () => { haptic(); onClick(); } : undefined}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '13px 16px',
        background: 'var(--tg-section-bg)',
        borderBottom: '1px solid var(--tg-secondary-bg)',
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <span style={{
        fontSize: 15,
        color: destructive ? 'var(--tg-destructive, #e53935)' : 'var(--tg-text)',
      }}>
        {label}
      </span>
      {value && (
        <span style={{ fontSize: 14, color: 'var(--tg-hint)', marginLeft: 8 }}>
          {value}
        </span>
      )}
      {onClick && (
        <span style={{ color: 'var(--tg-hint)', fontSize: 18, marginLeft: 4 }}>›</span>
      )}
    </div>
  );
}

export default function More() {
  const { data: master } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 60_000,
  });

  const { data: inviteData, isLoading: inviteLoading } = useQuery({
    queryKey: ['master-invite-link'],
    queryFn: getMasterInviteLink,
    staleTime: 5 * 60_000,
  });

  const inviteLink = inviteData?.invite_link || '';

  const handleCopyInvite = () => {
    if (!inviteLink) return;
    haptic();
    if (typeof navigator?.clipboard?.writeText === 'function') {
      navigator.clipboard.writeText(inviteLink).then(() => {
        if (typeof WebApp?.showPopup === 'function') {
          WebApp.showPopup({
            title: 'Ссылка скопирована',
            message: inviteLink,
            buttons: [{ type: 'ok' }],
          });
        }
      });
    } else if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup({
        title: 'Пригласить клиента',
        message: inviteLink,
        buttons: [{ type: 'ok', text: 'Закрыть' }],
      });
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
      {/* Profile */}
      <SectionTitle>Профиль мастера</SectionTitle>
      <div style={{ background: 'var(--tg-section-bg)', borderRadius: '0 0 12px 12px', overflow: 'hidden' }}>
        <Cell label="Имя" value={master?.name || '—'} />
        <Cell label="Сфера" value={master?.sphere || '—'} />
      </div>

      {/* Clients */}
      <SectionTitle>Клиенты</SectionTitle>
      <div style={{ background: 'var(--tg-section-bg)', borderRadius: '12px', overflow: 'hidden' }}>
        <Cell
          label="Пригласить клиента"
          value={inviteLoading ? '...' : undefined}
          onClick={inviteLink ? handleCopyInvite : undefined}
        />
      </div>

      {/* Support */}
      <SectionTitle>Поддержка</SectionTitle>
      <div style={{ background: 'var(--tg-section-bg)', borderRadius: '12px', overflow: 'hidden' }}>
        <Cell label="Написать в поддержку" onClick={handleSupport} />
      </div>

      {/* About */}
      <SectionTitle>О приложении</SectionTitle>
      <div style={{ background: 'var(--tg-section-bg)', borderRadius: '12px', overflow: 'hidden' }}>
        <Cell label="Версия" value="1.0.0" />
        <Cell label="crmfit.ru" value="" />
      </div>
    </div>
  );
}
