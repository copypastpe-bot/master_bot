import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  checkPromoPageSlug,
  createPromoPage,
  getPromoPage,
  getPromoPageCategories,
  publishPromoPage,
  unpublishPromoPage,
  updatePromoPage,
  updatePromoPageSlug,
  uploadPromoPagePhoto,
} from '../../api/client';
import { useI18n } from '../../i18n';
import { resetViewportScroll } from '../../utils/scroll';

const WebApp = window.Telegram?.WebApp;
const API_BASE = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

const EMPTY_FORM = {
  category_id: '',
  style_id: '',
  display_name: '',
  specialization: '',
  tagline: '',
  badge_text: '',
  service_name: '',
  service_price: '',
  promo_enabled: false,
  promo_text: '',
  advantages: [
    { text: '', icon: '' },
    { text: '', icon: '' },
    { text: '', icon: '' },
  ],
  sub_button_text: 'Бонусы и уведомления в Telegram',
  slug: '',
};

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{1,48}[a-z0-9])$/;

const ICON_SVG = {
  '⏰': '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 11h5v-2h-4V6h-2v7Z"/></svg>',
  '🧴': '<svg viewBox="0 0 24 24"><path d="M9 2h6v3l-2 2v2h1a4 4 0 0 1 4 4v7a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-7a4 4 0 0 1 4-4h1V7L9 5V2Zm1 12v5h4v-5h-4Z"/></svg>',
  '🔔': '<svg viewBox="0 0 24 24"><path d="M12 22a2.8 2.8 0 0 0 2.65-2H9.35A2.8 2.8 0 0 0 12 22Zm7-6-2-2v-4a5 5 0 0 0-4-4.9V3h-2v2.1A5 5 0 0 0 7 10v4l-2 2v2h14v-2Z"/></svg>',
  '🌿': '<svg viewBox="0 0 24 24"><path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8Z"/></svg>',
  '📸': '<svg viewBox="0 0 24 24"><path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4ZM9 2 7.17 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3.17L15 2H9Zm3 15a5 5 0 1 1 0-10 5 5 0 0 1 0 10Z"/></svg>',
  '⭐': '<svg viewBox="0 0 24 24"><path d="m12 2.5 2.9 5.87 6.48.94-4.69 4.57 1.11 6.45L12 17.28l-5.8 3.05 1.11-6.45-4.69-4.57 6.48-.94L12 2.5Z"/></svg>',
  '✂️': '<svg viewBox="0 0 24 24"><path d="M9.6 7.4A3.5 3.5 0 1 0 8 10.34L11.66 14 8 17.66A3.5 3.5 0 1 0 9.6 20.6L20.2 10l-1.4-1.4-5.72 5.72-3.48-3.48ZM5.5 9A1.5 1.5 0 1 1 5.5 6a1.5 1.5 0 0 1 0 3Zm0 10A1.5 1.5 0 1 1 5.5 16a1.5 1.5 0 0 1 0 3Z"/></svg>',
  '💈': '<svg viewBox="0 0 24 24"><path d="M9 2h6v3l-2 2v2h1a4 4 0 0 1 4 4v7a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-7a4 4 0 0 1 4-4h1V7L9 5V2Zm1 12v5h4v-5h-4Z"/></svg>',
  '🧼': '<svg viewBox="0 0 24 24"><path d="M12 2 4 5v6c0 5.1 3.4 9.9 8 11 4.6-1.1 8-5.9 8-11V5l-8-3Zm-1 14-4-4 1.4-1.4 2.6 2.6 5.6-5.6L18 9l-7 7Z"/></svg>',
  '💡': '<svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-4 12.74V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.26A7 7 0 0 0 12 2ZM9 20v1a3 3 0 0 0 6 0v-1H9Z"/></svg>',
  '📍': '<svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z"/></svg>',
  '💅': '<svg viewBox="0 0 24 24"><path d="M18.7 3.3a2.4 2.4 0 0 0-3.4 0l-7.8 7.8 3.4 3.4 7.8-7.8a2.4 2.4 0 0 0 0-3.4ZM7 12.8c-2.8.7-4 2.7-4 5.7 0 1 .7 1.5 1.6 1.2 1.6-.5 3.2-.3 4.4-1.5 1.2-1.2 1.2-3.1 0-4.3L7 12.8Z"/></svg>',
  '✨': '<svg viewBox="0 0 24 24"><path d="M13 2 9.9 8.9 3 12l6.9 3.1L13 22l3.1-6.9L23 12l-6.9-3.1L13 2ZM5 3l-1 2-2 1 2 1 1 2 1-2 2-1-2-1-1-2Z"/></svg>',
  '💗': '<svg viewBox="0 0 24 24"><path d="m12 21.35-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35Z"/></svg>',
  '🕯️': '<svg viewBox="0 0 24 24"><path d="M12 2C9.24 6 8 8.5 8 10.5A4 4 0 0 0 16 10.5C16 8.5 14.76 6 12 2ZM7 14v8h10v-8H7Z"/></svg>',
  '🤲': '<svg viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 9-8 9s-8-4-8-9a8 8 0 0 1 3-6.24V4a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2.76A8 8 0 0 1 20 13Z"/></svg>',
  '💪': '<svg viewBox="0 0 24 24"><path d="m12 2.5 2.9 5.87 6.48.94-4.69 4.57 1.11 6.45L12 17.28l-5.8 3.05 1.11-6.45-4.69-4.57 6.48-.94L12 2.5Z"/></svg>',
  '📚': '<svg viewBox="0 0 24 24"><path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H6Zm1 4h10v2H7V6Zm0 4h7v2H7v-2Z"/></svg>',
  '🎯': '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 16a6 6 0 1 1 6-6 6 6 0 0 1-6 6Zm0-8a2 2 0 1 0 2 2 2 2 0 0 0-2-2Z"/></svg>',
  '✏️': '<svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25ZM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83Z"/></svg>',
  '📖': '<svg viewBox="0 0 24 24"><path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H6Zm1 4h10v2H7V6Zm0 4h7v2H7v-2Z"/></svg>',
  '✓': '<svg viewBox="0 0 24 24"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17Z"/></svg>',
};

const DEFAULT_ICON_SVG = ICON_SVG['✓'];

function haptic(type = 'light') {
  WebApp?.HapticFeedback?.impactOccurred?.(type);
}

function notify(type = 'success') {
  WebApp?.HapticFeedback?.notificationOccurred?.(type);
}

function AdvantageIcon({ icon }) {
  return (
    <span
      className="promo-builder-svg-icon"
      dangerouslySetInnerHTML={{ __html: ICON_SVG[icon || ''] || DEFAULT_ICON_SVG }}
    />
  );
}

function absoluteMediaUrl(url) {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  return `${API_BASE.replace(/\/$/, '')}${url}`;
}

function errorText(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

function normalizeSlug(value) {
  return (value || '')
    .trim()
    .toLowerCase()
    .replace(/ё/g, 'e')
    .replace(/[а-я]/g, (char) => ({
      а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ж: 'zh', з: 'z',
      и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p',
      р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'c', ч: 'ch',
      ш: 'sh', щ: 'sch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
    }[char] || ''))
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50);
}

function buildInitialForm(page, categories) {
  if (page) {
    return {
      ...EMPTY_FORM,
      category_id: page.category_id || '',
      style_id: page.style_id || '',
      display_name: page.display_name || '',
      specialization: page.specialization || '',
      tagline: page.tagline || '',
      badge_text: page.badge_text || '',
      service_name: page.service_name || '',
      service_price: page.service_price || '',
      promo_enabled: Boolean(page.promo_enabled),
      promo_text: page.promo_text || '',
      advantages: (page.advantages || []).slice(0, 3).map((item) => ({
        text: item.text || '',
        icon: item.icon || '',
      })),
      sub_button_text: page.sub_button_text || EMPTY_FORM.sub_button_text,
      slug: page.slug || '',
    };
  }

  const category = categories[0];
  const presets = category?.advantages || [];
  return {
    ...EMPTY_FORM,
    category_id: category?.id || '',
    style_id: category?.styles?.[0]?.id || '',
    advantages: [0, 1, 2].map((index) => ({
      text: presets[index]?.text || '',
      icon: presets[index]?.icon || '',
    })),
  };
}

function styleVars(styleConfig = {}) {
  const screenBg = styleConfig.screen_bg || styleConfig.bg_color || '#f7faf5';
  const screenFg = styleConfig.screen_fg || styleConfig.text_color || '#1a2a1e';
  const screenMuted = styleConfig.screen_muted || '#566b5e';
  const screenAccent = styleConfig.screen_accent || styleConfig.primary_color || '#2d8049';
  const badgeBg = styleConfig.badge_bg || 'rgba(255,255,255,.8)';
  const badgeFg = styleConfig.badge_fg || styleConfig.badge_text || '#1f6e3a';
  const badgeBorder = styleConfig.badge_border || 'rgba(255,255,255,.68)';
  const cardBg = styleConfig.card_bg || '#eef5eb';
  const cardBorder = styleConfig.card_border || '#d5e5cf';
  const pillBg = styleConfig.pill_bg || '#deedda';
  const pillBorder = styleConfig.pill_border || '#7aba6e';
  const offerBg = styleConfig.offer_bg || '#faf0ec';
  const offerBorder = styleConfig.offer_border || '#e8c9bc';
  const offerFg = styleConfig.offer_fg || '#8c4a2a';
  const ctaBg = styleConfig.cta_bg || styleConfig.button_bg || screenAccent;
  const ctaFg = styleConfig.cta_fg || styleConfig.button_text || '#ffffff';
  const ctaShadow = styleConfig.cta_shadow || 'rgba(31,135,79,.22)';
  const swatch = `linear-gradient(135deg, ${screenBg} 0 35%, ${cardBg} 35% 65%, ${ctaBg} 65% 100%)`;
  return {
    '--promo-gradient': swatch,
    '--screen-bg': screenBg,
    '--screen-fg': screenFg,
    '--screen-muted': screenMuted,
    '--screen-accent': screenAccent,
    '--badge-bg': badgeBg,
    '--badge-fg': badgeFg,
    '--badge-border': badgeBorder,
    '--card-bg': cardBg,
    '--card-border': cardBorder,
    '--pill-bg': pillBg,
    '--pill-border': pillBorder,
    '--offer-bg': offerBg,
    '--offer-border': offerBorder,
    '--offer-fg': offerFg,
    '--cta-bg': ctaBg,
    '--cta-fg': ctaFg,
    '--cta-shadow': ctaShadow,
  };
}

function Progress({ step }) {
  return (
    <div className="promo-builder-progress" aria-label={`Шаг ${step} из 4`}>
      {[1, 2, 3, 4].map((item) => (
        <span key={item} className={item <= step ? 'is-active' : ''} />
      ))}
    </div>
  );
}

function Field({ label, children, hint, error }) {
  return (
    <label className="promo-builder-field">
      <span className="promo-builder-label">{label}</span>
      {children}
      {hint && <span className="promo-builder-hint">{hint}</span>}
      {error && <span className="promo-builder-error">{error}</span>}
    </label>
  );
}

function PromoPreview({ form, styleVars: vars, photoPreview }) {
  const advantages = form.advantages.filter((item) => item.text.trim()).slice(0, 3);
  return (
    <div className="prlp-page" style={vars}>
      <div className="hero" style={photoPreview ? { backgroundImage: `url("${photoPreview}")` } : undefined}>
        {photoPreview
          ? null
          : <div className="hero__placeholder" />
        }
        <div className="hero__grad" />
        <div className="hero__fade" />
        {form.badge_text && <div className="hero__badge">{form.badge_text}</div>}
      </div>

      <div className="content">
        <div className="identity">
          <h1 className="identity__name">{form.display_name || 'Имя мастера'}</h1>
          <p className="identity__role">{form.specialization || 'Специализация'}</p>
        </div>

        <p className="tagline">{form.tagline || 'Короткое предложение для новых клиентов'}</p>

        <div className="service-card">
          <span className="service-card__label">Популярная услуга</span>
          <p className="service-card__name">{form.service_name || 'Название услуги'}</p>
          <p className="service-card__price">
            <small>от</small>
            <strong>{form.service_price || '0'}</strong>
          </p>
        </div>

        {form.promo_enabled && form.promo_text && (
          <div className="offer-card">
            <div className="offer-card__icon">
              <svg viewBox="0 0 24 24"><path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L3 13V4h9l8.59 8.59a2 2 0 0 1 0 2.82ZM7.5 8.5A1.5 1.5 0 1 0 7.5 5.5a1.5 1.5 0 0 0 0 3Z"/></svg>
            </div>
            <span>{form.promo_text}</span>
          </div>
        )}

        <div className="advantages">
          {advantages.map((item, index) => (
            <div key={`${item.text}-${index}`} className="advantage">
              <div className="advantage__icon">
                <AdvantageIcon icon={item.icon} />
              </div>
              <span className="advantage__text">{item.text}</span>
            </div>
          ))}
        </div>

        <button type="button" className="cta-button">Забрать бонусы и подписаться</button>
        <p className="cta-subtext">{form.sub_button_text || EMPTY_FORM.sub_button_text}</p>
      </div>
    </div>
  );
}

export default function PromoPageBuilder() {
  const { tr } = useI18n();
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState('wizard');
  const [form, setForm] = useState(EMPTY_FORM);
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState('');
  const [slugState, setSlugState] = useState(null);
  const [hydratedKey, setHydratedKey] = useState('');

  const categoriesQuery = useQuery({
    queryKey: ['promo-page-categories'],
    queryFn: getPromoPageCategories,
    staleTime: 5 * 60_000,
  });

  const pageQuery = useQuery({
    queryKey: ['promo-page'],
    queryFn: () => getPromoPage().catch((err) => {
      if (err?.response?.status === 404) return null;
      throw err;
    }),
    staleTime: 20_000,
  });

  const categories = useMemo(() => categoriesQuery.data?.categories || [], [categoriesQuery.data]);
  const savedPage = pageQuery.data;
  const currentCategory = categories.find((item) => item.id === Number(form.category_id));
  const currentStyle = currentCategory?.styles?.find((item) => item.id === Number(form.style_id));
  const existingPhotoUrl = absoluteMediaUrl(savedPage?.photo_url);
  const previewUrl = photoPreview || existingPhotoUrl;

  useEffect(() => {
    resetViewportScroll();
  }, [step, mode]);

  useEffect(() => {
    if (!categories.length || pageQuery.isLoading) return;
    const nextKey = savedPage ? `page:${savedPage.id}:${savedPage.updated_at || ''}` : `empty:${categories.length}`;
    if (hydratedKey === nextKey) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setForm(buildInitialForm(savedPage, categories));
      setMode(savedPage ? 'manage' : 'wizard');
      setStep(savedPage ? 4 : 1);
      setHydratedKey(nextKey);
    });
    return () => {
      cancelled = true;
    };
  }, [categories, savedPage, pageQuery.isLoading, hydratedKey]);

  const pageMutation = useMutation({
    mutationFn: async ({ publish }) => {
      const payload = buildPayload(form);
      let page = savedPage ? await updatePromoPage(payload) : await createPromoPage(payload);
      const normalizedSlug = normalizeSlug(form.slug || page.slug || form.display_name);
      if (normalizedSlug && normalizedSlug !== page.slug) {
        page = await updatePromoPageSlug(normalizedSlug);
      }
      if (photoFile) {
        const upload = await uploadPromoPagePhoto(photoFile);
        page = upload.page;
      }
      if (publish) {
        page = await publishPromoPage();
      }
      return page;
    },
    onSuccess: (page) => {
      notify('success');
      qc.setQueryData(['promo-page'], page);
      qc.invalidateQueries({ queryKey: ['promo-page'] });
      setPhotoFile(null);
      setPhotoPreview('');
      setMode('manage');
      setStep(4);
      setError('');
    },
    onError: (err) => {
      notify('error');
      setError(errorText(err, tr('Не удалось сохранить промо-страницу', 'Failed to save promo page')));
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: unpublishPromoPage,
    onSuccess: (page) => {
      notify('success');
      qc.setQueryData(['promo-page'], page);
      qc.invalidateQueries({ queryKey: ['promo-page'] });
    },
    onError: (err) => {
      notify('error');
      setError(errorText(err, tr('Не удалось снять с публикации', 'Failed to unpublish')));
    },
  });

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => ({ ...prev, [key]: '' }));
    if (key === 'slug') setSlugState(null);
  };

  const handleCategoryChange = (categoryId) => {
    const category = categories.find((item) => item.id === Number(categoryId));
    const presets = category?.advantages || [];
    setForm((prev) => ({
      ...prev,
      category_id: category?.id || '',
      style_id: category?.styles?.[0]?.id || '',
      advantages: [0, 1, 2].map((index) => ({
        text: presets[index]?.text || prev.advantages[index]?.text || '',
        icon: presets[index]?.icon || prev.advantages[index]?.icon || '',
      })),
    }));
    setFieldErrors({});
  };

  const handlePhotoChange = (file) => {
    setPhotoFile(file || null);
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoPreview(file ? URL.createObjectURL(file) : '');
  };

  useEffect(() => () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
  }, [photoPreview]);

  const toggleAdvantage = (preset) => {
    const exists = form.advantages.some((item) => item.text === preset.text);
    if (exists) {
      const next = form.advantages.filter((item) => item.text !== preset.text);
      while (next.length < 3) next.push({ text: '', icon: '' });
      setForm((prev) => ({ ...prev, advantages: next.slice(0, 3) }));
      return;
    }
    const emptyIndex = form.advantages.findIndex((item) => !item.text.trim());
    if (emptyIndex === -1) return;
    const next = [...form.advantages];
    next[emptyIndex] = { text: preset.text, icon: preset.icon || '' };
    setForm((prev) => ({ ...prev, advantages: next }));
  };

  const validateStep = () => {
    const nextErrors = {};
    if (step === 1) {
      if (!form.category_id) nextErrors.category_id = tr('Выберите категорию', 'Choose a category');
      if (form.display_name.trim().length < 2) nextErrors.display_name = tr('Минимум 2 символа', 'At least 2 characters');
      if (form.specialization.trim().length < 2) nextErrors.specialization = tr('Минимум 2 символа', 'At least 2 characters');
      if (form.tagline.trim().length < 10) nextErrors.tagline = tr('Минимум 10 символов', 'At least 10 characters');
      if (form.service_name.trim().length < 2) nextErrors.service_name = tr('Укажите услугу', 'Enter a service');
      if (!form.service_price.trim()) nextErrors.service_price = tr('Укажите цену', 'Enter a price');
    }
    if (step === 2) {
      if (!form.style_id) nextErrors.style_id = tr('Выберите стиль', 'Choose a style');
      form.advantages.forEach((item, index) => {
        if (item.text.trim().length < 2) nextErrors[`advantage_${index}`] = tr('Заполните преимущество', 'Fill the advantage');
      });
    }
    if (step === 4) {
      const slug = normalizeSlug(form.slug || form.display_name);
      if (!SLUG_RE.test(slug)) nextErrors.slug = tr('Только латиница, цифры и дефис, 3-50 символов', 'Use latin letters, digits and hyphens, 3-50 chars');
      if (!photoFile && !savedPage?.photo_url) nextErrors.photo = tr('Добавьте фото перед публикацией', 'Add a photo before publishing');
    }
    setFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const nextStep = () => {
    setError('');
    if (!validateStep()) {
      notify('error');
      return;
    }
    haptic('medium');
    setStep((value) => Math.min(4, value + 1));
  };

  const checkSlug = async () => {
    const slug = normalizeSlug(form.slug || form.display_name);
    updateField('slug', slug);
    if (!SLUG_RE.test(slug)) {
      setFieldErrors((prev) => ({ ...prev, slug: tr('Только латиница, цифры и дефис, 3-50 символов', 'Use latin letters, digits and hyphens, 3-50 chars') }));
      return;
    }
    try {
      const result = await checkPromoPageSlug(slug);
      setSlugState(result.available ? { ok: true } : { ok: false, suggestions: result.suggestions || [] });
    } catch {
      setSlugState(null);
    }
  };

  const handlePublish = () => {
    setError('');
    if (!validateStep()) {
      notify('error');
      return;
    }
    pageMutation.mutate({ publish: true });
  };

  const handleEdit = () => {
    haptic();
    setMode('wizard');
    setStep(1);
  };

  const copyLink = (link) => {
    if (!link) return;
    haptic();
    navigator?.clipboard?.writeText?.(link);
    WebApp?.showAlert?.(tr('Ссылка скопирована', 'Link copied'));
  };

  if (categoriesQuery.isLoading || pageQuery.isLoading) {
    return <div className="promo-builder-state">{tr('Загрузка...', 'Loading...')}</div>;
  }

  if (categoriesQuery.isError || pageQuery.isError) {
    return (
      <div className="promo-builder-state">
        <p>{tr('Не удалось загрузить конструктор', 'Failed to load builder')}</p>
        <button type="button" onClick={() => { categoriesQuery.refetch(); pageQuery.refetch(); }}>
          {tr('Повторить', 'Retry')}
        </button>
      </div>
    );
  }

  if (mode === 'manage' && savedPage) {
    return (
      <div className="promo-builder-page">
        <section className="promo-builder-management">
          <div>
            <span className={`promo-builder-status${savedPage.is_published ? ' is-live' : ''}`}>
              {savedPage.is_published ? tr('Опубликована', 'Published') : tr('Черновик', 'Draft')}
            </span>
            <h2 className="promo-builder-title">{savedPage.display_name}</h2>
            <p className="promo-builder-subtitle">{savedPage.tagline}</p>
          </div>
          <PromoPreview
            form={form}
            styleVars={styleVars(currentStyle?.config)}
            photoPreview={existingPhotoUrl}
          />
        </section>

        <section className="promo-builder-card">
          <div className="promo-builder-stats">
            <div><b>{savedPage.views_count || 0}</b><span>{tr('просмотров', 'views')}</span></div>
            <div><b>{savedPage.clicks_count || 0}</b><span>{tr('кликов', 'clicks')}</span></div>
          </div>
          <Field label={tr('Публичная ссылка', 'Public link')}>
            <div className="promo-builder-link-row">
              <input value={savedPage.page_url || ''} readOnly />
              <button type="button" onClick={() => copyLink(savedPage.page_url)}>{tr('Копировать', 'Copy')}</button>
            </div>
          </Field>
          {savedPage.qr_url && (
            <div className="promo-builder-qr">
              <img src={absoluteMediaUrl(savedPage.qr_url)} alt="QR" />
              <button type="button" onClick={() => copyLink(savedPage.page_url)}>{tr('Ссылка для QR', 'QR link')}</button>
            </div>
          )}
        </section>

        {error && <div className="promo-builder-error is-global">{error}</div>}

        <div className="promo-builder-actions">
          <button type="button" className="promo-builder-btn is-secondary" onClick={handleEdit}>
            {tr('Редактировать', 'Edit')}
          </button>
          {savedPage.is_published ? (
            <button
              type="button"
              className="promo-builder-btn is-danger"
              onClick={() => unpublishMutation.mutate()}
              disabled={unpublishMutation.isPending}
            >
              {unpublishMutation.isPending ? tr('Снимаем...', 'Unpublishing...') : tr('Снять с публикации', 'Unpublish')}
            </button>
          ) : (
            <button type="button" className="promo-builder-btn" onClick={handleEdit}>
              {tr('Опубликовать', 'Publish')}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="promo-builder-page">
      <Progress step={step} />
      <header className="promo-builder-header">
        <h2>{stepTitle(step, tr)}</h2>
        <p>{stepSubtitle(step, tr)}</p>
      </header>

      {step === 1 && (
        <section className="promo-builder-card">
          <Field label={tr('Категория', 'Category')} error={fieldErrors.category_id}>
            <select value={form.category_id} onChange={(event) => handleCategoryChange(event.target.value)}>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>{category.name}</option>
              ))}
            </select>
          </Field>
          <Field label={tr('Имя или название', 'Name or title')} error={fieldErrors.display_name}>
            <input value={form.display_name} maxLength={60} onChange={(event) => updateField('display_name', event.target.value)} placeholder="Мария Иванова" />
          </Field>
          <Field label={tr('Специализация', 'Specialization')} error={fieldErrors.specialization}>
            <input value={form.specialization} maxLength={80} onChange={(event) => updateField('specialization', event.target.value)} placeholder={tr('Частный клинер', 'Private cleaner')} />
          </Field>
          <Field label={tr('Короткое предложение', 'Short offer')} hint={`${form.tagline.length}/120`} error={fieldErrors.tagline}>
            <textarea value={form.tagline} maxLength={120} rows={3} onChange={(event) => updateField('tagline', event.target.value)} placeholder={tr('Уборка квартиры без хлопот, с бонусами за повторные визиты', 'A clear offer for new clients')} />
          </Field>
          <div className="promo-builder-grid">
            <Field label={tr('Популярная услуга', 'Popular service')} error={fieldErrors.service_name}>
              <input value={form.service_name} maxLength={100} onChange={(event) => updateField('service_name', event.target.value)} placeholder={tr('Уборка квартиры до 50 м²', 'Apartment cleaning up to 50 sqm')} />
            </Field>
            <Field label={tr('Цена', 'Price')} error={fieldErrors.service_price}>
              <input value={form.service_price} maxLength={30} onChange={(event) => updateField('service_price', event.target.value)} placeholder={tr('от 4 000 дин', 'from 4,000 RSD')} />
            </Field>
          </div>
          <Field label={tr('Бейдж', 'Badge')}>
            <input value={form.badge_text} maxLength={40} onChange={(event) => updateField('badge_text', event.target.value)} placeholder={tr('ЧИСТО БЫСТРО НАДЁЖНО', 'CLEAN FAST RELIABLE')} />
          </Field>
          <label className="promo-builder-toggle">
            <input type="checkbox" checked={form.promo_enabled} onChange={(event) => updateField('promo_enabled', event.target.checked)} />
            <span>{tr('Добавить акцию на страницу', 'Add an offer to the page')}</span>
          </label>
          {form.promo_enabled && (
            <Field label={tr('Текст акции', 'Offer text')}>
              <input value={form.promo_text} maxLength={60} onChange={(event) => updateField('promo_text', event.target.value)} placeholder={tr('-20% на первый визит', '20% off first visit')} />
            </Field>
          )}
        </section>
      )}

      {step === 2 && (
        <>
          <section className="promo-builder-card">
            <div className="promo-builder-card-title">{tr('Стиль', 'Style')}</div>
            <div className="promo-builder-style-grid">
              {(currentCategory?.styles || []).map((style) => (
                <button
                  key={style.id}
                  type="button"
                  className={`promo-builder-style${Number(form.style_id) === style.id ? ' is-selected' : ''}`}
                  onClick={() => updateField('style_id', style.id)}
                  style={styleVars(style.config)}
                >
                  <span className="promo-builder-style-swatch" />
                  <b>{style.name}</b>
                </button>
              ))}
            </div>
            {fieldErrors.style_id && <div className="promo-builder-error">{fieldErrors.style_id}</div>}
          </section>

          <section className="promo-builder-card">
            <div className="promo-builder-card-title">{tr('Преимущества', 'Advantages')}</div>
            <div className="promo-builder-chip-row">
              {(currentCategory?.advantages || []).map((preset) => {
                const selected = form.advantages.some((item) => item.text === preset.text);
                return (
                  <button
                    key={preset.id}
                    type="button"
                    className={`promo-builder-chip${selected ? ' is-selected' : ''}`}
                    onClick={() => toggleAdvantage(preset)}
                  >
                    <AdvantageIcon icon={preset.icon} />{preset.text}
                  </button>
                );
              })}
            </div>
            <div className="promo-builder-advantage-edit">
              {form.advantages.map((item, index) => (
                <Field key={index} label={tr(`Преимущество ${index + 1}`, `Advantage ${index + 1}`)} error={fieldErrors[`advantage_${index}`]}>
                  <div className="promo-builder-advantage-row">
                    <span className="promo-builder-advantage-icon-preview">
                      <AdvantageIcon icon={item.icon} />
                    </span>
                    <input
                      value={item.text}
                      maxLength={60}
                      onChange={(event) => {
                        const next = [...form.advantages];
                        next[index] = { ...next[index], text: event.target.value };
                        updateField('advantages', next);
                      }}
                    />
                  </div>
                </Field>
              ))}
            </div>
          </section>
        </>
      )}

      {step === 3 && (
        <section className="promo-builder-preview-wrap">
          <PromoPreview form={form} styleVars={styleVars(currentStyle?.config)} photoPreview={previewUrl} />
        </section>
      )}

      {step === 4 && (
        <section className="promo-builder-card">
          <Field label={tr('Адрес страницы', 'Page address')} hint={tr('Можно оставить автогенерацию из имени', 'Can be generated from the name')} error={fieldErrors.slug}>
            <div className="promo-builder-slug-row">
              <span>crmfit.ru/m/</span>
              <input
                value={form.slug}
                onChange={(event) => updateField('slug', normalizeSlug(event.target.value))}
                onBlur={checkSlug}
                placeholder={normalizeSlug(form.display_name) || 'maria-cleaning'}
              />
              <button type="button" onClick={checkSlug}>{tr('Проверить', 'Check')}</button>
            </div>
          </Field>
          {slugState?.ok && <div className="promo-builder-success">{tr('Адрес свободен', 'Address is available')}</div>}
          {slugState && !slugState.ok && (
            <div className="promo-builder-error">
              {tr('Адрес занят', 'Address is taken')}
              {slugState.suggestions?.length > 0 && (
                <button type="button" onClick={() => updateField('slug', slugState.suggestions[0])}>
                  {slugState.suggestions[0]}
                </button>
              )}
            </div>
          )}

          <Field label={tr('Фото', 'Photo')} error={fieldErrors.photo}>
            <div className="promo-builder-photo-row">
              <div className="promo-builder-photo-thumb">
                {previewUrl ? <img src={previewUrl} alt="" /> : <span>{tr('Нет фото', 'No photo')}</span>}
              </div>
              <input
                type="file"
                accept="image/*"
                onChange={(event) => handlePhotoChange(event.target.files?.[0] || null)}
              />
            </div>
          </Field>

          <Field label={tr('Текст под кнопкой', 'Text under button')}>
            <input value={form.sub_button_text} maxLength={60} onChange={(event) => updateField('sub_button_text', event.target.value)} />
          </Field>
        </section>
      )}

      {error && <div className="promo-builder-error is-global">{error}</div>}

      <div className="promo-builder-actions">
        {step > 1 && (
          <button type="button" className="promo-builder-btn is-secondary" onClick={() => { haptic(); setStep((value) => value - 1); }}>
            {tr('Назад', 'Back')}
          </button>
        )}
        {step < 4 ? (
          <button type="button" className="promo-builder-btn" onClick={nextStep}>
            {tr('Далее', 'Next')}
          </button>
        ) : (
          <button
            type="button"
            className="promo-builder-btn"
            onClick={handlePublish}
            disabled={pageMutation.isPending}
          >
            {pageMutation.isPending ? tr('Публикуем...', 'Publishing...') : tr('Сохранить и опубликовать', 'Save and publish')}
          </button>
        )}
      </div>
    </div>
  );
}

function stepTitle(step, tr) {
  return {
    1: tr('Основная информация', 'Main information'),
    2: tr('Стиль и преимущества', 'Style and advantages'),
    3: tr('Превью', 'Preview'),
    4: tr('Публикация', 'Publishing'),
  }[step];
}

function stepSubtitle(step, tr) {
  return {
    1: tr('Соберите оффер, который клиент увидит первым.', 'Create the offer clients see first.'),
    2: tr('Выберите визуальный стиль и ровно 3 преимущества.', 'Choose a visual style and exactly 3 advantages.'),
    3: tr('Проверьте, как страница выглядит на телефоне.', 'Check how the page looks on a phone.'),
    4: tr('Добавьте фото, настройте адрес и опубликуйте.', 'Add a photo, set the address and publish.'),
  }[step];
}

function buildPayload(form) {
  return {
    category_id: Number(form.category_id),
    style_id: Number(form.style_id),
    display_name: form.display_name.trim(),
    specialization: form.specialization.trim(),
    tagline: form.tagline.trim(),
    badge_text: form.badge_text.trim() || null,
    service_name: form.service_name.trim(),
    service_price: form.service_price.trim(),
    promo_text: form.promo_enabled ? (form.promo_text.trim() || null) : null,
    promo_enabled: Boolean(form.promo_enabled && form.promo_text.trim()),
    advantages: form.advantages.slice(0, 3).map((item) => ({
      text: item.text.trim(),
      icon: item.icon.trim() || null,
    })),
    sub_button_text: form.sub_button_text.trim() || EMPTY_FORM.sub_button_text,
  };
}
