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

function ScreenHeader({ title, subtitle, onBack, backLabel }) {
  return (
    <header className="client-page-header client-contact-header">
      <div>
        {onBack && (
          <button type="button" className="client-contact-back-btn" onClick={onBack}>
            ← {backLabel}
          </button>
        )}
        <h1 className="client-page-title">{title}</h1>
        {subtitle && <p className="client-page-subtitle">{subtitle}</p>}
      </div>
    </header>
  );
}

function SubmitBar({ label, disabled, keyboardOpen, onClick }) {
  return (
    <div className={`client-contact-submit-wrap${keyboardOpen ? ' is-keyboard-open' : ''}`}>
      <button
        type="button"
        className="client-contact-submit-btn"
        disabled={disabled}
        onClick={onClick}
      >
        {label}
      </button>
    </div>
  );
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

  const openInput = () => {
    haptic();
    inputRef.current?.click();
  };

  return (
    <div className="client-contact-upload-block">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,video/mp4"
        multiple
        className="client-contact-hidden-input"
        onChange={handleChange}
      />

      {files?.length ? (
        <div className="client-card client-contact-files-card">
          <div className="client-contact-files-list">
            {files.map((f, i) => {
              const isPhoto = f.type.startsWith('image/');
              return (
                <div key={`${f.name}-${i}`} className="client-contact-file-row">
                  <span className="client-contact-file-name">
                    {isPhoto ? '🖼️' : '🎥'} {f.name}
                  </span>
                  <button type="button" className="client-contact-file-remove" onClick={() => removeFile(i)}>
                    {t('contact.filePicker.delete')}
                  </button>
                </div>
              );
            })}
          </div>

          <div className="client-contact-file-actions">
            <button type="button" className="client-contact-file-btn" onClick={openInput}>
              {t('contact.filePicker.add')}
            </button>
            <button
              type="button"
              className="client-contact-file-btn is-secondary"
              onClick={() => {
                haptic();
                onFilesChange([]);
              }}
            >
              {t('contact.filePicker.clear')}
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="client-card client-contact-upload-btn" onClick={openInput}>
          {t('contact.filePicker.attach')}
        </button>
      )}
    </div>
  );
}

function BookingForm({ onSuccess, keyboardOpen, preselectedService }) {
  const { t, locale } = useI18n();
  const [selectedService, setSelectedService] = useState(preselectedService || null);
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
    <div className="client-page client-contact-page">
      <section className="client-contact-content">
        <div className="client-contact-section">
          <p className="client-section-title">{t('contact.modes.bookingTitle')}</p>
          {isLoading ? (
            <div className="client-contact-chips">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} width={120} height={40} style={{ borderRadius: 999 }} />
              ))}
            </div>
          ) : (
            <div className="client-contact-chips">
              {services.map((s) => {
                const selected = selectedService?.id === s.id;
                return (
                  <button
                    key={s.id}
                    type="button"
                    className={`client-contact-chip${selected ? ' is-selected' : ''}`}
                    onClick={() => {
                      haptic();
                      setSelectedService(s);
                      setError('');
                    }}
                  >
                    {s.name}
                    {s.price ? ` · ${s.price} ₽` : ''}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="client-contact-grid">
          <label className="client-contact-field">
            <span className="client-contact-label">{t('contact.booking.dateLabel')}</span>
            <div className="client-contact-picker-wrap">
              <div className="client-contact-picker-display">{formatDateDisplay(desiredDate, locale, t)}</div>
              <input
                type="date"
                value={desiredDate}
                onChange={(e) => setDesiredDate(e.target.value)}
                className="client-contact-picker-input"
              />
            </div>
          </label>

          <label className="client-contact-field">
            <span className="client-contact-label">{t('contact.booking.timeLabel')}</span>
            <div className="client-contact-picker-wrap">
              <div className="client-contact-picker-display">{desiredTime || t('common.dash')}</div>
              <input
                type="time"
                value={desiredTime}
                onChange={(e) => setDesiredTime(e.target.value)}
                className="client-contact-picker-input"
              />
            </div>
          </label>
        </div>

        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder={t('contact.booking.commentPlaceholder')}
          rows={4}
          className="client-contact-textarea"
        />

        <FilePicker files={files} onFilesChange={setFiles} />

        {error && <p className="client-contact-error">{error}</p>}
      </section>

      <SubmitBar
        label={submitting ? t('contact.booking.submitting') : t('contact.booking.submit')}
        disabled={submitting}
        keyboardOpen={keyboardOpen}
        onClick={handleSubmit}
      />
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
    <div className="client-page client-contact-page">
      <section className="client-contact-content">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t('contact.question.placeholder')}
          rows={6}
          className="client-contact-textarea"
        />

        <FilePicker files={files} onFilesChange={setFiles} />

        {error && <p className="client-contact-error">{error}</p>}
      </section>

      <SubmitBar
        label={submitting ? t('contact.question.submitting') : t('contact.question.submit')}
        disabled={submitting || !text.trim()}
        keyboardOpen={keyboardOpen}
        onClick={handleSubmit}
      />
    </div>
  );
}

function SuccessScreen({ onBack }) {
  const { t } = useI18n();

  return (
    <div className="client-page client-contact-page">
      <div className="client-contact-success">
        <div className="client-contact-success-icon">✓</div>
        <h1 className="client-page-title">{t('contact.success.title')}</h1>
        <p className="client-page-subtitle client-contact-success-subtitle">{t('contact.success.subtitle')}</p>
        <button type="button" className="client-contact-success-btn" onClick={onBack}>
          {t('common.toHome')}
        </button>
      </div>
    </div>
  );
}

function ContactModeCard({ icon, title, subtitle, onClick }) {
  return (
    <button type="button" className="client-card client-contact-mode-card" onClick={onClick}>
      <span className="client-contact-mode-icon">{icon}</span>
      <span className="client-contact-mode-copy">
        <span className="client-contact-mode-title">{title}</span>
        <span className="client-contact-mode-subtitle">{subtitle}</span>
      </span>
      <span className="client-contact-mode-chevron">›</span>
    </button>
  );
}

export default function Contact({ onNavigate, keyboardOpen, preselectedService, initialMode }) {
  const { t } = useI18n();
  const [mode, setMode] = useState(initialMode || null);
  const [done, setDone] = useState(false);

  if (done) return <SuccessScreen onBack={() => onNavigate('home')} />;

  if (mode === 'booking') {
    return (
      <div className="client-page client-contact-page">
        <ScreenHeader
          title={t('contact.booking.title')}
          subtitle={t('contact.booking.hint')}
          onBack={() => {
            haptic();
            setMode(null);
          }}
          backLabel={t('common.back')}
        />
        <BookingForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} preselectedService={preselectedService} />
      </div>
    );
  }

  if (mode === 'question') {
    return (
      <div className="client-page client-contact-page">
        <ScreenHeader
          title={t('contact.question.title')}
          subtitle={t('contact.question.hint')}
          onBack={() => {
            haptic();
            setMode(null);
          }}
          backLabel={t('common.back')}
        />
        <QuestionForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} />
      </div>
    );
  }

  return (
    <div className="client-page client-contact-page">
      <ScreenHeader title={t('contact.root.title')} subtitle={t('contact.root.subtitle')} />

      <section className="client-contact-content client-contact-root-list">
        <ContactModeCard
          icon="📅"
          title={t('contact.modes.bookingTitle')}
          subtitle={t('contact.modes.bookingSubtitle')}
          onClick={() => {
            haptic();
            setMode('booking');
          }}
        />

        <ContactModeCard
          icon="💬"
          title={t('contact.modes.questionTitle')}
          subtitle={t('contact.modes.questionSubtitle')}
          onClick={() => {
            haptic();
            setMode('question');
          }}
        />
      </section>
    </div>
  );
}
