import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  applyMasterSubscriptionPayment,
  getMasterSubscription,
  trackMasterReferralLinkCopied,
} from '../../api/client';
import { Skeleton } from '../../components/Skeleton';

const WebApp = window.Telegram?.WebApp;

const PLANS = [
  { payload: 'plan_month', stars: 500, days: 30, label: '1 месяц' },
  { payload: 'plan_quarter', stars: 1300, days: 90, label: '3 месяца', popular: true, discount: 'Выгода 13%' },
  { payload: 'plan_year', stars: 4500, days: 365, label: '1 год', discount: 'Выгода 25%' },
];

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

function formatDateShort(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}

function HistoryRow({ item, isLast }) {
  const title = item.type === 'payment'
    ? item.plan_label
    : item.type === 'referral_payment'
      ? `Реферал: +${item.days_added} дн`
      : `Реферал: +${item.days_added} дн`;
  const amount = item.type === 'payment'
    ? `${(item.stars_amount || 0).toLocaleString('ru-RU')} ★`
    : 'бонус';

  return (
    <div
      style={{
        padding: '12px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        borderBottom: isLast ? 'none' : '1px solid var(--tg-secondary-bg)',
      }}
    >
      <div>
        <div style={{ color: 'var(--tg-text)', fontSize: 16, fontWeight: 600 }}>
          {title}
        </div>
        <div style={{ color: 'var(--tg-hint)', fontSize: 13 }}>
          {formatDate(item.created_at)}
        </div>
      </div>
      <div style={{ color: item.type === 'payment' ? 'var(--tg-text)' : 'var(--tg-accent)', fontSize: 16, fontWeight: 700 }}>
        {amount}
      </div>
    </div>
  );
}

export default function Subscription() {
  const qc = useQueryClient();
  const [selectedPlan, setSelectedPlan] = useState('plan_quarter');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['master-subscription'],
    queryFn: getMasterSubscription,
    staleTime: 20_000,
  });

  const payMutation = useMutation({
    mutationFn: applyMasterSubscriptionPayment,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-subscription'] });
      qc.invalidateQueries({ queryKey: ['master-dashboard'] });
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert('Подписка обновлена');
      }
    },
  });

  const copyMutation = useMutation({
    mutationFn: trackMasterReferralLinkCopied,
  });

  const statusKind = useMemo(() => {
    if (!data) return 'active';
    if (!data.is_active) return 'expired';
    if (data.is_trial) return 'trial';
    return 'active';
  }, [data]);

  const statusStyles = {
    active: { bg: '#e9f1ff', border: '#9ec3f2', title: '#2b65b9', text: '#2f74d2', icon: '#2f74d2' },
    trial: { bg: '#eaf4df', border: '#b4d39b', title: '#4f7a2d', text: '#5e8d38', icon: '#5e8d38' },
    expired: { bg: '#fbecec', border: '#e8bcbc', title: '#bf4c4c', text: '#d46262', icon: '#333333' },
  }[statusKind];

  const selected = PLANS.find((p) => p.payload === selectedPlan) || PLANS[0];

  const handlePay = () => {
    haptic();
    const charge = `manual_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    payMutation.mutate({
      telegram_charge_id: charge,
      payload: selected.payload,
      stars_amount: selected.stars,
    });
  };

  const handleCopyReferral = async () => {
    haptic();
    const link = data?.referral_link;
    if (!link) return;

    try {
      if (typeof navigator?.clipboard?.writeText === 'function') {
        await navigator.clipboard.writeText(link);
      }
    } catch (_) {
      // non-critical
    }
    copyMutation.mutate('subscription');
    if (typeof WebApp?.showAlert === 'function') {
      WebApp.showAlert('Ссылка скопирована');
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: '16px 12px 96px' }}>
        <Skeleton height={68} style={{ marginBottom: 12 }} />
        <Skeleton height={220} style={{ marginBottom: 12 }} />
        <Skeleton height={68} />
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 16px' }}>
        <p style={{ marginBottom: 10, color: 'var(--tg-text)' }}>Не удалось загрузить подписку</p>
        <button
          onClick={() => { haptic(); refetch(); }}
          style={{
            border: 'none',
            borderRadius: 12,
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            padding: '11px 18px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Повторить
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px 12px 98px' }}>
      <div
        style={{
          border: `1px solid ${statusStyles.border}`,
          background: statusStyles.bg,
          borderRadius: 16,
          padding: '12px 14px',
          marginBottom: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <div>
          <div style={{ color: statusStyles.title, fontSize: 17, fontWeight: 700 }}>
            {statusKind === 'expired'
              ? 'Подписка истекла'
              : statusKind === 'trial'
                ? 'Пробный период'
                : `Активна до ${formatDate(data.subscription_until)}`}
          </div>
          <div style={{ color: statusStyles.text, fontSize: 14, marginTop: 2 }}>
            {statusKind === 'expired'
              ? 'Оплатите для продолжения'
              : statusKind === 'trial'
                ? `Истекает ${formatDateShort(data.subscription_until)} · ${data.days_left} дней`
                : `Осталось ${data.days_left} дней`}
          </div>
        </div>
        <div style={{ color: statusStyles.icon, fontSize: 31, lineHeight: 1 }}>
          ★
        </div>
      </div>

      <div style={{ color: 'var(--tg-hint)', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', margin: '0 2px 8px' }}>
        {statusKind === 'expired' ? 'Выберите тариф' : 'Продлить'}
      </div>
      <div
        style={{
          border: '1px solid var(--tg-enterprise-border)',
          borderRadius: 16,
          background: 'var(--tg-section-bg)',
          overflow: 'hidden',
          marginBottom: 12,
        }}
      >
        {PLANS.map((plan, idx) => {
          const selectedRow = selectedPlan === plan.payload;
          return (
            <button
              key={plan.payload}
              onClick={() => { haptic(); setSelectedPlan(plan.payload); }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                textAlign: 'left',
                cursor: 'pointer',
                background: selectedRow ? 'rgba(51, 144, 236, 0.08)' : 'transparent',
                border: 'none',
                borderBottom: idx === PLANS.length - 1 ? 'none' : '1px solid var(--tg-secondary-bg)',
                padding: '12px 14px',
                boxShadow: selectedRow ? 'inset 0 0 0 2px var(--tg-button)' : 'none',
                borderRadius: selectedRow ? 12 : 0,
              }}
            >
              <div>
                {plan.popular && (
                  <div style={{ color: 'var(--tg-button)', fontSize: 12, fontWeight: 700, marginBottom: 2 }}>
                    Популярный
                  </div>
                )}
                <div style={{ color: 'var(--tg-text)', fontSize: 17, fontWeight: 700 }}>{plan.label}</div>
                <div style={{ color: 'var(--tg-hint)', fontSize: 14 }}>
                  {plan.days} дней{plan.discount ? ` · ${plan.discount}` : ''}
                </div>
              </div>
              <div
                style={{
                  color: selectedRow ? 'var(--tg-button)' : 'var(--tg-text)',
                  background: 'var(--tg-secondary-bg)',
                  borderRadius: 12,
                  padding: '6px 10px',
                  fontWeight: 700,
                  whiteSpace: 'nowrap',
                  fontSize: 17,
                }}
              >
                {plan.stars.toLocaleString('ru-RU')} ★
              </div>
            </button>
          );
        })}
      </div>

      <button
        onClick={handlePay}
        disabled={payMutation.isPending}
        style={{
          width: '100%',
          border: 'none',
          borderRadius: 13,
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          padding: '13px 14px',
          fontWeight: 700,
          fontSize: 16,
          cursor: payMutation.isPending ? 'default' : 'pointer',
          opacity: payMutation.isPending ? 0.7 : 1,
          marginBottom: 12,
        }}
      >
        {payMutation.isPending ? 'Оплата...' : '★ Оплатить Stars'}
      </button>

      <div
        style={{
          border: '1px solid var(--tg-enterprise-border)',
          borderRadius: 16,
          background: 'var(--tg-section-bg)',
          padding: '12px 14px',
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <div>
          <div style={{ color: 'var(--tg-text)', fontSize: 16, fontWeight: 700 }}>Пригласить друга</div>
          <div style={{ color: 'var(--tg-hint)', fontSize: 14 }}>+14 дней за каждого</div>
        </div>
        <button
          onClick={handleCopyReferral}
          style={{
            border: 'none',
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-accent)',
            borderRadius: 10,
            minWidth: 42,
            height: 42,
            fontSize: 20,
            cursor: 'pointer',
          }}
          title="Скопировать ссылку"
        >
          🔗
        </button>
      </div>

      {data.is_trial && (
        <div
          style={{
            border: '1px solid #e3c472',
            borderRadius: 14,
            background: '#f7edcf',
            color: '#8b6a1d',
            padding: '12px 14px',
            marginBottom: 12,
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          Оплатите до окончания триала, дни добавятся сверху
        </div>
      )}

      <div style={{ color: 'var(--tg-hint)', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', margin: '0 2px 8px' }}>
        История
      </div>
      <div
        style={{
          border: '1px solid var(--tg-enterprise-border)',
          borderRadius: 16,
          background: 'var(--tg-section-bg)',
          padding: '0 14px',
        }}
      >
        {(data.payment_history || []).length === 0 ? (
          <div style={{ color: 'var(--tg-hint)', padding: '14px 0', textAlign: 'center' }}>
            Пока пусто
          </div>
        ) : (
          (data.payment_history || []).map((item, idx, arr) => (
            <HistoryRow key={`${item.type}_${item.created_at || idx}`} item={item} isLast={idx === arr.length - 1} />
          ))
        )}
      </div>
    </div>
  );
}
