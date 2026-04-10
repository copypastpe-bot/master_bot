import { useState, useRef } from 'react';
import { createMasterClient, restoreArchivedClient } from '../../api/client';
import { useI18n } from '../../i18n';

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
  const { tr } = useI18n();
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const birthdayRef = useRef(null);
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
    // Read date from DOM ref to avoid React controlled-input issues on Telegram WebView
    const birthdayVal = birthdayRef.current?.value || undefined;
    try {
      const client = await createMasterClient({
        name: name.trim(),
        phone: phone.trim(),
        birthday: birthdayVal || undefined,
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
          setFieldError(tr('Клиент с таким номером уже есть', 'A client with this phone already exists'));
        }
      } else if (err?.response?.status === 422) {
        const msg = typeof data === 'string' ? data : (data?.detail || tr('Проверьте данные', 'Check your input'));
        setFieldError(typeof msg === 'string' ? msg : tr('Проверьте данные', 'Check your input'));
      } else {
        setFieldError(tr('Не удалось добавить клиента', 'Failed to add client'));
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
      setFieldError(tr('Не удалось разархивировать', 'Failed to restore client'));
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
              {tr('Клиент уже есть', 'Client already exists')}
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 20 }}>
              {tr('Клиент', 'Client')} <strong style={{ color: 'var(--tg-text)' }}>{archivedClient.name}</strong>{' '}
              {tr('с таким номером находится в архиве. Разархивировать?', 'with this phone is archived. Restore?')}
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
                {tr('Отмена', 'Cancel')}
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
                {loading ? tr('Загрузка...', 'Loading...') : tr('Разархивировать', 'Restore')}
              </button>
            </div>
          </>
        ) : (
          /* ── Add client form ── */
          <>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 16 }}>
              {tr('Новый клиент', 'New client')}
            </div>

            <div style={{ marginBottom: 12 }}>
              <FieldLabel>{tr('Имя *', 'Name *')}</FieldLabel>
              <input
                type="text"
                value={name}
                onChange={e => { setName(e.target.value); setFieldError(''); }}
                placeholder={tr('Иван Петров', 'John Doe')}
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <FieldLabel>{tr('Телефон *', 'Phone *')}</FieldLabel>
              <input
                type="tel"
                value={phone}
                onChange={e => { setPhone(e.target.value); setFieldError(''); }}
                placeholder="+7 999 123 45 67"
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <FieldLabel>{tr('Дата рождения (необязательно)', 'Birthday (optional)')}</FieldLabel>
              <input
                type="date"
                ref={birthdayRef}
                max={today}
                style={inputStyle}
              />
              <div style={{ fontSize: 11, color: 'var(--tg-hint)', marginTop: 3 }}>
                {tr('Для бонуса на день рождения', 'Used for birthday bonus')}
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
              {loading ? tr('Загрузка...', 'Loading...') : tr('Добавить клиента', 'Add client')}
            </button>
          </>
        )}
      </div>
    </>
  );
}
