import { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getServices, createOrderRequest, createQuestion } from '../api/client';
import { Skeleton } from '../components/Skeleton';

const WebApp = window.Telegram?.WebApp;

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

const DATE_MONTHS = ['января','февраля','марта','апреля','мая','июня',
  'июля','августа','сентября','октября','ноября','декабря'];

function formatDateDisplay(iso) {
  if (!iso) return 'Выберите дату';
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${DATE_MONTHS[m - 1]} ${y}`;
}

// ── File picker ───────────────────────────────────────────────────────────────

function FilePicker({ file, fileType, onFile, onRemove }) {
  const inputRef = useRef(null);

  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const isPhoto = f.type.startsWith('image/');
    const isVideo = f.type === 'video/mp4';
    if (!isPhoto && !isVideo) { alert('Только JPEG, PNG или MP4'); return; }
    if (isPhoto && f.size > 10 * 1024 * 1024) { alert('Фото до 10 МБ'); e.target.value = ''; return; }
    if (isVideo && f.size > 50 * 1024 * 1024) { alert('Видео до 50 МБ'); e.target.value = ''; return; }
    haptic();
    onFile(f, isPhoto ? 'photo' : 'video');
  };

  if (file) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px', background: 'var(--tg-surface)',
        borderRadius: 12, marginBottom: 14,
      }}>
        <span style={{ fontSize: 14, color: 'var(--tg-text)' }}>
          {fileType === 'photo' ? '🖼️' : '🎥'} {file.name}
        </span>
        <button onClick={() => { haptic(); onRemove(); }}
          style={{ background: 'none', border: 'none', color: '#e74c3c', fontSize: 13, cursor: 'pointer' }}>
          Удалить
        </button>
      </div>
    );
  }

  return (
    <>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,video/mp4"
        style={{ display: 'none' }} onChange={handleChange} />
      <button onClick={() => { haptic(); inputRef.current?.click(); }}
        style={{
          width: '100%', padding: '12px', marginBottom: 14,
          background: 'var(--tg-surface)', border: '1.5px dashed var(--tg-hint)',
          borderRadius: 12, color: 'var(--tg-hint)', fontSize: 14, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
        📎 Приложить фото или видео (необязательно)
      </button>
    </>
  );
}

// ── Booking form ──────────────────────────────────────────────────────────────

function BookingForm({ onSuccess, keyboardOpen }) {
  const [selectedService, setSelectedService] = useState(null);
  const [desiredDate, setDesiredDate] = useState('');
  const [desiredTime, setDesiredTime] = useState('');
  const [comment, setComment] = useState('');
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const { data: services = [], isLoading } = useQuery({
    queryKey: ['services'],
    queryFn: getServices,
  });

  const handleSubmit = async () => {
    if (!selectedService) { setError('Выберите услугу'); return; }
    haptic('medium');
    setError('');
    setSubmitting(true);
    try {
      await createOrderRequest({
        service_name: selectedService.name,
        comment: comment || undefined,
        desired_date: desiredDate || undefined,
        desired_time: desiredTime || undefined,
        file: file || undefined,
        media_type: fileType || undefined,
      });
      onSuccess();
    } catch {
      setError('Не удалось отправить заявку. Попробуйте ещё раз.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '0 16px 120px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: '0 0 16px' }}>
        Выберите услугу и укажите желаемое время
      </p>

      {isLoading ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} width={100} height={36} style={{ borderRadius: 20 }} />)}
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {services.map(s => {
            const sel = selectedService?.id === s.id;
            return (
              <button key={s.id} onClick={() => { haptic(); setSelectedService(s); setError(''); }}
                style={{
                  padding: '8px 14px', borderRadius: 20, fontSize: 14, cursor: 'pointer',
                  border: `1.5px solid ${sel ? 'var(--tg-button)' : 'var(--tg-hint)'}`,
                  background: sel ? 'var(--tg-button)' : 'transparent',
                  color: sel ? 'var(--tg-button-text)' : 'var(--tg-text)',
                }}>
                {s.name}{s.price ? ` · ${s.price} ₽` : ''}
              </button>
            );
          })}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, color: 'var(--tg-hint)', display: 'block', marginBottom: 4 }}>Дата (необязательно)</label>
          <div style={{ position: 'relative' }}>
            <div style={inputDisplayStyle}>{formatDateDisplay(desiredDate)}</div>
            <input type="date" value={desiredDate} onChange={e => setDesiredDate(e.target.value)}
              style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }} />
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, color: 'var(--tg-hint)', display: 'block', marginBottom: 4 }}>Время</label>
          <div style={{ position: 'relative' }}>
            <div style={inputDisplayStyle}>{desiredTime || '—'}</div>
            <input type="time" value={desiredTime} onChange={e => setDesiredTime(e.target.value)}
              style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }} />
          </div>
        </div>
      </div>

      <textarea value={comment} onChange={e => setComment(e.target.value)}
        placeholder="Адрес, пожелания..."
        rows={3}
        style={{
          width: '100%', padding: '12px 14px', marginBottom: 14,
          background: 'var(--tg-surface)', border: '1px solid var(--tg-hint)',
          borderRadius: 12, color: 'var(--tg-text)', fontSize: 15,
          resize: 'none', outline: 'none', boxSizing: 'border-box',
        }} />

      <FilePicker file={file} fileType={fileType}
        onFile={(f, t) => { setFile(f); setFileType(t); }}
        onRemove={() => { setFile(null); setFileType(null); }} />

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button onClick={handleSubmit} disabled={submitting}
        style={{
          position: 'fixed',
          bottom: keyboardOpen ? 'calc(14px + env(safe-area-inset-bottom))' : 'calc(80px + env(safe-area-inset-bottom))',
          left: 16, right: 16, padding: '14px',
          background: 'var(--tg-button)', color: 'var(--tg-button-text)',
          border: 'none', borderRadius: 12, fontSize: 16, fontWeight: 600,
          cursor: submitting ? 'default' : 'pointer', opacity: submitting ? 0.6 : 1, zIndex: 50,
        }}>
        {submitting ? 'Отправляем...' : 'Отправить заявку'}
      </button>
    </div>
  );
}

// ── Question form ─────────────────────────────────────────────────────────────

function QuestionForm({ onSuccess, keyboardOpen }) {
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!text.trim()) { setError('Напишите вопрос'); return; }
    haptic('medium');
    setError('');
    setSubmitting(true);
    try {
      await createQuestion({
        text: text.trim(),
        file: file || undefined,
        media_type: fileType || undefined,
      });
      onSuccess();
    } catch {
      setError('Не удалось отправить. Попробуйте ещё раз.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '0 16px 120px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: '0 0 16px' }}>
        Напишите вопрос — мастер ответит в Telegram
      </p>

      <textarea value={text} onChange={e => setText(e.target.value)}
        placeholder="Например: сколько стоит уборка 2-комнатной квартиры?"
        rows={5}
        style={{
          width: '100%', padding: '12px 14px', marginBottom: 14,
          background: 'var(--tg-surface)', border: '1px solid var(--tg-hint)',
          borderRadius: 12, color: 'var(--tg-text)', fontSize: 15,
          resize: 'none', outline: 'none', boxSizing: 'border-box',
        }} />

      <FilePicker file={file} fileType={fileType}
        onFile={(f, t) => { setFile(f); setFileType(t); }}
        onRemove={() => { setFile(null); setFileType(null); }} />

      {error && <p style={{ color: '#e74c3c', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      <button onClick={handleSubmit} disabled={submitting || !text.trim()}
        style={{
          position: 'fixed',
          bottom: keyboardOpen ? 'calc(14px + env(safe-area-inset-bottom))' : 'calc(80px + env(safe-area-inset-bottom))',
          left: 16, right: 16, padding: '14px',
          background: 'var(--tg-button)', color: 'var(--tg-button-text)',
          border: 'none', borderRadius: 12, fontSize: 16, fontWeight: 600,
          cursor: (submitting || !text.trim()) ? 'default' : 'pointer',
          opacity: (submitting || !text.trim()) ? 0.6 : 1, zIndex: 50,
        }}>
        {submitting ? 'Отправляем...' : 'Отправить'}
      </button>
    </div>
  );
}

// ── Success screen ────────────────────────────────────────────────────────────

function SuccessScreen({ onBack }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 24px' }}>
      <div style={{ fontSize: 56, marginBottom: 16 }}>✅</div>
      <h2 style={{ color: 'var(--tg-text)', marginBottom: 8 }}>Отправлено!</h2>
      <p style={{ color: 'var(--tg-hint)', marginBottom: 32, lineHeight: 1.5 }}>
        Мастер получил уведомление и свяжется с вами в Telegram
      </p>
      <button onClick={onBack}
        style={{
          background: 'var(--tg-button)', color: 'var(--tg-button-text)',
          border: 'none', borderRadius: 12, padding: '14px 32px',
          fontSize: 16, cursor: 'pointer',
        }}>
        На главную
      </button>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const inputDisplayStyle = {
  padding: '11px 14px', borderRadius: 12,
  border: '1px solid var(--tg-hint)', background: 'var(--tg-surface)',
  color: 'var(--tg-text)', fontSize: 15,
};

const modeCardStyle = {
  display: 'flex', alignItems: 'center', gap: 16,
  padding: '16px 20px', background: 'var(--tg-surface)',
  border: 'none', borderRadius: 16, cursor: 'pointer',
  textAlign: 'left', width: '100%',
};

// ── Root Contact page ─────────────────────────────────────────────────────────

export default function Contact({ onNavigate, keyboardOpen }) {
  const [mode, setMode] = useState(null);  // null | 'booking' | 'question'
  const [done, setDone] = useState(false);

  if (done) return <SuccessScreen onBack={() => onNavigate('home')} />;

  if (mode === 'booking') {
    return (
      <div style={{ paddingBottom: 80 }}>
        <div style={{ padding: '14px 16px 0' }}>
          <button onClick={() => { haptic(); setMode(null); }}
            style={{ background: 'none', border: 'none', color: 'var(--tg-button)', fontSize: 15, cursor: 'pointer', padding: 0 }}>
            ← Назад
          </button>
          <h2 style={{ color: 'var(--tg-text)', margin: '8px 0 16px', fontSize: 20, fontWeight: 700 }}>Записаться</h2>
        </div>
        <BookingForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} />
      </div>
    );
  }

  if (mode === 'question') {
    return (
      <div style={{ paddingBottom: 80 }}>
        <div style={{ padding: '14px 16px 0' }}>
          <button onClick={() => { haptic(); setMode(null); }}
            style={{ background: 'none', border: 'none', color: 'var(--tg-button)', fontSize: 15, cursor: 'pointer', padding: 0 }}>
            ← Назад
          </button>
          <h2 style={{ color: 'var(--tg-text)', margin: '8px 0 16px', fontSize: 20, fontWeight: 700 }}>Задать вопрос</h2>
        </div>
        <QuestionForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px 16px 80px' }}>
      <h2 style={{ color: 'var(--tg-text)', fontSize: 22, fontWeight: 700, marginBottom: 6 }}>Связаться</h2>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 24 }}>
        Выберите тип обращения
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <button onClick={() => { haptic(); setMode('booking'); }} style={modeCardStyle}>
          <span style={{ fontSize: 32 }}>📅</span>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--tg-text)', marginBottom: 2 }}>Записаться</div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>Выберите услугу и время</div>
          </div>
        </button>

        <button onClick={() => { haptic(); setMode('question'); }} style={modeCardStyle}>
          <span style={{ fontSize: 32 }}>💬</span>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--tg-text)', marginBottom: 2 }}>Задать вопрос</div>
            <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>Уточните цену или детали</div>
          </div>
        </button>
      </div>
    </div>
  );
}
