import { useState, useEffect } from 'react';
import { registerMaster, createMasterClient, createMasterOrder, updateMasterProfile } from '../../api/client';
import { useI18n } from '../../i18n';

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

function formatDateDisplay(iso, locale, tr) {
  if (!iso) return tr('Выберите дату', 'Pick date');
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
}

function DatePickerField({ label, value, onChange }) {
  const { tr, locale } = useI18n();
  return (
    <div className="onb-field-group onb-field-flex">
      {label && <label className="onb-label">{label}</label>}
      <div className="onb-picker-wrap">
        <div className="onb-input onb-picker-display">{formatDateDisplay(value, locale, tr)}</div>
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
  const { tr } = useI18n();
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
        const msg = err?.response?.data?.detail || tr('Ошибка регистрации. Попробуйте ещё раз.', 'Registration failed. Please try again.');
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
      setError(err?.response?.data?.detail || tr('Не удалось добавить клиента.', 'Failed to add client.'));
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
    WebApp.MainButton.setText(tr('Начать работу', 'Start working'));
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleStart);
    return () => { WebApp.MainButton.offClick(handleStart); WebApp.MainButton.hide(); };
  }, [step, onRegistered, tr]);

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
          <h1 className="onb-title">{tr('Как тебя зовут?', 'What is your name?')}</h1>
          <p className="onb-subtitle">{tr('Будем обращаться по имени', 'We will address you by name')}</p>

          <div className="onb-field-group">
            <label className="onb-label">{tr('Имя', 'Name')}</label>
            <input
              className="onb-input"
              placeholder={tr('Например: Анна', 'For example: Anna')}
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
            {tr('Продолжить', 'Continue')}
          </button>
        </section>
      )}

      {/* ── Step 2: Niche ─────────────────────────────── */}
      {step === 2 && (
        <section className="onb-card">
          <button className="onb-back-btn" type="button" onClick={() => { setError(''); setStep(1); }}>
            <ChevronLeftIcon />
            <span>{tr('Назад', 'Back')}</span>
          </button>
          <h1 className="onb-title">{tr('Чем занимаешься?', 'What do you do?')}</h1>
          <p className="onb-subtitle">{tr('Выбери до 3 направлений', 'Select up to 3 niches')}</p>

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
                  {tr(
                    niche,
                    niche === 'Клининг' ? 'Cleaning'
                      : niche === 'Химчистка мебели и ковров' ? 'Furniture and carpet cleaning'
                      : niche === 'Парикмахер и барбер' ? 'Hairdresser and barber'
                      : niche === 'Маникюр и бьюти-услуги' ? 'Manicure and beauty services'
                      : niche === 'Груминг и животные' ? 'Grooming and pets'
                      : niche === 'Массаж' ? 'Massage'
                      : niche === 'Ремонт бытовой техники' ? 'Appliance repair'
                      : niche === 'Мастер на час, мелкий ремонт' ? 'Handyman, minor repairs'
                      : niche === 'Репетитор' ? 'Tutor'
                      : niche === 'Фотограф и видеограф' ? 'Photographer and videographer'
                      : niche === 'Психолог' ? 'Psychologist'
                      : niche === 'Садовник' ? 'Gardener'
                      : 'Other'
                  )}
                </button>
              );
          })}
          </div>

          {selectedNiches.includes('Другое') && (
            <div className="onb-field-group">
              <label className="onb-label">{tr('Своя ниша', 'Your niche')}</label>
              <input
                className="onb-input"
                placeholder={tr('Напишите вашу нишу', 'Write your niche')}
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
            {loading ? tr('Сохраняем...', 'Saving...') : tr('Продолжить', 'Continue')}
          </button>
        </section>
      )}

      {/* ── Step 3: First Client ───────────────────────── */}
      {step === 3 && (
        <section className="onb-card">
          <button className="onb-back-btn" type="button" onClick={() => { setError(''); setStep(2); }}>
            <ChevronLeftIcon />
            <span>{tr('Назад', 'Back')}</span>
          </button>
          <h1 className="onb-title">{tr('Добавим первого клиента?', 'Add your first client?')}</h1>
          <p className="onb-subtitle">{tr('Создай свою первую запись сейчас или позже', 'Create your first booking now or later')}</p>

          {[
            { label: tr('Имя клиента', 'Client name'), type: 'text', value: clientName, set: setClientName, placeholder: tr('Например: Мария', 'For example: Maria') },
            { label: tr('Телефон', 'Phone'), type: 'tel', value: clientPhone, set: setClientPhone, placeholder: '+7 999 123 45 67' },
          ].map(({ label, type, value, set, placeholder }) => (
            <div key={label} className="onb-field-group">
              <label className="onb-label">{label}</label>
              <input className="onb-input" type={type} placeholder={placeholder} value={value} onChange={(e) => set(e.target.value)} />
            </div>
          ))}

          <div className="onb-row">
            <DatePickerField
              label={tr('Дата записи', 'Booking date')}
              value={clientDate}
              onChange={(e) => setClientDate(e.target.value)}
            />
            <TimePickerField
              label={tr('Время', 'Time')}
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
            {loading ? tr('Сохраняем...', 'Saving...') : tr('Добавить и продолжить', 'Add and continue')}
          </button>
          <button className="onb-btn-secondary" disabled={loading} type="button" onClick={handleSkipClient}>
            {tr('Пропустить', 'Skip')}
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
              {tr('Всё готово', 'All set')}, {name}!
          </div>
          <div className="onb-final-subtitle">
            {clientAdded
              ? tr('Остались вопросы? Пиши нам @pastushenko12', 'Any questions? Message us @pastushenko12')
              : tr('Добавь первого клиента — это займёт 30 секунд', 'Add your first client - it takes 30 seconds')}
          </div>

          {!WebApp?.MainButton && (
            <button className="onb-btn-primary" type="button" onClick={onRegistered}>
              {tr('Начать работу', 'Start working')}
            </button>
          )}
        </section>
      )}
      </div>
    </div>
  );
}
