import { useI18n } from '../../i18n';
const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

export default function SubscriptionPaywallSheet({
  open,
  onClose,
  onPay,
  onInvite,
  title,
  description,
}) {
  const { t } = useI18n();
  const resolvedTitle = title || t('paywall.title');
  const resolvedDescription = description || t('paywall.description');
  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.45)',
        zIndex: 300,
        display: 'flex',
        alignItems: 'flex-end',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          borderRadius: '16px 16px 0 0',
          background: 'var(--tg-section-bg)',
          border: '1px solid var(--tg-enterprise-border)',
          borderBottom: 'none',
          padding: '10px 14px calc(18px + env(safe-area-inset-bottom))',
        }}
      >
        <div
          style={{
            width: 44,
            height: 4,
            borderRadius: 3,
            background: 'var(--tg-hint)',
            opacity: 0.45,
            margin: '2px auto 16px',
          }}
        />

        <div
          style={{
            width: 64,
            height: 64,
            margin: '0 auto 14px',
            borderRadius: 32,
            background: '#efe3b9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#b28316',
            fontSize: 34,
            lineHeight: 1,
          }}
        >
          ★
        </div>

        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 4 }}>
            {resolvedTitle}
          </div>
          <div style={{ color: 'var(--tg-hint)', fontSize: 16, lineHeight: 1.35 }}>
            {resolvedDescription}
          </div>
        </div>

        <button
          onClick={() => { haptic(); onPay?.(); }}
          style={{
            width: '100%',
            border: 'none',
            borderRadius: 14,
            padding: '14px 12px',
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            fontSize: 16,
            fontWeight: 700,
            cursor: 'pointer',
            marginBottom: 10,
          }}
        >
          {t('paywall.pay')}
        </button>

        <button
          onClick={() => { haptic(); onInvite?.(); }}
          style={{
            width: '100%',
            border: '1px solid var(--tg-enterprise-border)',
            borderRadius: 14,
            padding: '14px 12px',
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-text)',
            fontSize: 16,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {t('paywall.invite')}
        </button>
      </div>
    </div>
  );
}
