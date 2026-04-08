import { useState, useEffect } from 'react';
import { registerMaster, createMasterClient, createMasterOrder, updateMasterProfile } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

const iconProps = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
};

const ChevronLeftIcon = () => (
  <svg {...iconProps}>
    <path d="m15 18-6-6 6-6" />
  </svg>
);

const CheckIcon = () => (
  <svg {...iconProps} width={34} height={34}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8.8 12 2.4 2.4 4.8-4.8" />
  </svg>
);

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
    <div className="onb-field-group onb-field-flex">
      {label && <label className="onb-label">{label}</label>}
      <div className="onb-picker-wrap">
        <div className="onb-input onb-picker-display">{formatDateDisplay(value)}</div>
        <input
          type="date"
          value={value}
          onChange={onChange}
          className="onb-native-picker"
        />
      </div>
    </div>
  );
}

function TimePickerField({ label, value, onChange }) {
  return (
    <div className="onb-field-group onb-field-flex">
      {label && <label className="onb-label">{label}</label>}
      <div className="onb-picker-wrap">
        <div className="onb-input onb-picker-display">{value || '00:00'}</div>
        <input
          type="time"
          value={value}
          onChange={onChange}
          className="onb-native-picker"
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

export default function MasterOnboarding({ onRegistered, referralCode = null }) {
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

  useEffect(() => {
    document.body.classList.add('typeui-enterprise-body');
    return () => {
      document.body.classList.remove('typeui-enterprise-body');
    };
  }, []);

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
      await registerMaster({ name: name.trim(), sphere, referral_code: referralCode || undefined });
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
  }, [step, onRegistered]);

  const step2Ready = selectedNiches.length > 0 &&
    (!selectedNiches.includes('Другое') || customNiche.trim().length > 0);
  const step3Ready = clientName.trim() && clientPhone.trim() && clientDate && clientTime;
  const progressStep = step === 4 ? 3 : step;

  return (
    <div className="master-onboarding">
      <div className="master-onboarding-shell">
      <div className="onb-progress" aria-hidden="true">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className={`onb-dot${progressStep >= n ? ' is-active' : ''}`}
          />
        ))}
      </div>

      {/* ── Step 1: Name ─────────────────────────────── */}
      {step === 1 && (
        <section className="onb-card">
          <h1 className="onb-title">Как тебя зовут?</h1>
          <p className="onb-subtitle">Будем обращаться по имени</p>

          <div className="onb-field-group">
            <label className="onb-label">Имя</label>
            <input
              className="onb-input"
              placeholder="Например: Анна"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <button
            className="onb-btn-primary"
            disabled={!name.trim()}
            type="button"
            onClick={() => setStep(2)}
          >
            Продолжить
          </button>
        </section>
      )}

      {/* ── Step 2: Niche ─────────────────────────────── */}
      {step === 2 && (
        <section className="onb-card">
          <button className="onb-back-btn" type="button" onClick={() => { setError(''); setStep(1); }}>
            <ChevronLeftIcon />
            <span>Назад</span>
          </button>
          <h1 className="onb-title">Чем занимаешься?</h1>
          <p className="onb-subtitle">Выбери до 3 направлений</p>

          <div className="onb-chip-grid">
            {NICHES.map((niche) => {
              const isSelected = selectedNiches.includes(niche);
              const isDisabled = loading || (!isSelected && selectedNiches.length >= 3);
              return (
                <button
                  key={niche}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => toggleNiche(niche)}
                  className={`onb-chip${isSelected ? ' is-selected' : ''}`}
                >
                  {niche}
                </button>
              );
          })}
          </div>

          {selectedNiches.includes('Другое') && (
            <div className="onb-field-group">
              <label className="onb-label">Своя ниша</label>
              <input
                className="onb-input"
                placeholder="Напишите вашу нишу"
                value={customNiche}
                onChange={(e) => setCustomNiche(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {error && <div className="onb-error">{error}</div>}

          <button
            className="onb-btn-primary"
            disabled={!step2Ready || loading}
            type="button"
            onClick={doRegister}
          >
            {loading ? 'Сохраняем...' : 'Продолжить'}
          </button>
        </section>
      )}

      {/* ── Step 3: First Client ───────────────────────── */}
      {step === 3 && (
        <section className="onb-card">
          <button className="onb-back-btn" type="button" onClick={() => { setError(''); setStep(2); }}>
            <ChevronLeftIcon />
            <span>Назад</span>
          </button>
          <h1 className="onb-title">Добавим первого клиента?</h1>
          <p className="onb-subtitle">Создай свою первую запись сейчас или позже</p>

          {[
            { label: 'Имя клиента', type: 'text', value: clientName, set: setClientName, placeholder: 'Например: Мария' },
            { label: 'Телефон', type: 'tel', value: clientPhone, set: setClientPhone, placeholder: '+7 999 123 45 67' },
          ].map(({ label, type, value, set, placeholder }) => (
            <div key={label} className="onb-field-group">
              <label className="onb-label">{label}</label>
              <input className="onb-input" type={type} placeholder={placeholder} value={value} onChange={(e) => set(e.target.value)} />
            </div>
          ))}

          <div className="onb-row">
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

          {error && <div className="onb-error">{error}</div>}

          <button
            className="onb-btn-primary"
            disabled={!step3Ready || loading}
            type="button"
            onClick={handleAddClient}
          >
            {loading ? 'Сохраняем...' : 'Добавить и продолжить'}
          </button>
          <button className="onb-btn-secondary" disabled={loading} type="button" onClick={handleSkipClient}>
            Пропустить
          </button>
        </section>
      )}

      {/* ── Step 4: Final ─────────────────────────────── */}
      {step === 4 && (
        <section className="onb-card onb-card-final">
          <div className="onb-success-icon">
            <CheckIcon />
          </div>
          <div className="onb-final-title">
              Всё готово, {name}!
          </div>
          <div className="onb-final-subtitle">
            {clientAdded
              ? 'Остались вопросы? Пиши нам @pastushenko12'
              : 'Добавь первого клиента — это займёт 30 секунд'}
          </div>

          {!WebApp?.MainButton && (
            <button className="onb-btn-primary" type="button" onClick={onRegistered}>
              Начать работу
            </button>
          )}
        </section>
      )}
      </div>
    </div>
  );
}
