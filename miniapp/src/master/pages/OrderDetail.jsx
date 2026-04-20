import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getMasterOrder,
  completeMasterOrder,
  moveMasterOrder,
  cancelMasterOrder,
} from '../../api/client';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

const STATUS_COLOR = {
  new: 'var(--tg-button)',
  confirmed: '#f5a623',
  done: '#27ae60',
  cancelled: '#e74c3c',
  moved: '#8e44ad',
};

const STATUS_TINT = {
  new: 'rgba(51, 144, 236, 0.16)',
  confirmed: 'rgba(245, 166, 35, 0.18)',
  done: 'rgba(39, 174, 96, 0.18)',
  cancelled: 'rgba(231, 76, 60, 0.16)',
  moved: 'rgba(142, 68, 173, 0.16)',
};

function formatDateTime(iso, locale) {
  if (!iso) return '—';
  const d = new Date(iso.replace(' ', 'T'));
  if (isNaN(d)) return iso;
  const date = d.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
  const time = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  return { date, time };
}

function formatAmount(value, locale) {
  return Number(value || 0).toLocaleString(locale);
}

function getStatusLabel(status, tr) {
  const labels = {
    new: tr('Новый', 'New'),
    confirmed: tr('Подтверждён', 'Confirmed'),
    done: tr('Выполнен', 'Done'),
    cancelled: tr('Отменён', 'Cancelled'),
    moved: tr('Перенесён', 'Moved'),
  };
  return labels[status] || status;
}

function getPaymentLabel(type, tr) {
  const labels = {
    cash: tr('Наличные', 'Cash'),
    card: tr('Карта', 'Card'),
    transfer: tr('Перевод', 'Transfer'),
    invoice: tr('По счёту', 'Invoice'),
  };
  return labels[type] || type || '—';
}

// ============================================================
// Bottom Sheet
// ============================================================
function BottomSheet({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100,
        display: 'flex', alignItems: 'flex-end',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          background: 'var(--tg-section-bg)',
          borderRadius: '16px 16px 0 0',
          padding: '20px 16px 32px',
          maxHeight: '85vh',
          overflowY: 'auto',
        }}
      >
        <div style={{
          width: 36, height: 4, background: 'var(--tg-hint)',
          borderRadius: 2, margin: '0 auto 16px',
        }} />
        {title && (
          <h3 style={{ margin: '0 0 16px', color: 'var(--tg-text)', fontSize: 17 }}>{title}</h3>
        )}
        {children}
      </div>
    </div>
  );
}

// ============================================================
// Complete Order Sheet
// ============================================================
function CompleteSheet({ order, master, onSuccess }) {
  const { tr } = useI18n();
  const [amount, setAmount] = useState(String(order.amount_total || 0));
  const [paymentType, setPaymentType] = useState('cash');
  const [useBonus, setUseBonus] = useState(false);
  const [bonusSpent, setBonusSpent] = useState('0');
  const [comment, setComment] = useState(order.note || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const clientBalance = order.client?.bonus_balance || 0;
  const bonusEnabled = master?.bonus_enabled && clientBalance > 0;
  const maxBonusPercent = master?.bonus_max_spend || 50;

  const amountNum = parseInt(amount, 10) || 0;
  const bonusSpentNum = useBonus ? (parseInt(bonusSpent, 10) || 0) : 0;
  const maxBonus = Math.min(clientBalance, Math.floor(amountNum * maxBonusPercent / 100));
  const amountPaid = Math.max(0, amountNum - bonusSpentNum);
  const bonusRate = master?.bonus_rate || 0;
  const bonusAccrued = master?.bonus_enabled ? Math.round(amountPaid * bonusRate / 100) : 0;

  const handleSubmit = async () => {
    haptic('medium');
    setError('');
    if (amountNum <= 0) { setError(tr('Укажите сумму', 'Specify amount')); return; }
    if (bonusSpentNum < 0 || bonusSpentNum > maxBonus) {
      setError(tr(`Бонусы: от 0 до ${maxBonus}`, `Bonuses: from 0 to ${maxBonus}`));
      return;
    }
    setLoading(true);
    try {
      const result = await completeMasterOrder(order.id, {
        amount: amountNum,
        payment_type: paymentType,
        bonus_spent: bonusSpentNum,
        comment: comment.trim() || null,
      });
      onSuccess(result);
    } catch (e) {
      setError(e?.response?.data?.detail || tr('Ошибка при проведении', 'Failed to complete order'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label style={styles.label}>{tr('Сумма', 'Amount')}</label>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          style={styles.input}
          min="1"
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={styles.label}>{tr('Способ оплаты', 'Payment type')}</label>
        <div style={{ display: 'flex', gap: 8 }}>
          {['cash', 'card', 'transfer', 'invoice'].map(pt => (
            <button
              key={pt}
              onClick={() => { haptic(); setPaymentType(pt); }}
              style={{
                ...styles.pillBtn,
                background: paymentType === pt ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                color: paymentType === pt ? 'var(--tg-button-text)' : 'var(--tg-text)',
                flex: 1,
              }}
            >
              {getPaymentLabel(pt, tr)}
            </button>
          ))}
        </div>
      </div>

      {bonusEnabled && (
        <div style={{ marginBottom: 16 }}>
          <div
            onClick={() => { haptic(); setUseBonus(v => !v); }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 0', cursor: 'pointer',
            }}
          >
            <span style={{ color: 'var(--tg-text)', fontSize: 15 }}>
              {tr(`Списать бонусы (баланс: ${clientBalance})`, `Spend bonuses (balance: ${clientBalance})`)}
            </span>
            <div style={{
              width: 44, height: 24, borderRadius: 12,
              background: useBonus ? 'var(--tg-button)' : 'var(--tg-hint)',
              position: 'relative', transition: 'background 0.2s',
            }}>
              <div style={{
                position: 'absolute', top: 2, left: useBonus ? 22 : 2,
                width: 20, height: 20, borderRadius: '50%',
                background: '#fff', transition: 'left 0.2s',
              }} />
            </div>
          </div>
          {useBonus && (
            <div>
              <label style={styles.label}>{tr(`Сумма бонусов (макс. ${maxBonus})`, `Bonus amount (max ${maxBonus})`)}</label>
              <input
                type="number"
                value={bonusSpent}
                onChange={e => setBonusSpent(e.target.value)}
                style={styles.input}
                min="0"
                max={maxBonus}
              />
            </div>
          )}
        </div>
      )}

      <div style={{
        background: 'var(--tg-secondary-bg)', borderRadius: 10,
        padding: '12px 14px', marginBottom: 16, fontSize: 14,
        color: 'var(--tg-text)',
      }}>
        {bonusSpentNum > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ color: 'var(--tg-hint)' }}>{tr('Списано бонусов:', 'Bonuses spent:')}</span>
            <span>— {bonusSpentNum}</span>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ color: 'var(--tg-hint)' }}>{tr('Итого к оплате:', 'Total to pay:')}</span>
          <span style={{ fontWeight: 600 }}>{amountPaid}</span>
        </div>
        {master?.bonus_enabled && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--tg-hint)' }}>{tr('Будет начислено:', 'Will be accrued:')}</span>
            <span style={{ color: '#27ae60' }}>+ {bonusAccrued}</span>
          </div>
        )}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={styles.label}>{tr('Комментарий к заказу', 'Order comment')}</label>
        <textarea
          value={comment}
          onChange={e => setComment(e.target.value)}
          rows={3}
          placeholder={tr('Например: особенности услуги, пожелания, что сделали', 'For example: service details, wishes, what was done')}
          style={{ ...styles.input, resize: 'vertical', minHeight: 82 }}
        />
      </div>

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{ ...styles.primaryBtn, opacity: loading ? 0.6 : 1 }}
      >
        {loading ? tr('Проводим...', 'Completing...') : tr('Подтвердить', 'Confirm')}
      </button>
    </>
  );
}

// ============================================================
// Date/time display helpers
// ============================================================
function formatDateDisplay(iso, locale, tr) {
  if (!iso) return tr('Выберите дату', 'Pick date');
  return new Date(iso + 'T00:00:00').toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
}

function DatePickerField({ label, value, onChange, inputStyle, labelStyle, locale, tr }) {
  return (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={labelStyle}>{label}</label>}
      <div style={{ position: 'relative' }}>
        <div style={{ ...inputStyle, pointerEvents: 'none' }}>{formatDateDisplay(value, locale, tr)}</div>
        <input
          type="date"
          value={value}
          onChange={onChange}
          style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }}
        />
      </div>
    </div>
  );
}

function TimePickerField({ label, value, onChange, inputStyle, labelStyle }) {
  return (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={labelStyle}>{label}</label>}
      <div style={{ position: 'relative' }}>
        <div style={{ ...inputStyle, pointerEvents: 'none' }}>{value || '00:00'}</div>
        <input
          type="time"
          value={value}
          onChange={onChange}
          style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }}
        />
      </div>
    </div>
  );
}

// ============================================================
// Move Order Sheet
// ============================================================
function MoveSheet({ order, onSuccess }) {
  const { tr, locale } = useI18n();
  const scheduled = formatDateTime(order.scheduled_at, locale);
  const [newDate, setNewDate] = useState(
    order.scheduled_at ? order.scheduled_at.substring(0, 10) : ''
  );
  const [newTime, setNewTime] = useState(
    scheduled && scheduled.time ? scheduled.time : '10:00'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    haptic('medium');
    setError('');
    if (!newDate || !newTime) { setError(tr('Укажите дату и время', 'Specify date and time')); return; }
    setLoading(true);
    try {
      const result = await moveMasterOrder(order.id, { new_date: newDate, new_time: newTime });
      onSuccess(result);
    } catch (e) {
      setError(e?.response?.data?.detail || tr('Ошибка при переносе', 'Failed to move order'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <DatePickerField
        label={tr('Новая дата', 'New date')}
        value={newDate}
        onChange={e => setNewDate(e.target.value)}
        inputStyle={styles.input}
        labelStyle={styles.label}
        locale={locale}
        tr={tr}
      />
      <TimePickerField
        label={tr('Новое время', 'New time')}
        value={newTime}
        onChange={e => setNewTime(e.target.value)}
        inputStyle={styles.input}
        labelStyle={styles.label}
      />

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{ ...styles.primaryBtn, opacity: loading ? 0.6 : 1 }}
      >
        {loading ? tr('Переносим...', 'Moving...') : tr('Перенести', 'Move')}
      </button>
    </>
  );
}

// ============================================================
// Main OrderDetail component
// ============================================================
export default function OrderDetail({ orderId, onBack, onUpdated, onNavigate }) {
  const { tr, locale } = useI18n();
  const queryClient = useQueryClient();
  const [sheet, setSheet] = useState(null); // 'complete' | 'move' | null
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [actionError, setActionError] = useState('');

  const { data: order, isLoading, error } = useQuery({
    queryKey: ['master-order', orderId],
    queryFn: () => getMasterOrder(orderId),
    staleTime: 10_000,
  });

  // Master data for bonus calculations — from dashboard/me cache
  const activeMaster = queryClient.getQueryData(['master-me']);

  const handleActionSuccess = (result) => {
    haptic('medium');
    setSheet(null);
    setCancelConfirm(false);
    setActionError('');
    // Invalidate caches — React Query will refetch automatically
    queryClient.invalidateQueries({ queryKey: ['master-order', orderId] });
    queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['master-calendar'] });
    queryClient.invalidateQueries({ queryKey: ['master-orders'] });
    if (onUpdated) onUpdated(result);
  };

  const handleCancel = async () => {
    haptic('medium');
    setActionError('');
    try {
      const result = await cancelMasterOrder(orderId, {});
      handleActionSuccess(result);
    } catch (e) {
      setActionError(e?.response?.data?.detail || tr('Ошибка при отмене', 'Failed to cancel'));
      setCancelConfirm(false);
    }
  };

  const hasTgBack = typeof WebApp?.BackButton?.show === 'function';

  if (isLoading) {
    return (
      <div style={{ padding: '16px' }}>
        {!hasTgBack && <button onClick={() => { haptic(); onBack(); }} style={styles.backBtn}>{tr('← Назад', '← Back')}</button>}
        <div style={{ marginTop: 24 }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ ...styles.skeleton, marginBottom: 12, height: 60, borderRadius: 12 }} />
          ))}
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div style={{ padding: '16px' }}>
        {!hasTgBack && <button onClick={() => { haptic(); onBack(); }} style={styles.backBtn}>{tr('← Назад', '← Back')}</button>}
        <p style={{ color: '#e74c3c', marginTop: 24 }}>
          {error?.response?.data?.detail || tr('Заказ не найден', 'Order not found')}
        </p>
      </div>
    );
  }

  const scheduled = formatDateTime(order.scheduled_at, locale);
  const isActive = order.status === 'new' || order.status === 'confirmed';
  const client = order.client || {};
  const services = order.services || [];

  return (
    <div className="master-detail-page order-detail-page">
      {/* Back — only shown when Telegram BackButton unavailable */}
      {!hasTgBack && (
        <div style={{ padding: '12px 16px 0' }}>
          <button onClick={() => { haptic(); onBack(); }} style={styles.backBtn}>
            {tr('← Назад', '← Back')}
          </button>
        </div>
      )}

      {/* Block 1: Status + DateTime */}
      <div style={styles.heroCard}>
        <span style={{
          display: 'inline-block',
          padding: '5px 11px',
          borderRadius: 20,
          fontSize: 13,
          fontWeight: 700,
          background: STATUS_TINT[order.status] || 'rgba(127,127,127,0.16)',
          color: STATUS_COLOR[order.status] || 'var(--tg-hint)',
          marginBottom: 8,
        }}>
          {getStatusLabel(order.status, tr)}
        </span>

        {scheduled && (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: 38, fontWeight: 800, color: 'var(--tg-text)', lineHeight: 1.1 }}>
              {scheduled.time}
            </span>
            <span style={{ fontSize: 18, color: 'var(--tg-hint)', fontWeight: 600 }}>
              {scheduled.date}
            </span>
          </div>
        )}
      </div>

      {/* Block 2: Client */}
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>{tr('Клиент', 'Client')}</h3>
        {client.tg_id ? (
          <a
            href={`tg://user?id=${client.tg_id}`}
            style={{ ...styles.clientName, textDecoration: 'none' }}
            onClick={() => haptic()}
          >
            {client.name || '—'}
          </a>
        ) : (
          <span style={styles.clientName}>{client.name || '—'}</span>
        )}

        {client.phone && (
          <a
            href={`tel:${client.phone}`}
            onClick={() => haptic()}
            style={{ display: 'block', color: 'var(--tg-button)', fontSize: 16, marginTop: 6, fontWeight: 600 }}
          >
            {client.phone}
          </a>
        )}

        {client.bonus_balance !== undefined && (
          <div style={{ marginTop: 10, fontSize: 13, color: 'var(--tg-hint)' }}>
            {tr('Бонусный баланс', 'Bonus balance')}: <span style={{ color: 'var(--tg-text)', fontWeight: 600 }}>
              {client.bonus_balance}
            </span>
          </div>
        )}
        {client.id && typeof onNavigate === 'function' && (
          <button
            onClick={() => { haptic(); onNavigate('client', { id: client.id }); }}
            style={{
              marginTop: 10,
              border: 'none',
              background: 'var(--tg-secondary-bg)',
              color: 'var(--tg-button)',
              borderRadius: 9,
              padding: '8px 12px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {tr('Открыть карточку клиента', 'Open client card')}
          </button>
        )}
      </div>

      {/* Block 3: Services + Amount */}
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>{tr('Услуги', 'Services')}</h3>
        {services.length > 0 ? (
          services.map((s, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              paddingBottom: 8, marginBottom: 8,
              borderBottom: i < services.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
            }}>
              <span style={{ color: 'var(--tg-text)', fontSize: 15 }}>{s.name}</span>
              {s.price > 0 && (
                <span style={{ color: 'var(--tg-hint)', fontSize: 14 }}>{formatAmount(s.price, locale)} ₽</span>
              )}
            </div>
          ))
        ) : (
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>{tr('Услуги не указаны', 'No services specified')}</p>
        )}

        <div style={{
          display: 'flex', justifyContent: 'space-between', marginTop: 8,
          paddingTop: 8, borderTop: '1px solid var(--tg-secondary-bg)',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--tg-text)', fontSize: 16 }}>{tr('Итого', 'Total')}</span>
          <span style={{ fontWeight: 700, color: 'var(--tg-text)', fontSize: 16 }}>
            {formatAmount(order.amount_total, locale)} ₽
          </span>
        </div>

        {order.address && (
          <div
            style={{
              marginTop: 12,
              fontSize: 16,
              color: 'var(--tg-text)',
              fontWeight: 650,
              padding: '10px 12px',
              borderRadius: 10,
              background: 'var(--tg-secondary-bg)',
              lineHeight: 1.35,
            }}
          >
            📍 {order.address}
          </div>
        )}
      </div>

      {/* Block 3b: Payment info (for done orders) */}
      {order.status === 'done' && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>{tr('Оплата', 'Payment')}</h3>
          <div style={styles.row}>
            <span style={styles.rowLabel}>{tr('Способ', 'Method')}</span>
            <span style={styles.rowValue}>{getPaymentLabel(order.payment_type, tr)}</span>
          </div>
          {order.bonus_spent > 0 && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>{tr('Списано бонусов', 'Bonuses spent')}</span>
              <span style={styles.rowValue}>— {order.bonus_spent}</span>
            </div>
          )}
          {order.bonus_accrued > 0 && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>{tr('Начислено бонусов', 'Bonuses accrued')}</span>
              <span style={{ ...styles.rowValue, color: '#27ae60' }}>+ {order.bonus_accrued}</span>
            </div>
          )}
          {order.note && (
            <div style={{ marginTop: 10 }}>
              <div style={{ ...styles.rowLabel, marginBottom: 4 }}>{tr('Комментарий', 'Comment')}</div>
              <div style={{ color: 'var(--tg-text)', fontSize: 14, whiteSpace: 'pre-wrap' }}>
                {order.note}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Cancel reason */}
      {order.status === 'cancelled' && order.cancel_reason && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>{tr('Причина отмены', 'Cancellation reason')}</h3>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: 0 }}>{order.cancel_reason}</p>
        </div>
      )}

      {/* Block 4: Actions (only for active orders) */}
      {isActive && (
        <div style={{ ...styles.card, display: 'flex', flexDirection: 'column', gap: 10, padding: '12px' }}>
          <button
            onClick={() => { haptic(); setSheet('complete'); }}
            style={styles.actionBtn}
          >
            {tr('Провести', 'Complete')}
          </button>
          <button
            onClick={() => { haptic(); setSheet('move'); }}
            style={{ ...styles.actionBtn, background: 'var(--tg-secondary-bg)', color: 'var(--tg-text)' }}
          >
            {tr('Перенести', 'Move')}
          </button>
          <button
            onClick={() => { haptic(); setCancelConfirm(true); }}
            style={{ ...styles.actionBtn, background: '#e74c3c22', color: '#e74c3c' }}
          >
            {tr('Отменить', 'Cancel')}
          </button>
        </div>
      )}

      {actionError && (
        <p style={{ color: '#e74c3c', fontSize: 13, padding: '8px 16px' }}>{actionError}</p>
      )}

      {/* Complete Sheet */}
      <BottomSheet
        open={sheet === 'complete'}
        onClose={() => setSheet(null)}
        title={tr('Провести заказ', 'Complete order')}
      >
        <CompleteSheet
          order={order}
          master={activeMaster}
          onClose={() => setSheet(null)}
          onSuccess={handleActionSuccess}
        />
      </BottomSheet>

      {/* Move Sheet */}
      <BottomSheet
        open={sheet === 'move'}
        onClose={() => setSheet(null)}
        title={tr('Перенести заказ', 'Move order')}
      >
        <MoveSheet
          order={order}
          onClose={() => setSheet(null)}
          onSuccess={handleActionSuccess}
        />
      </BottomSheet>

      {/* Cancel Confirm Dialog */}
      <BottomSheet
        open={cancelConfirm}
        onClose={() => setCancelConfirm(false)}
        title={tr('Отменить заказ?', 'Cancel order?')}
      >
        <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 20 }}>
          {tr('Заказ будет отменён, клиент получит уведомление.', 'The order will be cancelled, the client will be notified.')}
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => { haptic(); setCancelConfirm(false); }}
            style={{ ...styles.actionBtn, flex: 1, background: 'var(--tg-secondary-bg)', color: 'var(--tg-text)' }}
          >
            {tr('Нет', 'No')}
          </button>
          <button
            onClick={handleCancel}
            style={{ ...styles.actionBtn, flex: 1, background: '#e74c3c', color: '#fff' }}
          >
            {tr('Да, отменить', 'Yes, cancel')}
          </button>
        </div>
      </BottomSheet>
    </div>
  );
}

// ============================================================
// Styles
// ============================================================
const styles = {
  backBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--tg-button)',
    fontSize: 15,
    cursor: 'pointer',
    padding: 0,
    marginBottom: 8,
  },
  heroCard: {
    margin: '8px 0 0',
    background: 'var(--tg-section-bg)',
    borderRadius: 16,
    padding: '14px 16px',
    border: '1px solid var(--tg-enterprise-border)',
    boxShadow: 'var(--tg-enterprise-shadow)',
  },
  card: {
    margin: '8px 0 0',
    background: 'var(--tg-section-bg)',
    borderRadius: 16,
    padding: '14px 16px',
    border: '1px solid var(--tg-enterprise-border)',
    boxShadow: 'var(--tg-enterprise-shadow)',
  },
  cardTitle: {
    margin: '0 0 10px',
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--tg-hint)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  clientName: {
    fontSize: 30,
    fontWeight: 800,
    color: 'var(--tg-text)',
    display: 'block',
    lineHeight: 1.15,
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: 8,
    marginBottom: 8,
  },
  rowLabel: {
    color: 'var(--tg-hint)',
    fontSize: 14,
  },
  rowValue: {
    color: 'var(--tg-text)',
    fontSize: 14,
    fontWeight: 600,
  },
  label: {
    display: 'block',
    fontSize: 13,
    color: 'var(--tg-hint)',
    marginBottom: 6,
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    padding: '10px 12px',
    borderRadius: 10,
    border: '1px solid var(--tg-hint)',
    background: 'var(--tg-bg)',
    color: 'var(--tg-text)',
    fontSize: 16,
  },
  pillBtn: {
    padding: '8px 12px',
    borderRadius: 20,
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 500,
  },
  primaryBtn: {
    width: '100%',
    padding: '14px',
    borderRadius: 12,
    border: 'none',
    background: 'var(--tg-button)',
    color: 'var(--tg-button-text)',
    fontSize: 16,
    fontWeight: 600,
    cursor: 'pointer',
  },
  actionBtn: {
    width: '100%',
    padding: '14px',
    borderRadius: 11,
    border: 'none',
    background: 'var(--tg-button)',
    color: 'var(--tg-button-text)',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
  },
  skeleton: {
    background: 'var(--tg-secondary-bg)',
    animation: 'skeleton-pulse 1.5s ease-in-out infinite',
  },
};
