import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterClient,
  updateMasterClient,
  updateMasterClientNote,
  masterClientBonus,
} from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

function hapticNotify(type = 'success') {
  if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
    WebApp.HapticFeedback.notificationOccurred(type);
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatBadge({ label, value }) {
  return (
    <div style={{ textAlign: 'center', flex: 1 }}>
      <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)' }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>{label}</div>
    </div>
  );
}

function TabBar({ active, onChange }) {
  const tabs = [
    { id: 'history', label: 'История' },
    { id: 'bonuses', label: 'Бонусы' },
    { id: 'actions', label: 'Действия' },
  ];
  return (
    <div style={{
      display: 'flex',
      borderBottom: '1px solid var(--tg-secondary-bg)',
      background: 'var(--tg-section-bg)',
      position: 'sticky',
      top: 0,
      zIndex: 5,
    }}>
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => { haptic(); onChange(t.id); }}
          style={{
            flex: 1,
            padding: '12px 0',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: active === t.id ? 600 : 400,
            color: active === t.id ? 'var(--tg-accent)' : 'var(--tg-hint)',
            borderBottom: active === t.id ? '2px solid var(--tg-accent)' : '2px solid transparent',
            transition: 'color 0.15s',
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    done: { label: 'Выполнен', color: '#4caf50' },
    new: { label: 'Новый', color: 'var(--tg-accent)' },
    confirmed: { label: 'Подтверждён', color: 'var(--tg-accent)' },
    moved: { label: 'Перенесён', color: '#ff9800' },
    cancelled: { label: 'Отменён', color: 'var(--tg-destructive, #e53935)' },
  };
  const s = map[status] || { label: status, color: 'var(--tg-hint)' };
  return (
    <span style={{
      fontSize: 11,
      fontWeight: 500,
      color: s.color,
      background: `${s.color}22`,
      padding: '2px 6px',
      borderRadius: 4,
    }}>
      {s.label}
    </span>
  );
}

function BonusSheet({ type, onClose, onSubmit, loading }) {
  const [amount, setAmount] = useState('');
  const [comment, setComment] = useState('');
  const isAccrual = type === 'accrue';

  const handleSubmit = () => {
    const n = parseInt(amount, 10);
    if (!n || n <= 0) {
      hapticNotify('error');
      return;
    }
    haptic('medium');
    onSubmit(isAccrual ? n : -n, comment);
  };

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.5)',
          zIndex: 200,
        }}
      />
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: 'var(--tg-section-bg)',
        borderRadius: '16px 16px 0 0',
        padding: '20px 16px 32px',
        zIndex: 201,
        animation: 'slideUp 0.2s ease',
      }}>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
          {isAccrual ? '+ Начислить бонусы' : '- Списать бонусы'}
        </div>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          placeholder="Сумма"
          autoFocus
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: 10,
            border: '1px solid var(--tg-secondary-bg)',
            background: 'var(--tg-bg)',
            color: 'var(--tg-text)',
            fontSize: 15,
            boxSizing: 'border-box',
            marginBottom: 10,
          }}
        />
        <input
          type="text"
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Комментарий (необязательно)"
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: 10,
            border: '1px solid var(--tg-secondary-bg)',
            background: 'var(--tg-bg)',
            color: 'var(--tg-text)',
            fontSize: 15,
            boxSizing: 'border-box',
            marginBottom: 16,
          }}
        />
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: '12px', borderRadius: 10,
              border: '1px solid var(--tg-secondary-bg)',
              background: 'none', color: 'var(--tg-text)',
              fontSize: 15, cursor: 'pointer',
            }}
          >
            Отмена
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{
              flex: 2, padding: '12px', borderRadius: 10,
              background: isAccrual ? 'var(--tg-accent)' : 'var(--tg-destructive, #e53935)',
              color: '#fff', fontSize: 15, fontWeight: 600,
              border: 'none', cursor: 'pointer', opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? '...' : (isAccrual ? 'Начислить' : 'Списать')}
          </button>
        </div>
      </div>
      <style>{`@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }`}</style>
    </>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ClientCard({ clientId, onBack, onNavigate }) {
  const [tab, setTab] = useState('history');
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editNote, setEditNote] = useState(false);
  const [noteValue, setNoteValue] = useState('');
  const [bonusSheet, setBonusSheet] = useState(null); // 'accrue' | 'deduct'
  const [successMsg, setSuccessMsg] = useState('');

  const qc = useQueryClient();
  const birthdayInputRef = useRef(null);

  const { data: client, isLoading, error } = useQuery({
    queryKey: ['master-client', clientId],
    queryFn: () => getMasterClient(clientId),
    staleTime: 30_000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['master-client', clientId] });
    qc.invalidateQueries({ queryKey: ['master-clients'] });
  };

  const showSuccess = (msg) => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 2000);
  };

  const editMutation = useMutation({
    mutationFn: (data) => updateMasterClient(clientId, data),
    onSuccess: () => { invalidate(); setEditMode(false); showSuccess('Сохранено ✓'); },
    onError: () => hapticNotify('error'),
  });

  const noteMutation = useMutation({
    mutationFn: (note) => updateMasterClientNote(clientId, note),
    onSuccess: () => { invalidate(); setEditNote(false); showSuccess('Заметка сохранена ✓'); },
    onError: () => hapticNotify('error'),
  });

  const bonusMutation = useMutation({
    mutationFn: ({ amount, comment }) => masterClientBonus(clientId, amount, comment),
    onSuccess: () => { invalidate(); setBonusSheet(null); showSuccess('Бонусы обновлены ✓'); },
    onError: () => hapticNotify('error'),
  });

  if (isLoading) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        Загрузка...
      </div>
    );
  }

  if (error || !client) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center' }}>
        <p style={{ color: 'var(--tg-hint)' }}>Не удалось загрузить клиента</p>
        <button onClick={onBack} style={{ color: 'var(--tg-accent)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 15 }}>
          ← Назад
        </button>
      </div>
    );
  }

  const handleEditSave = () => {
    haptic('medium');
    // Read birthday from DOM ref to avoid React controlled-input issues on Telegram WebView
    const birthday = birthdayInputRef.current?.value ?? editForm.birthday;
    editMutation.mutate({ ...editForm, birthday });
  };

  const handleEditStart = () => {
    haptic();
    setEditForm({ name: client.name, phone: client.phone, birthday: client.birthday || '' });
    setEditMode(true);
  };

  const handleNoteEdit = () => {
    haptic();
    setNoteValue(client.note || '');
    setEditNote(true);
  };

  const handleNoteSave = () => {
    haptic('medium');
    noteMutation.mutate(noteValue);
  };

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Success toast */}
      {successMsg && (
        <div style={{
          position: 'fixed', top: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--tg-accent)', color: '#fff',
          padding: '8px 20px', borderRadius: 20, fontSize: 13, fontWeight: 500,
          zIndex: 300, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}>
          {successMsg}
        </div>
      )}

      {/* Header */}
      <div style={{
        padding: '20px 16px 16px',
        background: 'var(--tg-section-bg)',
        borderBottom: '1px solid var(--tg-secondary-bg)',
      }}>
        {editMode ? (
          // Edit form
          <div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>Имя</div>
            <input
              value={editForm.name || ''}
              onChange={e => setEditForm(p => ({ ...p, name: e.target.value }))}
              style={inputStyle}
            />
            <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 10, marginBottom: 4 }}>Телефон</div>
            <input
              type="tel"
              value={editForm.phone || ''}
              onChange={e => setEditForm(p => ({ ...p, phone: e.target.value }))}
              style={inputStyle}
            />
            <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 10, marginBottom: 4 }}>Дата рождения</div>
            <input
              type="date"
              ref={birthdayInputRef}
              defaultValue={editForm.birthday || ''}
              style={inputStyle}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <button onClick={() => { haptic(); setEditMode(false); }} style={btnSecondary}>Отмена</button>
              <button onClick={handleEditSave} disabled={editMutation.isPending} style={btnPrimary}>
                {editMutation.isPending ? '...' : 'Сохранить'}
              </button>
            </div>
          </div>
        ) : (
          // View mode
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--tg-text)' }}>
                {client.name || '—'}
              </div>
              {client.phone && (
                <a
                  href={`tel:${client.phone}`}
                  style={{ fontSize: 15, color: 'var(--tg-accent)', textDecoration: 'none', marginTop: 4, display: 'block' }}
                  onClick={() => haptic()}
                >
                  {client.phone}
                </a>
              )}
              {client.birthday && (
                <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 4 }}>
                  ДР: {client.birthday}
                </div>
              )}
            </div>
            <button
              onClick={handleEditStart}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--tg-hint)', padding: '4px 8px' }}
            >
              ✏️
            </button>
          </div>
        )}
      </div>

      {/* Stats strip */}
      <div style={{
        display: 'flex',
        background: 'var(--tg-section-bg)',
        borderBottom: '1px solid var(--tg-secondary-bg)',
        padding: '14px 16px',
        gap: 8,
      }}>
        <StatBadge label="Бонусы" value={`${client.bonus_balance || 0} ₽`} />
        <div style={{ width: 1, background: 'var(--tg-secondary-bg)' }} />
        <StatBadge label="Заказов" value={client.order_count || 0} />
        <div style={{ width: 1, background: 'var(--tg-secondary-bg)' }} />
        <StatBadge label="Потрачено" value={`${(client.total_spent || 0).toLocaleString()} ₽`} />
      </div>

      {/* Note */}
      <div style={{ background: 'var(--tg-section-bg)', padding: '14px 16px', borderBottom: '1px solid var(--tg-secondary-bg)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
              Заметка
            </div>
            {editNote ? (
              <div>
                <textarea
                  value={noteValue}
                  onChange={e => setNoteValue(e.target.value)}
                  placeholder="Заметка о клиенте..."
                  rows={3}
                  autoFocus
                  style={{
                    ...inputStyle,
                    resize: 'vertical',
                    fontFamily: 'inherit',
                    minHeight: 72,
                  }}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button onClick={() => { haptic(); setEditNote(false); }} style={btnSecondary}>Отмена</button>
                  <button onClick={handleNoteSave} disabled={noteMutation.isPending} style={btnPrimary}>
                    {noteMutation.isPending ? '...' : 'Сохранить'}
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{ fontSize: 14, color: client.note ? 'var(--tg-text)' : 'var(--tg-hint)', lineHeight: 1.4 }}
              >
                {client.note || 'Нет заметки'}
              </div>
            )}
          </div>
          {!editNote && (
            <button onClick={handleNoteEdit} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--tg-hint)', fontSize: 15, padding: '0 0 0 8px' }}>
              ✏️
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <TabBar active={tab} onChange={setTab} />

      {/* Tab content */}
      <div style={{ padding: '0 0 16px' }}>
        {tab === 'history' && (
          <HistoryTab orders={client.orders || []} onNavigate={onNavigate} />
        )}
        {tab === 'bonuses' && (
          <BonusesTab
            balance={client.bonus_balance || 0}
            log={client.bonus_log || []}
            onAccrue={() => { haptic(); setBonusSheet('accrue'); }}
            onDeduct={() => { haptic(); setBonusSheet('deduct'); }}
          />
        )}
        {tab === 'actions' && (
          <ActionsTab
            onCreateOrder={() => { haptic('medium'); onNavigate('create_order', { preselectedClientId: clientId, preselectedClientName: client.name }); }}
            onEdit={handleEditStart}
          />
        )}
      </div>

      {/* Bonus bottom sheet */}
      {bonusSheet && (
        <BonusSheet
          type={bonusSheet}
          onClose={() => setBonusSheet(null)}
          onSubmit={(amount, comment) => bonusMutation.mutate({ amount, comment })}
          loading={bonusMutation.isPending}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: History
// ---------------------------------------------------------------------------

function HistoryTab({ orders, onNavigate }) {
  if (!orders.length) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        Нет заказов
      </div>
    );
  }

  const fmtDate = (str) => {
    if (!str) return '—';
    try {
      return new Date(str).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch { return str; }
  };

  return (
    <div style={{ background: 'var(--tg-section-bg)' }}>
      {orders.map((o, idx) => (
        <div
          key={o.id}
          onClick={() => { haptic(); onNavigate('order', { id: o.id }); }}
          style={{
            padding: '12px 16px',
            borderBottom: idx < orders.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {o.services || 'Без услуг'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
              {fmtDate(o.scheduled_at)}
            </div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--tg-text)' }}>
              {(o.amount_total || 0).toLocaleString()} ₽
            </div>
            <StatusBadge status={o.status} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Bonuses
// ---------------------------------------------------------------------------

function BonusesTab({ balance, log, onAccrue, onDeduct }) {
  const fmtDate = (str) => {
    if (!str) return '—';
    try { return new Date(str).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }); }
    catch { return str; }
  };

  return (
    <div>
      {/* Balance */}
      <div style={{
        background: 'var(--tg-section-bg)',
        padding: '20px 16px',
        textAlign: 'center',
        borderBottom: '1px solid var(--tg-secondary-bg)',
      }}>
        <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--tg-text)' }}>
          {balance.toLocaleString()} ₽
        </div>
        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 4 }}>Бонусный баланс</div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, padding: '14px 16px', background: 'var(--tg-section-bg)', borderBottom: '1px solid var(--tg-secondary-bg)' }}>
        <button onClick={onAccrue} style={{ ...btnPrimary, flex: 1 }}>+ Начислить</button>
        <button onClick={onDeduct} style={{ ...btnSecondary, flex: 1 }}>− Списать</button>
      </div>

      {/* Log */}
      {log.length === 0 ? (
        <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
          Нет операций
        </div>
      ) : (
        <div style={{ background: 'var(--tg-section-bg)' }}>
          {log.map((entry, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '10px 16px',
                borderBottom: idx < log.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
                gap: 12,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {entry.comment || (entry.type === 'accrual' ? 'Начисление' : 'Списание')}
                </div>
                <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>{fmtDate(entry.date)}</div>
              </div>
              <div style={{
                fontSize: 15,
                fontWeight: 600,
                color: entry.amount > 0 ? '#4caf50' : 'var(--tg-destructive, #e53935)',
                flexShrink: 0,
              }}>
                {entry.amount > 0 ? '+' : ''}{entry.amount} ₽
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Actions
// ---------------------------------------------------------------------------

function ActionsTab({ onCreateOrder, onEdit }) {
  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      <button onClick={onCreateOrder} style={{ ...btnPrimary, width: '100%', padding: '14px' }}>
        + Создать заказ
      </button>
      <button onClick={onEdit} style={{ ...btnSecondary, width: '100%', padding: '14px' }}>
        ✏️ Редактировать
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'var(--tg-bg)',
  color: 'var(--tg-text)',
  fontSize: 15,
  boxSizing: 'border-box',
  display: 'block',
};

const btnPrimary = {
  padding: '10px 16px',
  borderRadius: 10,
  background: 'var(--tg-accent)',
  color: '#fff',
  fontWeight: 600,
  fontSize: 14,
  border: 'none',
  cursor: 'pointer',
};

const btnSecondary = {
  padding: '10px 16px',
  borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'none',
  color: 'var(--tg-text)',
  fontSize: 14,
  cursor: 'pointer',
};
