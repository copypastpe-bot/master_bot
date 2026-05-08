import { useRef } from 'react';
import { uploadPromoPagePhoto } from '../../../../api/client';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

function absoluteUrl(url) {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return `${API_BASE}${url}`;
}

export default function HeroSheet({ data, onChange, onClose }) {
  const fileRef = useRef(null);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await uploadPromoPagePhoto(file);
      if (result?.photo_url) {
        onChange('photo_url', result.photo_url);
      }
    } catch {
      // silently ignore upload errors in preview context
    }
  }

  const photoUrl = absoluteUrl(data.photo_url);

  return (
    <div className="sheet-form">
      <div className="sheet-section-label">Фото профиля</div>

      {photoUrl && (
        <div className="hero-sheet-preview">
          <img
            src={photoUrl}
            alt="Фото"
            className="hero-sheet-photo"
          />
        </div>
      )}

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      <div className="sheet-field">
        <label className="sheet-label">Бейдж (необязательно)</label>
        <input
          className="sheet-input"
          type="text"
          value={data.badge_text || ''}
          maxLength={40}
          placeholder="Например: Доступно запись"
          onChange={(e) => onChange('badge_text', e.target.value)}
        />
      </div>

      <button
        type="button"
        className="sheet-btn sheet-btn--accent"
        onClick={() => fileRef.current?.click()}
      >
        {photoUrl ? 'Заменить фото' : 'Выбрать фото'}
      </button>

      {photoUrl && (
        <button
          type="button"
          className="sheet-btn sheet-btn--danger"
          onClick={() => onChange('photo_url', '')}
        >
          Удалить фото
        </button>
      )}

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>
    </div>
  );
}
