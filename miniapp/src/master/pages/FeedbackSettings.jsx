import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getMasterFeedbackSettings, updateMasterFeedbackSettings } from '../../api/client';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

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

function emptyButton() {
  return { label: '', url: '' };
}

function normalizeButtons(buttons) {
  if (!Array.isArray(buttons) || buttons.length === 0) return [emptyButton()];
  return buttons.slice(0, 3).map((item) => ({
    label: String(item?.label || ''),
    url: String(item?.url || ''),
  }));
}

function snapshotState({ delayHours, message, reply5, buttons }) {
  return JSON.stringify({
    delayHours: String(delayHours || ''),
    message: String(message || ''),
    reply5: String(reply5 || ''),
    buttons: normalizeButtons(buttons).map((btn) => ({
      label: String(btn.label || ''),
      url: String(btn.url || ''),
    })),
  });
}

function previewText(value, fallback) {
  return String(value || '').trim() || fallback;
}

export default function FeedbackSettings() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [successMsg, setSuccessMsg] = useState('');

  const [delayHours, setDelayHours] = useState('3');
  const [message, setMessage] = useState('');
  const [reply5, setReply5] = useState('');
  const [buttons, setButtons] = useState([emptyButton()]);
  const [isInitialized, setIsInitialized] = useState(false);
  const [initialSnapshot, setInitialSnapshot] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['master-feedback-settings'],
    queryFn: getMasterFeedbackSettings,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!data || isInitialized) return;
    const nextState = {
      delayHours: String(data.feedback_delay_hours ?? 3),
      message: data.feedback_message ?? '',
      reply5: data.feedback_reply_5 ?? '',
      buttons: normalizeButtons(data.review_buttons),
    };
    setDelayHours(nextState.delayHours);
    setMessage(nextState.message);
    setReply5(nextState.reply5);
    setButtons(nextState.buttons);
    setInitialSnapshot(snapshotState(nextState));
    setIsInitialized(true);
  }, [data, isInitialized]);

  const mutation = useMutation({
    mutationFn: updateMasterFeedbackSettings,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-feedback-settings'] });
      hapticNotify('success');
      setSuccessMsg(t('feedbackSettings.toastSaved'));
      setInitialSnapshot(snapshotState({ delayHours, message, reply5, buttons }));
      setTimeout(() => setSuccessMsg(''), 1800);
    },
    onError: (error) => {
      hapticNotify('error');
      const detail = error?.response?.data?.detail;
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(typeof detail === 'string' ? detail : t('feedbackSettings.errorSave'));
      }
    },
  });

  const addButton = () => {
    if (buttons.length >= 3) return;
    haptic();
    setButtons((prev) => [...prev, emptyButton()]);
  };

  const removeButton = (index) => {
    haptic();
    setButtons((prev) => {
      const next = prev.filter((_, idx) => idx !== index);
      return next.length ? next : [emptyButton()];
    });
  };

  const updateButton = (index, field, value) => {
    setButtons((prev) => prev.map((btn, idx) => (idx === index ? { ...btn, [field]: value } : btn)));
  };

  const insertVariable = (token) => {
    haptic();
    setMessage((prev) => `${prev}${prev && !prev.endsWith(' ') ? ' ' : ''}${token}`);
  };

  const handleSave = () => {
    haptic('medium');

    const parsedDelay = Number.parseInt(delayHours, 10);
    const normalizedDelay = Number.isNaN(parsedDelay) ? 3 : Math.max(1, Math.min(72, parsedDelay));

    const normalizedButtons = buttons
      .map((btn) => ({ label: btn.label.trim(), url: btn.url.trim() }))
      .filter((btn) => btn.label && btn.url);

    mutation.mutate({
      feedback_delay_hours: normalizedDelay,
      feedback_message: message.trim() || null,
      feedback_reply_5: reply5.trim() || null,
      review_buttons: normalizedButtons.length ? normalizedButtons : null,
    });
  };

  const normalizedDelay = Number.isNaN(Number.parseInt(delayHours, 10)) ? 3 : Math.max(1, Math.min(72, Number.parseInt(delayHours, 10)));
  const activeButtons = buttons
    .map((btn) => ({ label: btn.label.trim(), url: btn.url.trim() }))
    .filter((btn) => btn.label && btn.url);
  const isDirty = isInitialized && initialSnapshot !== snapshotState({ delayHours, message, reply5, buttons });
  const statusTone = mutation.isPending ? 'is-saving' : isDirty ? 'is-dirty' : 'is-saved';
  const statusLabel = mutation.isPending
    ? t('common.saving')
    : isDirty
      ? t('feedbackSettings.unsaved')
      : t('feedbackSettings.savedState');
  const requestPreview = previewText(
    message,
    t('feedbackSettings.placeholders.message', {
      master_name: '{master_name}',
      service: '{service}',
    }),
  );
  const replyPreview = previewText(reply5, t('feedbackSettings.placeholders.reply5'));
  const variableTokens = ['{master_name}', '{service}'];

  if (isLoading && !isInitialized) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        {t('feedbackSettings.loading')}
      </div>
    );
  }

  return (
    <div className="enterprise-feedback-page">
      {successMsg && <div className="enterprise-profile-toast">{successMsg}</div>}

      <div className="enterprise-feedback-hero">
        <div className="enterprise-feedback-hero-copy">
          <div className="enterprise-feedback-eyebrow">{t('feedbackSettings.eyebrow')}</div>
          <h2 className="enterprise-feedback-title">{t('feedbackSettings.title')}</h2>
          <p className="enterprise-feedback-subtitle">{t('feedbackSettings.subtitle')}</p>
        </div>
        <div className={`enterprise-feedback-status ${statusTone}`}>
          {statusLabel}
        </div>
      </div>

      <section className="enterprise-feedback-card">
        <div className="enterprise-feedback-card-head">
          <div>
            <div className="enterprise-feedback-card-title">{t('feedbackSettings.sections.delay')}</div>
            <div className="enterprise-feedback-card-subtitle">{t('feedbackSettings.helpers.delay')}</div>
          </div>
        </div>
        <div className="enterprise-feedback-grid">
          <div className="enterprise-feedback-field">
            <label className="enterprise-feedback-label">{t('feedbackSettings.fields.delay')}</label>
            <input
              className="enterprise-input enterprise-feedback-input"
              type="number"
              min={1}
              max={72}
              value={delayHours}
              onChange={(e) => setDelayHours(e.target.value)}
            />
            <div className="enterprise-feedback-helper">
              {t('feedbackSettings.helpers.delayHint', { count: normalizedDelay })}
            </div>
          </div>
        </div>
      </section>

      <section className="enterprise-feedback-card">
        <div className="enterprise-feedback-card-head">
          <div>
            <div className="enterprise-feedback-card-title">{t('feedbackSettings.sections.message')}</div>
            <div className="enterprise-feedback-card-subtitle">{t('feedbackSettings.helpers.message')}</div>
          </div>
        </div>
        <div className="enterprise-feedback-field">
          <label className="enterprise-feedback-label">
            {t('feedbackSettings.fields.message', {
              master_name: '{master_name}',
              service: '{service}',
            })}
          </label>
          <textarea
            className="enterprise-input enterprise-feedback-textarea"
            rows={4}
            placeholder={t('feedbackSettings.placeholders.message', {
              master_name: '{master_name}',
              service: '{service}',
            })}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <div className="enterprise-feedback-chip-row">
            {variableTokens.map((token) => (
              <button
                key={token}
                type="button"
                className="enterprise-feedback-chip"
                onClick={() => insertVariable(token)}
              >
                {token}
              </button>
            ))}
          </div>
          <div className="enterprise-feedback-helper enterprise-feedback-meta-row">
            <span>{t('feedbackSettings.helpers.messageHint')}</span>
            <span>{message.trim().length}</span>
          </div>
        </div>
      </section>

      <section className="enterprise-feedback-card">
        <div className="enterprise-feedback-card-head">
          <div>
            <div className="enterprise-feedback-card-title">{t('feedbackSettings.sections.reply5')}</div>
            <div className="enterprise-feedback-card-subtitle">{t('feedbackSettings.helpers.reply5')}</div>
          </div>
        </div>
        <div className="enterprise-feedback-field">
          <label className="enterprise-feedback-label">{t('feedbackSettings.fields.reply5')}</label>
          <textarea
            className="enterprise-input enterprise-feedback-textarea"
            rows={4}
            placeholder={t('feedbackSettings.placeholders.reply5')}
            value={reply5}
            onChange={(e) => setReply5(e.target.value)}
          />
          <div className="enterprise-feedback-helper enterprise-feedback-meta-row">
            <span>{t('feedbackSettings.helpers.reply5Hint')}</span>
            <span>{reply5.trim().length}</span>
          </div>
        </div>
      </section>

      <section className="enterprise-feedback-card">
        <div className="enterprise-feedback-card-head">
          <div>
            <div className="enterprise-feedback-card-title">{t('feedbackSettings.sections.buttons')}</div>
            <div className="enterprise-feedback-card-subtitle">{t('feedbackSettings.helpers.buttons')}</div>
          </div>
          <div className="enterprise-feedback-badge">{activeButtons.length}/3</div>
        </div>
        <div className="enterprise-feedback-button-list">
          {buttons.map((btn, index) => (
            <div
              key={index}
              className="enterprise-feedback-link-card"
            >
              <div className="enterprise-feedback-link-card-head">
                <div className="enterprise-feedback-link-card-title">
                  {t('feedbackSettings.buttonCardTitle', { index: index + 1 })}
                </div>
                {buttons.length > 1 && (
                  <button
                    type="button"
                    className="enterprise-feedback-link-remove"
                    onClick={() => removeButton(index)}
                  >
                    {t('feedbackSettings.removeButton')}
                  </button>
                )}
              </div>
              <label className="enterprise-feedback-label">{t('feedbackSettings.fields.buttonLabel', { index: index + 1 })}</label>
              <input
                className="enterprise-input enterprise-feedback-input"
                placeholder={t('feedbackSettings.placeholders.buttonLabel')}
                value={btn.label}
                onChange={(e) => updateButton(index, 'label', e.target.value)}
              />
              <label className="enterprise-feedback-label">{t('feedbackSettings.fields.buttonUrl')}</label>
              <input
                className="enterprise-input enterprise-feedback-input"
                type="url"
                placeholder={t('feedbackSettings.placeholders.buttonUrl')}
                value={btn.url}
                onChange={(e) => updateButton(index, 'url', e.target.value)}
              />
              <div className="enterprise-feedback-helper">{t('feedbackSettings.helpers.buttonUrl')}</div>
            </div>
          ))}
        </div>

        {buttons.length < 3 && (
          <div className="enterprise-feedback-add-wrap">
            <button type="button" className="enterprise-btn-secondary" onClick={addButton}>
              {t('feedbackSettings.addButton')}
            </button>
          </div>
        )}
      </section>

      <section className="enterprise-feedback-card">
        <div className="enterprise-feedback-card-head">
          <div>
            <div className="enterprise-feedback-card-title">{t('feedbackSettings.previewTitle')}</div>
            <div className="enterprise-feedback-card-subtitle">{t('feedbackSettings.previewSubtitle')}</div>
          </div>
        </div>
        <div className="enterprise-feedback-preview-wrap">
          <div className="enterprise-feedback-preview-card">
            <div className="enterprise-feedback-preview-label">{t('feedbackSettings.sections.message')}</div>
            <div className="enterprise-feedback-preview-text">{requestPreview}</div>
            {activeButtons.length > 0 && (
              <div className="enterprise-feedback-preview-buttons">
                {activeButtons.map((btn, index) => (
                  <div key={`${btn.label}-${index}`} className="enterprise-feedback-preview-button">
                    {btn.label}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="enterprise-feedback-preview-card is-secondary">
            <div className="enterprise-feedback-preview-label">{t('feedbackSettings.sections.reply5')}</div>
            <div className="enterprise-feedback-preview-text">{replyPreview}</div>
          </div>
        </div>
      </section>

      <div className="enterprise-feedback-actions">
        <div className={`enterprise-feedback-status ${statusTone}`}>
          {statusLabel}
        </div>
        <button
          className="enterprise-btn-primary"
          onClick={handleSave}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? t('common.saving') : t('common.save')}
        </button>
      </div>
    </div>
  );
}
