import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getMasterMe, getPromoPage, startPromoPage } from '../../api/client';
import { useI18n } from '../../i18n';
import PromoPageBuilder from './PromoPageBuilder';

const WebApp = window.Telegram?.WebApp;

function IntroPoint({ children }) {
  return (
    <li className="minisite-intro-point">
      <span>✓</span>
      <b>{children}</b>
    </li>
  );
}

export default function Minisite() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [error, setError] = useState('');

  const masterQuery = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 30_000,
  });

  const pageQuery = useQuery({
    queryKey: ['promo-page'],
    queryFn: () => getPromoPage().catch((err) => {
      if (err?.response?.status === 404) return null;
      throw err;
    }),
    staleTime: 20_000,
  });

  const shouldShowIntro = useMemo(() => {
    if (pageQuery.data) return false;
    return !masterQuery.data?.promo_page_started_at;
  }, [masterQuery.data?.promo_page_started_at, pageQuery.data]);

  const startMutation = useMutation({
    mutationFn: startPromoPage,
    onSuccess: (data) => {
      WebApp?.HapticFeedback?.notificationOccurred?.('success');
      qc.setQueryData(['master-me'], (old) => ({
        ...(old || {}),
        promo_page_started_at: data?.promo_page_started_at || new Date().toISOString(),
      }));
      setError('');
    },
    onError: () => {
      WebApp?.HapticFeedback?.notificationOccurred?.('error');
      setError(t('minisite.intro.error'));
    },
  });

  if (pageQuery.isLoading || (masterQuery.isLoading && !pageQuery.data)) {
    return <div className="promo-builder-state">{t('common.loading')}</div>;
  }

  if (pageQuery.isError) {
    return (
      <div className="promo-builder-state">
        <p>{t('minisite.intro.error')}</p>
        <button type="button" onClick={() => pageQuery.refetch()}>{t('common.retry')}</button>
      </div>
    );
  }

  if (!shouldShowIntro) {
    return <PromoPageBuilder />;
  }

  return (
    <div className="minisite-intro-page">
      <section className="minisite-intro-hero">
        <span className="minisite-intro-orbit" aria-hidden="true">◎</span>
        <h2>{t('minisite.intro.title')}</h2>
        <p>{t('minisite.intro.subtitle')}</p>
      </section>

      <ul className="minisite-intro-list">
        <IntroPoint>{t('minisite.intro.pointServices')}</IntroPoint>
        <IntroPoint>{t('minisite.intro.pointTrust')}</IntroPoint>
        <IntroPoint>{t('minisite.intro.pointShare')}</IntroPoint>
      </ul>

      {error && <div className="promo-builder-error is-global">{error}</div>}

      <button
        type="button"
        className="promo-builder-btn minisite-intro-cta"
        onClick={() => startMutation.mutate()}
        disabled={startMutation.isPending}
      >
        {startMutation.isPending ? t('common.saving') : t('minisite.intro.create')}
      </button>
    </div>
  );
}
