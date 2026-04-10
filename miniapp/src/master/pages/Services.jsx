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

function getCurrencySymbol(code) {
  const map = {
    RUB: '₽',
    EUR: '€',
    ILS: '₪',
    USD: '$',
    UAH: '₴',
    BYN: 'Br',
    KZT: '₸',
    TRY: '₺',
    GEL: '₾',
    UZS: 'сум',
  };
  return map[code] || code || '₽';
}

function formatPrice(value, currencySymbol) {
  return `${(value || 0).toLocaleString('ru-RU')} ${currencySymbol}`;
}

function ServiceSheet({ initial, onClose, onSave, onArchive, loading, currencySymbol }) {
  const isNew = !initial;
  const [name, setName] = useState(initial?.name || '');
  const [price, setPrice] = useState(String(initial?.price || ''));
  const [description, setDescription] = useState(initial?.description || '');

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
    });
  };

  return (
    <>
      <div className="enterprise-sheet-backdrop" onClick={onClose} />
      <div className="enterprise-sheet enterprise-services-sheet">
        <div className="enterprise-sheet-handle" />
        <div className="enterprise-sheet-title">{isNew ? 'Новая услуга' : 'Редактировать услугу'}</div>

        <label className="enterprise-services-sheet-label">Название</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Например: ремонт измельчителя"
          autoFocus
          className="enterprise-sheet-input"
        />

        <label className="enterprise-services-sheet-label">Цена, {currencySymbol}</label>
        <input
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder={`3000 ${currencySymbol}`}
          className="enterprise-sheet-input"
        />

        <label className="enterprise-services-sheet-label">Описание</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Необязательно"
          rows={3}
          className="enterprise-sheet-input"
        />

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
              В архив
            </button>
          )}
          <button type="button" className="enterprise-sheet-btn secondary" onClick={onClose}>
            Отмена
          </button>
          <button type="button" className="enterprise-sheet-btn primary" onClick={handleSave} disabled={loading}>
            {loading ? 'Сохраняем...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </>
  );
}

export default function Services() {
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

  const showSuccess = (msg = 'Готово') => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 1600);
  };

  const createMutation = useMutation({
    mutationFn: createMasterService,
    onSuccess: () => {
      invalidate();
      setSheet(null);
      showSuccess('Услуга добавлена');
    },
    onError: () => hapticNotify('error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data: nextData }) => updateMasterService(id, nextData),
    onSuccess: () => {
      invalidate();
      setSheet(null);
      showSuccess('Сохранено');
    },
    onError: () => hapticNotify('error'),
  });

  const archiveMutation = useMutation({
    mutationFn: archiveMasterService,
    onSuccess: () => {
      invalidate();
      setSheet(null);
      showSuccess('Услуга архивирована');
    },
    onError: () => hapticNotify('error'),
  });

  const restoreMutation = useMutation({
    mutationFn: restoreMasterService,
    onSuccess: () => {
      invalidate();
      showSuccess('Услуга восстановлена');
    },
    onError: () => hapticNotify('error'),
  });

  if (isLoading) {
    return (
      <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
        Загрузка...
      </div>
    );
  }

  const active = data?.active || [];
  const archived = data?.archived || [];
  const currencySymbol = getCurrencySymbol(masterData?.currency);

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

      <SectionTitle>Режим отображения</SectionTitle>
      <div className="enterprise-services-tabs">
        <button
          type="button"
          className={`enterprise-services-tab${tab === 'active' ? ' is-active' : ''}`}
          onClick={() => {
            haptic();
            setTab('active');
          }}
        >
          Активные ({active.length})
        </button>
        <button
          type="button"
          className={`enterprise-services-tab${tab === 'archived' ? ' is-active' : ''}`}
          onClick={() => {
            haptic();
            setTab('archived');
          }}
        >
          Архив ({archived.length})
        </button>
      </div>

      <SectionTitle>Управление</SectionTitle>
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
          <span>Добавить услугу</span>
        </button>
      </div>

      <SectionTitle>{tab === 'active' ? 'Активные услуги' : 'Архив услуг'}</SectionTitle>
      <div className="enterprise-cell-group">
        {tab === 'active' && active.length === 0 && (
          <div className="enterprise-services-empty">Нет активных услуг</div>
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
              <span className="enterprise-services-desc">{service.description || 'Без описания'}</span>
            </span>
            <span className="enterprise-cell-value">{formatPrice(service.price, currencySymbol)}</span>
            <span className="enterprise-cell-chevron"><ChevronIcon /></span>
          </button>
        ))}

        {tab === 'archived' && archived.length === 0 && (
          <div className="enterprise-services-empty">Архив пуст</div>
        )}

        {tab === 'archived' && archived.map((service, idx) => (
          <div className={`enterprise-services-archived-row${idx === archived.length - 1 ? ' is-last' : ''}`} key={service.id}>
            <div className="enterprise-services-archived-main">
              <span className="enterprise-cell-icon"><ToolIcon /></span>
              <div className="enterprise-services-label">
                <div className="enterprise-services-name">{service.name}</div>
                <div className="enterprise-services-desc">{formatPrice(service.price, currencySymbol)}</div>
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
              Восстановить
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
        />
      )}
    </div>
  );
}
