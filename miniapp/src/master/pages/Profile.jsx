import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterMe,
  getMasterInvite,
  updateMasterProfile,
  updateMasterTimezone,
  updateMasterCurrency,
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

const TIMEZONES = [
  { value: 'Europe/London', label: 'Лондон' },
  { value: 'Europe/Lisbon', label: 'Лиссабон' },
  { value: 'Europe/Madrid', label: 'Мадрид' },
  { value: 'Europe/Paris', label: 'Париж' },
  { value: 'Europe/Berlin', label: 'Берлин' },
  { value: 'Europe/Rome', label: 'Рим' },
  { value: 'Europe/Amsterdam', label: 'Амстердам' },
  { value: 'Europe/Brussels', label: 'Брюссель' },
  { value: 'Europe/Vienna', label: 'Вена' },
  { value: 'Europe/Prague', label: 'Прага' },
  { value: 'Europe/Warsaw', label: 'Варшава' },
  { value: 'Europe/Belgrade', label: 'Белград' },
  { value: 'Europe/Athens', label: 'Афины' },
  { value: 'Europe/Bucharest', label: 'Бухарест' },
  { value: 'Europe/Helsinki', label: 'Хельсинки' },
  { value: 'Europe/Riga', label: 'Рига' },
  { value: 'Europe/Vilnius', label: 'Вильнюс' },
  { value: 'Europe/Tallinn', label: 'Таллин' },
  { value: 'Asia/Jerusalem', label: 'Иерусалим' },
  { value: 'Europe/Kaliningrad', label: 'Калининград (UTC+2)' },
  { value: 'Europe/Moscow', label: 'Москва (UTC+3)' },
  { value: 'Europe/Minsk', label: 'Минск (UTC+3)' },
  { value: 'Europe/Kiev', label: 'Киев (UTC+2/3)' },
  { value: 'Europe/Istanbul', label: 'Стамбул (UTC+3)' },
  { value: 'Asia/Yekaterinburg', label: 'Екатеринбург (UTC+5)' },
  { value: 'Asia/Almaty', label: 'Алматы (UTC+5)' },
  { value: 'Asia/Novosibirsk', label: 'Новосибирск (UTC+7)' },
  { value: 'Asia/Krasnoyarsk', label: 'Красноярск (UTC+7)' },
  { value: 'Asia/Irkutsk', label: 'Иркутск (UTC+8)' },
  { value: 'Asia/Vladivostok', label: 'Владивосток (UTC+10)' },
  { value: 'Asia/Kamchatka', label: 'Камчатка (UTC+12)' },
];

const CURRENCIES = [
  { value: 'RUB', label: 'Рубль ₽' },
  { value: 'EUR', label: 'Евро €' },
  { value: 'ILS', label: 'Шекель ₪' },
  { value: 'UAH', label: 'Гривна ₴' },
  { value: 'BYN', label: 'Белорусский рубль Br' },
  { value: 'KZT', label: 'Тенге ₸' },
  { value: 'USD', label: 'Доллар $' },
  { value: 'TRY', label: 'Лира ₺' },
  { value: 'GEL', label: 'Лари ₾' },
  { value: 'UZS', label: 'Сум' },
];

const WORK_MODES = [
  { value: 'home', label: 'Дома' },
  { value: 'travel', label: 'На выезде' },
];

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

const UserIcon = () => (
  <svg {...iconProps}>
    <circle cx="12" cy="8" r="4" />
    <path d="M5 21a7 7 0 0 1 14 0" />
  </svg>
);

const BriefcaseIcon = () => (
  <svg {...iconProps}>
    <rect x="3" y="7" width="18" height="14" rx="2" />
    <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <path d="M3 12h18" />
  </svg>
);

const PhoneIcon = () => (
  <svg {...iconProps}>
    <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.9 19.9 0 0 1-8.7-3.1 19.4 19.4 0 0 1-6-6A19.9 19.9 0 0 1 2 4.1 2 2 0 0 1 4 1.9h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.6a2 2 0 0 1-.4 2.1L8 9.6a16 16 0 0 0 6.4 6.4l1.3-1.2a2 2 0 0 1 2.1-.4c.8.3 1.7.5 2.6.6A2 2 0 0 1 22 16.9Z" />
  </svg>
);

const LinkIcon = () => (
  <svg {...iconProps}>
    <path d="M10 13a5 5 0 0 0 7.1 0l2.8-2.8a5 5 0 1 0-7.1-7.1L10 4" />
    <path d="M14 11a5 5 0 0 0-7.1 0L4.1 13.8a5 5 0 1 0 7.1 7.1L14 20" />
  </svg>
);

const ClockIcon = () => (
  <svg {...iconProps}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v6l4 2" />
  </svg>
);

const HomeIcon = () => (
  <svg {...iconProps}>
    <path d="M3 10.5 12 3l9 7.5" />
    <path d="M5 9.5V21h14V9.5" />
  </svg>
);

const GlobeIcon = () => (
  <svg {...iconProps}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18" />
    <path d="M12 3c2.8 2.5 4.5 5.7 4.5 9s-1.7 6.5-4.5 9c-2.8-2.5-4.5-5.7-4.5-9S9.2 5.5 12 3Z" />
  </svg>
);

const DollarIcon = () => (
  <svg {...iconProps}>
    <path d="M12 2v20" />
    <path d="M17 6.5c0-2-2.2-3.5-5-3.5S7 4.5 7 6.5 9.2 10 12 10s5 1.5 5 3.5-2.2 3.5-5 3.5-5-1.5-5-3.5" />
  </svg>
);

const MapPinIcon = () => (
  <svg {...iconProps}>
    <path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12Z" />
    <circle cx="12" cy="10" r="2.5" />
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

function Cell({ icon, label, value, onClick }) {
  return (
    <button className="enterprise-cell is-interactive" onClick={() => { haptic(); onClick(); }}>
      {icon && <span className="enterprise-cell-icon">{icon}</span>}
      <span className="enterprise-cell-label">{label}</span>
      <span className="enterprise-cell-value">{value || 'не указано'}</span>
      <span className="enterprise-cell-chevron"><ChevronIcon /></span>
    </button>
  );
}

function PickerSheet({ title, options, value, onChange, onClose, loading }) {
  return (
    <>
      <div className="enterprise-sheet-backdrop" onClick={onClose} />
      <div className="enterprise-sheet">
        <div className="enterprise-sheet-handle" />
        <div className="enterprise-sheet-title">{title}</div>
        {options.map((opt) => (
          <button
            key={opt.value}
            className={`enterprise-sheet-option${opt.value === value ? ' is-active' : ''}`}
            onClick={() => {
              if (loading) return;
              haptic();
              onChange(opt.value);
              onClose();
            }}
          >
            <span>{opt.label}</span>
            {opt.value === value && <span>✓</span>}
          </button>
        ))}
      </div>
    </>
  );
}

function TextEditSheet({ title, value, placeholder, multiline, loading, onClose, onSave }) {
  const [draft, setDraft] = useState(value || '');

  const handleSave = async () => {
    haptic('medium');
    await onSave(draft);
  };

  return (
    <>
      <div className="enterprise-sheet-backdrop" onClick={onClose} />
      <div className="enterprise-sheet">
        <div className="enterprise-sheet-handle" />
        <div className="enterprise-sheet-title">{title}</div>
        {multiline ? (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            rows={4}
            className="enterprise-sheet-input"
          />
        ) : (
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            className="enterprise-sheet-input"
          />
        )}
        <div className="enterprise-sheet-actions">
          <button className="enterprise-sheet-btn secondary" onClick={onClose}>
            Отмена
          </button>
          <button className="enterprise-sheet-btn primary" onClick={handleSave} disabled={loading}>
            {loading ? 'Сохраняем...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </>
  );
}

export default function Profile() {
  const [picker, setPicker] = useState(null);
  const [editor, setEditor] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  const qc = useQueryClient();

  const { data: master, isLoading } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 60_000,
  });

  const { data: inviteData } = useQuery({
    queryKey: ['master-invite'],
    queryFn: getMasterInvite,
    staleTime: 5 * 60_000,
  });

  const showSuccess = (msg = 'Сохранено') => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 1800);
  };

  const profileMutation = useMutation({
    mutationFn: updateMasterProfile,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-me'] });
      showSuccess('Профиль обновлён');
    },
    onError: (err) => {
      hapticNotify('error');
      const msg = err?.response?.data?.detail || 'Не удалось сохранить';
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
    },
  });

  const tzMutation = useMutation({
    mutationFn: updateMasterTimezone,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-me'] });
      showSuccess('Часовой пояс сохранён');
    },
    onError: () => hapticNotify('error'),
  });

  const curMutation = useMutation({
    mutationFn: updateMasterCurrency,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-me'] });
      showSuccess('Валюта сохранена');
    },
    onError: () => hapticNotify('error'),
  });

  const handleCopyInvite = async () => {
    const link = inviteData?.invite_link;
    if (!link) return;
    haptic('medium');
    try {
      if (typeof navigator?.clipboard?.writeText === 'function') {
        await navigator.clipboard.writeText(link);
        showSuccess('Ссылка скопирована');
        return;
      }
    } catch (_) {
      // Fallback to popup below.
    }
    if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup({ title: 'Инвайт-ссылка', message: link, buttons: [{ type: 'ok' }] });
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        Загрузка профиля...
      </div>
    );
  }

  const tzLabel = TIMEZONES.find((t) => t.value === master?.timezone)?.label || master?.timezone || '—';
  const curLabel = CURRENCIES.find((c) => c.value === master?.currency)?.label || master?.currency || '—';
  const workModeLabel = WORK_MODES.find((m) => m.value === master?.work_mode)?.label || 'На выезде';

  return (
    <div className="enterprise-profile-page">
      {successMsg && (
        <div className="enterprise-profile-toast">
          {successMsg}
        </div>
      )}

      <div className="enterprise-profile-hero">
        <div className="enterprise-profile-avatar">
          {(master?.name || '?')[0].toUpperCase()}
        </div>
        <div className="enterprise-profile-name">{master?.name || '—'}</div>
        <div className="enterprise-profile-subtitle">{master?.sphere || 'Сфера не указана'}</div>
      </div>

      <SectionTitle>Профиль</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<UserIcon />}
          label="Имя"
          value={master?.name || 'не указано'}
          onClick={() => setEditor({ field: 'name', title: 'Имя', value: master?.name || '', placeholder: 'Введите имя' })}
        />
        <Cell
          icon={<BriefcaseIcon />}
          label="Сфера деятельности"
          value={master?.sphere || 'не указано'}
          onClick={() => setEditor({ field: 'sphere', title: 'Сфера деятельности', value: master?.sphere || '', placeholder: 'Например: барбер, мастер маникюра' })}
        />
        <Cell
          icon={<PhoneIcon />}
          label="Контакты"
          value={master?.contacts || 'не указано'}
          onClick={() => setEditor({ field: 'contacts', title: 'Контакты', value: master?.contacts || '', placeholder: 'Телефон, Telegram, WhatsApp' })}
        />
        <Cell
          icon={<LinkIcon />}
          label="Соцсети"
          value={master?.socials || 'не указано'}
          onClick={() => setEditor({ field: 'socials', title: 'Соцсети', value: master?.socials || '', placeholder: '@username или ссылка' })}
        />
        <Cell
          icon={<ClockIcon />}
          label="График работы"
          value={master?.work_hours || 'не указано'}
          onClick={() => setEditor({ field: 'work_hours', title: 'График работы', value: master?.work_hours || '', placeholder: 'Пн-Пт 10:00-20:00' })}
        />
      </div>

      <SectionTitle>Формат работы</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<HomeIcon />}
          label="Я работаю"
          value={workModeLabel}
          onClick={() => setPicker('work_mode')}
        />
        <Cell
          icon={<MapPinIcon />}
          label="Мой адрес по умолчанию"
          value={master?.work_address_default || 'не указан'}
          onClick={() => setEditor({
            field: 'work_address_default',
            title: 'Мой адрес по умолчанию',
            value: master?.work_address_default || '',
            placeholder: 'Адрес дома / кабинета / салона',
            multiline: true,
          })}
        />
      </div>

      <SectionTitle>Регион</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<GlobeIcon />}
          label="Часовой пояс"
          value={tzLabel}
          onClick={() => setPicker('timezone')}
        />
        <Cell
          icon={<DollarIcon />}
          label="Валюта"
          value={curLabel}
          onClick={() => setPicker('currency')}
        />
      </div>

      <SectionTitle>Инвайт</SectionTitle>
      <div className="enterprise-profile-invite">
        <div className="enterprise-profile-invite-link">{inviteData?.invite_link || '—'}</div>
        <button
          className="enterprise-profile-copy-btn"
          onClick={handleCopyInvite}
          disabled={!inviteData?.invite_link}
        >
          Копировать ссылку
        </button>
      </div>

      {picker === 'work_mode' && (
        <PickerSheet
          title="Я работаю"
          options={WORK_MODES}
          value={master?.work_mode || 'travel'}
          onChange={(mode) => profileMutation.mutate({ work_mode: mode })}
          onClose={() => setPicker(null)}
          loading={profileMutation.isPending}
        />
      )}

      {picker === 'timezone' && (
        <PickerSheet
          title="Часовой пояс"
          options={TIMEZONES}
          value={master?.timezone}
          onChange={(tz) => tzMutation.mutate(tz)}
          onClose={() => setPicker(null)}
          loading={tzMutation.isPending}
        />
      )}

      {picker === 'currency' && (
        <PickerSheet
          title="Валюта"
          options={CURRENCIES}
          value={master?.currency}
          onChange={(cur) => curMutation.mutate(cur)}
          onClose={() => setPicker(null)}
          loading={curMutation.isPending}
        />
      )}

      {editor && (
        <TextEditSheet
          title={editor.title}
          value={editor.value}
          placeholder={editor.placeholder}
          multiline={Boolean(editor.multiline)}
          loading={profileMutation.isPending}
          onClose={() => setEditor(null)}
          onSave={async (nextValue) => {
            await profileMutation.mutateAsync({ [editor.field]: nextValue });
            setEditor(null);
          }}
        />
      )}
    </div>
  );
}
