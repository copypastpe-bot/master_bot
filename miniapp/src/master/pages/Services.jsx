import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
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

// Bottom sheet for create / edit
function ServiceSheet({ initial, onClose, onSave, onArchive, loading }) {
  const isNew = !initial;
  const [name, setName] = useState(initial?.name || '');
  const [price, setPrice] = useState(String(initial?.price || ''));
  const [description, setDescription] = useState(initial?.description || '');

  const handleSave = () => {
    const p = parseInt(price, 10);
    if (!name.trim() || !p || p <= 0) {
      hapticNotify('error');
      return;
    }
    haptic('medium');
    onSave({ name: name.trim(), price: p, description: description.trim() || null });
  };

  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200 }} />
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: 'var(--tg-section-bg)',
        borderRadius: '16px 16px 0 0',
        padding: '20px 16px',
        paddingBottom: 'max(32px, env(safe-area-inset-bottom))',
        zIndex: 201,
        animation: 'slideUp 0.2s ease',
      }}>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
          {isNew ? '+ Новая услуга' : 'Редактировать услугу'}
        </div>

        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>Название *</div>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="Уборка квартиры"
          autoFocus
          style={inputStyle}
        />

        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 12, marginBottom: 4 }}>Цена, ₽ *</div>
        <input
          type="number"
          value={price}
          onChange={e => setPrice(e.target.value)}
          placeholder="3000"
          style={inputStyle}
        />

        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 12, marginBottom: 4 }}>Описание</div>
        <input
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Необязательно"
          style={inputStyle}
        />

        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          {!isNew && (
            <button
              onClick={() => { haptic(); onArchive(); }}
              disabled={loading}
              style={{
                padding: '12px', borderRadius: 10, flex: 1,
                border: '1px solid var(--tg-destructive, #e53935)',
                background: 'none',
                color: 'var(--tg-destructive, #e53935)',
                fontSize: 14, cursor: 'pointer',
              }}
            >
              В архив
            </button>
          )}
          <button
            onClick={onClose}
            style={{
              padding: '12px', borderRadius: 10, flex: 1,
              border: '1px solid var(--tg-secondary-bg)',
              background: 'none', color: 'var(--tg-text)', fontSize: 14, cursor: 'pointer',
            }}
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            style={{
              padding: '12px', borderRadius: 10, flex: 2,
              background: 'var(--tg-accent)', color: '#fff',
              fontSize: 14, fontWeight: 600, border: 'none', cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? '...' : 'Сохранить'}
          </button>
        </div>
      </div>
      <style>{`@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }`}</style>
    </>
  );
}

export default function Services() {
  const [sheet, setSheet] = useState(null); // null | { service: obj | null }
  const [tab, setTab] = useState('active'); // active | archived
  const [successMsg, setSuccessMsg] = useState('');

  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['master-services-all'],
    queryFn: getMasterServicesAll,
    staleTime: 30_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['master-services-all'] });

  const showSuccess = (msg = 'Готово ✓') => {
    hapticNotify('success');
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 2000);
  };

  const createMutation = useMutation({
    mutationFn: createMasterService,
    onSuccess: () => { invalidate(); setSheet(null); showSuccess('Услуга добавлена ✓'); },
    onError: () => hapticNotify('error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateMasterService(id, data),
    onSuccess: () => { invalidate(); setSheet(null); showSuccess('Сохранено ✓'); },
    onError: () => hapticNotify('error'),
  });

  const archiveMutation = useMutation({
    mutationFn: archiveMasterService,
    onSuccess: () => { invalidate(); setSheet(null); showSuccess('Услуга архивирована'); },
    onError: () => hapticNotify('error'),
  });

  const restoreMutation = useMutation({
    mutationFn: restoreMasterService,
    onSuccess: () => { invalidate(); showSuccess('Услуга восстановлена ✓'); },
    onError: () => hapticNotify('error'),
  });

  if (isLoading) {
    return <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>Загрузка...</div>;
  }

  const active = data?.active || [];
  const archived = data?.archived || [];

  const handleSave = (serviceData) => {
    if (sheet?.service) {
      updateMutation.mutate({ id: sheet.service.id, data: serviceData });
    } else {
      createMutation.mutate(serviceData);
    }
  };

  const mutationLoading = createMutation.isPending || updateMutation.isPending || archiveMutation.isPending;

  return (
    <div style={{ padding: '12px 12px 88px', maxWidth: 760, margin: '0 auto' }}>
      {successMsg && (
        <div style={{
          position: 'fixed', top: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--tg-accent)', color: '#fff',
          padding: '8px 20px', borderRadius: 20, fontSize: 13, fontWeight: 500,
          zIndex: 300, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}>
          {successMsg}
        </div>
      )}

      {/* Tabs */}
      <div style={panelStyle}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          <button
            onClick={() => { haptic(); setTab('active'); }}
            style={{
              ...tabBtnStyle,
              background: tab === 'active' ? 'var(--tg-button)' : 'transparent',
              color: tab === 'active' ? 'var(--tg-button-text)' : 'var(--tg-hint)',
            }}
          >
            Активные ({active.length})
          </button>
          <button
            onClick={() => { haptic(); setTab('archived'); }}
            style={{
              ...tabBtnStyle,
              background: tab === 'archived' ? 'var(--tg-button)' : 'transparent',
              color: tab === 'archived' ? 'var(--tg-button-text)' : 'var(--tg-hint)',
            }}
          >
            Архив ({archived.length})
          </button>
        </div>
      </div>

      {/* Add button */}
      <div style={{ ...panelStyle, padding: 12, marginTop: 10 }}>
        <button
          onClick={() => { haptic(); setSheet({ service: null }); }}
          style={{
            width: '100%', padding: '13px', borderRadius: 12,
            background: 'var(--tg-accent)', color: '#fff',
            fontSize: 15, fontWeight: 600, border: 'none', cursor: 'pointer',
          }}
        >
          + Добавить услугу
        </button>
      </div>

      {/* List */}
      <div style={{ ...panelStyle, marginTop: 10, overflow: 'hidden', padding: 0 }}>
        {tab === 'active' && active.length === 0 && (
          <div style={{ padding: '26px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Нет активных услуг
          </div>
        )}

        {tab === 'active' && active.map((s, idx) => (
          <div
            key={s.id}
            onClick={() => { haptic(); setSheet({ service: s }); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '14px 14px',
              borderBottom: idx < active.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
              cursor: 'pointer',
              gap: 12,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.description || 'Без описания'}
              </div>
            </div>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--tg-button)',
              background: 'rgba(51,144,236,0.12)',
              borderRadius: 999,
              padding: '4px 10px',
              flexShrink: 0,
            }}>
              {(s.price || 0).toLocaleString()} ₽
            </div>
            <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
          </div>
        ))}

        {tab === 'archived' && archived.length === 0 && (
          <div style={{ padding: '26px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Архив пуст
          </div>
        )}

        {tab === 'archived' && archived.map((s, idx) => (
          <div
            key={s.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '14px 14px',
              borderBottom: idx < archived.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
              gap: 12,
              opacity: 0.72,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 3 }}>
                {(s.price || 0).toLocaleString()} ₽
              </div>
            </div>
            <button
              onClick={() => { haptic(); restoreMutation.mutate(s.id); }}
              disabled={restoreMutation.isPending}
              style={{
                padding: '8px 12px',
                borderRadius: 10,
                border: '1px solid var(--tg-accent)',
                background: 'none',
                color: 'var(--tg-accent)',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Восстановить
            </button>
          </div>
        ))}
      </div>

      {/* Sheet */}
      {sheet !== null && (
        <ServiceSheet
          initial={sheet.service}
          onClose={() => setSheet(null)}
          onSave={handleSave}
          onArchive={() => sheet.service && archiveMutation.mutate(sheet.service.id)}
          loading={mutationLoading}
        />
      )}
    </div>
  );
}

const panelStyle = {
  background: 'var(--tg-section-bg)',
  border: '1px solid var(--tg-enterprise-border)',
  borderRadius: 16,
  boxShadow: 'var(--tg-enterprise-shadow)',
  padding: 6,
};

const tabBtnStyle = {
  border: 'none',
  borderRadius: 12,
  padding: '10px 8px',
  fontSize: 13,
  fontWeight: 700,
  cursor: 'pointer',
  transition: 'background 0.15s, color 0.15s',
  minWidth: 0,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
};

const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'var(--tg-bg)', color: 'var(--tg-text)',
  fontSize: 15, boxSizing: 'border-box', display: 'block',
};
