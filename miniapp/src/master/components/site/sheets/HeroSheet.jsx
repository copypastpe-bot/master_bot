import { useRef, useState } from 'react';
import { uploadPromoPagePhoto } from '../../../../api/client';
import { useI18n } from '../../../../i18n';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

function absoluteUrl(url, bust) {
  if (!url) return '';
  const base = url.startsWith('http') ? url : `${API_BASE}${url}`;
  const clean = base.split('?')[0];
  return bust ? `${clean}?t=${bust}` : clean;
}

export default function HeroSheet({ data, onChange, onClose, photoTs }) {
  const { tr } = useI18n();
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
        setUploadError(tr('Не удалось получить URL фото. Попробуйте ещё раз.', 'Failed to get photo URL. Please try again.'));
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || tr('Ошибка загрузки фото', 'Photo upload failed');
      setUploadError(msg);
    } finally {
      setUploading(false);
      // Reset input so the same file can be re-selected if needed
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  // Always show current photo from parent state (no local copy — single source of truth)
  const photoUrl = absoluteUrl(data.photo_url, photoTs);

  return (
    <div className="sheet-form">
      <div className="sheet-section-label">{tr('Фото профиля', 'Profile photo')}</div>

      {photoUrl && (
        <div className="hero-sheet-preview">
          <img
            key={photoUrl}
            src={photoUrl}
            alt={tr('Фото', 'Photo')}
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
        <label className="sheet-label">{tr('Бейдж (необязательно)', 'Badge (optional)')}</label>
        <input
          className="sheet-input"
          type="text"
          value={data.badge_text || ''}
          maxLength={40}
          placeholder={tr('Например: Доступно запись', 'E.g.: Booking available')}
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
        {uploading ? tr('Загружаю...', 'Uploading...') : photoUrl ? tr('Заменить фото', 'Replace photo') : tr('Выбрать фото', 'Choose photo')}
      </button>

      {photoUrl && !uploading && (
        <button
          type="button"
          className="sheet-btn sheet-btn--danger"
          onClick={() => onChange('photo_url', '')}
        >
          {tr('Удалить фото', 'Delete photo')}
        </button>
      )}

      <button
        type="button"
        className="sheet-btn sheet-btn--done"
        onClick={onClose}
        disabled={uploading}
      >
        {uploading ? tr('Подождите...', 'Please wait...') : tr('Готово', 'Done')}
      </button>
    </div>
  );
}
