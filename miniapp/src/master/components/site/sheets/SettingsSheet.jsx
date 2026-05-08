import { useState } from 'react';
import { updatePromoPageSlug, checkPromoPageSlug, publishPromoPage, unpublishPromoPage } from '../../../../api/client';

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{1,48}[a-z0-9])$/;

export default function SettingsSheet({ data, onChange, onClose }) {
  const [slug, setSlug] = useState(data.slug || '');
  const [slugError, setSlugError] = useState('');
  const [slugSaving, setSlugSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  async function handleSlugSave() {
    if (!SLUG_RE.test(slug)) {
      setSlugError('Только латиница, цифры и дефис, 3–50 символов');
      return;
    }
    setSlugSaving(true);
    setSlugError('');
    try {
      const check = await checkPromoPageSlug(slug);
      if (!check.available && slug !== data.slug) {
        setSlugError('Этот адрес уже занят');
        return;
      }
      await updatePromoPageSlug(slug);
      onChange('slug', slug);
    } catch {
      setSlugError('Ошибка сохранения');
    } finally {
      setSlugSaving(false);
    }
  }

  async function handlePublishToggle() {
    setPublishing(true);
    try {
      if (data.is_published) {
        await unpublishPromoPage();
        onChange('is_published', false);
      } else {
        await publishPromoPage();
        onChange('is_published', true);
      }
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">Адрес страницы</label>
        <div className="sheet-slug-row">
          <span className="sheet-slug-prefix">crmfit.ru/m/</span>
          <input
            className="sheet-input sheet-slug-input"
            type="text"
            value={slug}
            maxLength={50}
            placeholder="my-page"
            onChange={(e) => { setSlug(e.target.value.toLowerCase()); setSlugError(''); }}
          />
        </div>
        {slugError && <span className="sheet-error">{slugError}</span>}
        <button
          type="button"
          className="sheet-btn"
          onClick={handleSlugSave}
          disabled={slugSaving || slug === data.slug}
        >
          {slugSaving ? 'Сохраняю...' : 'Сохранить адрес'}
        </button>
      </div>

      <div className="sheet-field sheet-field--toggle">
        <label className="sheet-label">
          {data.is_published ? '✅ Страница опубликована' : '⭕ Страница скрыта'}
        </label>
        <label className="sheet-toggle">
          <input
            type="checkbox"
            checked={!!data.is_published}
            disabled={publishing}
            onChange={handlePublishToggle}
          />
          <span className="sheet-toggle__track" />
        </label>
      </div>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>

      <style>{`
        .sheet-slug-row { display: flex; align-items: center; gap: 0; }
        .sheet-slug-prefix { font-size: 14px; color: var(--tg-theme-hint-color, #999); white-space: nowrap; padding: 12px 0 12px 14px; background: var(--tg-theme-secondary-bg-color, #f4f4f4); border-radius: 12px 0 0 12px; border: 1px solid transparent; }
        .sheet-slug-input { border-radius: 0 12px 12px 0 !important; flex: 1; }
      `}</style>
    </div>
  );
}
