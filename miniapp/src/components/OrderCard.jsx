import { useI18n } from '../i18n';

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
  const ds = order.display_status || 'new';
  const badge = STATUS_BADGE[ds] || STATUS_BADGE.new;

  const buttons = [];

  if (ds === 'reminder') {
    buttons.push(
      <button key="confirm" className="client-order-card-btn is-primary"
        onClick={() => { haptic(); onConfirm?.(order.id); }}>
        {t('orderCard.btnConfirm')}
      </button>
    );
  }

  if (ds === 'done') {
    if (!order.has_review) {
      buttons.push(
        <button key="review" className="client-order-card-btn is-primary"
          onClick={() => { haptic(); onReview?.(order); }}>
          {t('orderCard.btnReview')}
        </button>
      );
      buttons.push(
        <button key="repeat" className="client-order-card-btn is-outline"
          onClick={() => { haptic(); onRepeat?.(order); }}>
          {t('orderCard.btnRepeat')}
        </button>
      );
    }
  }

  const showContact = ['new', 'reminder', 'confirmed'].includes(ds);
  if (showContact) {
    buttons.push(
      <button key="contact" className="client-order-card-btn is-outline"
        onClick={() => { haptic(); onContact?.(order); }}>
        {t('orderCard.btnContact')}
      </button>
    );
  }

  const currency = order.currency || '₽';
  const price = order.price != null ? `${order.price} ${currency}` : null;
  const bonusEarned = order.bonus_accrued > 0 ? `+${order.bonus_accrued} бонусов` : null;
  const bonusSpent = order.bonus_spent > 0 ? `−${order.bonus_spent} бонусов` : null;

  return (
    <div className="client-order-card">
      <div className="client-order-card-topline">
        <span className={`client-status-badge ${badge.cls}`}>{t(badge.label)}</span>
        <span className="client-order-card-date">
          {formatDate(order.scheduled_at, lang)}
        </span>
      </div>

      <p className="client-order-card-services">
        {order.services || order.service_name || '—'}
      </p>

      {(price || bonusEarned || bonusSpent) && (
        <div className="client-order-card-meta">
          {price && <span className="client-order-card-price">{price}</span>}
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
  );
}
