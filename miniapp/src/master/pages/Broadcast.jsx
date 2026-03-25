import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getBroadcastSegments, previewBroadcast, sendBroadcast } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const MAX_TEXT = 1000;

// ─── Progress bar ─────────────────────────────────────────────────────────────

function ProgressBar({ step }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '12px 16px',
    }}>
      {[1, 2, 3].map((s) => (
        <div
          key={s}
          style={{
            width: s === step ? 24 : 8,
            height: 8,
            borderRadius: 4,
            background: s <= step ? 'var(--tg-button)' : 'var(--tg-hint)',
            opacity: s < step ? 0.45 : 1,
            transition: 'all 0.25s ease',
          }}
        />
      ))}
    </div>
  );
}

// ─── Back button ──────────────────────────────────────────────────────────────

function BackBtn({ onClick }) {
  return (
    <button
      onClick={() => { haptic(); onClick(); }}
      style={{
        background: 'none',
        border: 'none',
        color: 'var(--tg-button)',
        fontSize: 15,
        cursor: 'pointer',
        padding: '4px 0',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
      }}
    >
      ← Назад
    </button>
  );
}

// ─── Step 1: Segment selection ────────────────────────────────────────────────

function StepSegment({ segments, selected, onSelect, onNext }) {
  return (
    <div style={{ padding: '0 16px 80px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 13, margin: '0 0 12px' }}>
        Выберите аудиторию
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {segments.map((seg) => {
          const isActive = selected === seg.id;
          return (
            <button
              key={seg.id}
              onClick={() => { haptic(); onSelect(seg.id); }}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 14px',
                background: isActive ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                color: isActive ? 'var(--tg-button-text)' : 'var(--tg-text)',
                border: isActive ? 'none' : '1px solid transparent',
                borderRadius: 12,
                cursor: 'pointer',
                fontSize: 15,
                textAlign: 'left',
                transition: 'background 0.15s',
              }}
            >
              <span>{seg.name}</span>
              <span style={{
                fontSize: 13,
                opacity: 0.75,
                fontWeight: 600,
                marginLeft: 8,
              }}>
                {seg.count}
              </span>
            </button>
          );
        })}
      </div>

      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px', background: 'var(--tg-bg)' }}>
        <button
          onClick={() => { haptic(); onNext(); }}
          disabled={!selected}
          style={{
            width: '100%',
            padding: '14px',
            background: selected ? 'var(--tg-button)' : 'var(--tg-hint)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: selected ? 'pointer' : 'default',
            opacity: selected ? 1 : 0.5,
          }}
        >
          Далее
        </button>
      </div>
    </div>
  );
}

// ─── Step 2: Text input ───────────────────────────────────────────────────────

function StepText({ text, onTextChange, onNext }) {
  const remaining = MAX_TEXT - text.length;
  const canContinue = text.trim().length > 0 && text.length <= MAX_TEXT;

  return (
    <div style={{ padding: '0 16px 80px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 13, margin: '0 0 4px' }}>
        Текст сообщения
      </p>
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 10px' }}>
        Используйте <code style={{ background: 'var(--tg-secondary-bg)', padding: '1px 4px', borderRadius: 4 }}>{'{name}'}</code> — вставит имя клиента
      </p>

      <textarea
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder="Введите текст рассылки..."
        autoFocus
        rows={8}
        style={{
          width: '100%',
          padding: '12px',
          fontSize: 15,
          background: 'var(--tg-secondary-bg)',
          color: 'var(--tg-text)',
          border: remaining < 0 ? '1.5px solid #e74c3c' : '1px solid var(--tg-hint)',
          borderRadius: 12,
          outline: 'none',
          resize: 'none',
          boxSizing: 'border-box',
          lineHeight: 1.5,
        }}
        maxLength={MAX_TEXT + 50}
      />

      <div style={{
        textAlign: 'right',
        fontSize: 12,
        color: remaining < 0 ? '#e74c3c' : remaining < 100 ? '#e67e22' : 'var(--tg-hint)',
        marginTop: 4,
      }}>
        {remaining < 0 ? `Превышено на ${-remaining}` : `Осталось ${remaining}`}
      </div>

      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px', background: 'var(--tg-bg)' }}>
        <button
          onClick={() => { haptic(); onNext(); }}
          disabled={!canContinue}
          style={{
            width: '100%',
            padding: '14px',
            background: canContinue ? 'var(--tg-button)' : 'var(--tg-hint)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: canContinue ? 'pointer' : 'default',
            opacity: canContinue ? 1 : 0.5,
          }}
        >
          Предпросмотр
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Preview & send ───────────────────────────────────────────────────

function StepPreview({ segment, text, previewData, isLoading, onSend, isSending }) {
  const { recipients_count = 0, preview_text = '', sample_recipients = [] } = previewData || {};

  // Show Telegram MainButton on this step only
  useEffect(() => {
    if (!WebApp?.MainButton) return;

    if (isSending) {
      WebApp.MainButton.showProgress(false);
      return;
    }

    WebApp.MainButton.setText(`Отправить ${recipients_count} клиентам`);
    WebApp.MainButton.color = WebApp.themeParams?.button_color || '#2481cc';
    WebApp.MainButton.textColor = WebApp.themeParams?.button_text_color || '#ffffff';
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(onSend);

    return () => {
      WebApp.MainButton.offClick(onSend);
      WebApp.MainButton.hide();
      if (WebApp.MainButton.isProgressVisible) {
        WebApp.MainButton.hideProgress();
      }
    };
  }, [recipients_count, isSending, onSend]);

  if (isLoading) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        Загрузка предпросмотра...
      </div>
    );
  }

  return (
    <div style={{ padding: '0 16px 100px' }}>
      {/* Recipient count */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '12px 14px',
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        marginBottom: 12,
      }}>
        <span style={{ fontSize: 22 }}>👥</span>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--tg-text)' }}>
            {recipients_count} получателей
          </div>
          {sample_recipients.length > 0 && (
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
              {sample_recipients.join(', ')}{recipients_count > 3 ? ` и ещё ${recipients_count - 3}` : ''}
            </div>
          )}
        </div>
      </div>

      {/* Preview message */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 13, margin: '0 0 6px' }}>
        Пример сообщения
      </p>
      <div style={{
        padding: '12px 14px',
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        fontSize: 14,
        color: 'var(--tg-text)',
        lineHeight: 1.55,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {preview_text || text}
      </div>

      {recipients_count === 0 && (
        <div style={{
          marginTop: 16,
          padding: '12px 14px',
          background: 'var(--tg-secondary-bg)',
          borderRadius: 12,
          color: 'var(--tg-hint)',
          fontSize: 14,
          textAlign: 'center',
        }}>
          В этом сегменте нет клиентов с включёнными уведомлениями
        </div>
      )}
    </div>
  );
}

// ─── Success screen ───────────────────────────────────────────────────────────

function SuccessScreen({ result, onReset }) {
  const { sent_count = 0, failed_count = 0 } = result;
  const total = sent_count + failed_count;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      textAlign: 'center',
      gap: 16,
    }}>
      <div style={{ fontSize: 56 }}>✅</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--tg-text)' }}>
        Рассылка отправлена
      </div>
      <div style={{
        padding: '16px 20px',
        background: 'var(--tg-secondary-bg)',
        borderRadius: 14,
        width: '100%',
        maxWidth: 300,
      }}>
        <div style={{ fontSize: 15, color: 'var(--tg-text)', marginBottom: 8 }}>
          Отправлено: <strong>{sent_count}</strong> из <strong>{total}</strong>
        </div>
        {failed_count > 0 && (
          <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
            Не доставлено: {failed_count}
          </div>
        )}
      </div>
      <button
        onClick={() => { haptic(); onReset(); }}
        style={{
          marginTop: 8,
          padding: '12px 32px',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 12,
          fontSize: 15,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Новая рассылка
      </button>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Broadcast() {
  const [step, setStep] = useState(1);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [text, setText] = useState('');
  const [sendResult, setSendResult] = useState(null);

  // Load segments on mount
  const {
    data: segmentsData,
    isLoading: segmentsLoading,
    isError: segmentsError,
  } = useQuery({
    queryKey: ['broadcast-segments'],
    queryFn: getBroadcastSegments,
    staleTime: 60 * 1000,
  });

  const segments = segmentsData?.segments || [];

  // Preview query — runs when entering step 3
  const {
    data: previewData,
    isLoading: previewLoading,
    refetch: refetchPreview,
  } = useQuery({
    queryKey: ['broadcast-preview', selectedSegment, text],
    queryFn: () => previewBroadcast({ segment: selectedSegment, text }),
    enabled: step === 3 && !!selectedSegment && text.trim().length > 0,
    staleTime: 0,
  });

  // Send mutation
  const sendMutation = useMutation({
    mutationFn: sendBroadcast,
    onSuccess: (data) => {
      setSendResult(data);
      if (typeof WebApp?.MainButton?.hideProgress === 'function') {
        WebApp.MainButton.hideProgress();
      }
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
    },
    onError: (err) => {
      if (typeof WebApp?.MainButton?.hideProgress === 'function') {
        WebApp.MainButton.hideProgress();
      }
      const msg = err?.response?.data?.detail || 'Ошибка отправки';
      alert(msg);
    },
  });

  // Hide MainButton when not on step 3
  useEffect(() => {
    if (step !== 3 && !sendResult) {
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
    }
  }, [step, sendResult]);

  const handleSend = () => {
    haptic();
    if (!selectedSegment || !text.trim()) return;
    sendMutation.mutate({ segment: selectedSegment, text });
  };

  const handleReset = () => {
    setStep(1);
    setSelectedSegment(null);
    setText('');
    setSendResult(null);
  };

  // Success screen
  if (sendResult) {
    return <SuccessScreen result={sendResult} onReset={handleReset} />;
  }

  const stepTitle = step === 1 ? 'Аудитория' : step === 2 ? 'Текст' : 'Предпросмотр';

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  return (
    <div>
      {/* Header */}
      <div style={{ padding: '12px 16px 0' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}>
          {step > 1 ? (
            <BackBtn onClick={handleBack} />
          ) : (
            <div style={{ width: 60 }} />
          )}
          <h2 style={{
            margin: 0,
            fontSize: 17,
            fontWeight: 700,
            color: 'var(--tg-text)',
            textAlign: 'center',
            flex: 1,
          }}>
            {stepTitle}
          </h2>
          <div style={{ width: 60 }} />
        </div>

        <ProgressBar step={step} />
      </div>

      {/* Step content */}
      {step === 1 && (
        segmentsLoading ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Загрузка...
          </div>
        ) : segmentsError ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Ошибка загрузки сегментов
          </div>
        ) : (
          <StepSegment
            segments={segments}
            selected={selectedSegment}
            onSelect={setSelectedSegment}
            onNext={() => setStep(2)}
          />
        )
      )}

      {step === 2 && (
        <StepText
          text={text}
          onTextChange={setText}
          onNext={() => setStep(3)}
        />
      )}

      {step === 3 && (
        <StepPreview
          segment={selectedSegment}
          text={text}
          previewData={previewData}
          isLoading={previewLoading}
          onSend={handleSend}
          isSending={sendMutation.isPending}
        />
      )}
    </div>
  );
}
