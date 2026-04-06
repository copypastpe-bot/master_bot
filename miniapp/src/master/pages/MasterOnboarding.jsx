import { useState, useEffect, useRef } from 'react';
import { registerMaster, createMasterClient, createMasterOrder, updateMasterProfile } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

// ─── Styles ────────────────────────────────────────────────────────────────

const S = {
  wrap: { padding: '32px 20px', maxWidth: 420, margin: '0 auto' },
  dots: { display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 36 },
  dot: (active) => ({
    width: 8, height: 8, borderRadius: '50%',
    background: active ? 'var(--tg-button)' : 'var(--tg-hint)',
    opacity: active ? 1 : 0.35,
    transition: 'all 0.2s',
  }),
  h1: { fontSize: 26, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 6 },
  sub: { fontSize: 14, color: 'var(--tg-hint)', marginBottom: 28 },
  label: { fontSize: 13, color: 'var(--tg-hint)', display: 'block', marginBottom: 6 },
  input: {
    width: '100%', padding: '12px 14px', borderRadius: 12,
    border: '1.5px solid var(--tg-hint)', background: 'var(--tg-bg)',
    color: 'var(--tg-text)', fontSize: 16, outline: 'none', boxSizing: 'border-box',
  },
  btnPrimary: (disabled) => ({
    width: '100%', padding: '14px', borderRadius: 12, border: 'none',
    background: 'var(--tg-button)', color: 'var(--tg-button-text)',
    fontSize: 16, fontWeight: 600, cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  }),
  btnSecondary: {
    width: '100%', padding: '12px', borderRadius: 12,
    border: '1.5px solid var(--tg-hint)', background: 'transparent',
    color: 'var(--tg-hint)', fontSize: 15, cursor: 'pointer', marginTop: 10,
  },
  backBtn: {
    background: 'none', border: 'none', color: 'var(--tg-button)',
    fontSize: 15, cursor: 'pointer', padding: 0, marginBottom: 20,
    display: 'flex', alignItems: 'center', gap: 4,
  },
  error: { color: '#e53935', fontSize: 13, marginBottom: 12 },
};

// ─── Niches ─────────────────────────────────────────────────────────────────

const NICHES = [
  'Клининг',
  'Химчистка мебели и ковров',
  'Парикмахер и барбер',
  'Маникюр и бьюти-услуги',
  'Груминг и животные',
  'Массаж',
  'Ремонт бытовой техники',
  'Мастер на час, мелкий ремонт',
  'Репетитор',
  'Фотограф и видеограф',
  'Психолог',
  'Садовник',
  'Другое',
];

// ─── Date/Time helpers ───────────────────────────────────────────────────────

const DATE_MONTHS = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];

function formatDateDisplay(iso) {
  if (!iso) return 'Выберите дату';
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${DATE_MONTHS[m - 1]} ${y}`;
}

function DatePickerField({ label, value, onChange }) {
  return (
    <div style={{ flex: 1 }}>
      {label && <label style={S.label}>{label}</label>}
      <div style={{ position: 'relative' }}>
        <div style={S.input}>{formatDateDisplay(value)}</div>
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

function TimePickerField({ label, value, onChange }) {
  return (
    <div style={{ flex: 1 }}>
      {label && <label style={S.label}>{label}</label>}
      <div style={{ position: 'relative' }}>
        <div style={S.input}>{value || '00:00'}</div>
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

// ─── Utils ───────────────────────────────────────────────────────────────────

function tomorrowDate() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0];
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function MasterOnboarding({ onRegistered }) {
  const [step, setStep] = useState(1);

  // Step 1
  const [name, setName] = useState('');

  // Step 2 — multi-select up to 3 niches
  const [selectedNiches, setSelectedNiches] = useState([]);
  const [customNiche, setCustomNiche] = useState('');

  // Step 3
  const [clientName, setClientName] = useState('');
  const [clientPhone, setClientPhone] = useState('');
  const [clientDate, setClientDate] = useState(tomorrowDate());
  const [clientTime, setClientTime] = useState('10:00');
  const [clientAdded, setClientAdded] = useState(false);

  // Shared
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Cleanup on unmount
  useEffect(() => () => {}, []);

  // ── Toggle niche selection (max 3)
  const toggleNiche = (niche) => {
    if (loading) return;
    WebApp?.HapticFeedback?.selectionChanged();
    setSelectedNiches(prev => {
      if (prev.includes(niche)) {
        if (niche === 'Другое') setCustomNiche('');
        return prev.filter(n => n !== niche);
      }
      if (prev.length >= 3) return prev;
      return [...prev, niche];
    });
    setError('');
  };

  const doRegister = async () => {
    setLoading(true);
    setError('');
    const sphereParts = selectedNiches.map(n => n === 'Другое' ? customNiche.trim() : n);
    const sphere = sphereParts.join(', ');
    try {
      await registerMaster({ name: name.trim(), sphere });
      setStep(3);
    } catch (err) {
      if (err?.response?.status === 409) {
        setStep(3);
      } else {
        const msg = err?.response?.data?.detail || 'Ошибка регистрации. Попробуйте ещё раз.';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Step 3 → add first client
  const handleAddClient = async () => {
    setLoading(true);
    setError('');
    try {
      const client = await createMasterClient({ name: clientName.trim(), phone: clientPhone.trim() });
      await createMasterOrder({
        client_id: client.id,
        scheduled_date: clientDate,
        scheduled_time: clientTime,
        services: [],
      });
      setClientAdded(true);
      setStep(4);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Не удалось добавить клиента.');
    } finally {
      setLoading(false);
    }
  };

  const handleSkipClient = async () => {
    setLoading(true);
    try {
      await updateMasterProfile({ onboarding_skipped_first_client: true });
    } catch (_) {
      // non-critical
    } finally {
      setLoading(false);
      setClientAdded(false);
      setStep(4);
    }
  };

  // ── Final screen → Telegram MainButton
  useEffect(() => {
    if (step !== 4 || !WebApp?.MainButton) return;
    const handleStart = () => { WebApp.MainButton.hide(); onRegistered(); };
    WebApp.MainButton.setText('Начать работу');
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleStart);
    return () => { WebApp.MainButton.offClick(handleStart); WebApp.MainButton.hide(); };
  }, [step]);

  const step2Ready = selectedNiches.length > 0 &&
    (!selectedNiches.includes('Другое') || customNiche.trim().length > 0);
  const step3Ready = clientName.trim() && clientPhone.trim() && clientDate && clientTime;

  return (
    <div style={S.wrap}>
      {/* Progress dots — 3 visible steps */}
      <div style={S.dots}>
        {[1, 2, 3].map((n) => <div key={n} style={S.dot(step === n || (step === 4 && n === 3))} />)}
      </div>

      {/* ── Step 1: Name ─────────────────────────────── */}
      {step === 1 && (
        <>
          <div style={S.h1}>Как тебя зовут?</div>
          <div style={S.sub}>Будем обращаться по имени</div>
          <div style={{ marginBottom: 24 }}>
            <label style={S.label}>Имя</label>
            <input
              style={S.input}
              placeholder="Например: Анна"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <button
            style={S.btnPrimary(!name.trim())}
            disabled={!name.trim()}
            onClick={() => setStep(2)}
          >
            Продолжить
          </button>
        </>
      )}

      {/* ── Step 2: Niche ─────────────────────────────── */}
      {step === 2 && (
        <>
          <button style={S.backBtn} onClick={() => { setError(''); setStep(1); }}>
            ← Назад
          </button>
          <div style={S.h1}>Чем занимаешься?</div>
          <div style={S.sub}>Выбери до 3 направлений</div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
            {NICHES.map((niche) => {
              const isSelected = selectedNiches.includes(niche);
              const isDisabled = loading || (!isSelected && selectedNiches.length >= 3);
              return (
                <button
                  key={niche}
                  disabled={isDisabled}
                  onClick={() => toggleNiche(niche)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 20,
                    border: `1.5px solid ${isSelected ? 'var(--tg-button)' : 'var(--tg-hint)'}`,
                    background: isSelected ? 'var(--tg-button)' : 'transparent',
                    color: isSelected ? 'var(--tg-button-text)' : 'var(--tg-text)',
                    fontSize: 14,
                    cursor: isDisabled ? 'default' : 'pointer',
                    transition: 'all 0.15s',
                    opacity: isDisabled && !isSelected ? 0.4 : 1,
                  }}
                >
                  {niche}
                </button>
              );
            })}
          </div>

          {selectedNiches.includes('Другое') && (
            <div style={{ marginBottom: 16 }}>
              <input
                style={S.input}
                placeholder="Напишите вашу нишу"
                value={customNiche}
                onChange={(e) => setCustomNiche(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {error && <div style={S.error}>{error}</div>}

          <button
            style={S.btnPrimary(!step2Ready || loading)}
            disabled={!step2Ready || loading}
            onClick={doRegister}
          >
            {loading ? 'Сохраняем...' : 'Продолжить'}
          </button>
        </>
      )}

      {/* ── Step 3: First Client ───────────────────────── */}
      {step === 3 && (
        <>
          <button style={S.backBtn} onClick={() => { setError(''); setStep(2); }}>
            ← Назад
          </button>
          <div style={S.h1}>Добавим первого клиента?</div>
          <div style={S.sub}>Создай свою первую запись сейчас или позже</div>

          {[
            { label: 'Имя клиента', type: 'text', value: clientName, set: setClientName, placeholder: 'Например: Мария' },
            { label: 'Телефон', type: 'tel', value: clientPhone, set: setClientPhone, placeholder: '+7 999 123 45 67' },
          ].map(({ label, type, value, set, placeholder }) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <label style={S.label}>{label}</label>
              <input style={S.input} type={type} placeholder={placeholder} value={value} onChange={(e) => set(e.target.value)} />
            </div>
          ))}

          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <DatePickerField
              label="Дата записи"
              value={clientDate}
              onChange={(e) => setClientDate(e.target.value)}
            />
            <TimePickerField
              label="Время"
              value={clientTime}
              onChange={(e) => setClientTime(e.target.value)}
            />
          </div>

          {error && <div style={S.error}>{error}</div>}

          <button
            style={S.btnPrimary(!step3Ready || loading)}
            disabled={!step3Ready || loading}
            onClick={handleAddClient}
          >
            {loading ? 'Сохраняем...' : 'Добавить и продолжить'}
          </button>
          <button style={S.btnSecondary} disabled={loading} onClick={handleSkipClient}>
            Пропустить
          </button>
        </>
      )}

      {/* ── Step 4: Final ─────────────────────────────── */}
      {step === 4 && (
        <>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ fontSize: 64, animation: 'popIn 0.4s cubic-bezier(0.175,0.885,0.32,1.275)' }}>✅</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--tg-text)', marginTop: 16 }}>
              Всё готово, {name}!
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginTop: 8 }}>
              {clientAdded
                ? 'Остались вопросы? Пиши нам @pastushenko12'
                : 'Добавь первого клиента — это займёт 30 секунд'}
            </div>
          </div>

          {!WebApp?.MainButton && (
            <button style={S.btnPrimary(false)} onClick={onRegistered}>
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
