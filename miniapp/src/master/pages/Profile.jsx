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
  { value: 'UAH', label: 'Гривна ₴' },
  { value: 'BYN', label: 'Белорусский рубль Br' },
  { value: 'KZT', label: 'Тенге ₸' },
  { value: 'USD', label: 'Доллар $' },
  { value: 'EUR', label: 'Евро €' },
  { value: 'TRY', label: 'Лира ₺' },
  { value: 'GEL', label: 'Лари ₾' },
  { value: 'UZS', label: 'Сум' },
];

const WORK_MODES = [
  { value: 'home', label: 'Дома' },
  { value: 'travel', label: 'На выезде' },
];

// Inline-editable field
function EditableField({ label, value, onSave, loading }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value || '');
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    haptic('medium');
    await onSave(val);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
    setEditing(false);
  };

  const handleStart = () => {
    haptic();
    setVal(value || '');
    setEditing(true);
  };

  if (editing) {
    return (
      <div style={{ padding: '12px 16px', background: 'var(--tg-section-bg)', borderBottom: '1px solid var(--tg-secondary-bg)' }}>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </div>
        <input
          value={val}
          onChange={e => setVal(e.target.value)}
          autoFocus
          style={{
            width: '100%',
            padding: '8px 10px',
            borderRadius: 8,
            border: '1px solid var(--tg-accent)',
            background: 'var(--tg-bg)',
            color: 'var(--tg-text)',
            fontSize: 15,
            boxSizing: 'border-box',
            marginBottom: 8,
          }}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => { haptic(); setEditing(false); }}
            style={{ padding: '6px 16px', borderRadius: 8, border: '1px solid var(--tg-secondary-bg)', background: 'none', color: 'var(--tg-text)', cursor: 'pointer', fontSize: 14 }}
          >
            ✕
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            style={{ padding: '6px 20px', borderRadius: 8, background: 'var(--tg-accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
          >
            ✓
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleStart}
      style={{
        padding: '12px 16px',
        background: 'var(--tg-section-bg)',
        borderBottom: '1px solid var(--tg-secondary-bg)',
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
        <div style={{ fontSize: 15, color: value ? 'var(--tg-text)' : 'var(--tg-hint)', marginTop: 2 }}>
          {saved ? '✓ Сохранено' : (value || 'не указано')}
        </div>
      </div>
      <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
    </div>
  );
}

// Bottom sheet selector
function PickerSheet({ title, options, value, onChange, onClose }) {
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200 }} />
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: 'var(--tg-section-bg)',
        borderRadius: '16px 16px 0 0',
        maxHeight: '60vh',
        overflow: 'auto',
        zIndex: 201,
        animation: 'slideUp 0.2s ease',
      }}>
        <div style={{ padding: '16px', fontSize: 16, fontWeight: 600, borderBottom: '1px solid var(--tg-secondary-bg)' }}>
          {title}
        </div>
        {options.map(opt => (
          <div
            key={opt.value}
            onClick={() => { haptic(); onChange(opt.value); onClose(); }}
            style={{
              padding: '14px 16px',
              borderBottom: '1px solid var(--tg-secondary-bg)',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              color: opt.value === value ? 'var(--tg-accent)' : 'var(--tg-text)',
              fontWeight: opt.value === value ? 600 : 400,
            }}
          >
            {opt.label}
            {opt.value === value && <span>✓</span>}
          </div>
        ))}
        <div style={{ height: 'env(safe-area-inset-bottom, 16px)' }} />
      </div>
      <style>{`@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }`}</style>
    </>
  );
}

export default function Profile() {
  const [picker, setPicker] = useState(null); // 'work_mode' | 'timezone' | 'currency'
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

  const showSuccess = (msg = 'Сохранено ✓') => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 2000);
  };

  const profileMutation = useMutation({
    mutationFn: updateMasterProfile,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['master-me'] }); showSuccess(); },
    onError: () => hapticNotify('error'),
  });

  const tzMutation = useMutation({
    mutationFn: updateMasterTimezone,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['master-me'] }); showSuccess('Часовой пояс сохранён ✓'); },
    onError: () => hapticNotify('error'),
  });

  const curMutation = useMutation({
    mutationFn: updateMasterCurrency,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['master-me'] }); showSuccess('Валюта сохранена ✓'); },
    onError: () => hapticNotify('error'),
  });

  const handleCopyInvite = () => {
    const link = inviteData?.invite_link;
    if (!link) return;
    haptic('medium');
    if (typeof navigator?.clipboard?.writeText === 'function') {
      navigator.clipboard.writeText(link).then(() => showSuccess('Ссылка скопирована ✓'));
    } else if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup({ title: 'Инвайт-ссылка', message: link, buttons: [{ type: 'ok' }] });
    }
  };

  if (isLoading) {
    return <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>Загрузка...</div>;
  }

  const tzLabel = TIMEZONES.find(t => t.value === master?.timezone)?.label || master?.timezone || '—';
  const curLabel = CURRENCIES.find(c => c.value === master?.currency)?.label || master?.currency || '—';
  const workModeLabel = WORK_MODES.find(m => m.value === master?.work_mode)?.label || 'На выезде';

  return (
    <div style={{ paddingBottom: 80 }}>
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

      {/* Avatar */}
      <div style={{ padding: '24px 16px 16px', textAlign: 'center', background: 'var(--tg-section-bg)', borderBottom: '1px solid var(--tg-secondary-bg)' }}>
        <div style={{
          width: 64, height: 64, borderRadius: '50%',
          background: 'var(--tg-accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: 28, fontWeight: 700, margin: '0 auto 12px',
        }}>
          {(master?.name || '?')[0].toUpperCase()}
        </div>
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--tg-text)' }}>{master?.name || '—'}</div>
        {master?.sphere && <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginTop: 4 }}>{master.sphere}</div>}
      </div>

      {/* Profile fields */}
      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
          Профиль
        </div>
        <EditableField
          label="Имя"
          value={master?.name}
          onSave={(v) => profileMutation.mutate({ name: v })}
          loading={profileMutation.isPending}
        />
        <EditableField
          label="Сфера деятельности"
          value={master?.sphere}
          onSave={(v) => profileMutation.mutate({ sphere: v })}
          loading={profileMutation.isPending}
        />
        <EditableField
          label="Контакты"
          value={master?.contacts}
          onSave={(v) => profileMutation.mutate({ contacts: v })}
          loading={profileMutation.isPending}
        />
        <EditableField
          label="Соцсети"
          value={master?.socials}
          onSave={(v) => profileMutation.mutate({ socials: v })}
          loading={profileMutation.isPending}
        />
        <EditableField
          label="График работы"
          value={master?.work_hours}
          onSave={(v) => profileMutation.mutate({ work_hours: v })}
          loading={profileMutation.isPending}
        />
        <EditableField
          label="Мой адрес по умолчанию"
          value={master?.work_address_default}
          onSave={(v) => profileMutation.mutate({ work_address_default: v })}
          loading={profileMutation.isPending}
        />
      </div>

      {/* Work mode / Timezone / Currency */}
      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
          Настройки заказов
        </div>
        <div
          onClick={() => { haptic(); setPicker('work_mode'); }}
          style={{ padding: '12px 16px', background: 'var(--tg-section-bg)', borderBottom: '1px solid var(--tg-secondary-bg)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <div>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Я работаю</div>
            <div style={{ fontSize: 15, color: 'var(--tg-text)', marginTop: 2 }}>{workModeLabel}</div>
          </div>
          <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
          Региональные настройки
        </div>
        <div
          onClick={() => { haptic(); setPicker('timezone'); }}
          style={{ padding: '12px 16px', background: 'var(--tg-section-bg)', borderBottom: '1px solid var(--tg-secondary-bg)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <div>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Часовой пояс</div>
            <div style={{ fontSize: 15, color: 'var(--tg-text)', marginTop: 2 }}>{tzLabel}</div>
          </div>
          <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
        </div>
        <div
          onClick={() => { haptic(); setPicker('currency'); }}
          style={{ padding: '12px 16px', background: 'var(--tg-section-bg)', borderBottom: '1px solid var(--tg-secondary-bg)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <div>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Валюта</div>
            <div style={{ fontSize: 15, color: 'var(--tg-text)', marginTop: 2 }}>{curLabel}</div>
          </div>
          <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
        </div>
      </div>

      {/* Invite link */}
      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
          Инвайт-ссылка
        </div>
        <div style={{ background: 'var(--tg-section-bg)', padding: '14px 16px', borderRadius: 0 }}>
          <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 8, wordBreak: 'break-all' }}>
            {inviteData?.invite_link || '—'}
          </div>
          <button
            onClick={handleCopyInvite}
            disabled={!inviteData?.invite_link}
            style={{
              padding: '10px 20px', borderRadius: 10,
              background: 'var(--tg-accent)', color: '#fff',
              border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 600,
            }}
          >
            Копировать
          </button>
        </div>
      </div>

      {/* Pickers */}
      {picker === 'work_mode' && (
        <PickerSheet
          title="Я работаю"
          options={WORK_MODES}
          value={master?.work_mode || 'travel'}
          onChange={(mode) => profileMutation.mutate({ work_mode: mode })}
          onClose={() => setPicker(null)}
        />
      )}
      {picker === 'timezone' && (
        <PickerSheet
          title="Часовой пояс"
          options={TIMEZONES}
          value={master?.timezone}
          onChange={(tz) => tzMutation.mutate(tz)}
          onClose={() => setPicker(null)}
        />
      )}
      {picker === 'currency' && (
        <PickerSheet
          title="Валюта"
          options={CURRENCIES}
          value={master?.currency}
          onChange={(cur) => curMutation.mutate(cur)}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  );
}
