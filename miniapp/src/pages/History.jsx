import { useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getClientMasterHistory, confirmClientOrder } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import OrderCard from '../components/OrderCard';
import ReviewModal from '../components/ReviewModal';
import ContactSheet from '../components/ContactSheet';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
const PAGE = 20;

export default function History({ activeMasterId, navigate, masterProfile }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [bonusBalance, setBonusBalance] = useState(null);
  const [reviewOrder, setReviewOrder] = useState(null);
  const [contactMaster, setContactMaster] = useState(null);
  const triggerRef = useRef(null);

  const loadPage = useCallback(async (off) => {
    if (!activeMasterId) return;
    setLoading(true);
    try {
      const data = await getClientMasterHistory(activeMasterId, PAGE, off);
      if (off === 0) setBonusBalance(data.bonus_balance ?? null);
      setItems(prev => off === 0 ? (data.items || []) : [...prev, ...(data.items || [])]);
      setHasMore((data.items || []).length >= PAGE);
    } finally {
      setLoading(false);
    }
  }, [activeMasterId]);

  useEffect(() => { setOffset(0); loadPage(0); }, [loadPage]);

  // Intersection observer for lazy load
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

  const handleConfirm = async (orderId) => {
    try {
      await confirmClientOrder(orderId);
      qc.invalidateQueries({ queryKey: ['client-activity', activeMasterId] });
      setItems(prev => prev.map(item =>
        item.id === orderId && item.type === 'order'
          ? { ...item, display_status: 'confirmed', client_confirmed: true }
          : item
      ));
      WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch { WebApp?.HapticFeedback?.notificationOccurred('error'); }
  };

  const handleRepeat = (order) => {
    const service = order.services ? { name: order.services } : null;
    navigate('create_order', service ? { service } : {});
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long' });
  };

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      <div className="client-tab-header">
        <span className="client-page-title">{t('history.title')}</span>
        {bonusBalance !== null && (
          <span style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>
            {t('history.balanceLabel')}: <strong style={{ color: 'var(--tg-theme-text-color)' }}>{bonusBalance}</strong> {t('history.bonusSuffix')}
          </span>
        )}
      </div>

      {loading && items.length === 0 ? (
        <><Skeleton height={90} style={{ marginBottom: 8 }} /><Skeleton height={90} /></>
      ) : items.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--tg-theme-hint-color)', marginTop: 40 }}>{t('history.empty')}</p>
      ) : (
        <>
          {items.map((item, i) => item.type === 'order' ? (
            <OrderCard key={`${item.type}-${item.id}-${i}`} order={item}
              onConfirm={handleConfirm}
              onReview={o => setReviewOrder(o)}
              onRepeat={handleRepeat}
              onContact={() => setContactMaster(masterProfile)}
            />
          ) : (
            <div key={`bonus-${item.id}-${i}`} className="client-bonus-row">
              <div className="client-bonus-row-left">
                <div className="client-bonus-row-desc">{item.comment || t('history.noBonusDesc')}</div>
                <div className="client-bonus-row-date">{formatDate(item.created_at)}</div>
              </div>
              <div className={`client-bonus-row-amount ${item.amount > 0 ? 'is-positive' : 'is-negative'}`}>
                {item.amount > 0 ? '+' : ''}{item.amount}
              </div>
            </div>
          ))}
          {loading && <Skeleton height={60} style={{ marginTop: 8 }} />}
          <div ref={triggerRef} className="client-load-more-trigger" />
        </>
      )}

      {reviewOrder && (
        <ReviewModal order={reviewOrder} onClose={() => setReviewOrder(null)}
          onSuccess={(orderId) => {
            setItems(prev => prev.map(item =>
              item.id === orderId && item.type === 'order' ? { ...item, has_review: true } : item
            ));
            setReviewOrder(null);
          }}
        />
      )}
      {contactMaster && (
        <ContactSheet master={contactMaster} onClose={() => setContactMaster(null)} />
      )}
    </div>
  );
}
