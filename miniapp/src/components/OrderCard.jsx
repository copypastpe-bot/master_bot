import { useState } from 'react';
import { useI18n } from '../i18n';
import { DEFAULT_CURRENCY, getCurrencySymbol } from '../master/profileOptions';

const WebApp = window.Telegram?.WebApp;
function haptic(t = 'light') {
  WebApp?.HapticFeedback?.impactOccurred(t);
}

function formatDate(dateStr, lang) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  const locale = lang === 'en' ? 'en-US' : 'ru-RU';
  return d.toLocaleString(locale, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
}

const STATUS_BADGE = {
  new:       { label: 'orderCard.statusNew',       cls: 'is-yellow' },
  reminder:  { label: 'orderCard.statusReminder',  cls: 'is-yellow' },
  confirmed: { label: 'orderCard.statusConfirmed', cls: 'is-blue'   },
  done:      { label: 'orderCard.statusDone',      cls: 'is-green'  },
  cancelled: { label: 'orderCard.statusCancelled', cls: 'is-red'    },
  moved:     { label: 'orderCard.statusMoved',     cls: 'is-grey'   },
};

export default function OrderCard({ order, onConfirm, onReview, onRepeat, onContact }) {
  const { t, lang } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const ds = order.display_status || 'new';
  const badge = STATUS_BADGE[ds] || STATUS_BADGE.new;

  const buttons = [];
  const onAction = (fn) => (event) => {
    event.stopPropagation();
    haptic();
    fn?.();
  };

  if (ds === 'reminder') {
    buttons.push(
      <button key="confirm" className="client-order-card-btn is-primary"
        onClick={onAction(() => onConfirm?.(order.id))}>
        {t('orderCard.btnConfirm')}
      </button>
    );
  }

  if (ds === 'done') {
    if (!order.has_review) {
      buttons.push(
        <button key="review" className="client-order-card-btn is-primary"
          onClick={onAction(() => onReview?.(order))}>
          {t('orderCard.btnReview')}
        </button>
      );
    }
    buttons.push(
      <button key="repeat" className="client-order-card-btn is-outline"
        onClick={onAction(() => onRepeat?.(order))}>
        {t('orderCard.btnRepeat')}
      </button>
    );
  }

  if (ds === 'cancelled') {
    buttons.push(
      <button key="repeat" className="client-order-card-btn is-outline"
        onClick={onAction(() => onRepeat?.(order))}>
        {t('orderCard.btnRepeat')}
      </button>
    );
  }

  const showContact = ['new', 'reminder', 'confirmed'].includes(ds);
  if (showContact) {
    buttons.push(
      <button key="contact" className="client-order-card-btn is-outline"
        onClick={onAction(() => onContact?.(order))}>
        {t('orderCard.btnContact')}
      </button>
    );
  }

  const currency = getCurrencySymbol(order.currency || DEFAULT_CURRENCY);
  const amount = order.amount_total ?? order.price;
  const price = amount != null ? `${amount} ${currency}` : null;
  const bonusEarned = order.bonus_accrued > 0 ? t('orderCard.bonusAccrued', { count: order.bonus_accrued }) : null;
  const bonusSpent = order.bonus_spent > 0 ? t('orderCard.bonusSpent', { count: order.bonus_spent }) : null;
  const services = order.services || order.service_name || '—';

  return (
    <div
      className={`client-order-card${expanded ? ' is-expanded' : ''}`}
      role="button"
      tabIndex={0}
      onClick={() => { haptic(); setExpanded(value => !value); }}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          haptic();
          setExpanded(value => !value);
        }
      }}
    >
      <div className="client-order-card-main">
        <div className="client-order-card-topline">
          <span className={`client-status-badge ${badge.cls}`}>{t(badge.label)}</span>
          <span className="client-order-card-date">
            {formatDate(order.scheduled_at, lang)}
          </span>
        </div>

        <div className="client-order-card-summary">
          <p className="client-order-card-services">
            {services}
          </p>
          <div className="client-order-card-summary-right">
            {price && <span className="client-order-card-price">{price}</span>}
            <span className="client-order-card-chevron" aria-hidden="true">
              {expanded ? '▴' : '▾'}
            </span>
          </div>
        </div>
      </div>

      <div className="client-order-card-expand">
        <div className="client-order-card-expand-inner">
          {order.address && (
            <div className="client-order-card-address">
              <span>{t('orderCard.addressLabel')}</span>
              <strong>{order.address}</strong>
            </div>
          )}

          {(bonusEarned || bonusSpent) && (
            <div className="client-order-card-meta">
              {bonusEarned && <span className="client-order-card-bonuses is-positive">{bonusEarned}</span>}
              {bonusSpent && <span className="client-order-card-bonuses is-negative">{bonusSpent}</span>}
            </div>
          )}

          {ds === 'done' && order.has_review && (
            <p className="client-order-review-left">{t('orderCard.reviewLeft')}</p>
          )}

          {buttons.length > 0 && (
            <div className="client-order-card-actions">{buttons}</div>
          )}
        </div>
      </div>
    </div>
  );
}
