import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createMasterPromo, getPromoRecipientsCount } from '../../api/client';
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

function today() {
  return new Date().toISOString().slice(0, 10);
}

function ProgressBar({ step, total }) {
  return (
    <div style={{ display: 'flex', gap: 4, padding: '0 16px 16px' }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          style={{
            flex: 1, height: 3, borderRadius: 2,
            background: i < step ? 'var(--tg-accent)' : 'var(--tg-secondary-bg)',
            transition: 'background 0.2s',
          }}
        />
      ))}
    </div>
  );
}

export default function PromoCreate({ onBack, onCreated }) {
  const { tr, locale } = useI18n();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    title: '',
    text: '',
    active_from: today(),
    active_to: '',
    notify_clients: false,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);

  const qc = useQueryClient();

  const { data: recipientsData } = useQuery({
    queryKey: ['promo-recipients-count'],
    queryFn: getPromoRecipientsCount,
    staleTime: 60_000,
  });
  const recipientsCount = recipientsData?.count || 0;

  const mutation = useMutation({
    mutationFn: createMasterPromo,
    onSuccess: (data) => {
      hapticNotify('success');
      qc.invalidateQueries({ queryKey: ['master-promos'] });
      setSuccess(data);
    },
    onError: () => { hapticNotify('error'); setError(tr('Ошибка при создании акции', 'Failed to create promo')); },
  });

  const nextStep = () => {
    setError('');
    if (step === 1) {
      if (!form.title.trim() || !form.text.trim()) {
        setError(tr('Заполните название и описание', 'Fill title and description'));
        hapticNotify('error');
        return;
      }
    }
    if (step === 2) {
      if (!form.active_to) {
        setError(tr('Укажите дату окончания', 'Specify end date'));
        hapticNotify('error');
        return;
      }
      if (form.active_to <= form.active_from) {
        setError(tr('Дата окончания должна быть позже даты начала', 'End date must be later than start date'));
        hapticNotify('error');
        return;
      }
    }
    haptic('medium');
    setStep(s => s + 1);
  };

  const handleSubmit = () => {
    haptic('medium');
    mutation.mutate(form);
  };

  const fmtDate = (str) => {
    if (!str) return '—';
    try { return new Date(str + 'T00:00:00').toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch { return str; }
  };

  // Success screen
  if (success) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
        <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 8 }}>
          {tr('Акция создана!', 'Promo created!')}
        </div>
        {success.sent_count > 0 && (
          <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 24 }}>
            {tr(`Уведомлено ${success.sent_count} клиентов`, `Notified ${success.sent_count} clients`)}
          </div>
        )}
        <button
          onClick={onCreated}
          style={{
            padding: '12px 32px', borderRadius: 12,
            background: 'var(--tg-accent)', color: '#fff',
            fontSize: 15, fontWeight: 600, border: 'none', cursor: 'pointer',
          }}
        >
          {tr('К списку акций', 'Back to promos')}
        </button>
      </div>
    );
  }

  return (
    <div style={{ paddingBottom: 80 }}>
      <ProgressBar step={step} total={3} />

      {step === 1 && (
        <div style={{ padding: '0 16px' }}>
          <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 16, color: 'var(--tg-text)' }}>
            {tr('Шаг 1 — Название и описание', 'Step 1 - Title and description')}
          </div>
          <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>{tr('Название *', 'Title *')}</div>
          <input
            value={form.title}
            onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
            placeholder={tr('Скидка 20% на уборку', '20% off cleaning')}
            autoFocus
            style={inputStyle}
          />
          <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 12, marginBottom: 4 }}>{tr('Описание / условия *', 'Description / terms *')}</div>
          <textarea
            value={form.text}
            onChange={e => setForm(p => ({ ...p, text: e.target.value }))}
            placeholder={tr('Только в этом месяце на все услуги!', 'This month only for all services!')}
            rows={4}
            style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit', minHeight: 96 }}
          />
          {error && <div style={{ color: 'var(--tg-destructive, #e53935)', fontSize: 13, marginTop: 8 }}>{error}</div>}
          <button onClick={nextStep} style={{ ...btnPrimary, width: '100%', marginTop: 16 }}>{tr('Далее →', 'Next ->')}</button>
        </div>
      )}

      {step === 2 && (
        <div style={{ padding: '0 16px' }}>
          <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 16, color: 'var(--tg-text)' }}>
            {tr('Шаг 2 — Даты', 'Step 2 - Dates')}
          </div>
          <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>{tr('Дата начала', 'Start date')}</div>
          <input
            type="date"
            value={form.active_from}
            onChange={e => setForm(p => ({ ...p, active_from: e.target.value }))}
            style={inputStyle}
          />
          <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 12, marginBottom: 4 }}>{tr('Дата окончания *', 'End date *')}</div>
          <input
            type="date"
            value={form.active_to}
            onChange={e => setForm(p => ({ ...p, active_to: e.target.value }))}
            min={form.active_from}
            style={inputStyle}
          />
          {error && <div style={{ color: 'var(--tg-destructive, #e53935)', fontSize: 13, marginTop: 8 }}>{error}</div>}
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button onClick={() => { haptic(); setStep(1); }} style={{ ...btnSecondary, flex: 1 }}>{tr('← Назад', '← Back')}</button>
            <button onClick={nextStep} style={{ ...btnPrimary, flex: 2 }}>{tr('Далее →', 'Next ->')}</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div style={{ padding: '0 16px' }}>
          <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 16, color: 'var(--tg-text)' }}>
            {tr('Шаг 3 — Подтверждение', 'Step 3 - Confirm')}
          </div>

          {/* Summary */}
          <div style={{
            background: 'var(--tg-section-bg)', borderRadius: 12,
            padding: '14px 16px', marginBottom: 16,
          }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>{form.title}</div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 8, lineHeight: 1.4 }}>{form.text}</div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
              {fmtDate(form.active_from)} — {fmtDate(form.active_to)}
            </div>
          </div>

          {/* Notify toggle */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            background: 'var(--tg-section-bg)', borderRadius: 12,
            padding: '14px 16px', marginBottom: 16,
          }}>
            <input
              type="checkbox"
              id="notify"
              checked={form.notify_clients}
              onChange={e => { haptic(); setForm(p => ({ ...p, notify_clients: e.target.checked })); }}
              style={{ width: 18, height: 18, cursor: 'pointer' }}
            />
            <label htmlFor="notify" style={{ flex: 1, fontSize: 14, cursor: 'pointer', color: 'var(--tg-text)' }}>
              {tr('Уведомить клиентов о новой акции', 'Notify clients about new promo')}
              {form.notify_clients && recipientsCount > 0 && (
                <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
                  {tr(`Будет отправлено ${recipientsCount} клиентам`, `Will be sent to ${recipientsCount} clients`)}
                </div>
              )}
            </label>
          </div>

          {error && <div style={{ color: 'var(--tg-destructive, #e53935)', fontSize: 13, marginBottom: 8 }}>{error}</div>}

          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={() => { haptic(); setStep(2); }} style={{ ...btnSecondary, flex: 1 }}>{tr('← Назад', '← Back')}</button>
            <button
              onClick={handleSubmit}
              disabled={mutation.isPending}
              style={{ ...btnPrimary, flex: 2, opacity: mutation.isPending ? 0.7 : 1 }}
            >
              {mutation.isPending ? tr('Создаём...', 'Creating...') : tr('Создать акцию', 'Create promo')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'var(--tg-bg)', color: 'var(--tg-text)',
  fontSize: 15, boxSizing: 'border-box', display: 'block',
};
const btnPrimary = {
  padding: '12px 20px', borderRadius: 10,
  background: 'var(--tg-accent)', color: '#fff',
  fontSize: 15, fontWeight: 600, border: 'none', cursor: 'pointer',
};
const btnSecondary = {
  padding: '12px 20px', borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'none', color: 'var(--tg-text)',
  fontSize: 15, cursor: 'pointer',
};
