import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterInvite,
  getMasterSubscription,
  getMasterGoogleCalendar,
  getMasterGoogleCalendarConnectUrl,
  disconnectMasterGoogleCalendar,
  trackMasterReferralLinkCopied,
} from '../../api/client';
import SubscriptionPaywallSheet from '../components/SubscriptionPaywallSheet';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const iconProps = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
};

const UsersIcon = () => (
  <svg {...iconProps}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="8.5" cy="7" r="4" />
    <path d="M20 8v6" />
    <path d="M17 11h6" />
  </svg>
);

const LinkIcon = () => (
  <svg {...iconProps}>
    <path d="M10 13a5 5 0 0 0 7.1 0l2.8-2.8a5 5 0 1 0-7.1-7.1L10 4" />
    <path d="M14 11a5 5 0 0 0-7.1 0L4.1 13.8a5 5 0 1 0 7.1 7.1L14 20" />
  </svg>
);

const SendIcon = () => (
  <svg {...iconProps}>
    <path d="M22 2L11 13" />
    <path d="M22 2 15 22l-4-9-9-4 20-7Z" />
  </svg>
);

const MegaphoneIcon = () => (
  <svg {...iconProps}>
    <path d="M3 11v2a2 2 0 0 0 2 2h2l3 5h2l-2-5h4l6 4V5l-6 4H5a2 2 0 0 0-2 2Z" />
  </svg>
);

const UserIcon = () => (
  <svg {...iconProps}>
    <circle cx="12" cy="8" r="4" />
    <path d="M5 21a7 7 0 0 1 14 0" />
  </svg>
);

const GiftIcon = () => (
  <svg {...iconProps}>
    <path d="M20 12v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-8" />
    <path d="M2 7h20v5H2z" />
    <path d="M12 22V7" />
    <path d="M12 7h-2a3 3 0 1 1 0-6c3 0 3 6 3 6Z" />
    <path d="M12 7h2a3 3 0 1 0 0-6c-3 0-3 6-3 6Z" />
  </svg>
);

const ToolIcon = () => (
  <svg {...iconProps}>
    <path d="m14.7 6.3 3 3" />
    <path d="m12.2 8.8 3 3" />
    <path d="M3 21a2 2 0 0 1 0-3l9.2-9.2a2 2 0 0 1 2.8 0l.2.2a2 2 0 0 1 0 2.8L6 21a2 2 0 0 1-3 0Z" />
    <path d="m18.5 2.5 3 3a2.1 2.1 0 0 1 0 3l-2 2-6-6 2-2a2.1 2.1 0 0 1 3 0Z" />
  </svg>
);

const MessageIcon = () => (
  <svg {...iconProps}>
    <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8A8.5 8.5 0 0 1 12.5 20H4l1.9-3.8A8.5 8.5 0 1 1 21 11.5Z" />
  </svg>
);

const CalendarIcon = () => (
  <svg {...iconProps}>
    <rect x="3" y="4" width="18" height="18" rx="2" />
    <path d="M16 2v4" />
    <path d="M8 2v4" />
    <path d="M3 10h18" />
  </svg>
);

const ChevronIcon = () => (
  <svg {...iconProps} width={14} height={14}>
    <path d="m9 18 6-6-6-6" />
  </svg>
);

function SectionTitle({ children }) {
  return (
    <div className="enterprise-section-title">
      {children}
    </div>
  );
}

function Cell({ icon, label, value, onClick, hideChevron = false }) {
  const className = `enterprise-cell${onClick ? ' is-interactive' : ''}`;
  const content = (
    <>
      {icon && (
        <span className="enterprise-cell-icon">{icon}</span>
      )}
      <span className="enterprise-cell-label">{label}</span>
      {value && <span className="enterprise-cell-value">{value}</span>}
      {onClick && !hideChevron && <span className="enterprise-cell-chevron"><ChevronIcon /></span>}
    </>
  );

  if (onClick) {
    return (
      <button
        onClick={() => { haptic(); onClick(); }}
        className={className}
      >
        {content}
      </button>
    );
  }

  return (
    <div className={className}>
      {content}
    </div>
  );
}

export default function More({ onNavigate }) {
  const qc = useQueryClient();
  const [paywallOpen, setPaywallOpen] = useState(false);

  const { data: inviteData, isLoading: inviteLoading } = useQuery({
    queryKey: ['master-invite'],
    queryFn: getMasterInvite,
    staleTime: 5 * 60_000,
  });

  const { data: gcData, isLoading: gcLoading } = useQuery({
    queryKey: ['master-google-calendar'],
    queryFn: getMasterGoogleCalendar,
    staleTime: 15_000,
  });
  const { data: subscription } = useQuery({
    queryKey: ['master-subscription'],
    queryFn: getMasterSubscription,
    staleTime: 20_000,
  });

  const connectGcMutation = useMutation({
    mutationFn: getMasterGoogleCalendarConnectUrl,
    onSuccess: (data) => {
      const url = data?.url;
      if (!url) {
        if (typeof WebApp?.showAlert === 'function') {
          WebApp.showAlert('Не удалось создать ссылку подключения');
        }
        return;
      }
      if (typeof WebApp?.openLink === 'function') {
        WebApp.openLink(url);
      } else if (typeof window !== 'undefined') {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
    },
  });

  const disconnectGcMutation = useMutation({
    mutationFn: disconnectMasterGoogleCalendar,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-google-calendar'] });
      qc.invalidateQueries({ queryKey: ['master-me'] });
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert('Google Calendar отключён');
      }
    },
  });

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        qc.invalidateQueries({ queryKey: ['master-google-calendar'] });
        qc.invalidateQueries({ queryKey: ['master-me'] });
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [qc]);

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

  const handleGoogleCalendar = () => {
    const isConnected = Boolean(gcData?.connected);

    if (!isConnected) {
      connectGcMutation.mutate();
      return;
    }

    if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup(
        {
          title: 'Отключить Google Calendar?',
          message: 'Новые заказы перестанут автоматически добавляться в календарь.',
          buttons: [
            { id: 'disconnect', type: 'destructive', text: 'Отключить' },
            { type: 'cancel' },
          ],
        },
        (buttonId) => {
          if (buttonId === 'disconnect') {
            disconnectGcMutation.mutate();
          }
        }
      );
      return;
    }

    if (typeof window !== 'undefined' && window.confirm('Отключить Google Calendar?')) {
      disconnectGcMutation.mutate();
    }
  };

  const gcValue = gcLoading
    ? '...'
    : gcData?.connected
      ? (gcData?.email || 'Подключён')
      : 'Не подключён';
  const isSubscriptionActive = subscription?.is_active ?? true;
  const subscriptionUntil = subscription?.subscription_until;
  const subscriptionDays = subscription?.days_left ?? 0;

  const handleOpenSubscription = () => {
    haptic();
    onNavigate('subscription');
  };

  const handleLockedTap = () => {
    setPaywallOpen(true);
  };

  const handlePaywallPay = () => {
    setPaywallOpen(false);
    onNavigate('subscription');
  };

  const handlePaywallInvite = async () => {
    const link = subscription?.referral_link;
    if (!link) {
      setPaywallOpen(false);
      onNavigate('subscription');
      return;
    }
    try {
      if (typeof navigator?.clipboard?.writeText === 'function') {
        await navigator.clipboard.writeText(link);
      }
    } catch (_) {
      // non-critical
    }
    trackMasterReferralLinkCopied('more-paywall').catch(() => {});
    if (typeof WebApp?.showAlert === 'function') {
      WebApp.showAlert('Ссылка скопирована');
    }
    setPaywallOpen(false);
  };

  return (
    <div className="enterprise-more-page">
      <button
        onClick={handleOpenSubscription}
        className="enterprise-subscription-card"
      >
        <div>
          <div className="enterprise-subscription-card-title">
            Подписка
          </div>
          <div className={`enterprise-subscription-card-subtitle${isSubscriptionActive ? '' : ' is-expired'}`}>
            {isSubscriptionActive
              ? `до ${subscriptionUntil ? new Date(subscriptionUntil).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' }) : '—'} · осталось ${subscriptionDays} дн`
              : 'Подписка истекла'}
          </div>
        </div>
        <span className={`enterprise-subscription-card-star${isSubscriptionActive ? '' : ' is-expired'}`}>
          ★
        </span>
      </button>

      <SectionTitle>Клиенты</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell icon={<UsersIcon />} label="Список клиентов" onClick={() => onNavigate('clients')} />
        <Cell
          icon={<LinkIcon />}
          label="Пригласить клиента"
          value={inviteLoading ? '...' : undefined}
          onClick={inviteData?.invite_link ? handleCopyInvite : undefined}
        />
      </div>

      <SectionTitle>Маркетинг</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<SendIcon />}
          label="Рассылки"
          value={isSubscriptionActive ? undefined : '🔒'}
          hideChevron={!isSubscriptionActive}
          onClick={isSubscriptionActive ? () => onNavigate('broadcast') : handleLockedTap}
        />
        <Cell
          icon={<MegaphoneIcon />}
          label="Акции"
          value={isSubscriptionActive ? undefined : '🔒'}
          hideChevron={!isSubscriptionActive}
          onClick={isSubscriptionActive ? () => onNavigate('promos') : handleLockedTap}
        />
      </div>

      <SectionTitle>Настройки</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell icon={<UserIcon />} label="Профиль мастера" onClick={() => onNavigate('profile')} />
        <Cell icon={<GiftIcon />} label="Бонусная программа" onClick={() => onNavigate('bonus')} />
        <Cell icon={<ToolIcon />} label="Справочник услуг" onClick={() => onNavigate('services')} />
        <Cell
          icon={<CalendarIcon />}
          label="Google Calendar"
          value={gcValue}
          onClick={handleGoogleCalendar}
        />
      </div>

      <SectionTitle>Поддержка</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell icon={<MessageIcon />} label="Написать в поддержку" onClick={handleSupport} />
      </div>

      <SectionTitle>О приложении</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell label="Версия" value="2.0.0" />
        <Cell label="crmfit.ru" />
      </div>

      <SubscriptionPaywallSheet
        open={paywallOpen}
        onClose={() => setPaywallOpen(false)}
        onPay={handlePaywallPay}
        onInvite={handlePaywallInvite}
      />
    </div>
  );
}
