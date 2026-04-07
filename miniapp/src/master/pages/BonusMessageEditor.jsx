import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteMasterBonusPhoto,
  getMasterBonusSettings,
  updateMasterBonusSettings,
  uploadMasterBonusPhoto,
} from '../../api/client';

const WebApp = window.Telegram?.WebApp;
const API_URL = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

function hapticNotify(type = 'success') {
  if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
    WebApp.HapticFeedback.notificationOccurred(type);
  }
}

function toAbsoluteMediaUrl(url) {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `${API_URL}${url}`;
}

const TITLE = {
  welcome: 'Приветствие',
  birthday: 'Поздравление с ДР',
};

const SAMPLE_DEFAULT = {
  welcome: 'Привет, {name}! Ваш бонус: {inv_bonus}',
  birthday: 'С днём рождения, {name}! Подарок: {bd_bonus}',
};

function applyPreview(template, settings, kind) {
  const source = (template || '').trim() || SAMPLE_DEFAULT[kind] || SAMPLE_DEFAULT.welcome;
  return source
    .replaceAll('{name}', 'Анна')
    .replaceAll('{inv_bonus}', String(settings?.bonus_welcome ?? 0))
    .replaceAll('{bd_bonus}', String(settings?.bonus_birthday ?? 0));
}

export default function BonusMessageEditor({ kind = 'welcome' }) {
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const textareaRef = useRef(null);

  const [text, setText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [toast, setToast] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['master-bonus-settings'],
    queryFn: getMasterBonusSettings,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!data) return;
    const field = kind === 'birthday' ? 'birthday_message' : 'welcome_message';
    setText(data[field] || '');
  }, [data, kind]);

  const existingPhotoUrlRaw = kind === 'birthday' ? data?.birthday_photo_url : data?.welcome_photo_url;
  const existingPhotoUrl = toAbsoluteMediaUrl(existingPhotoUrlRaw);

  const localPreviewUrl = useMemo(
    () => (selectedFile ? URL.createObjectURL(selectedFile) : null),
    [selectedFile],
  );

  useEffect(() => {
    return () => {
      if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    };
  }, [localPreviewUrl]);

  const previewImage = removePhoto ? null : (localPreviewUrl || existingPhotoUrl || null);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const field = kind === 'birthday' ? 'birthday_message' : 'welcome_message';
      await updateMasterBonusSettings({ [field]: text.trim() || null });

      if (removePhoto) {
        await deleteMasterBonusPhoto(kind);
      }
      if (selectedFile) {
        await uploadMasterBonusPhoto(kind, selectedFile);
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['master-bonus-settings'] });
      setSelectedFile(null);
      setRemovePhoto(false);
      setToast('Сохранено ✓');
      hapticNotify('success');
      setTimeout(() => setToast(''), 1800);
    },
    onError: () => {
      hapticNotify('error');
    },
  });

  const insertToken = (token) => {
    haptic();
    const node = textareaRef.current;
    if (!node) {
      setText((prev) => `${prev}${token}`);
      return;
    }
    const start = node.selectionStart ?? text.length;
    const end = node.selectionEnd ?? text.length;
    const next = `${text.slice(0, start)}${token}${text.slice(end)}`;
    setText(next);
    requestAnimationFrame(() => {
      node.focus();
      const caret = start + token.length;
      node.setSelectionRange(caret, caret);
    });
  };

  const onPickImage = () => {
    haptic();
    if (fileRef.current) fileRef.current.click();
  };

  const onFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setRemovePhoto(false);
  };

  const onRemoveImage = () => {
    haptic();
    setSelectedFile(null);
    setRemovePhoto(true);
    if (fileRef.current) fileRef.current.value = '';
  };

  if (isLoading || !data) {
    return <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>Загрузка...</div>;
  }

  const previewText = applyPreview(text, data, kind);

  return (
    <div style={{ padding: '16px 16px 88px' }}>
      {toast && (
        <div style={{
          position: 'fixed', top: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--tg-accent)', color: '#fff',
          padding: '8px 20px', borderRadius: 20, fontSize: 13, fontWeight: 500,
          zIndex: 300, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}>
          {toast}
        </div>
      )}

      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 6 }}>
        {TITLE[kind] || 'Сообщение'}
      </div>
      <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 12 }}>
        Если поле пустое, используется стандартный текст бота.
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
        {['{name}', '{inv_bonus}', '{bd_bonus}'].map((token) => (
          <button
            key={token}
            onClick={() => insertToken(token)}
            style={{
              border: '1px solid var(--tg-secondary-bg)',
              background: 'var(--tg-section-bg)',
              color: 'var(--tg-text)',
              borderRadius: 8,
              fontSize: 12,
              padding: '6px 10px',
              cursor: 'pointer',
            }}
          >
            {token}
          </button>
        ))}
      </div>

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Введите текст сообщения"
        rows={8}
        style={{
          width: '100%',
          boxSizing: 'border-box',
          borderRadius: 12,
          border: '1px solid var(--tg-secondary-bg)',
          background: 'var(--tg-section-bg)',
          color: 'var(--tg-text)',
          fontSize: 14,
          lineHeight: 1.45,
          padding: '12px',
          resize: 'vertical',
          minHeight: 160,
          marginBottom: 14,
        }}
      />

      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--tg-hint)', marginBottom: 8 }}>
        Изображение
      </div>

      {previewImage ? (
        <img
          src={previewImage}
          alt="preview"
          style={{ width: '100%', maxHeight: 220, objectFit: 'cover', borderRadius: 12, border: '1px solid var(--tg-secondary-bg)', marginBottom: 10 }}
        />
      ) : (
        <div style={{
          border: '1px dashed var(--tg-secondary-bg)',
          borderRadius: 12,
          padding: '18px 12px',
          textAlign: 'center',
          color: 'var(--tg-hint)',
          fontSize: 13,
          marginBottom: 10,
          background: 'var(--tg-section-bg)',
        }}>
          Изображение не добавлено
        </div>
      )}

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        onChange={onFileChange}
        style={{ display: 'none' }}
      />

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button onClick={onPickImage} style={btnSecondary}>Выбрать изображение</button>
        {(previewImage || selectedFile || existingPhotoUrl) && (
          <button onClick={onRemoveImage} style={btnDangerGhost}>Удалить</button>
        )}
      </div>

      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--tg-hint)', marginBottom: 6 }}>
        Предпросмотр
      </div>
      <div style={{
        whiteSpace: 'pre-wrap',
        background: 'var(--tg-section-bg)',
        border: '1px solid var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: '12px',
        color: 'var(--tg-text)',
        fontSize: 14,
        lineHeight: 1.45,
      }}>
        {previewText}
      </div>

      <button
        onClick={() => { haptic('medium'); saveMutation.mutate(); }}
        disabled={saveMutation.isPending}
        style={{ ...btnPrimary, width: '100%', marginTop: 16, opacity: saveMutation.isPending ? 0.7 : 1 }}
      >
        {saveMutation.isPending ? 'Сохраняем...' : 'Сохранить'}
      </button>
    </div>
  );
}

const btnPrimary = {
  padding: '12px 16px',
  borderRadius: 10,
  background: 'var(--tg-accent)',
  color: '#fff',
  fontWeight: 600,
  fontSize: 14,
  border: 'none',
  cursor: 'pointer',
};

const btnSecondary = {
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'var(--tg-section-bg)',
  color: 'var(--tg-text)',
  fontSize: 13,
  cursor: 'pointer',
};

const btnDangerGhost = {
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'var(--tg-section-bg)',
  color: 'var(--tg-destructive, #e53935)',
  fontSize: 13,
  cursor: 'pointer',
};
