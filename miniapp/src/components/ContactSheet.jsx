import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

export default function ContactSheet({ master, onClose }) {
  const { t } = useI18n();
  const phone = master?.phone || master?.contacts;
  const telegram = master?.telegram;

  const handlePhone = () => {
    WebApp?.HapticFeedback?.impactOccurred('light');
    if (phone) window.open(`tel:${phone.replace(/\s/g, '')}`, '_blank');
  };

  const handleTelegram = () => {
    WebApp?.HapticFeedback?.impactOccurred('light');
    if (telegram) {
      const username = telegram.replace(/^@/, '');
      window.open(`tg://resolve?domain=${username}`, '_blank');
    }
  };

  return (
    <div className="client-sheet-overlay" onClick={onClose}>
      <div className="client-sheet" onClick={e => e.stopPropagation()}>
        <p className="client-sheet-title">{t('contactSheet.title')}</p>
        {phone && (
          <button className="client-sheet-btn" onClick={handlePhone}>
            📞 {t('contactSheet.phone')}
          </button>
        )}
        {telegram && (
          <button className="client-sheet-btn is-secondary" onClick={handleTelegram}>
            ✈️ {t('contactSheet.telegram')}
          </button>
        )}
        <button className="client-sheet-btn is-secondary" onClick={onClose}>
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}
