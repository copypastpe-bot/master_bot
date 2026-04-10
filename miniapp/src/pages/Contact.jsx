import { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getServices, createOrderRequest, createQuestion } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

function formatDateDisplay(iso, locale, t) {
  if (!iso) return t('contact.booking.dateEmpty');
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
}

function FilePicker({ files, onFilesChange }) {
  const { t } = useI18n();
  const inputRef = useRef(null);

  const handleChange = (e) => {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;

    const valid = [];
    for (const f of selected) {
      const isPhoto = f.type.startsWith('image/');
      const isVideo = f.type === 'video/mp4';
      if (!isPhoto && !isVideo) {
        alert(t('contact.filePicker.invalidType'));
        continue;
      }
      if (isPhoto && f.size > 10 * 1024 * 1024) {
        alert(t('contact.filePicker.photoTooLarge', { name: f.name }));
        continue;
      }
      if (isVideo && f.size > 50 * 1024 * 1024) {
        alert(t('contact.filePicker.videoTooLarge', { name: f.name }));
        continue;
      }
      valid.push(f);
    }
    if (!valid.length) {
      e.target.value = '';
      return;
    }

    haptic();
    onFilesChange([...(files || []), ...valid]);
    e.target.value = '';
  };

  const removeFile = (index) => {
    haptic();
    onFilesChange((files || []).filter((_, i) => i !== index));
  };

  if (files?.length) {
    return (
      <div
        style={{
          padding: '10px 14px',
          background: 'var(--tg-surface)',
          borderRadius: 12,
          marginBottom: 14,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {files.map((f, i) => {
            const isPhoto = f.type.startsWith('image/');
            return (
              <div key={`${f.name}-${i}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                <span style={{ fontSize: 14, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {isPhoto ? '🖼️' : '🎥'} {f.name}
                </span>
                <button
                  onClick={() => removeFile(i)}
                  style={{ background: 'none', border: 'none', color: '#e74c3c', fontSize: 13, cursor: 'pointer', flexShrink: 0 }}
                >
                  {t('contact.filePicker.delete')}
                </button>
              </div>
            );
          })}
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <button
            onClick={() => {
              haptic();
              inputRef.current?.click();
            }}
            style={{
              flex: 1,
              padding: '9px 10px',
              borderRadius: 10,
              border: '1px solid var(--tg-hint)',
              background: 'transparent',
              color: 'var(--tg-text)',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            {t('contact.filePicker.add')}
          </button>
          <button
            onClick={() => {
              haptic();
              onFilesChange([]);
            }}
            style={{
              flex: 1,
              padding: '9px 10px',
              borderRadius: 10,
              border: 'none',
              background: 'var(--tg-secondary-bg)',
              color: 'var(--tg-text)',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            {t('contact.filePicker.clear')}
          </button>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,video/mp4"
          multiple
          style={{ display: 'none' }}
          onChange={handleChange}
        />
      </div>
    );
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,video/mp4"
        multiple
        style={{ display: 'none' }}
        onChange={handleChange}
      />
      <button
        onClick={() => {
          haptic();
          inputRef.current?.click();
        }}
        style={{
          width: '100%',
          padding: '12px',
          marginBottom: 14,
          background: 'var(--tg-surface)',
          border: '1.5px dashed var(--tg-hint)',
          borderRadius: 12,
          color: 'var(--tg-hint)',
          fontSize: 14,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
        }}
      >
        {t('contact.filePicker.attach')}
      </button>
    </>
  );
}

function BookingForm({ onSuccess, keyboardOpen }) {
  const { t, locale } = useI18n();
  const [selectedService, setSelectedService] = useState(null);
  const [desiredDate, setDesiredDate] = useState('');
  const [desiredTime, setDesiredTime] = useState('');
  const [comment, setComment] = useState('');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const { data: services = [], isLoading } = useQuery({
    queryKey: ['services'],
    queryFn: getServices,
  });

  const handleSubmit = async () => {
    if (!selectedService) {
      setError(t('contact.booking.selectServiceError'));
      return;
    }
    haptic('medium');
    setError('');
    setSubmitting(true);
    try {
      await createOrderRequest({
        service_name: selectedService.name,
        comment: comment || undefined,
        desired_date: desiredDate || undefined,
        desired_time: desiredTime || undefined,
        files: files.length ? files : undefined,
      });
      onSuccess();
    } catch {
      setError(t('contact.booking.submitError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '0 16px 120px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: '0 0 16px' }}>{t('contact.booking.hint')}</p>

      {isLoading ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} width={100} height={36} style={{ borderRadius: 20 }} />)}
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {services.map((s) => {
            const sel = selectedService?.id === s.id;
            return (
              <button
                key={s.id}
                onClick={() => {
                  haptic();
                  setSelectedService(s);
                  setError('');
                }}
                style={{
                  padding: '8px 14px',
                  borderRadius: 20,
                  fontSize: 14,
                  cursor: 'pointer',
                  border: `1.5px solid ${sel ? 'var(--tg-button)' : 'var(--tg-hint)'}`,
                  background: sel ? 'var(--tg-button)' : 'transparent',
                  color: sel ? 'var(--tg-button-text)' : 'var(--tg-text)',
                }}
              >
                {s.name}{s.price ? ` · ${s.price} ₽` : ''}
              </button>
            );
          })}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, color: 'var(--tg-hint)', display: 'block', marginBottom: 4 }}>{t('contact.booking.dateLabel')}</label>
          <div style={{ position: 'relative' }}>
            <div style={inputDisplayStyle}>{formatDateDisplay(desiredDate, locale, t)}</div>
            <input
              type="date"
              value={desiredDate}
              onChange={(e) => setDesiredDate(e.target.value)}
              style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }}
            />
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, color: 'var(--tg-hint)', display: 'block', marginBottom: 4 }}>{t('contact.booking.timeLabel')}</label>
          <div style={{ position: 'relative' }}>
            <div style={inputDisplayStyle}>{desiredTime || t('common.dash')}</div>
            <input
              type="time"
              value={desiredTime}
              onChange={(e) => setDesiredTime(e.target.value)}
              style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }}
            />
          </div>
        </div>
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder={t('contact.booking.commentPlaceholder')}
        rows={3}
        style={{
          width: '100%',
          padding: '12px 14px',
          marginBottom: 14,
          background: 'var(--tg-surface)',
          border: '1px solid var(--tg-hint)',
          borderRadius: 12,
          color: 'var(--tg-text)',
          fontSize: 15,
          resize: 'none',
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />

      <FilePicker files={files} onFilesChange={setFiles} />

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={submitting}
        style={{
          position: 'fixed',
          bottom: keyboardOpen ? 'calc(14px + env(safe-area-inset-bottom))' : 'calc(80px + env(safe-area-inset-bottom))',
          left: 16,
          right: 16,
          padding: '14px',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          cursor: submitting ? 'default' : 'pointer',
          opacity: submitting ? 0.6 : 1,
          zIndex: 50,
        }}
      >
        {submitting ? t('contact.booking.submitting') : t('contact.booking.submit')}
      </button>
    </div>
  );
}

function QuestionForm({ onSuccess, keyboardOpen }) {
  const { t } = useI18n();
  const [text, setText] = useState('');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!text.trim()) {
      setError(t('contact.question.requiredError'));
      return;
    }
    haptic('medium');
    setError('');
    setSubmitting(true);
    try {
      await createQuestion({
        text: text.trim(),
        files: files.length ? files : undefined,
      });
      onSuccess();
    } catch {
      setError(t('contact.question.submitError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '0 16px 120px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: '0 0 16px' }}>{t('contact.question.hint')}</p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t('contact.question.placeholder')}
        rows={5}
        style={{
          width: '100%',
          padding: '12px 14px',
          marginBottom: 14,
          background: 'var(--tg-surface)',
          border: '1px solid var(--tg-hint)',
          borderRadius: 12,
          color: 'var(--tg-text)',
          fontSize: 15,
          resize: 'none',
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />

      <FilePicker files={files} onFilesChange={setFiles} />

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={submitting || !text.trim()}
        style={{
          position: 'fixed',
          bottom: keyboardOpen ? 'calc(14px + env(safe-area-inset-bottom))' : 'calc(80px + env(safe-area-inset-bottom))',
          left: 16,
          right: 16,
          padding: '14px',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          cursor: (submitting || !text.trim()) ? 'default' : 'pointer',
          opacity: (submitting || !text.trim()) ? 0.6 : 1,
          zIndex: 50,
        }}
      >
        {submitting ? t('contact.question.submitting') : t('contact.question.submit')}
      </button>
    </div>
  );
}

function SuccessScreen({ onBack }) {
  const { t } = useI18n();

  return (
    <div style={{ textAlign: 'center', padding: '48px 24px' }}>
      <div style={{ fontSize: 56, marginBottom: 16 }}>✅</div>
      <h2 style={{ color: 'var(--tg-text)', marginBottom: 8 }}>{t('contact.success.title')}</h2>
      <p style={{ color: 'var(--tg-hint)', marginBottom: 32, lineHeight: 1.5 }}>{t('contact.success.subtitle')}</p>
      <button
        onClick={onBack}
        style={{
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 12,
          padding: '14px 32px',
          fontSize: 16,
          cursor: 'pointer',
        }}
      >
        {t('common.toHome')}
      </button>
    </div>
  );
}

const inputDisplayStyle = {
  padding: '11px 14px',
  borderRadius: 12,
  border: '1px solid var(--tg-hint)',
  background: 'var(--tg-surface)',
  color: 'var(--tg-text)',
  fontSize: 15,
};

const modeCardStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 16,
  padding: '16px 20px',
  background: 'var(--tg-surface)',
  border: 'none',
  borderRadius: 16,
  cursor: 'pointer',
  textAlign: 'left',
  width: '100%',
};

export default function Contact({ onNavigate, keyboardOpen }) {
  const { t } = useI18n();
  const [mode, setMode] = useState(null);
  const [done, setDone] = useState(false);

  if (done) return <SuccessScreen onBack={() => onNavigate('home')} />;

  if (mode === 'booking') {
    return (
      <div style={{ paddingBottom: 80 }}>
        <div style={{ padding: '14px 16px 0' }}>
          <button
            onClick={() => {
              haptic();
              setMode(null);
            }}
            style={{ background: 'none', border: 'none', color: 'var(--tg-button)', fontSize: 15, cursor: 'pointer', padding: 0 }}
          >
            ← {t('common.back')}
          </button>
          <h2 style={{ color: 'var(--tg-text)', margin: '8px 0 16px', fontSize: 20, fontWeight: 700 }}>
            {t('contact.booking.title')}
          </h2>
        </div>
        <BookingForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} />
      </div>
    );
  }

  if (mode === 'question') {
    return (
      <div style={{ paddingBottom: 80 }}>
        <div style={{ padding: '14px 16px 0' }}>
          <button
            onClick={() => {
              haptic();
              setMode(null);
            }}
            style={{ background: 'none', border: 'none', color: 'var(--tg-button)', fontSize: 15, cursor: 'pointer', padding: 0 }}
          >
            ← {t('common.back')}
          </button>
          <h2 style={{ color: 'var(--tg-text)', margin: '8px 0 16px', fontSize: 20, fontWeight: 700 }}>
            {t('contact.question.title')}
          </h2>
        </div>
        <QuestionForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px 16px 80px' }}>
      <h2 style={{ color: 'var(--tg-text)', fontSize: 22, fontWeight: 700, marginBottom: 6 }}>{t('contact.root.title')}</h2>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 24 }}>{t('contact.root.subtitle')}</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <button onClick={() => { haptic(); setMode('booking'); }} style={modeCardStyle}>
          <span style={{ fontSize: 32 }}>📅</span>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--tg-text)', marginBottom: 2 }}>{t('contact.modes.bookingTitle')}</div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>{t('contact.modes.bookingSubtitle')}</div>
          </div>
        </button>

        <button onClick={() => { haptic(); setMode('question'); }} style={modeCardStyle}>
          <span style={{ fontSize: 32 }}>💬</span>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--tg-text)', marginBottom: 2 }}>{t('contact.modes.questionTitle')}</div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>{t('contact.modes.questionSubtitle')}</div>
          </div>
        </button>
      </div>
    </div>
  );
}
