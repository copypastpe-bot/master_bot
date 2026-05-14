import { useI18n } from '../../../i18n';
import EditableBlock from './EditableBlock';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

function absoluteUrl(url, bust) {
  if (!url) return '';
  const base = url.startsWith('http') ? url : `${API_BASE}${url}`;
  // Strip existing ?t=... then add fresh one to force browser re-fetch.
  const clean = base.split('?')[0];
  return bust ? `${clean}?t=${bust}` : clean;
}

export default function PromoPreview({ data, styleConfig, onBlockTap, photoTs, heroOverlay }) {
  const { t } = useI18n();
  const cfg = styleConfig || {};

  const cssVars = {
    '--screen-bg': cfg.screen_bg,
    '--screen-fg': cfg.screen_fg,
    '--screen-muted': cfg.screen_muted,
    '--screen-accent': cfg.screen_accent,
    '--badge-bg': cfg.badge_bg,
    '--badge-fg': cfg.badge_fg,
    '--badge-border': cfg.badge_border,
    '--card-bg': cfg.card_bg,
    '--card-border': cfg.card_border,
    '--pill-bg': cfg.pill_bg,
    '--pill-border': cfg.pill_border,
    '--offer-bg': cfg.offer_bg,
    '--offer-border': cfg.offer_border,
    '--offer-fg': cfg.offer_fg,
    '--cta-bg': cfg.cta_bg,
    '--cta-fg': cfg.cta_fg,
    '--cta-shadow': cfg.cta_shadow,
    transition: 'background 300ms ease, color 300ms ease',
  };

  const photoUrl = absoluteUrl(data.photo_url, photoTs);

  return (
    <div className="promo-page" style={cssVars}>

      {/* Block 1: Hero */}
      <EditableBlock id="hero" label="Фото" onTap={onBlockTap}>
        <div className="hero">
          {photoUrl ? (
            <img
              key={photoUrl}
              className="hero__photo"
              src={photoUrl}
              alt={data.display_name || ''}
            />
          ) : (
            <div className="hero__placeholder">
              <span style={{ fontSize: 32 }}>📷</span>
              <span>{t('minisite.editor.photoPlaceholder')}</span>
            </div>
          )}
          <div className="hero__grad" />
          <div className="hero__fade" />
          {data.badge_text && (
            <div className="hero__badge">{data.badge_text}</div>
          )}
          {heroOverlay}
        </div>
      </EditableBlock>

      <div className="content">
        {/* Block 2: Identity */}
        <EditableBlock id="identity" label="Имя" onTap={onBlockTap}>
          <div className="identity">
            <h1 className="identity__name">
              {data.display_name || <span className="placeholder">{t('minisite.editor.yourName')}</span>}
            </h1>
            <p className="identity__role">
              {data.specialization || <span className="placeholder">{t('minisite.editor.specialization')}</span>}
            </p>
          </div>
        </EditableBlock>

        {/* Block 3: Tagline */}
        <EditableBlock id="tagline" label="Описание" onTap={onBlockTap}>
          <p className="tagline">
            {data.tagline || <span className="placeholder">{t('minisite.editor.addDescription')}</span>}
          </p>
        </EditableBlock>

        {/* Block 4: Service Card */}
        <EditableBlock id="service" label="Услуга" onTap={onBlockTap}>
          <div className="service-card">
            <span className="service-card__label">{t('minisite.editor.popularService')}</span>
            <p className="service-card__name">
              {data.service_name || <span className="placeholder">{t('minisite.editor.serviceName')}</span>}
            </p>
            <p className="service-card__price">
              <small>{t('minisite.editor.fromPrice')}</small>
              <span className="service-card__price-value">
                {data.service_price || <span className="placeholder">{t('minisite.editor.servicePrice')}</span>}
              </span>
            </p>
          </div>
        </EditableBlock>

        {/* Block 5: Promo Banner */}
        <EditableBlock id="promo" label="Акция" onTap={onBlockTap}>
          {data.promo_enabled && data.promo_text ? (
            <div className="offer-card">
              <div className="offer-card__icon">
                <svg viewBox="0 0 24 24"><path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L3 13V4h9l8.59 8.59a2 2 0 0 1 0 2.82ZM7.5 8.5A1.5 1.5 0 1 0 7.5 5.5a1.5 1.5 0 0 0 0 3Z" fill="currentColor"/></svg>
              </div>
              <span>{data.promo_text}</span>
            </div>
          ) : (
            <div className="offer-card--empty">
              {t('minisite.editor.addPromo')}
            </div>
          )}
        </EditableBlock>

        {/* Block 6: Advantages */}
        <EditableBlock id="advantages" label="Преимущества" onTap={onBlockTap}>
          <div className="advantages">
            {data.advantages?.length > 0 ? (
              data.advantages.map((adv, i) => (
                <div className="advantage" key={i}>
                  <div className="advantage__icon-wrap">
                    <span className="advantage__icon">{adv.icon || '✓'}</span>
                  </div>
                  <p className="advantage__text">{adv.text}</p>
                </div>
              ))
            ) : (
              <div className="advantages--empty">
                <span className="placeholder">{t('minisite.editor.addAdvantages')}</span>
              </div>
            )}
          </div>
        </EditableBlock>

        {/* Block 7: CTA */}
        <EditableBlock id="cta" label="Кнопка" onTap={onBlockTap}>
          <div className="cta-section">
            <div className="cta-button">{t('minisite.editor.ctaButton')}</div>
            <p className="cta-subtext">
              {data.sub_button_text || t('minisite.editor.ctaSubtext')}
            </p>
          </div>
        </EditableBlock>
      </div>
    </div>
  );
}
