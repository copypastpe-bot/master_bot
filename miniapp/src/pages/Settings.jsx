import { useState, useEffect } from 'react';
import { getClientMasterSettings, patchClientMasterSettings, deleteClientProfile } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
const APP_VERSION = import.meta.env.VITE_APP_VERSION || '1.0.0';
const SUPPORT_TG = import.meta.env.VITE_SUPPORT_TG || 'crmfit_support';
const PRIVACY_URL = import.meta.env.VITE_PRIVACY_URL || 'https://crmfit.ru/privacy';

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      className={`client-toggle${checked ? ' is-checked' : ''}`}
      aria-pressed={checked}
      onClick={() => onChange(!checked)}
      disabled={disabled}
    >
      <span className="client-toggle-track" />
      <span className="client-toggle-thumb" />
    </button>
  );
}

export default function Settings({ activeMasterId, onProfileDeleted }) {
  const { t } = useI18n();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!activeMasterId) return;
    let cancelled = false;
    setSettings(null);
    setLoading(true);
    getClientMasterSettings(activeMasterId)
      .then(data => {
        if (!cancelled) setSettings(data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [activeMasterId]);

  const handleToggle = async (key, value) => {
    if (saving === key) return;
    WebApp?.HapticFeedback?.impactOccurred('light');
    setSettings(prev => ({ ...prev, [key]: value }));
    setSaving(key);
    try {
      await patchClientMasterSettings(activeMasterId, { [key]: value });
    } catch {
      setSettings(prev => ({ ...prev, [key]: !value }));
      WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setSaving(null);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteClientProfile();
      WebApp?.HapticFeedback?.notificationOccurred('success');
      onProfileDeleted?.();
    } catch {
      WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setDeleting(false);
    }
  };

  if (confirmDelete) {
    return (
      <div className="client-page" style={{ padding: '0 16px 120px' }}>
        <div className="client-tab-header">
          <span className="client-page-title">{t('settings.title')}</span>
        </div>
        <div className="client-confirm-dialog">
          <p className="client-confirm-dialog-title">{t('settings.deleteConfirmTitle')}</p>
          <p className="client-confirm-dialog-text">{t('settings.deleteConfirmText')}</p>
          <button className="client-action-btn is-primary" style={{ width: '100%', marginBottom: 10, background: '#f44336' }}
            onClick={handleDelete} disabled={deleting}>
            {deleting ? t('settings.deleting') : t('settings.deleteConfirmBtn')}
          </button>
          <button className="client-action-btn is-secondary" style={{ width: '100%' }}
            onClick={() => setConfirmDelete(false)}>
            {t('settings.deleteCancelBtn')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      <div className="client-tab-header">
        <span className="client-page-title">{t('settings.title')}</span>
      </div>

      {loading ? (
        <Skeleton height={140} style={{ marginBottom: 16, borderRadius: 12 }} />
      ) : (
        <>
          {/* Notifications */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.notificationsGroup')}</p>
            <div className="client-settings-list">
              {[
                { key: 'notify_reminders', titleKey: 'settings.notifyReminders', hintKey: 'settings.notifyRemindersHint' },
                { key: 'notify_marketing', titleKey: 'settings.notifyMarketing', hintKey: 'settings.notifyMarketingHint' },
                { key: 'notify_bonuses',   titleKey: 'settings.notifyBonuses',   hintKey: 'settings.notifyBonusesHint' },
              ].map(({ key, titleKey, hintKey }) => (
                <div key={key} className="client-settings-row">
                  <div className="client-settings-row-copy">
                    <div className="client-settings-row-title">{t(titleKey)}</div>
                    <div className="client-settings-row-hint">{t(hintKey)}</div>
                  </div>
                  <Toggle
                    checked={!!settings?.[key]}
                    onChange={v => handleToggle(key, v)}
                    disabled={saving === key}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Support */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.supportGroup')}</p>
            <div className="client-settings-list">
              <button className="client-settings-row is-link" style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => window.open(`tg://resolve?domain=${SUPPORT_TG}`, '_blank')}>
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.supportBtn')}</div>
                </div>
                <span style={{ color: 'var(--tg-theme-hint-color)' }}>›</span>
              </button>
            </div>
          </div>

          {/* About */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.aboutGroup')}</p>
            <div className="client-settings-list">
              <div className="client-settings-row">
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.versionLabel')}</div>
                </div>
                <span className="client-settings-row-value">{APP_VERSION}</span>
              </div>
              <button className="client-settings-row is-link" style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => window.open(PRIVACY_URL, '_blank')}>
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.privacyBtn')}</div>
                </div>
                <span style={{ color: 'var(--tg-theme-hint-color)' }}>›</span>
              </button>
            </div>
          </div>

          {/* Account */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.accountGroup')}</p>
            <div className="client-settings-list">
              <button className="client-settings-row is-danger is-link" style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => setConfirmDelete(true)}>
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.deleteProfile')}</div>
                </div>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
