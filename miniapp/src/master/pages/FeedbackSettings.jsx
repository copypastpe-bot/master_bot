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

export default function FeedbackSettings() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [successMsg, setSuccessMsg] = useState('');

  const [delayHours, setDelayHours] = useState('3');
  const [message, setMessage] = useState('');
  const [reply5, setReply5] = useState('');
  const [buttons, setButtons] = useState([emptyButton()]);
  const [isInitialized, setIsInitialized] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['master-feedback-settings'],
    queryFn: getMasterFeedbackSettings,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!data || isInitialized) return;
    setDelayHours(String(data.feedback_delay_hours ?? 3));
    setMessage(data.feedback_message ?? '');
    setReply5(data.feedback_reply_5 ?? '');
    setButtons(normalizeButtons(data.review_buttons));
    setIsInitialized(true);
  }, [data, isInitialized]);

  const mutation = useMutation({
    mutationFn: updateMasterFeedbackSettings,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['master-feedback-settings'] });
      hapticNotify('success');
      setSuccessMsg(t('feedbackSettings.toastSaved'));
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

  if (isLoading && !isInitialized) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        {t('feedbackSettings.loading')}
      </div>
    );
  }

  return (
    <div className="enterprise-profile-page">
      {successMsg && <div className="enterprise-profile-toast">{successMsg}</div>}

      <div className="enterprise-section-title">{t('feedbackSettings.sections.delay')}</div>
      <div className="enterprise-cell-group">
        <div className="onb-field-group" style={{ padding: '0 16px 12px' }}>
          <label className="onb-label">{t('feedbackSettings.fields.delay')}</label>
          <input
            className="onb-input"
            type="number"
            min={1}
            max={72}
            value={delayHours}
            onChange={(e) => setDelayHours(e.target.value)}
          />
        </div>
      </div>

      <div className="enterprise-section-title">{t('feedbackSettings.sections.message')}</div>
      <div className="enterprise-cell-group">
        <div className="onb-field-group" style={{ padding: '0 16px 12px' }}>
          <label className="onb-label">
            {t('feedbackSettings.fields.message', {
              master_name: '{master_name}',
              service: '{service}',
            })}
          </label>
          <textarea
            className="enterprise-sheet-input"
            rows={3}
            placeholder={t('feedbackSettings.placeholders.message', {
              master_name: '{master_name}',
              service: '{service}',
            })}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
        </div>
      </div>

      <div className="enterprise-section-title">{t('feedbackSettings.sections.reply5')}</div>
      <div className="enterprise-cell-group">
        <div className="onb-field-group" style={{ padding: '0 16px 12px' }}>
          <label className="onb-label">{t('feedbackSettings.fields.reply5')}</label>
          <textarea
            className="enterprise-sheet-input"
            rows={3}
            placeholder={t('feedbackSettings.placeholders.reply5')}
            value={reply5}
            onChange={(e) => setReply5(e.target.value)}
          />
        </div>
      </div>

      <div className="enterprise-section-title">{t('feedbackSettings.sections.buttons')}</div>
      <div className="enterprise-cell-group">
        {buttons.map((btn, index) => (
          <div
            key={index}
            style={{
              padding: '8px 16px',
              borderBottom: index === buttons.length - 1 ? 'none' : '1px solid var(--tg-section-separator)',
            }}
          >
            <div className="onb-field-group">
              <label className="onb-label">{t('feedbackSettings.fields.buttonLabel', { index: index + 1 })}</label>
              <input
                className="onb-input"
                placeholder={t('feedbackSettings.placeholders.buttonLabel')}
                value={btn.label}
                onChange={(e) => updateButton(index, 'label', e.target.value)}
              />
            </div>
            <div className="onb-field-group">
              <label className="onb-label">{t('feedbackSettings.fields.buttonUrl')}</label>
              <input
                className="onb-input"
                type="url"
                placeholder={t('feedbackSettings.placeholders.buttonUrl')}
                value={btn.url}
                onChange={(e) => updateButton(index, 'url', e.target.value)}
              />
            </div>
            {buttons.length > 1 && (
              <button className="onb-btn-secondary" style={{ marginTop: 4 }} onClick={() => removeButton(index)}>
                {t('feedbackSettings.removeButton')}
              </button>
            )}
          </div>
        ))}

        {buttons.length < 3 && (
          <div style={{ padding: '8px 16px' }}>
            <button className="onb-btn-secondary" onClick={addButton}>
              {t('feedbackSettings.addButton')}
            </button>
          </div>
        )}
      </div>

      <div style={{ padding: '16px' }}>
        <button
          className="onb-btn-primary"
          onClick={handleSave}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? t('common.saving') : t('common.save')}
        </button>
      </div>
    </div>
  );
}
