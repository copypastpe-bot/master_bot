import { useState, useEffect } from 'react';
import {
  getClientMasterProfile,
  getClientMasterReviews,
  getPublicMasterProfile,
  linkToMaster,
} from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';
import { DEFAULT_CURRENCY, getCurrencySymbol } from '../master/profileOptions';

const WebApp = window.Telegram?.WebApp;
function haptic() { WebApp?.HapticFeedback?.impactOccurred('light'); }

const CLIENT_BOT = import.meta.env.VITE_CLIENT_BOT_USERNAME || '';

export default function MasterLanding({ mode, masterId, inviteToken, navigate, onLinked }) {
  const { t, locale } = useI18n();
  const [profile, setProfile] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (mode === 'public' && inviteToken) {
          const data = await getPublicMasterProfile(inviteToken);
          setProfile(data);
          setReviews(data.reviews || []);
        } else if (mode === 'private' && masterId) {
          const [prof, rev] = await Promise.all([
            getClientMasterProfile(masterId),
            getClientMasterReviews(masterId, 10, 0),
          ]);
          setProfile(prof);
          setReviews(rev.reviews || []);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [mode, masterId, inviteToken]);

  const handleConnect = async () => {
    haptic();
    setLinking(true);
    try {
      await linkToMaster(inviteToken);
    } catch (e) {
      if (e?.response?.status !== 409) {
        WebApp?.HapticFeedback?.notificationOccurred('error');
        setLinking(false);
        return;
      }
    }
    WebApp?.HapticFeedback?.notificationOccurred('success');
    onLinked?.();
  };

  const handleShare = () => {
    haptic();
    const token = profile?.invite_token || inviteToken;
    if (!token || !CLIENT_BOT) return;
    const url = `https://t.me/${CLIENT_BOT}?start=invite_${token}`;
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(profile?.name || '')}`;
    window.open(shareUrl, '_blank');
  };

  const formatReviewName = (name) => {
    if (!name) return 'Клиент';
    const parts = name.trim().split(' ');
    if (parts.length < 2) return name;
    return `${parts[0]} ${parts[1][0]}.`;
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  const avatarContent = profile?.photo_url
    ? <img src={profile.photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
    : (profile?.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  const currencySymbol = getCurrencySymbol(profile?.currency || DEFAULT_CURRENCY);

  const metrics = [
    profile?.review_count > 0 && t('masterLanding.reviewsMetric', { count: profile.review_count }),
    profile?.years_on_platform > 1 && t('masterLanding.yearsMetric', { count: profile.years_on_platform }),
    profile?.years_on_platform === 1 && t('masterLanding.yearMetric'),
  ].filter(Boolean).join(' · ');

  if (loading) {
    return (
      <div className="client-page" style={{ padding: '0 16px 120px' }}>
        <Skeleton height={80} style={{ borderRadius: '50%', width: 80, margin: '24px auto 12px' }} />
        <Skeleton height={24} style={{ width: 200, margin: '0 auto 8px' }} />
        <Skeleton height={16} style={{ width: 160, margin: '0 auto' }} />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="client-page" style={{ padding: '24px 16px', textAlign: 'center' }}>
        <p style={{ color: 'var(--tg-theme-hint-color)' }}>Специалист не найден</p>
      </div>
    );
  }

  return (
    <div className="client-page" style={{ paddingBottom: 120 }}>
      {/* Hero */}
      <div className="client-landing-hero">
        <div className="client-landing-avatar">{avatarContent}</div>
        <p className="client-landing-name">{profile.name}</p>
        {profile.sphere && <p className="client-landing-sphere">{profile.sphere}</p>}
        {metrics && <p className="client-landing-metrics">{metrics}</p>}
      </div>

      <div style={{ padding: '0 16px' }}>
        {/* Actions */}
        <div className="client-action-grid" style={{ marginBottom: 16 }}>
          {mode === 'public' ? (
            <button className="client-action-btn is-full" onClick={handleConnect} disabled={linking}>
              {linking ? t('masterLanding.connecting') : t('masterLanding.connectBtn')}
            </button>
          ) : (
            <>
              <button className="client-action-btn is-primary" onClick={() => { haptic(); navigate('create_order'); }}>
                {t('masterLanding.bookBtn')}
              </button>
              <button className="client-action-btn is-secondary" onClick={() => { haptic(); navigate('ask_question'); }}>
                {t('masterLanding.questionBtn')}
              </button>
            </>
          )}
        </div>

        {/* About */}
        {profile.bio && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.aboutTitle')}</p>
            <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)', lineHeight: 1.6 }}>{profile.bio}</p>
          </section>
        )}

        {/* Services */}
        {profile.services?.length > 0 && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.servicesTitle')}</p>
            <div className="client-card" style={{ padding: '0 14px' }}>
              {profile.services.map((s, i) => (
                <div key={s.id ?? i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '12px 0',
                  borderBottom: i < profile.services.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                }}>
                  <span style={{ fontSize: 15 }}>{s.name}</span>
                  {s.price != null && (
                    <span style={{ fontSize: 14, color: '#2481cc' }}>
                      {s.price.toLocaleString(locale)} {getCurrencySymbol(s.currency) || currencySymbol}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Contacts */}
        {(profile.phone || profile.telegram || profile.instagram || profile.website || profile.contact_address) && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.contactsTitle')}</p>
            <div className="client-card" style={{ padding: '0 14px' }}>
              {[
                profile.phone && { label: profile.phone, href: `tel:${profile.phone}` },
                profile.telegram && { label: `@${profile.telegram.replace('@', '')}`, href: `tg://resolve?domain=${profile.telegram.replace('@', '')}` },
                profile.instagram && { label: `@${profile.instagram.replace('@', '')}`, href: `https://instagram.com/${profile.instagram.replace('@', '')}` },
                profile.website && { label: profile.website, href: profile.website.startsWith('http') ? profile.website : `https://${profile.website}` },
                profile.contact_address && { label: profile.contact_address, href: null },
              ].filter(Boolean).map((c, i, arr) => (
                <div key={i} style={{
                  padding: '12px 0',
                  borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                }}>
                  {c.href ? (
                    <a href={c.href} style={{ color: 'var(--tg-theme-link-color, #2481cc)', fontSize: 14, textDecoration: 'none' }}>
                      {c.label}
                    </a>
                  ) : (
                    <span style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{c.label}</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Work mode */}
        {profile.work_mode && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.workModeTitle')}</p>
            <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{profile.work_mode}</p>
          </section>
        )}

        {/* Reviews */}
        <section style={{ marginBottom: 20 }}>
          <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.reviewsTitle')}</p>
          {reviews.length === 0 ? (
            <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{t('masterLanding.noReviews')}</p>
          ) : reviews.map((r, i) => (
            <div key={r.id ?? i} className="client-card" style={{ padding: '12px 14px', marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{formatReviewName(r.client_name)}</span>
                <span style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)' }}>{formatDate(r.created_at)}</span>
              </div>
              <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)', lineHeight: 1.5, margin: 0 }}>{r.text}</p>
            </div>
          ))}
        </section>

        {/* Share */}
        {CLIENT_BOT && (
          <button className="client-action-btn is-secondary" style={{ width: '100%', marginBottom: 8 }} onClick={handleShare}>
            {t('masterLanding.shareBtn')}
          </button>
        )}
      </div>
    </div>
  );
}
