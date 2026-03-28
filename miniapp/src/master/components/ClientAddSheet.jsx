import { useState } from 'react';
import { createMasterClient, restoreArchivedClient } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  border: '1px solid var(--tg-secondary-bg)',
  borderRadius: 8,
  padding: '10px 12px',
  background: 'var(--tg-surface)',
  color: 'var(--tg-text)',
  fontSize: 15,
  outline: 'none',
};

function FieldLabel({ children }) {
  return (
    <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>
      {children}
    </div>
  );
}

export default function ClientAddSheet({ onSuccess, onClose }) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [birthday, setBirthday] = useState('');
  const [loading, setLoading] = useState(false);
  const [fieldError, setFieldError] = useState('');
  // Archived conflict state
  const [archivedClient, setArchivedClient] = useState(null); // { client_id, name }

  const today = new Date().toISOString().slice(0, 10);
  const canSubmit = name.trim().length > 0 && phone.trim().length >= 10;

  const handleSubmit = async () => {
    if (!canSubmit || loading) return;
    haptic();
    setLoading(true);
    setFieldError('');
    try {
      const client = await createMasterClient({
        name: name.trim(),
        phone: phone.trim(),
        birthday: birthday || undefined,
      });
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
      onSuccess(client);
    } catch (err) {
      const data = err?.response?.data;
      if (err?.response?.status === 409) {
        if (data?.archived === true) {
          setArchivedClient({ client_id: data.client_id, name: data.name });
        } else {
          setFieldError('Клиент с таким номером уже есть');
        }
      } else if (err?.response?.status === 422) {
        const msg = typeof data === 'string' ? data : (data?.detail || 'Проверьте данные');
        setFieldError(typeof msg === 'string' ? msg : 'Проверьте данные');
      } else {
        setFieldError('Не удалось добавить клиента');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async () => {
    if (!archivedClient || loading) return;
    haptic();
    setLoading(true);
    try {
      const client = await restoreArchivedClient(archivedClient.client_id);
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
      onSuccess(client);
    } catch {
      setFieldError('Не удалось разархивировать');
      setArchivedClient(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100 }}
      />

      {/* Sheet */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 101,
        background: 'var(--tg-bg)',
        borderRadius: '16px 16px 0 0',
        padding: '20px 16px 32px',
      }}>
        {archivedClient ? (
          /* ── Archived conflict view ── */
          <>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 12 }}>
              Клиент уже есть
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 20 }}>
              Клиент <strong style={{ color: 'var(--tg-text)' }}>{archivedClient.name}</strong> с
              таким номером находится в архиве. Разархивировать?
            </div>
            {fieldError && (
              <div style={{ color: '#e53935', fontSize: 13, marginBottom: 12 }}>{fieldError}</div>
            )}
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={onClose}
                style={{
                  flex: 1, padding: '13px', borderRadius: 12, border: '1px solid var(--tg-secondary-bg)',
                  background: 'none', color: 'var(--tg-text)', fontSize: 15, cursor: 'pointer',
                }}
              >
                Отмена
              </button>
              <button
                onClick={handleRestore}
                disabled={loading}
                style={{
                  flex: 2, padding: '13px', borderRadius: 12, border: 'none',
                  background: loading ? 'var(--tg-hint)' : 'var(--tg-button)',
                  color: 'var(--tg-button-text)', fontSize: 15, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {loading ? 'Загрузка...' : 'Разархивировать'}
              </button>
            </div>
          </>
        ) : (
          /* ── Add client form ── */
          <>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 16 }}>
              Новый клиент
            </div>

            <div style={{ marginBottom: 12 }}>
              <FieldLabel>Имя *</FieldLabel>
              <input
                type="text"
                value={name}
                onChange={e => { setName(e.target.value); setFieldError(''); }}
                placeholder="Иван Петров"
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <FieldLabel>Телефон *</FieldLabel>
              <input
                type="tel"
                value={phone}
                onChange={e => { setPhone(e.target.value); setFieldError(''); }}
                placeholder="+7 999 123 45 67"
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <FieldLabel>Дата рождения (необязательно)</FieldLabel>
              <input
                type="date"
                value={birthday}
                max={today}
                onChange={e => setBirthday(e.target.value)}
                style={inputStyle}
              />
              <div style={{ fontSize: 11, color: 'var(--tg-hint)', marginTop: 3 }}>
                Для бонуса на день рождения
              </div>
            </div>

            {fieldError && (
              <div style={{ color: '#e53935', fontSize: 13, marginBottom: 10 }}>{fieldError}</div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!canSubmit || loading}
              style={{
                width: '100%', padding: '14px', borderRadius: 12, border: 'none',
                background: canSubmit && !loading ? 'var(--tg-button)' : 'var(--tg-hint)',
                color: 'var(--tg-button-text)', fontSize: 15, fontWeight: 600,
                cursor: canSubmit && !loading ? 'pointer' : 'default',
              }}
            >
              {loading ? 'Загрузка...' : 'Добавить клиента'}
            </button>
          </>
        )}
      </div>
    </>
  );
}
