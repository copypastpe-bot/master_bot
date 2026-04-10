import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createMasterSubscriptionInvoiceLink,
  getMasterSubscription,
  trackMasterReferralLinkCopied,
} from '../../api/client';
import { Skeleton } from '../../components/Skeleton';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

const PLANS = [
  { payload: 'plan_month', stars: 200, days: 30, labelKey: 'subscription.plans.month' },
  { payload: 'plan_quarter', stars: 500, days: 90, labelKey: 'subscription.plans.quarter', popular: true, discountKey: 'subscription.plans.quarterDiscount' },
  { payload: 'plan_year', stars: 1700, days: 365, labelKey: 'subscription.plans.year', discountKey: 'subscription.plans.yearDiscount' },
];

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function openTelegramInvoice(invoiceLink) {
  return new Promise((resolve, reject) => {
    if (typeof WebApp?.openInvoice !== 'function') {
      reject(new Error('openInvoice is unavailable'));
      return;
    }
    try {
      WebApp.openInvoice(invoiceLink, (status) => resolve(status || 'unknown'));
    } catch (error) {
      reject(error);
    }
  });
}

function formatDate(value, locale, t) {
  if (!value) return t('common.dash');
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
}

function formatDateShort(value, locale, t) {
  if (!value) return t('common.dash');
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'long' });
}

function HistoryRow({ item, isLast, t, locale }) {
  const title = item.type === 'payment'
    ? item.plan_label
    : item.type === 'referral_payment'
      ? t('subscription.history.referral', { days: item.days_added })
      : t('subscription.history.referral', { days: item.days_added });
  const amount = item.type === 'payment'
    ? `${(item.stars_amount || 0).toLocaleString(locale)} ★`
    : t('subscription.history.bonus');

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
          {formatDate(item.created_at, locale, t)}
        </div>
      </div>
      <div style={{ color: item.type === 'payment' ? 'var(--tg-text)' : 'var(--tg-accent)', fontSize: 16, fontWeight: 700 }}>
        {amount}
      </div>
    </div>
  );
}

export default function Subscription() {
  const { t, locale } = useI18n();
  const qc = useQueryClient();
  const [selectedPlan, setSelectedPlan] = useState('plan_quarter');
  const [isPaymentPolling, setIsPaymentPolling] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['master-subscription'],
    queryFn: getMasterSubscription,
    staleTime: 20_000,
  });

  const invoiceMutation = useMutation({
    mutationFn: createMasterSubscriptionInvoiceLink,
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
  const paymentPending = invoiceMutation.isPending || isPaymentPolling;

  const pollSubscriptionAfterPaid = async (baseline) => {
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
      const { data: fresh } = await refetch();
      if (fresh) {
        const historyLength = (fresh.payment_history || []).length;
        const becameActive = !baseline.is_active && fresh.is_active;
        const changedUntil = fresh.subscription_until !== baseline.subscription_until;
        const addedHistory = historyLength > baseline.history_length;
        if (becameActive || changedUntil || addedHistory) {
          return true;
        }
      }
      await wait(2_500);
    }
    return false;
  };

  const handlePay = async () => {
    haptic();
    const baseline = {
      is_active: Boolean(data?.is_active),
      subscription_until: data?.subscription_until || null,
      history_length: (data?.payment_history || []).length,
    };

    try {
      const invoice = await invoiceMutation.mutateAsync({ payload: selected.payload });
      const status = await openTelegramInvoice(invoice.invoice_link);

      if (status === 'paid') {
        setIsPaymentPolling(true);
        qc.invalidateQueries({ queryKey: ['master-subscription'] });
        qc.invalidateQueries({ queryKey: ['master-dashboard'] });

        const updated = await pollSubscriptionAfterPaid(baseline);
        qc.invalidateQueries({ queryKey: ['master-subscription'] });
        qc.invalidateQueries({ queryKey: ['master-dashboard'] });
        setIsPaymentPolling(false);

        if (typeof WebApp?.showAlert === 'function') {
          WebApp.showAlert(
            updated
              ? t('subscription.alerts.paidUpdated')
              : t('subscription.alerts.paidPending')
          );
        }
        return;
      }

      if (status === 'cancelled') {
        if (typeof WebApp?.showAlert === 'function') {
          WebApp.showAlert(t('subscription.alerts.cancelled'));
        }
        return;
      }

      if (status === 'failed') {
        if (typeof WebApp?.showAlert === 'function') {
          WebApp.showAlert(t('subscription.alerts.failed'));
        }
        return;
      }

      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(t('subscription.alerts.status', { status }));
      }
    } catch (_) {
      setIsPaymentPolling(false);
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(t('subscription.alerts.launchFailed'));
      }
    }
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
      WebApp.showAlert(t('common.copied'));
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
        <p style={{ marginBottom: 10, color: 'var(--tg-text)' }}>{t('subscription.errors.loadFailed')}</p>
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
          {t('common.retry')}
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
              ? t('subscription.status.expiredTitle')
              : statusKind === 'trial'
                ? t('subscription.status.trialTitle')
                : t('subscription.status.activeUntil', { date: formatDate(data.subscription_until, locale, t) })}
          </div>
          <div style={{ color: statusStyles.text, fontSize: 14, marginTop: 2 }}>
            {statusKind === 'expired'
              ? t('subscription.status.payToContinue')
              : statusKind === 'trial'
                ? t('subscription.status.trialExpires', { date: formatDateShort(data.subscription_until, locale, t), days: data.days_left })
                : t('subscription.status.daysLeft', { days: data.days_left })}
          </div>
        </div>
        <div style={{ color: statusStyles.icon, fontSize: 31, lineHeight: 1 }}>
          ★
        </div>
      </div>

      <div style={{ color: 'var(--tg-hint)', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', margin: '0 2px 8px' }}>
        {statusKind === 'expired' ? t('subscription.sections.choosePlan') : t('subscription.sections.renew')}
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
                    {t('subscription.plans.popular')}
                  </div>
                )}
                <div style={{ color: 'var(--tg-text)', fontSize: 17, fontWeight: 700 }}>{t(plan.labelKey)}</div>
                <div style={{ color: 'var(--tg-hint)', fontSize: 14 }}>
                  {t('subscription.plans.days', { days: plan.days })}
                  {plan.discountKey ? ` · ${t(plan.discountKey)}` : ''}
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
                {plan.stars.toLocaleString(locale)} ★
              </div>
            </button>
          );
        })}
      </div>

      <button
        onClick={handlePay}
        disabled={paymentPending}
        style={{
          width: '100%',
          border: 'none',
          borderRadius: 13,
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          padding: '13px 14px',
          fontWeight: 700,
          fontSize: 16,
          cursor: paymentPending ? 'default' : 'pointer',
          opacity: paymentPending ? 0.7 : 1,
          marginBottom: 12,
        }}
      >
        {invoiceMutation.isPending
          ? t('subscription.payment.creating')
          : isPaymentPolling
            ? t('subscription.payment.checking')
            : t('subscription.payment.pay')}
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
          <div style={{ color: 'var(--tg-text)', fontSize: 16, fontWeight: 700 }}>{t('subscription.referral.title')}</div>
          <div style={{ color: 'var(--tg-hint)', fontSize: 14 }}>{t('subscription.referral.subtitle')}</div>
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
          title={t('subscription.referral.copyTitle')}
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
          {t('subscription.trialNote')}
        </div>
      )}

      <div style={{ color: 'var(--tg-hint)', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', margin: '0 2px 8px' }}>
        {t('subscription.sections.history')}
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
            {t('subscription.history.empty')}
          </div>
        ) : (
          (data.payment_history || []).map((item, idx, arr) => (
            <HistoryRow
              key={`${item.type}_${item.created_at || idx}`}
              item={item}
              isLast={idx === arr.length - 1}
              t={t}
              locale={locale}
            />
          ))
        )}
      </div>
    </div>
  );
}
