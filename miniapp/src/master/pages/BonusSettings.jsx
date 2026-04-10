import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterBonusSettings, getMasterMe, updateMasterBonusSettings } from '../../api/client';

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

const iconProps = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
};

const GiftIcon = () => (
  <svg {...iconProps}>
    <path d="M20 12v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-8" />
    <path d="M2 7h20v5H2z" />
    <path d="M12 22V7" />
    <path d="M12 7h-2a3 3 0 1 1 0-6c3 0 3 6 3 6Z" />
    <path d="M12 7h2a3 3 0 1 0 0-6c-3 0-3 6-3 6Z" />
  </svg>
);

const PercentIcon = () => (
  <svg {...iconProps}>
    <path d="M19 5 5 19" />
    <circle cx="7" cy="7" r="2" />
    <circle cx="17" cy="17" r="2" />
  </svg>
);

const MessageIcon = () => (
  <svg {...iconProps}>
    <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8A8.5 8.5 0 0 1 12.5 20H4l1.9-3.8A8.5 8.5 0 1 1 21 11.5Z" />
  </svg>
);

const ChevronIcon = () => (
  <svg {...iconProps} width={14} height={14}>
    <path d="m9 18 6-6-6-6" />
  </svg>
);

function SectionTitle({ children }) {
  return <div className="enterprise-section-title">{children}</div>;
}

function getCurrencySymbol(code) {
  const map = {
    RUB: '₽',
    EUR: '€',
    ILS: '₪',
    USD: '$',
    UAH: '₴',
    BYN: 'Br',
    KZT: '₸',
    TRY: '₺',
    GEL: '₾',
    UZS: 'сум',
  };
  return map[code] || code || '₽';
}

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={`enterprise-bonus-toggle${checked ? ' is-on' : ''}`}
      onClick={() => {
        if (disabled) return;
        haptic();
        onChange(!checked);
      }}
    >
      <span className="enterprise-bonus-toggle-knob" />
    </button>
  );
}

function NumRow({ label, value, hint, unit, onChange, disabled, isLast = false }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ''));

  useEffect(() => {
    setDraft(String(value ?? ''));
  }, [value]);

  const handleSave = () => {
    const normalized = String(draft || '').trim().replace(',', '.');
    const parsed = Number(normalized);
    if (!Number.isNaN(parsed) && parsed >= 0) {
      onChange(parsed);
    }
    setEditing(false);
  };

  return (
    <div className={`enterprise-bonus-row${disabled ? ' is-disabled' : ''}${isLast ? ' is-last' : ''}`}>
      <div className="enterprise-bonus-row-head">
        <span className="enterprise-bonus-row-label">{label}</span>
        {editing ? (
          <div className="enterprise-bonus-row-edit-wrap">
            <input
              type="number"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoFocus
              className="enterprise-bonus-row-input"
              onBlur={handleSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave();
              }}
            />
            {unit && <span className="enterprise-bonus-row-unit">{unit}</span>}
          </div>
        ) : (
          <button
            type="button"
            disabled={disabled}
            className="enterprise-bonus-row-value"
            onClick={() => {
              if (disabled) return;
              haptic();
              setEditing(true);
            }}
          >
            {value ?? 0}{unit || ''}
          </button>
        )}
      </div>
      {hint && <div className="enterprise-bonus-row-hint">{hint}</div>}
    </div>
  );
}

function MessageCell({ label, value, onClick, isLast = false }) {
  return (
    <button
      type="button"
      className={`enterprise-cell is-interactive${isLast ? ' is-last' : ''}`}
      onClick={() => {
        haptic();
        onClick();
      }}
    >
      <span className="enterprise-cell-icon"><MessageIcon /></span>
      <span className="enterprise-cell-label">{label}</span>
      <span className="enterprise-cell-value">{value}</span>
      <span className="enterprise-cell-chevron"><ChevronIcon /></span>
    </button>
  );
}

export default function BonusSettings({ onNavigate }) {
  const [localSettings, setLocalSettings] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['master-bonus-settings'],
    queryFn: getMasterBonusSettings,
    staleTime: 30_000,
  });
  const { data: masterData } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (data && !localSettings) {
      setLocalSettings(data);
    }
  }, [data, localSettings]);

  const mutation = useMutation({
    mutationFn: updateMasterBonusSettings,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-bonus-settings'] });
      hapticNotify('success');
      setSuccessMsg('Сохранено');
      setTimeout(() => setSuccessMsg(''), 1600);
    },
    onError: () => hapticNotify('error'),
  });

  const update = (key, value) => {
    const next = { ...localSettings, [key]: value };
    setLocalSettings(next);
    mutation.mutate({ [key]: value });
  };

  if (isLoading || !localSettings) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        Загрузка...
      </div>
    );
  }

  const disabled = !localSettings.bonus_enabled;
  const currencySymbol = getCurrencySymbol(masterData?.currency);
  const currencyUnit = ` ${currencySymbol}`;
  const hasWelcomeTemplate = Boolean((localSettings.welcome_message || '').trim() || localSettings.welcome_photo_url);
  const hasBirthdayTemplate = Boolean((localSettings.birthday_message || '').trim() || localSettings.birthday_photo_url);

  return (
    <div className="enterprise-bonus-page">
      {successMsg && <div className="enterprise-profile-toast">{successMsg}</div>}

      <SectionTitle>Бонусная программа</SectionTitle>
      <div className="enterprise-cell-group">
        <div className="enterprise-bonus-switch-row">
          <div className="enterprise-bonus-switch-left">
            <span className="enterprise-cell-icon"><GiftIcon /></span>
            <div>
              <div className="enterprise-bonus-switch-title">Бонусная программа</div>
              <div className="enterprise-bonus-switch-subtitle">
                {localSettings.bonus_enabled ? 'Включена' : 'Выключена'}
              </div>
            </div>
          </div>
          <Toggle
            checked={localSettings.bonus_enabled}
            onChange={(v) => update('bonus_enabled', v)}
            disabled={mutation.isPending}
          />
        </div>
      </div>

      <SectionTitle>Параметры</SectionTitle>
      <div className="enterprise-cell-group">
        <div className="enterprise-bonus-param-head">
          <span className="enterprise-cell-icon"><PercentIcon /></span>
          <span>Начисления и списания</span>
        </div>
        <NumRow
          label="Процент начисления"
          value={localSettings.bonus_rate}
          unit="%"
          hint={`Клиент получит ${localSettings.bonus_rate}% от суммы заказа`}
          onChange={(v) => update('bonus_rate', v)}
          disabled={disabled}
        />
        <NumRow
          label="Макс. списание"
          value={localSettings.bonus_max_spend}
          unit="%"
          hint={`Клиент может оплатить бонусами до ${localSettings.bonus_max_spend}% заказа`}
          onChange={(v) => update('bonus_max_spend', v)}
          disabled={disabled}
        />
        <NumRow
          label="Приветственный бонус"
          value={localSettings.bonus_welcome}
          unit={currencyUnit}
          hint={localSettings.bonus_welcome > 0 ? `При первом визите: ${localSettings.bonus_welcome}${currencyUnit}` : '0 = выключено'}
          onChange={(v) => update('bonus_welcome', v)}
          disabled={disabled}
        />
        <NumRow
          label="Бонус на день рождения"
          value={localSettings.bonus_birthday}
          unit={currencyUnit}
          hint={localSettings.bonus_birthday > 0 ? `В день рождения: ${localSettings.bonus_birthday}${currencyUnit}` : '0 = выключено'}
          onChange={(v) => update('bonus_birthday', v)}
          disabled={disabled}
          isLast
        />
      </div>

      <SectionTitle>Сообщения</SectionTitle>
      <div className="enterprise-cell-group">
        <MessageCell
          label="Приветствие"
          value={hasWelcomeTemplate ? 'Кастомизировано' : 'Стандартный текст'}
          onClick={() => onNavigate?.('bonus_message', { kind: 'welcome' })}
        />
        <MessageCell
          label="Поздравление"
          value={hasBirthdayTemplate ? 'Кастомизировано' : 'Стандартный текст'}
          onClick={() => onNavigate?.('bonus_message', { kind: 'birthday' })}
          isLast
        />
      </div>
    </div>
  );
}
