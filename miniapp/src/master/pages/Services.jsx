import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterMe,
  getMasterServicesAll,
  createMasterService,
  updateMasterService,
  archiveMasterService,
  restoreMasterService,
} from '../../api/client';
import { useI18n } from '../../i18n';
import { DEFAULT_CURRENCY, getCurrencySymbol } from '../profileOptions';

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

const iconProps = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
};

const ToolIcon = () => (
  <svg {...iconProps}>
    <path d="m14.7 6.3 3 3" />
    <path d="m12.2 8.8 3 3" />
    <path d="M3 21a2 2 0 0 1 0-3l9.2-9.2a2 2 0 0 1 2.8 0l.2.2a2 2 0 0 1 0 2.8L6 21a2 2 0 0 1-3 0Z" />
    <path d="m18.5 2.5 3 3a2.1 2.1 0 0 1 0 3l-2 2-6-6 2-2a2.1 2.1 0 0 1 3 0Z" />
  </svg>
);

const PlusIcon = () => (
  <svg {...iconProps}>
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
);

const ChevronIcon = () => (
  <svg {...iconProps} width={14} height={14}>
    <path d="m9 18 6-6-6-6" />
  </svg>
);

function SectionTitle({ children }) {
  return <div className="enterprise-section-title">{children}</div>;
}

function formatPrice(value, currencySymbol, locale) {
  return `${(value || 0).toLocaleString(locale)} ${currencySymbol}`;
}

function ServiceSheet({ initial, onClose, onSave, onArchive, loading, currencySymbol, t }) {
  const isNew = !initial;
  const [name, setName] = useState(initial?.name || '');
  const [price, setPrice] = useState(String(initial?.price || ''));
  const [description, setDescription] = useState(initial?.description || '');
  const [showOnLanding, setShowOnLanding] = useState(initial?.show_on_landing ?? true);

  const handleSave = () => {
    const parsedPrice = parseInt(price, 10);
    if (!name.trim() || !parsedPrice || parsedPrice <= 0) {
      hapticNotify('error');
      return;
    }
    haptic('medium');
    onSave({
      name: name.trim(),
      price: parsedPrice,
      description: description.trim() || null,
      show_on_landing: showOnLanding,
    });
  };

  return (
    <>
      <div className="enterprise-sheet-backdrop" onClick={onClose} />
      <div className="enterprise-sheet enterprise-services-sheet">
        <div className="enterprise-sheet-handle" />
        <div className="enterprise-sheet-title">{isNew ? t('services.sheet.titleNew') : t('services.sheet.titleEdit')}</div>

        <label className="enterprise-services-sheet-label">{t('services.sheet.name')}</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('services.sheet.namePlaceholder')}
          autoFocus
          className="enterprise-sheet-input"
        />

        <label className="enterprise-services-sheet-label">{t('services.sheet.price', { currency: currencySymbol })}</label>
        <input
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder={`3000 ${currencySymbol}`}
          className="enterprise-sheet-input"
        />

        <label className="enterprise-services-sheet-label">{t('services.sheet.description')}</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t('services.sheet.descriptionPlaceholder')}
          rows={3}
          className="enterprise-sheet-input"
        />

        <div
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0 4px' }}
          onClick={() => { haptic(); setShowOnLanding((v) => !v); }}
        >
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--tg-text)' }}>
              {t('services.sheet.showOnLanding')}
            </div>
            <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
              {t('services.sheet.showOnLandingHint')}
            </div>
          </div>
          <div
            style={{
              width: 44, height: 26, borderRadius: 13, flexShrink: 0,
              background: showOnLanding ? 'var(--tg-accent, #6c47ff)' : 'var(--tg-section-separator, #ccc)',
              position: 'relative', transition: 'background 0.2s', cursor: 'pointer',
            }}
          >
            <div style={{
              position: 'absolute', top: 3, left: showOnLanding ? 21 : 3,
              width: 20, height: 20, borderRadius: '50%', background: '#fff',
              transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
            }} />
          </div>
        </div>

        <div className="enterprise-sheet-actions">
          {!isNew && (
            <button
              type="button"
              className="enterprise-sheet-btn destructive"
              onClick={() => {
                haptic();
                onArchive();
              }}
              disabled={loading}
            >
              {t('services.sheet.archive')}
            </button>
          )}
          <button type="button" className="enterprise-sheet-btn secondary" onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button type="button" className="enterprise-sheet-btn primary" onClick={handleSave} disabled={loading}>
            {loading ? t('common.saving') : t('common.save')}
          </button>
        </div>
      </div>
    </>
  );
}

export default function Services() {
  const { t, locale } = useI18n();
  const [sheet, setSheet] = useState(null);
  const [tab, setTab] = useState('active');
  const [successMsg, setSuccessMsg] = useState('');

  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['master-services-all'],
    queryFn: getMasterServicesAll,
    staleTime: 30_000,
  });
  const { data: masterData } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 60_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['master-services-all'] });

  const showSuccess = (msg = t('services.toasts.ready')) => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 1600);
  };

  const createMutation = useMutation({
    mutationFn: createMasterService,
    onSuccess: () => {
      invalidate();
      setSheet(null);
      showSuccess(t('services.toasts.created'));
    },
    onError: () => hapticNotify('error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data: nextData }) => updateMasterService(id, nextData),
    onSuccess: () => {
      invalidate();
      setSheet(null);
      showSuccess(t('services.toasts.saved'));
    },
    onError: () => hapticNotify('error'),
  });

  const archiveMutation = useMutation({
    mutationFn: archiveMasterService,
    onSuccess: () => {
      invalidate();
      setSheet(null);
      showSuccess(t('services.toasts.archived'));
    },
    onError: () => hapticNotify('error'),
  });

  const restoreMutation = useMutation({
    mutationFn: restoreMasterService,
    onSuccess: () => {
      invalidate();
      showSuccess(t('services.toasts.restored'));
    },
    onError: () => hapticNotify('error'),
  });

  if (isLoading) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        {t('services.loading')}
      </div>
    );
  }

  const active = data?.active || [];
  const archived = data?.archived || [];
  const currencySymbol = getCurrencySymbol(masterData?.currency || DEFAULT_CURRENCY);

  const handleSave = (serviceData) => {
    if (sheet?.service) {
      updateMutation.mutate({ id: sheet.service.id, data: serviceData });
    } else {
      createMutation.mutate(serviceData);
    }
  };

  const mutationLoading = createMutation.isPending || updateMutation.isPending || archiveMutation.isPending;

  return (
      <div className="enterprise-services-page">
      {successMsg && <div className="enterprise-profile-toast">{successMsg}</div>}

      <SectionTitle>{t('services.sections.displayMode')}</SectionTitle>
      <div className="enterprise-services-tabs">
        <button
          type="button"
          className={`enterprise-services-tab${tab === 'active' ? ' is-active' : ''}`}
          onClick={() => {
            haptic();
            setTab('active');
          }}
        >
          {t('services.tabs.active', { count: active.length })}
        </button>
        <button
          type="button"
          className={`enterprise-services-tab${tab === 'archived' ? ' is-active' : ''}`}
          onClick={() => {
            haptic();
            setTab('archived');
          }}
        >
          {t('services.tabs.archived', { count: archived.length })}
        </button>
      </div>

      <SectionTitle>{t('services.sections.management')}</SectionTitle>
      <div className="enterprise-services-add-wrap">
        <button
          type="button"
          className="enterprise-services-add-btn"
          onClick={() => {
            haptic();
            setSheet({ service: null });
          }}
        >
          <PlusIcon />
          <span>{t('services.addService')}</span>
        </button>
      </div>

      <SectionTitle>{tab === 'active' ? t('services.sections.activeServices') : t('services.sections.archivedServices')}</SectionTitle>
      <div className="enterprise-cell-group">
        {tab === 'active' && active.length === 0 && (
          <div className="enterprise-services-empty">{t('services.empty.active')}</div>
        )}

        {tab === 'active' && active.map((service, idx) => (
          <button
            key={service.id}
            type="button"
            className={`enterprise-cell is-interactive enterprise-services-cell${idx === active.length - 1 ? ' is-last' : ''}`}
            onClick={() => {
              haptic();
              setSheet({ service });
            }}
          >
            <span className="enterprise-cell-icon"><ToolIcon /></span>
            <span className="enterprise-cell-label enterprise-services-label">
              <span className="enterprise-services-name">{service.name}</span>
              <span className="enterprise-services-desc">{service.description || t('common.noDescription')}</span>
            </span>
            <span className="enterprise-cell-value">{formatPrice(service.price, currencySymbol, locale)}</span>
            <span className="enterprise-cell-chevron"><ChevronIcon /></span>
          </button>
        ))}

        {tab === 'archived' && archived.length === 0 && (
          <div className="enterprise-services-empty">{t('services.empty.archived')}</div>
        )}

        {tab === 'archived' && archived.map((service, idx) => (
          <div className={`enterprise-services-archived-row${idx === archived.length - 1 ? ' is-last' : ''}`} key={service.id}>
            <div className="enterprise-services-archived-main">
              <span className="enterprise-cell-icon"><ToolIcon /></span>
              <div className="enterprise-services-label">
                <div className="enterprise-services-name">{service.name}</div>
                <div className="enterprise-services-desc">{formatPrice(service.price, currencySymbol, locale)}</div>
              </div>
            </div>
            <button
              type="button"
              className="enterprise-services-restore-btn"
              disabled={restoreMutation.isPending}
              onClick={() => {
                haptic();
                restoreMutation.mutate(service.id);
              }}
            >
              {t('services.restore')}
            </button>
          </div>
        ))}
      </div>

      {sheet !== null && (
        <ServiceSheet
          initial={sheet.service}
          onClose={() => setSheet(null)}
          onSave={handleSave}
          onArchive={() => sheet.service && archiveMutation.mutate(sheet.service.id)}
          loading={mutationLoading}
          currencySymbol={currencySymbol}
          t={t}
        />
      )}
    </div>
  );
}
