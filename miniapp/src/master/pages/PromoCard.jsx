import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deactivateMasterPromo } from '../../api/client';
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

function fmtDate(str, locale) {
  if (!str) return '—';
  try {
    return new Date(str + 'T00:00:00').toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return str; }
}

function isActive(promo) {
  const today = new Date().toISOString().slice(0, 10);
  return promo.active_to >= today;
}

export default function PromoCard({ promo, onBack }) {
  const { tr, locale } = useI18n();
  const qc = useQueryClient();
  const active = isActive(promo);

  const mutation = useMutation({
    mutationFn: () => deactivateMasterPromo(promo.id),
    onSuccess: () => {
      hapticNotify('success');
      qc.invalidateQueries({ queryKey: ['master-promos'] });
      onBack();
    },
    onError: () => hapticNotify('error'),
  });

  const handleDeactivate = () => {
    haptic('medium');
    if (typeof WebApp?.showPopup === 'function') {
      WebApp.showPopup({
        title: tr('Завершить акцию?', 'Finish promo?'),
        message: tr('Акция станет недоступна для клиентов.', 'Promo will become unavailable for clients.'),
        buttons: [
          { id: 'cancel', type: 'cancel', text: tr('Отмена', 'Cancel') },
          { id: 'confirm', type: 'destructive', text: tr('Завершить', 'Finish') },
        ],
      }, (buttonId) => {
        if (buttonId === 'confirm') mutation.mutate();
      });
    } else if (window.confirm(tr('Завершить акцию? Она станет недоступна для клиентов.', 'Finish promo? It will become unavailable for clients.'))) {
      mutation.mutate();
    }
  };

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Status badge */}
      <div style={{ padding: '16px 16px 8px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          fontSize: 12, fontWeight: 600,
          color: active ? '#4caf50' : 'var(--tg-hint)',
          background: active ? '#4caf5022' : 'var(--tg-secondary-bg)',
          padding: '4px 10px', borderRadius: 8,
        }}>
          {active ? tr('Активна', 'Active') : tr('Завершена', 'Finished')}
        </span>
      </div>

      {/* Main card */}
      <div style={{ background: 'var(--tg-section-bg)', padding: '16px', margin: '0 0 1px' }}>
        <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 12 }}>
          {promo.title}
        </div>
        <div style={{ fontSize: 15, color: 'var(--tg-text)', lineHeight: 1.5, marginBottom: 16 }}>
          {promo.text}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
            <span style={{ color: 'var(--tg-hint)' }}>{tr('Период', 'Period')}</span>
            <span style={{ color: 'var(--tg-text)', fontWeight: 500 }}>
              {fmtDate(promo.active_from, locale)} — {fmtDate(promo.active_to, locale)}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
            <span style={{ color: 'var(--tg-hint)' }}>{tr('Уведомлено клиентов', 'Notified clients')}</span>
            <span style={{ color: 'var(--tg-text)', fontWeight: 500 }}>{promo.sent_count || 0}</span>
          </div>
          {promo.created_at && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
              <span style={{ color: 'var(--tg-hint)' }}>{tr('Создана', 'Created')}</span>
              <span style={{ color: 'var(--tg-text)' }}>{fmtDate(promo.created_at, locale)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Deactivate button */}
      {active && (
        <div style={{ padding: '16px' }}>
          <button
            onClick={handleDeactivate}
            disabled={mutation.isPending}
            style={{
              width: '100%', padding: '13px', borderRadius: 12,
              background: 'none',
              border: '1px solid var(--tg-destructive, #e53935)',
              color: 'var(--tg-destructive, #e53935)',
              fontSize: 15, fontWeight: 600, cursor: 'pointer',
              opacity: mutation.isPending ? 0.7 : 1,
            }}
          >
            {mutation.isPending ? tr('Завершаем...', 'Finishing...') : tr('Завершить акцию', 'Finish promo')}
          </button>
        </div>
      )}
    </div>
  );
}
