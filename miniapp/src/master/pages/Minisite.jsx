import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createPromoPage, getMasterMe, getPromoPage, startPromoPage } from '../../api/client';
import { useI18n } from '../../i18n';
import SiteEditor from './SiteEditor';

const WebApp = window.Telegram?.WebApp;

// Default advantages satisfy the backend's "exactly 3" validator.
const DEFAULT_ADVANTAGES = [
  { text: 'Приеду вовремя', icon: '⏰' },
  { text: 'Своё оборудование', icon: '🧴' },
  { text: 'Индивидуальный подход', icon: '🎯' },
];

// Legacy promo_categories.id = 1 (cleaning) — needed for NOT NULL column.
// Category selection is now handled via master_categories; this is a legacy FK.
const DEFAULT_CATEGORY_ID = 1;

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

  const createMutation = useMutation({
    mutationFn: async () => {
      const me = masterQuery.data || {};
      return createPromoPage({
        category_id: DEFAULT_CATEGORY_ID,
        style_id: null,
        display_name: me.name || '',
        specialization: me.sphere || '',
        tagline: '',
        badge_text: '',
        service_name: '',
        service_price: '',
        promo_enabled: false,
        promo_text: '',
        advantages: DEFAULT_ADVANTAGES,
        sub_button_text: 'Бесплатно · Без спама · Отписка в 1 клик',
      });
    },
    onSuccess: (data) => {
      WebApp?.HapticFeedback?.notificationOccurred?.('success');
      qc.setQueryData(['promo-page'], data);
      setError('');
    },
    onError: () => {
      WebApp?.HapticFeedback?.notificationOccurred?.('error');
      setError(t('minisite.intro.error'));
    },
  });

  function handleCreate() {
    if (!masterQuery.data?.promo_page_started_at) {
      // Mark started first, then create draft
      startMutation.mutate(undefined, {
        onSuccess: () => createMutation.mutate(),
      });
    } else {
      createMutation.mutate();
    }
  }

  function handleUpdate() {
    qc.invalidateQueries({ queryKey: ['promo-page'] });
  }

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

  // Page exists → open inline editor
  if (pageQuery.data) {
    return <SiteEditor initialData={pageQuery.data} onUpdate={handleUpdate} />;
  }

  // Intro screen
  if (shouldShowIntro) {
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
          onClick={handleCreate}
          disabled={startMutation.isPending || createMutation.isPending}
        >
          {(startMutation.isPending || createMutation.isPending)
            ? t('common.saving')
            : t('minisite.intro.create')}
        </button>
      </div>
    );
  }

  // Started but page not created yet → show create button
  return (
    <div className="minisite-intro-page">
      <section className="minisite-intro-hero">
        <span className="minisite-intro-orbit" aria-hidden="true">◎</span>
        <h2>{t('minisite.intro.title')}</h2>
        <p>{t('minisite.intro.subtitle')}</p>
      </section>

      {error && <div className="promo-builder-error is-global">{error}</div>}

      <button
        type="button"
        className="promo-builder-btn minisite-intro-cta"
        onClick={handleCreate}
        disabled={createMutation.isPending}
      >
        {createMutation.isPending ? t('common.saving') : t('minisite.intro.create')}
      </button>
    </div>
  );
}
