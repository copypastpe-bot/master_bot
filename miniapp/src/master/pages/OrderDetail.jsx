import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getMasterOrder,
  completeMasterOrder,
  moveMasterOrder,
  cancelMasterOrder,
} from '../../api/client';
import { useBackButton } from '../hooks/useBackButton';

const WebApp = window.Telegram?.WebApp;

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

const STATUS_LABEL = {
  new: '🆕 Новый',
  confirmed: '📌 Подтверждён',
  done: '✅ Выполнен',
  cancelled: '❌ Отменён',
  moved: '📅 Перенесён',
};

const STATUS_COLOR = {
  new: 'var(--tg-button)',
  confirmed: '#f5a623',
  done: '#27ae60',
  cancelled: '#e74c3c',
  moved: '#8e44ad',
};

const PAYMENT_LABELS = {
  cash: 'Наличные',
  card: 'Карта',
  transfer: 'Перевод',
  invoice: 'По счёту',
};

function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso.replace(' ', 'T'));
  if (isNaN(d)) return iso;
  const day = d.getDate();
  const months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const month = months[d.getMonth()];
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return { date: `${day} ${month}`, time: `${hh}:${mm}` };
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
function CompleteSheet({ order, master, onClose, onSuccess }) {
  const [amount, setAmount] = useState(String(order.amount_total || 0));
  const [paymentType, setPaymentType] = useState('cash');
  const [useBonus, setUseBonus] = useState(false);
  const [bonusSpent, setBonusSpent] = useState('0');
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
    if (amountNum <= 0) { setError('Укажите сумму'); return; }
    if (bonusSpentNum < 0 || bonusSpentNum > maxBonus) {
      setError(`Бонусы: от 0 до ${maxBonus}`);
      return;
    }
    setLoading(true);
    try {
      const result = await completeMasterOrder(order.id, {
        amount: amountNum,
        payment_type: paymentType,
        bonus_spent: bonusSpentNum,
      });
      onSuccess(result);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка при проведении');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label style={styles.label}>Сумма</label>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          style={styles.input}
          min="1"
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={styles.label}>Способ оплаты</label>
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
              {PAYMENT_LABELS[pt]}
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
              Списать бонусы (баланс: {clientBalance})
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
              <label style={styles.label}>Сумма бонусов (макс. {maxBonus})</label>
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
            <span style={{ color: 'var(--tg-hint)' }}>Списано бонусов:</span>
            <span>— {bonusSpentNum}</span>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ color: 'var(--tg-hint)' }}>Итого к оплате:</span>
          <span style={{ fontWeight: 600 }}>{amountPaid}</span>
        </div>
        {master?.bonus_enabled && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--tg-hint)' }}>Будет начислено:</span>
            <span style={{ color: '#27ae60' }}>+ {bonusAccrued}</span>
          </div>
        )}
      </div>

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{ ...styles.primaryBtn, opacity: loading ? 0.6 : 1 }}
      >
        {loading ? 'Проводим...' : 'Подтвердить'}
      </button>
    </>
  );
}

// ============================================================
// Date/time display helpers
// ============================================================
const DATE_MONTHS = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];

function formatDateDisplay(iso) {
  if (!iso) return 'Выберите дату';
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${DATE_MONTHS[m - 1]} ${y}`;
}

function DatePickerField({ label, value, onChange, inputStyle, labelStyle }) {
  return (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={labelStyle}>{label}</label>}
      <div style={{ position: 'relative' }}>
        <div style={{ ...inputStyle, pointerEvents: 'none' }}>{formatDateDisplay(value)}</div>
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
function MoveSheet({ order, onClose, onSuccess }) {
  const scheduled = formatDateTime(order.scheduled_at);
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
    if (!newDate || !newTime) { setError('Укажите дату и время'); return; }
    setLoading(true);
    try {
      const result = await moveMasterOrder(order.id, { new_date: newDate, new_time: newTime });
      onSuccess(result);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка при переносе');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <DatePickerField
        label="Новая дата"
        value={newDate}
        onChange={e => setNewDate(e.target.value)}
        inputStyle={styles.input}
        labelStyle={styles.label}
      />
      <TimePickerField
        label="Новое время"
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
        {loading ? 'Переносим...' : 'Перенести'}
      </button>
    </>
  );
}

// ============================================================
// Main OrderDetail component
// ============================================================
export default function OrderDetail({ orderId, onBack, onUpdated }) {
  const queryClient = useQueryClient();
  const [sheet, setSheet] = useState(null); // 'complete' | 'move' | null
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [actionError, setActionError] = useState('');

  const stableOnBack = useCallback(() => onBack(), [onBack]);
  useBackButton(stableOnBack);

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
      setActionError(e?.response?.data?.detail || 'Ошибка при отмене');
      setCancelConfirm(false);
    }
  };

  const hasTgBack = typeof WebApp?.BackButton?.show === 'function';

  if (isLoading) {
    return (
      <div style={{ padding: '16px' }}>
        {!hasTgBack && <button onClick={() => { haptic(); onBack(); }} style={styles.backBtn}>← Назад</button>}
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
        {!hasTgBack && <button onClick={() => { haptic(); onBack(); }} style={styles.backBtn}>← Назад</button>}
        <p style={{ color: '#e74c3c', marginTop: 24 }}>
          {error?.response?.data?.detail || 'Заказ не найден'}
        </p>
      </div>
    );
  }

  const scheduled = formatDateTime(order.scheduled_at);
  const isActive = order.status === 'new' || order.status === 'confirmed';
  const client = order.client || {};
  const services = order.services || [];

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Back — only shown when Telegram BackButton unavailable */}
      {!hasTgBack && (
        <div style={{ padding: '12px 16px 0' }}>
          <button onClick={() => { haptic(); onBack(); }} style={styles.backBtn}>
            ← Назад
          </button>
        </div>
      )}

      {/* Block 1: Status + DateTime */}
      <div style={{ padding: '12px 16px 0' }}>
        <span style={{
          display: 'inline-block',
          padding: '4px 10px',
          borderRadius: 20,
          fontSize: 13,
          fontWeight: 600,
          background: STATUS_COLOR[order.status] + '22',
          color: STATUS_COLOR[order.status],
          marginBottom: 8,
        }}>
          {STATUS_LABEL[order.status] || order.status}
        </span>

        {scheduled && (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--tg-text)' }}>
              {scheduled.time}
            </span>
            <span style={{ fontSize: 18, color: 'var(--tg-hint)' }}>
              {scheduled.date}
            </span>
          </div>
        )}
      </div>

      {/* Block 2: Client */}
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Клиент</h3>
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
            style={{ display: 'block', color: 'var(--tg-button)', fontSize: 15, marginTop: 4 }}
          >
            {client.phone}
          </a>
        )}

        {client.bonus_balance !== undefined && (
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--tg-hint)' }}>
            Бонусный баланс: <span style={{ color: 'var(--tg-text)', fontWeight: 600 }}>
              {client.bonus_balance}
            </span>
          </div>
        )}
      </div>

      {/* Block 3: Services + Amount */}
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Услуги</h3>
        {services.length > 0 ? (
          services.map((s, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              paddingBottom: 8, marginBottom: 8,
              borderBottom: i < services.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
            }}>
              <span style={{ color: 'var(--tg-text)', fontSize: 15 }}>{s.name}</span>
              {s.price > 0 && (
                <span style={{ color: 'var(--tg-hint)', fontSize: 14 }}>{s.price}</span>
              )}
            </div>
          ))
        ) : (
          <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Услуги не указаны</p>
        )}

        <div style={{
          display: 'flex', justifyContent: 'space-between', marginTop: 8,
          paddingTop: 8, borderTop: '1px solid var(--tg-secondary-bg)',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--tg-text)', fontSize: 16 }}>Итого</span>
          <span style={{ fontWeight: 700, color: 'var(--tg-text)', fontSize: 16 }}>
            {order.amount_total || 0}
          </span>
        </div>

        {order.address && (
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--tg-hint)' }}>
            📍 {order.address}
          </div>
        )}
      </div>

      {/* Block 3b: Payment info (for done orders) */}
      {order.status === 'done' && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Оплата</h3>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Способ</span>
            <span style={styles.rowValue}>{PAYMENT_LABELS[order.payment_type] || order.payment_type || '—'}</span>
          </div>
          {order.bonus_spent > 0 && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>Списано бонусов</span>
              <span style={styles.rowValue}>— {order.bonus_spent}</span>
            </div>
          )}
          {order.bonus_accrued > 0 && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>Начислено бонусов</span>
              <span style={{ ...styles.rowValue, color: '#27ae60' }}>+ {order.bonus_accrued}</span>
            </div>
          )}
        </div>
      )}

      {/* Cancel reason */}
      {order.status === 'cancelled' && order.cancel_reason && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Причина отмены</h3>
          <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: 0 }}>{order.cancel_reason}</p>
        </div>
      )}

      {/* Block 4: Actions (only for active orders) */}
      {isActive && (
        <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button
            onClick={() => { haptic(); setSheet('complete'); }}
            style={styles.actionBtn}
          >
            ✅ Провести
          </button>
          <button
            onClick={() => { haptic(); setSheet('move'); }}
            style={{ ...styles.actionBtn, background: 'var(--tg-secondary-bg)', color: 'var(--tg-text)' }}
          >
            📅 Перенести
          </button>
          <button
            onClick={() => { haptic(); setCancelConfirm(true); }}
            style={{ ...styles.actionBtn, background: '#e74c3c22', color: '#e74c3c' }}
          >
            ❌ Отменить
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
        title="Провести заказ"
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
        title="Перенести заказ"
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
        title="Отменить заказ?"
      >
        <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 20 }}>
          Заказ будет отменён, клиент получит уведомление.
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => { haptic(); setCancelConfirm(false); }}
            style={{ ...styles.actionBtn, flex: 1, background: 'var(--tg-secondary-bg)', color: 'var(--tg-text)' }}
          >
            Нет
          </button>
          <button
            onClick={handleCancel}
            style={{ ...styles.actionBtn, flex: 1, background: '#e74c3c', color: '#fff' }}
          >
            Да, отменить
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
  card: {
    margin: '12px 16px 0',
    background: 'var(--tg-section-bg)',
    borderRadius: 12,
    padding: '14px 16px',
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
    fontSize: 18,
    fontWeight: 600,
    color: 'var(--tg-text)',
    display: 'block',
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
    borderRadius: 12,
    border: 'none',
    background: 'var(--tg-button)',
    color: 'var(--tg-button-text)',
    fontSize: 16,
    fontWeight: 600,
    cursor: 'pointer',
  },
  skeleton: {
    background: 'var(--tg-secondary-bg)',
    animation: 'skeleton-pulse 1.5s ease-in-out infinite',
  },
};
