import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterMe,
  getMasterInvite,
  updateMasterProfile,
  updateMasterTimezone,
  updateMasterCurrency,
} from '../../api/client';
import { useI18n } from '../../i18n';

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
  { value: 'Europe/London', key: 'london' },
  { value: 'Europe/Lisbon', key: 'lisbon' },
  { value: 'Europe/Madrid', key: 'madrid' },
  { value: 'Europe/Paris', key: 'paris' },
  { value: 'Europe/Berlin', key: 'berlin' },
  { value: 'Europe/Rome', key: 'rome' },
  { value: 'Europe/Amsterdam', key: 'amsterdam' },
  { value: 'Europe/Brussels', key: 'brussels' },
  { value: 'Europe/Vienna', key: 'vienna' },
  { value: 'Europe/Prague', key: 'prague' },
  { value: 'Europe/Warsaw', key: 'warsaw' },
  { value: 'Europe/Belgrade', key: 'belgrade' },
  { value: 'Europe/Athens', key: 'athens' },
  { value: 'Europe/Bucharest', key: 'bucharest' },
  { value: 'Europe/Helsinki', key: 'helsinki' },
  { value: 'Europe/Riga', key: 'riga' },
  { value: 'Europe/Vilnius', key: 'vilnius' },
  { value: 'Europe/Tallinn', key: 'tallinn' },
  { value: 'Asia/Jerusalem', key: 'jerusalem' },
  { value: 'Europe/Kaliningrad', key: 'kaliningrad' },
  { value: 'Europe/Moscow', key: 'moscow' },
  { value: 'Europe/Minsk', key: 'minsk' },
  { value: 'Europe/Kiev', key: 'kiev' },
  { value: 'Europe/Istanbul', key: 'istanbul' },
  { value: 'Asia/Yekaterinburg', key: 'yekaterinburg' },
  { value: 'Asia/Almaty', key: 'almaty' },
  { value: 'Asia/Novosibirsk', key: 'novosibirsk' },
  { value: 'Asia/Krasnoyarsk', key: 'krasnoyarsk' },
  { value: 'Asia/Irkutsk', key: 'irkutsk' },
  { value: 'Asia/Vladivostok', key: 'vladivostok' },
  { value: 'Asia/Kamchatka', key: 'kamchatka' },
];

const CURRENCIES = ['RUB', 'EUR', 'ILS', 'UAH', 'BYN', 'KZT', 'USD', 'TRY', 'GEL', 'UZS'];
const WORK_MODES = ['home', 'travel'];
const LANG_OPTIONS = ['ru', 'en'];

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

const LanguageIcon = () => (
  <svg {...iconProps}>
    <path d="M4 5h16" />
    <path d="M12 3v2" />
    <path d="M7 5c0 5 2 9 5 11" />
    <path d="M17 5c0 5-2 9-5 11" />
    <path d="M8 14h8" />
    <path d="m14 21 2-6 2 6" />
    <path d="M13 19h6" />
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

function Cell({ icon, label, value, onClick, fallbackValue }) {
  return (
    <button className="enterprise-cell is-interactive" onClick={() => { haptic(); onClick(); }}>
      {icon && <span className="enterprise-cell-icon">{icon}</span>}
      <span className="enterprise-cell-label">{label}</span>
      <span className="enterprise-cell-value">{value || fallbackValue}</span>
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
  const { t } = useI18n();
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
            {t('common.cancel')}
          </button>
          <button className="enterprise-sheet-btn primary" onClick={handleSave} disabled={loading}>
            {loading ? t('common.saving') : t('common.save')}
          </button>
        </div>
      </div>
    </>
  );
}

export default function Profile() {
  const { t, lang, setLang } = useI18n();
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

  const showSuccess = (msg = t('profile.toasts.saved')) => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 1800);
  };

  const profileMutation = useMutation({
    mutationFn: updateMasterProfile,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-me'] });
      showSuccess(t('profile.toasts.profileUpdated'));
    },
    onError: (err) => {
      hapticNotify('error');
      const msg = err?.response?.data?.detail || t('profile.errors.saveFailed');
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
    },
  });

  const tzMutation = useMutation({
    mutationFn: updateMasterTimezone,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-me'] });
      showSuccess(t('profile.toasts.timezoneSaved'));
    },
    onError: () => hapticNotify('error'),
  });

  const curMutation = useMutation({
    mutationFn: updateMasterCurrency,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-me'] });
      showSuccess(t('profile.toasts.currencySaved'));
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
        showSuccess(t('profile.toasts.linkCopied'));
        return;
      }
    } catch (_) {
      // Fallback to popup below.
    }
    if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup({ title: t('profile.popup.inviteTitle'), message: link, buttons: [{ type: 'ok' }] });
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        {t('profile.loading')}
      </div>
    );
  }

  const timezoneOptions = TIMEZONES.map((item) => ({
    value: item.value,
    label: t(`profile.timezones.${item.key}`),
  }));

  const currencyOptions = CURRENCIES.map((code) => ({
    value: code,
    label: t(`profile.currencies.${code}`),
  }));

  const workModeOptions = WORK_MODES.map((mode) => ({
    value: mode,
    label: t(`profile.workModes.${mode}`),
  }));

  const languageOptions = LANG_OPTIONS.map((code) => ({
    value: code,
    label: t(`profile.language.${code}`),
  }));

  const tzLabel = timezoneOptions.find((item) => item.value === master?.timezone)?.label || master?.timezone || t('common.dash');
  const curLabel = currencyOptions.find((item) => item.value === master?.currency)?.label || master?.currency || t('common.dash');
  const workModeLabel = workModeOptions.find((item) => item.value === master?.work_mode)?.label || t('profile.workModes.travel');
  const langLabel = languageOptions.find((item) => item.value === lang)?.label || t('profile.language.ru');
  const contactsValue = master?.phone || master?.contacts;

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
        <div className="enterprise-profile-name">{master?.name || t('common.dash')}</div>
        <div className="enterprise-profile-subtitle">{master?.sphere || t('profile.values.sphereNotSpecified')}</div>
      </div>

      <SectionTitle>{t('profile.sections.profile')}</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<UserIcon />}
          label={t('profile.fields.name')}
          value={master?.name}
          fallbackValue={t('common.notSpecified')}
          onClick={() => setEditor({ field: 'name', title: t('profile.fields.name'), value: master?.name || '', placeholder: t('profile.placeholders.name') })}
        />
        <Cell
          icon={<BriefcaseIcon />}
          label={t('profile.fields.sphere')}
          value={master?.sphere}
          fallbackValue={t('common.notSpecified')}
          onClick={() => setEditor({ field: 'sphere', title: t('profile.fields.sphere'), value: master?.sphere || '', placeholder: t('profile.placeholders.sphere') })}
        />
        <Cell
          icon={<PhoneIcon />}
          label={t('profile.fields.contacts')}
          value={contactsValue}
          fallbackValue={t('common.notSpecified')}
          onClick={() => setEditor({ field: 'phone', title: t('profile.fields.contacts'), value: contactsValue || '', placeholder: t('profile.placeholders.contacts') })}
        />
        <Cell
          icon={<LinkIcon />}
          label={t('profile.fields.socials')}
          value={master?.socials}
          fallbackValue={t('common.notSpecified')}
          onClick={() => setEditor({ field: 'socials', title: t('profile.fields.socials'), value: master?.socials || '', placeholder: t('profile.placeholders.socials') })}
        />
        <Cell
          icon={<ClockIcon />}
          label={t('profile.fields.workHours')}
          value={master?.work_hours}
          fallbackValue={t('common.notSpecified')}
          onClick={() => setEditor({ field: 'work_hours', title: t('profile.fields.workHours'), value: master?.work_hours || '', placeholder: t('profile.placeholders.workHours') })}
        />
      </div>

      <SectionTitle>{t('profile.sections.workMode')}</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<HomeIcon />}
          label={t('profile.fields.iWork')}
          value={workModeLabel}
          fallbackValue={t('common.notSpecified')}
          onClick={() => setPicker('work_mode')}
        />
        <Cell
          icon={<MapPinIcon />}
          label={t('profile.fields.defaultAddress')}
          value={master?.work_address_default}
          fallbackValue={t('common.notSpecifiedMale')}
          onClick={() => setEditor({
            field: 'work_address_default',
            title: t('profile.fields.defaultAddress'),
            value: master?.work_address_default || '',
            placeholder: t('profile.placeholders.defaultAddress'),
            multiline: true,
          })}
        />
      </div>

      <SectionTitle>{t('profile.sections.region')}</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<GlobeIcon />}
          label={t('profile.fields.timezone')}
          value={tzLabel}
          fallbackValue={t('common.dash')}
          onClick={() => setPicker('timezone')}
        />
        <Cell
          icon={<DollarIcon />}
          label={t('profile.fields.currency')}
          value={curLabel}
          fallbackValue={t('common.dash')}
          onClick={() => setPicker('currency')}
        />
      </div>

      <SectionTitle>{t('profile.sections.preferences')}</SectionTitle>
      <div className="enterprise-cell-group">
        <Cell
          icon={<LanguageIcon />}
          label={t('profile.fields.language')}
          value={langLabel}
          fallbackValue={t('common.dash')}
          onClick={() => setPicker('language')}
        />
      </div>

      <SectionTitle>{t('profile.sections.invite')}</SectionTitle>
      <div className="enterprise-profile-invite">
        <div className="enterprise-profile-invite-link">{inviteData?.invite_link || t('common.dash')}</div>
        <button
          className="enterprise-profile-copy-btn"
          onClick={handleCopyInvite}
          disabled={!inviteData?.invite_link}
        >
          {t('common.copyLink')}
        </button>
      </div>

      {picker === 'work_mode' && (
        <PickerSheet
          title={t('profile.fields.iWork')}
          options={workModeOptions}
          value={master?.work_mode || 'travel'}
          onChange={(mode) => profileMutation.mutate({ work_mode: mode })}
          onClose={() => setPicker(null)}
          loading={profileMutation.isPending}
        />
      )}

      {picker === 'timezone' && (
        <PickerSheet
          title={t('profile.fields.timezone')}
          options={timezoneOptions}
          value={master?.timezone}
          onChange={(tz) => tzMutation.mutate(tz)}
          onClose={() => setPicker(null)}
          loading={tzMutation.isPending}
        />
      )}

      {picker === 'currency' && (
        <PickerSheet
          title={t('profile.fields.currency')}
          options={currencyOptions}
          value={master?.currency}
          onChange={(cur) => curMutation.mutate(cur)}
          onClose={() => setPicker(null)}
          loading={curMutation.isPending}
        />
      )}

      {picker === 'language' && (
        <PickerSheet
          title={t('profile.language.pickerTitle')}
          options={languageOptions}
          value={lang}
          onChange={(nextLang) => {
            setLang(nextLang);
            showSuccess(t('profile.toasts.languageSaved'));
          }}
          onClose={() => setPicker(null)}
          loading={false}
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
