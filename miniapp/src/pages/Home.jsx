import { useState, useEffect } from 'react';
import { useQueries, useQueryClient } from '@tanstack/react-query';
import {
  getClientMasterProfile,
  getClientMasterActivity,
  getClientMasterServices,
  getClientMasterNews,
  confirmClientOrder,
} from '../api/client';
import { Skeleton } from '../components/Skeleton';
import OrderCard from '../components/OrderCard';
import ReviewModal from '../components/ReviewModal';
import ContactSheet from '../components/ContactSheet';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
function haptic(t = 'light') { WebApp?.HapticFeedback?.impactOccurred(t); }

function Accordion({ services, onBook }) {
  const { t } = useI18n();
  const [openId, setOpenId] = useState(null);
  if (!services.length) return <p style={{ color: 'var(--tg-theme-hint-color)', fontSize: 14 }}>{t('clientHome.noServices')}</p>;
  return (
    <div className="client-card" style={{ padding: '0 14px' }}>
      {services.map(s => (
        <div key={s.id} className="client-accordion-item">
          <button className="client-accordion-trigger" onClick={() => { haptic(); setOpenId(openId === s.id ? null : s.id); }}>
            <span className="client-accordion-trigger-name">{s.name}</span>
            <span className="client-accordion-trigger-right">
              {s.price != null && <span className="client-accordion-trigger-price">{s.price} ₽</span>}
              <span className={`client-accordion-chevron${openId === s.id ? ' is-open' : ''}`}>▸</span>
            </span>
          </button>
          {openId === s.id && (
            <div className="client-accordion-body">
              {s.description && <p style={{ marginBottom: 8 }}>{s.description}</p>}
              <button className="client-order-card-btn is-primary" onClick={() => { haptic(); onBook(s); }}>
                {t('clientHome.bookService')}
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function Home({ activeMasterId, navigate, masterName, onProfileLoaded }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [reviewOrder, setReviewOrder] = useState(null);
  const [contactOrder, setContactOrder] = useState(null);

  const results = useQueries({
    queries: [
      { queryKey: ['client-profile', activeMasterId], queryFn: () => getClientMasterProfile(activeMasterId), enabled: !!activeMasterId },
      { queryKey: ['client-activity', activeMasterId], queryFn: () => getClientMasterActivity(activeMasterId, 4), enabled: !!activeMasterId },
      { queryKey: ['client-services', activeMasterId], queryFn: () => getClientMasterServices(activeMasterId), enabled: !!activeMasterId },
      { queryKey: ['client-news', activeMasterId], queryFn: () => getClientMasterNews(activeMasterId), enabled: !!activeMasterId },
    ],
  });

  const [profRes, actRes, svcRes, newsRes] = results;
  const prof = profRes.data;
  const activity = actRes.data?.items || [];
  const services = svcRes.data?.services || [];
  const news = newsRes.data?.publications?.[0] || null;

  // Notify parent when profile is loaded (needed for History ContactSheet)
  useEffect(() => {
    if (prof) {
      onProfileLoaded?.(prof);
    }
  }, [prof, onProfileLoaded]);

  const handleConfirm = async (orderId) => {
    try {
      await confirmClientOrder(orderId);
      qc.invalidateQueries({ queryKey: ['client-activity', activeMasterId] });
      WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch { WebApp?.HapticFeedback?.notificationOccurred('error'); }
  };

  const handleRepeat = (order) => {
    const service = order.services ? { name: order.services } : null;
    navigate('create_order', service ? { service } : {});
  };

  const avatarContent = prof?.photo_url
    ? <img src={prof.photo_url} alt="" />
    : (prof?.name || masterName || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      {/* Specialist header */}
      <div className="client-profile-card" style={{ marginTop: 12 }}>
        <div className="client-profile-avatar">{avatarContent}</div>
        <div className="client-profile-info">
          {profRes.isLoading ? <Skeleton width={140} height={20} /> : (
            <p className="client-profile-name">{prof?.name || masterName || '—'}</p>
          )}
          {prof?.sphere && <p className="client-profile-sphere">{prof.sphere}</p>}
          {prof?.bio && <p className="client-profile-bio">{prof.bio}</p>}
          <button className="client-profile-details-link"
            onClick={() => { haptic(); navigate('landing', { masterId: activeMasterId }); }}>
            {t('clientHome.detailsLink')}
          </button>
        </div>
        <div className="client-profile-bonus">
          {profRes.isLoading ? <Skeleton width={40} height={24} /> : (
            <>
              <div className="client-profile-bonus-value">{prof?.bonus_balance ?? 0}</div>
              <div className="client-profile-bonus-label">{t('clientHome.bonusLabel')}</div>
            </>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="client-action-grid">
        <button className="client-action-btn is-primary" onClick={() => { haptic(); navigate('create_order'); }}>
          {t('clientHome.bookBtn')}
        </button>
        <button className="client-action-btn is-secondary" onClick={() => { haptic(); navigate('ask_question'); }}>
          {t('clientHome.questionBtn')}
        </button>
      </div>

      {/* Activity */}
      <div className="client-section-header">
        <span className="client-section-header-title">{t('clientHome.activityTitle')}</span>
        <button className="client-section-header-link" onClick={() => { haptic(); navigate('history'); }}>
          {t('clientHome.allHistory')}
        </button>
      </div>
      {actRes.isLoading ? (
        <><Skeleton height={80} style={{ marginBottom: 8 }} /><Skeleton height={80} /></>
      ) : activity.length === 0 ? (
        <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{t('clientHome.noActivity')}</p>
      ) : activity.map(order => (
        <OrderCard key={order.id} order={order}
          onConfirm={handleConfirm}
          onReview={o => setReviewOrder(o)}
          onRepeat={handleRepeat}
          onContact={o => setContactOrder(o)}
        />
      ))}

      {/* Services */}
      <div className="client-section-header" style={{ marginTop: 8 }}>
        <span className="client-section-header-title">{t('clientHome.servicesTitle')}</span>
      </div>
      {svcRes.isLoading ? <Skeleton height={50} /> : (
        <Accordion services={services} onBook={s => navigate('create_order', { service: s })} />
      )}

      {/* News preview */}
      {(newsRes.isLoading || news) && (
        <>
          <div className="client-section-header" style={{ marginTop: 8 }}>
            <span className="client-section-header-title">{t('clientHome.newsTitle')}</span>
          </div>
          {newsRes.isLoading ? <Skeleton height={60} /> : news && (
            <div className="client-card" style={{ padding: 14, cursor: 'pointer' }}
              onClick={() => { haptic(); navigate('news'); }}>
              <p style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)', marginBottom: 4 }}>
                {new Date(news.created_at).toLocaleDateString('ru', { day: 'numeric', month: 'long' })}
              </p>
              <p style={{ fontSize: 14, color: 'var(--tg-theme-text-color)', lineHeight: 1.4 }}>
                {news.text?.slice(0, 120)}{news.text?.length > 120 ? '…' : ''}
              </p>
            </div>
          )}
        </>
      )}

      {reviewOrder && (
        <ReviewModal
          order={reviewOrder}
          onClose={() => setReviewOrder(null)}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ['client-activity', activeMasterId] });
            setReviewOrder(null);
          }}
        />
      )}
      {contactOrder && (
        <ContactSheet master={prof} onClose={() => setContactOrder(null)} />
      )}
    </div>
  );
}
