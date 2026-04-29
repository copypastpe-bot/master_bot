import { useState, useEffect, useRef, useCallback } from 'react';
import { getClientMasterPublications } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
function haptic() { WebApp?.HapticFeedback?.impactOccurred('light'); }
const PAGE = 20;

const TAG_CONFIG = {
  promo:        { key: 'news.tagPromo',        cls: 'is-promo' },
  announcement: { key: 'news.tagAnnouncement', cls: 'is-announcement' },
  free_slot:    { key: 'news.tagFreeSlot',     cls: 'is-free_slot' },
};

export default function News({ activeMasterId, navigate }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const triggerRef = useRef(null);

  const loadPage = useCallback(async (off) => {
    if (!activeMasterId) return;
    setLoading(true);
    try {
      const data = await getClientMasterPublications(activeMasterId, PAGE, off);
      const pubs = data.publications || [];
      setItems(prev => off === 0 ? pubs : [...prev, ...pubs]);
      setHasMore(pubs.length >= PAGE);
    } finally {
      setLoading(false);
    }
  }, [activeMasterId]);

  useEffect(() => { setOffset(0); loadPage(0); }, [loadPage]);

  useEffect(() => {
    if (!triggerRef.current || !hasMore || loading) return;
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        setOffset(prev => { const next = prev + PAGE; loadPage(next); return next; });
      }
    }, { threshold: 0.1 });
    obs.observe(triggerRef.current);
    return () => obs.disconnect();
  }, [hasMore, loading, loadPage]);

  const renderButton = (pub) => {
    if (pub.type === 'promo' || pub.type === 'free_slot') {
      return (
        <button className="client-order-card-btn is-primary" style={{ marginTop: 8 }}
          onClick={() => { haptic(); navigate('create_order'); }}>
          {t('news.btnBook')}
        </button>
      );
    }
    if (pub.type === 'portfolio') {
      return (
        <button className="client-order-card-btn is-outline" style={{ marginTop: 8 }}
          onClick={() => { haptic(); navigate('create_order'); }}>
          {t('news.btnWantSame')}
        </button>
      );
    }
    return null;
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      <div className="client-tab-header">
        <span className="client-page-title">{t('news.title')}</span>
      </div>

      {loading && items.length === 0 ? (
        <><Skeleton height={100} style={{ marginBottom: 10 }} /><Skeleton height={100} /></>
      ) : items.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--tg-theme-hint-color)', marginTop: 40 }}>{t('news.empty')}</p>
      ) : (
        <>
          {items.map((pub, i) => {
            const tag = TAG_CONFIG[pub.type];
            return (
              <div key={`${pub.id}-${i}`} className="client-news-card">
                {pub.image_url && <img className="client-news-card-image" src={pub.image_url} alt="" />}
                <div className="client-news-card-body">
                  <div className="client-news-card-topline">
                    {tag && <span className={`client-news-tag ${tag.cls}`}>{t(tag.key)}</span>}
                    <span style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)' }}>{formatDate(pub.created_at)}</span>
                  </div>
                  {pub.title && <p className="client-news-card-title">{pub.title}</p>}
                  {pub.text && <p className="client-news-card-text">{pub.text}</p>}
                  {renderButton(pub)}
                </div>
              </div>
            );
          })}
          {loading && <Skeleton height={60} style={{ marginTop: 8 }} />}
          <div ref={triggerRef} className="client-load-more-trigger" />
        </>
      )}
    </div>
  );
}
