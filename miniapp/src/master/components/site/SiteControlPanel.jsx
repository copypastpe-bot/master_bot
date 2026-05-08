import { useState } from 'react';

const WebApp = window.Telegram?.WebApp;
const API_BASE = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

export default function SiteControlPanel({ data, isDirty, saving, onSave, onSettings }) {
  const [copyDone, setCopyDone] = useState(false);

  // Use page_url from API response (e.g. https://api.crmfit.ru/m/{slug}).
  const pageUrl = data.page_url || (data.slug ? `${API_BASE}/m/${data.slug}` : null);
  const qrUrl = data.qr_url
    ? (data.qr_url.startsWith('http') ? data.qr_url : `${API_BASE}${data.qr_url}`)
    : null;

  async function handleCopy() {
    if (!pageUrl) return;
    try {
      await navigator.clipboard.writeText(pageUrl);
      WebApp?.HapticFeedback?.notificationOccurred?.('success');
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), 2000);
    } catch {
      // clipboard not available
    }
  }

  function handleQr() {
    if (!qrUrl) return;
    const a = document.createElement('a');
    a.href = qrUrl;
    a.download = 'qr.png';
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.click();
  }

  return (
    <div className="site-control-panel">
      {isDirty && (
        <button
          type="button"
          className="site-control-panel__save"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? '...' : copyDone ? '✓ Сохранено' : 'Опубликовать изменения'}
        </button>
      )}

      {pageUrl && data.is_published && (
        <div className="site-control-panel__link-row">
          <span className="site-control-panel__url">{pageUrl}</span>
          <button
            type="button"
            className="site-control-panel__copy"
            onClick={handleCopy}
          >
            {copyDone ? '✓ Скопировано' : 'Копировать ссылку'}
          </button>
        </div>
      )}

      {data.is_published && (
        <div className="site-control-panel__stats">
          <div className="stat-card">
            <span className="stat-card__num">👁 {data.views_count ?? 0}</span>
            <span className="stat-card__label">просмотров</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__num">👆 {data.clicks_count ?? 0}</span>
            <span className="stat-card__label">кликов</span>
          </div>
        </div>
      )}

      {data.is_published && (
        <div className="site-control-panel__actions">
          {qrUrl && (
            <button type="button" className="site-control-panel__action" onClick={handleQr}>
              📱 QR-код
            </button>
          )}
          <button type="button" className="site-control-panel__action" onClick={onSettings}>
            ⚙️ Настройки
          </button>
        </div>
      )}

      {!data.is_published && (
        <button type="button" className="site-control-panel__settings-ghost" onClick={onSettings}>
          ⚙️ Настройки страницы
        </button>
      )}

      <style>{`
        .site-control-panel {
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: linear-gradient(180deg, var(--master-bg-card), var(--master-bg-surface));
          border-top: 1px solid var(--master-border);
          box-shadow: 0 -12px 28px rgba(0, 0, 0, 0.08);
        }
        .site-control-panel__save {
          width: 100%;
          height: 48px;
          border-radius: 12px;
          border: none;
          background: var(--master-accent);
          color: var(--master-button-text);
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 10px 24px var(--master-accent-22);
        }
        .site-control-panel__save:disabled { opacity: 0.6; }
        .site-control-panel__link-row {
          display: flex;
          align-items: center;
          gap: 8px;
          justify-content: space-between;
        }
        .site-control-panel__url {
          font-size: 13px;
          color: var(--master-text-secondary);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .site-control-panel__copy {
          background: var(--master-accent-8);
          border: 1px solid var(--master-accent);
          border-radius: 8px;
          color: var(--master-accent);
          font-size: 13px;
          padding: 6px 10px;
          cursor: pointer;
          white-space: nowrap;
          flex-shrink: 0;
        }
        .site-control-panel__stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }
        .stat-card {
          background: var(--master-bg-surface);
          border: 1px solid var(--master-border);
          border-radius: 12px;
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .stat-card__num {
          font-size: 20px;
          font-weight: 700;
          color: var(--master-text-primary);
        }
        .stat-card__label {
          font-size: 12px;
          color: var(--master-text-secondary);
        }
        .site-control-panel__actions {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }
        .site-control-panel__action {
          background: var(--master-bg-surface);
          border: 1px solid var(--master-border);
          border-radius: 12px;
          padding: 12px;
          font-size: 14px;
          cursor: pointer;
          color: var(--master-text-primary);
        }
        .site-control-panel__settings-ghost {
          background: none;
          border: none;
          color: var(--master-text-secondary);
          font-size: 14px;
          cursor: pointer;
          padding: 4px 0;
          text-align: left;
        }
      `}</style>
    </div>
  );
}
