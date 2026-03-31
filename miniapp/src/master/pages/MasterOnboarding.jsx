import { useState, useEffect } from 'react';
import { registerMaster } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

const DOT_STYLE = (active) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: active ? 'var(--tg-button)' : 'var(--tg-hint)',
  opacity: active ? 1 : 0.35,
  transition: 'all 0.2s',
});

const INPUT_STYLE = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 12,
  border: '1.5px solid var(--tg-hint)',
  background: 'var(--tg-bg)',
  color: 'var(--tg-text)',
  fontSize: 16,
  outline: 'none',
  boxSizing: 'border-box',
};

const BTN_PRIMARY = {
  width: '100%',
  padding: '14px',
  borderRadius: 12,
  border: 'none',
  background: 'var(--tg-button)',
  color: 'var(--tg-button-text)',
  fontSize: 16,
  fontWeight: 600,
  cursor: 'pointer',
};

const BTN_SECONDARY = {
  width: '100%',
  padding: '12px',
  borderRadius: 12,
  border: '1.5px solid var(--tg-hint)',
  background: 'transparent',
  color: 'var(--tg-hint)',
  fontSize: 15,
  cursor: 'pointer',
  marginTop: 10,
};

export default function MasterOnboarding({ onRegistered }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name: '', sphere: '', contacts: '', work_hours: '' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (skipOptional = false) => {
    setLoading(true);
    setError('');
    try {
      const payload = { name: form.name.trim() };
      if (!skipOptional) {
        if (form.sphere.trim()) payload.sphere = form.sphere.trim();
        if (form.contacts.trim()) payload.contacts = form.contacts.trim();
        if (form.work_hours.trim()) payload.work_hours = form.work_hours.trim();
      }
      const data = await registerMaster(payload);
      setResult(data);
      WebApp?.HapticFeedback?.notificationOccurred('success');
      setStep(3);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Ошибка. Попробуйте ещё раз.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const copyLink = () => {
    const link = result?.invite_link || '';
    if (WebApp?.copyToClipboard) {
      WebApp.copyToClipboard(link);
    } else {
      navigator.clipboard?.writeText(link);
    }
    WebApp?.HapticFeedback?.selectionChanged();
  };

  const handleStart = () => {
    if (WebApp?.MainButton) {
      WebApp.MainButton.hide();
    }
    onRegistered();
  };

  // Show Telegram MainButton on step 3
  useEffect(() => {
    if (step !== 3 || !WebApp?.MainButton) return;
    WebApp.MainButton.setText('Начать работу');
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleStart);
    return () => {
      WebApp.MainButton.offClick(handleStart);
      WebApp.MainButton.hide();
    };
  }, [step]);

  return (
    <div style={{ padding: '32px 20px', maxWidth: 420, margin: '0 auto' }}>
      {/* Progress dots */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 36 }}>
        {[1, 2, 3].map((n) => <div key={n} style={DOT_STYLE(step === n)} />)}
      </div>

      {step === 1 && (
        <>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 8 }}>
            Добро пожаловать в CRMfit!
          </div>
          <div style={{ fontSize: 15, color: 'var(--tg-hint)', marginBottom: 32 }}>
            Настроим ваш профиль за 1 минуту
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ fontSize: 13, color: 'var(--tg-hint)', display: 'block', marginBottom: 6 }}>
              Ваше имя или псевдоним
            </label>
            <input
              style={INPUT_STYLE}
              placeholder="Например: Анна"
              value={form.name}
              onChange={update('name')}
              autoFocus
            />
          </div>
          {error && <div style={{ color: '#e53935', fontSize: 13, marginBottom: 12 }}>{error}</div>}
          <button
            style={{ ...BTN_PRIMARY, opacity: form.name.trim() ? 1 : 0.5 }}
            disabled={!form.name.trim() || loading}
            onClick={() => setStep(2)}
          >
            Далее
          </button>
        </>
      )}

      {step === 2 && (
        <>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 8 }}>
            Расскажите о себе
          </div>
          <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 28 }}>
            Всё необязательно — можно заполнить позже
          </div>

          {[
            { field: 'sphere', label: 'Сфера деятельности', placeholder: 'Например: клининг, парикмахер, репетитор' },
            { field: 'contacts', label: 'Контакты для клиентов', placeholder: 'Телефон, мессенджеры' },
            { field: 'work_hours', label: 'Режим работы', placeholder: 'Например: Пн-Пт 9:00-18:00' },
          ].map(({ field, label, placeholder }) => (
            <div key={field} style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, color: 'var(--tg-hint)', display: 'block', marginBottom: 6 }}>
                {label}
              </label>
              <input
                style={INPUT_STYLE}
                placeholder={placeholder}
                value={form[field]}
                onChange={update(field)}
              />
            </div>
          ))}

          {error && <div style={{ color: '#e53935', fontSize: 13, marginBottom: 12 }}>{error}</div>}

          <button style={BTN_PRIMARY} disabled={loading} onClick={() => submit(false)}>
            {loading ? 'Сохраняем...' : 'Далее'}
          </button>
          <button style={BTN_SECONDARY} disabled={loading} onClick={() => submit(true)}>
            Пропустить
          </button>
        </>
      )}

      {step === 3 && result && (
        <>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{
              fontSize: 64,
              animation: 'popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            }}>
              ✅
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--tg-text)', marginTop: 16 }}>
              Профиль создан!
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginTop: 8 }}>
              Поделитесь ссылкой с клиентами
            </div>
          </div>

          <div style={{
            background: 'var(--tg-secondary-bg)',
            borderRadius: 12,
            padding: '12px 14px',
            marginBottom: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <div style={{
              flex: 1,
              fontSize: 13,
              color: 'var(--tg-hint)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {result.invite_link}
            </div>
            <button
              onClick={copyLink}
              style={{
                border: 'none',
                background: 'var(--tg-button)',
                color: 'var(--tg-button-text)',
                borderRadius: 8,
                padding: '6px 12px',
                fontSize: 13,
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              Копировать
            </button>
          </div>

          {/* MainButton "Начать работу" is set above — fallback button if MainButton not available */}
          {!WebApp?.MainButton && (
            <button style={{ ...BTN_PRIMARY, marginTop: 16 }} onClick={handleStart}>
              Начать работу
            </button>
          )}
        </>
      )}

      <style>{`
        @keyframes popIn {
          0% { transform: scale(0); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
