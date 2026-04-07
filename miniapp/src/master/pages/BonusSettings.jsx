import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterBonusSettings, updateMasterBonusSettings } from '../../api/client';

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

// iOS-style toggle
function Toggle({ checked, onChange }) {
  return (
    <div
      onClick={() => { haptic(); onChange(!checked); }}
      style={{
        width: 50, height: 28, borderRadius: 14,
        background: checked ? 'var(--tg-accent)' : 'var(--tg-secondary-bg)',
        position: 'relative', cursor: 'pointer', flexShrink: 0,
        transition: 'background 0.2s',
      }}
    >
      <div style={{
        position: 'absolute',
        top: 3, left: checked ? 24 : 3,
        width: 22, height: 22, borderRadius: '50%',
        background: '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
        transition: 'left 0.2s',
      }} />
    </div>
  );
}

// Inline-editable number row
function NumRow({ label, value, hint, unit, onChange, disabled }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(String(value ?? ''));

  useEffect(() => {
    setVal(String(value ?? ''));
  }, [value]);

  const handleSave = () => {
    const n = parseFloat(val);
    if (!isNaN(n) && n >= 0) {
      onChange(n);
    }
    setEditing(false);
  };

  return (
    <div style={{
      padding: '12px 16px',
      background: 'var(--tg-section-bg)',
      borderBottom: '1px solid var(--tg-secondary-bg)',
      opacity: disabled ? 0.4 : 1,
      pointerEvents: disabled ? 'none' : 'auto',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: hint ? 6 : 0 }}>
        <span style={{ fontSize: 15, color: 'var(--tg-text)' }}>{label}</span>
        {editing ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input
              type="number"
              value={val}
              onChange={e => setVal(e.target.value)}
              autoFocus
              style={{
                width: 70, padding: '4px 8px', borderRadius: 6,
                border: '1px solid var(--tg-accent)',
                background: 'var(--tg-bg)', color: 'var(--tg-text)',
                fontSize: 15, textAlign: 'right',
              }}
              onBlur={handleSave}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
            />
            {unit && <span style={{ fontSize: 14, color: 'var(--tg-hint)' }}>{unit}</span>}
          </div>
        ) : (
          <span
            onClick={() => { if (!disabled) { haptic(); setEditing(true); } }}
            style={{
              fontSize: 15, fontWeight: 500, color: 'var(--tg-accent)', cursor: 'pointer',
              padding: '4px 8px', borderRadius: 6, background: 'var(--tg-accent)22',
            }}
          >
            {value ?? 0}{unit}
          </span>
        )}
      </div>
      {hint && <div style={{ fontSize: 12, color: 'var(--tg-hint)' }}>{hint}</div>}
    </div>
  );
}

function LinkRow({ label, hint, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        padding: '12px 16px',
        background: 'var(--tg-section-bg)',
        border: 'none',
        borderBottom: '1px solid var(--tg-secondary-bg)',
        color: 'var(--tg-text)',
        textAlign: 'left',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 10,
      }}
    >
      <span>
        <span style={{ display: 'block', fontSize: 15 }}>{label}</span>
        {hint && <span style={{ display: 'block', fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>{hint}</span>}
      </span>
      <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
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

  useEffect(() => {
    if (data && !localSettings) {
      setLocalSettings(data);
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: updateMasterBonusSettings,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-bonus-settings'] });
      hapticNotify('success');
      setSuccessMsg('Сохранено ✓');
      setTimeout(() => setSuccessMsg(''), 2000);
    },
    onError: () => hapticNotify('error'),
  });

  const update = (key, value) => {
    const next = { ...localSettings, [key]: value };
    setLocalSettings(next);
    mutation.mutate({ [key]: value });
  };

  if (isLoading || !localSettings) {
    return <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>Загрузка...</div>;
  }

  const disabled = !localSettings.bonus_enabled;
  const hasWelcomeTemplate = Boolean((localSettings.welcome_message || '').trim() || localSettings.welcome_photo_url);
  const hasBirthdayTemplate = Boolean((localSettings.birthday_message || '').trim() || localSettings.birthday_photo_url);

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

      {/* Main toggle */}
      <div style={{ marginTop: 16 }}>
        <div
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '14px 16px',
            background: 'var(--tg-section-bg)',
          }}
        >
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)' }}>Бонусная программа</div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 2 }}>
              {localSettings.bonus_enabled ? 'Включена' : 'Выключена'}
            </div>
          </div>
          <Toggle
            checked={localSettings.bonus_enabled}
            onChange={(v) => update('bonus_enabled', v)}
          />
        </div>
      </div>

      {/* Parameters */}
      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
          Параметры
        </div>
        <NumRow
          label="Процент начисления"
          value={localSettings.bonus_rate}
          unit="%"
          hint={`Клиент получит ${localSettings.bonus_rate}% от суммы каждого заказа`}
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
          unit=" ₽"
          hint={localSettings.bonus_welcome > 0 ? `Клиент получит ${localSettings.bonus_welcome} ₽ при первом визите` : '0 = выключено'}
          onChange={(v) => update('bonus_welcome', v)}
          disabled={disabled}
        />
        <NumRow
          label="Бонус на день рождения"
          value={localSettings.bonus_birthday}
          unit=" ₽"
          hint={localSettings.bonus_birthday > 0 ? `Клиент получит ${localSettings.bonus_birthday} ₽ в день рождения` : '0 = выключено'}
          onChange={(v) => update('bonus_birthday', v)}
          disabled={disabled}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
          Сообщения
        </div>
        <LinkRow
          label="Настроить приветствие"
          hint={hasWelcomeTemplate ? 'Кастомизировано' : 'Используется стандартный текст'}
          onClick={() => {
            haptic();
            if (onNavigate) onNavigate('bonus_message', { kind: 'welcome' });
          }}
        />
        <LinkRow
          label="Настроить поздравление"
          hint={hasBirthdayTemplate ? 'Кастомизировано' : 'Используется стандартный текст'}
          onClick={() => {
            haptic();
            if (onNavigate) onNavigate('bonus_message', { kind: 'birthday' });
          }}
        />
      </div>
    </div>
  );
}
