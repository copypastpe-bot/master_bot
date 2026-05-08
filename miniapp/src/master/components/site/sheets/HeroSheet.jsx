import { useRef, useState } from 'react';
import { uploadPromoPagePhoto } from '../../../../api/client';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

function absoluteUrl(url) {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return `${API_BASE}${url}`;
}

export default function HeroSheet({ data, onChange, onClose }) {
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError('');
    try {
      const result = await uploadPromoPagePhoto(file);
      if (result?.photo_url) {
        onChange('photo_url', result.photo_url);
      } else {
        setUploadError('Не удалось получить URL фото. Попробуйте ещё раз.');
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Ошибка загрузки фото';
      setUploadError(msg);
    } finally {
      setUploading(false);
      // Reset input so the same file can be re-selected if needed
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  // Always show current photo from parent state (no local copy — single source of truth)
  const photoUrl = absoluteUrl(data.photo_url);

  return (
    <div className="sheet-form">
      <div className="sheet-section-label">Фото профиля</div>

      {photoUrl && (
        <div className="hero-sheet-preview">
          <img
            key={photoUrl}
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

      {uploadError && (
        <p className="sheet-error">{uploadError}</p>
      )}

      <button
        type="button"
        className="sheet-btn sheet-btn--accent"
        onClick={() => fileRef.current?.click()}
        disabled={uploading}
      >
        {uploading ? 'Загружаю...' : photoUrl ? 'Заменить фото' : 'Выбрать фото'}
      </button>

      {photoUrl && !uploading && (
        <button
          type="button"
          className="sheet-btn sheet-btn--danger"
          onClick={() => onChange('photo_url', '')}
        >
          Удалить фото
        </button>
      )}

      <button
        type="button"
        className="sheet-btn sheet-btn--done"
        onClick={onClose}
        disabled={uploading}
      >
        {uploading ? 'Подождите...' : 'Готово'}
      </button>
    </div>
  );
}
