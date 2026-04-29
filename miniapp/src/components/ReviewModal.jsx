import { useState } from 'react';
import { createClientOrderReview } from '../api/client';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

function formatDate(dateStr, lang) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  const locale = lang === 'en' ? 'en-US' : 'ru-RU';
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
}

export default function ReviewModal({ order, onClose, onSuccess }) {
  const { t, lang } = useI18n();
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (text.trim().length < 10) {
      setError(t('reviewModal.minLengthError'));
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await createClientOrderReview(order.id, { text: text.trim() });
      WebApp?.HapticFeedback?.notificationOccurred('success');
      onSuccess?.(order.id);
      onClose?.();
    } catch {
      setError(t('reviewModal.minLengthError'));
      WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setSubmitting(false);
    }
  };

  const subtitle = [order.services || order.service_name, formatDate(order.scheduled_at, lang)]
    .filter(Boolean).join(' · ');

  return (
    <div className="client-sheet-overlay" onClick={onClose}>
      <div className="client-sheet" onClick={e => e.stopPropagation()}>
        <p className="client-sheet-title">{t('reviewModal.title')}</p>
        {subtitle && (
          <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 12, textAlign: 'center' }}>
            {subtitle}
          </p>
        )}
        <textarea
          value={text}
          onChange={e => { setText(e.target.value); setError(''); }}
          placeholder={t('reviewModal.placeholder')}
          rows={4}
          style={{
            width: '100%', background: 'rgba(255,255,255,0.06)', border: 'none',
            borderRadius: 12, padding: '12px 14px', color: 'var(--tg-theme-text-color)',
            fontSize: 15, resize: 'none', fontFamily: 'inherit', outline: 'none',
            boxSizing: 'border-box', marginBottom: error ? 6 : 12,
          }}
        />
        {error && (
          <p style={{ fontSize: 13, color: '#f44336', marginBottom: 10 }}>{error}</p>
        )}
        <button
          className="client-sheet-btn"
          onClick={handleSubmit}
          disabled={submitting}
          style={{ opacity: submitting ? 0.7 : 1 }}
        >
          {submitting ? t('reviewModal.submitting') : t('reviewModal.submit')}
        </button>
        <button className="client-sheet-btn is-secondary" onClick={onClose}>
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}
