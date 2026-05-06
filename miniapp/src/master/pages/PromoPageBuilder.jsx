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

function haptic(type = 'light') {
  WebApp?.HapticFeedback?.impactOccurred?.(type);
}

function notify(type = 'success') {
  WebApp?.HapticFeedback?.notificationOccurred?.(type);
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
  return {
    '--promo-primary': styleConfig.primary_color || '#2E7D32',
    '--promo-secondary': styleConfig.secondary_color || '#E8F5E9',
    '--promo-accent': styleConfig.accent_color || '#1B5E20',
    '--promo-text': styleConfig.text_color || '#17211B',
    '--promo-light': styleConfig.text_color_light || '#FFFFFF',
    '--promo-bg': styleConfig.bg_color || '#FFFFFF',
    '--promo-card': styleConfig.card_bg || '#F1F8E9',
    '--promo-button': styleConfig.button_bg || styleConfig.primary_color || '#2E7D32',
    '--promo-button-text': styleConfig.button_text || '#FFFFFF',
    '--promo-gradient': styleConfig.gradient || `linear-gradient(135deg, ${styleConfig.primary_color || '#2E7D32'}, ${styleConfig.accent_color || '#1B5E20'})`,
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

function PromoPreview({ form, category, style, photoPreview }) {
  const vars = styleVars(style?.config);
  const advantages = form.advantages.filter((item) => item.text.trim()).slice(0, 3);
  return (
    <div className="promo-preview-shell" style={vars}>
      <section className="promo-preview-hero">
        <div className="promo-preview-badge">{form.badge_text || category?.name || 'CRM Fit'}</div>
        <h3>{form.display_name || 'Имя мастера'}</h3>
        <p>{form.specialization || 'Специализация'}</p>
        <strong>{form.tagline || 'Короткое предложение для новых клиентов'}</strong>
        <div className="promo-preview-photo">
          {photoPreview ? <img src={photoPreview} alt="" /> : <span>Фото</span>}
        </div>
      </section>

      <section className="promo-preview-service">
        <div>
          <span>Популярная услуга</span>
          <b>{form.service_name || 'Название услуги'}</b>
        </div>
        <strong>{form.service_price || 'от 0'}</strong>
      </section>

      {form.promo_enabled && form.promo_text && (
        <section className="promo-preview-offer">{form.promo_text}</section>
      )}

      <section className="promo-preview-advantages">
        {advantages.map((item, index) => (
          <div key={`${item.text}-${index}`}>
            <span>{item.icon || '✓'}</span>
            <b>{item.text}</b>
          </div>
        ))}
      </section>

      <button type="button" className="promo-preview-cta">Забрать бонусы и подписаться</button>
      <p className="promo-preview-sub">{form.sub_button_text || EMPTY_FORM.sub_button_text}</p>
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
            category={currentCategory}
            style={currentStyle}
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
                    <span>{preset.icon || '✓'}</span>{preset.text}
                  </button>
                );
              })}
            </div>
            <div className="promo-builder-advantage-edit">
              {form.advantages.map((item, index) => (
                <Field key={index} label={tr(`Преимущество ${index + 1}`, `Advantage ${index + 1}`)} error={fieldErrors[`advantage_${index}`]}>
                  <div className="promo-builder-advantage-row">
                    <input
                      value={item.icon}
                      maxLength={4}
                      onChange={(event) => {
                        const next = [...form.advantages];
                        next[index] = { ...next[index], icon: event.target.value };
                        updateField('advantages', next);
                      }}
                      aria-label={tr('Иконка', 'Icon')}
                    />
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
          <PromoPreview form={form} category={currentCategory} style={currentStyle} photoPreview={previewUrl} />
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
