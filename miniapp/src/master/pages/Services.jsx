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
  const [archiveExpanded, setArchiveExpanded] = useState(false);
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
    <div style={{ paddingBottom: 80 }}>
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

      {/* Add button */}
      <div style={{ padding: '16px' }}>
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

      {/* Active services */}
      {active.length === 0 ? (
        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
          Нет активных услуг
        </div>
      ) : (
        <div style={{ background: 'var(--tg-section-bg)' }}>
          <div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
            Активные ({active.length})
          </div>
          {active.map((s, idx) => (
            <div
              key={s.id}
              onClick={() => { haptic(); setSheet({ service: s }); }}
              style={{
                display: 'flex', alignItems: 'center',
                padding: '13px 16px',
                borderBottom: idx < active.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
                cursor: 'pointer', gap: 12,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.name}
                </div>
                {s.description && (
                  <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {s.description}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--tg-accent)', flexShrink: 0 }}>
                {(s.price || 0).toLocaleString()} ₽
              </div>
              <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
            </div>
          ))}
        </div>
      )}

      {/* Archived section */}
      {archived.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div
            onClick={() => { haptic(); setArchiveExpanded(e => !e); }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px',
              background: 'var(--tg-section-bg)',
              cursor: 'pointer',
              borderBottom: '1px solid var(--tg-secondary-bg)',
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-hint)' }}>
              Архив ({archived.length})
            </div>
            <span style={{
              color: 'var(--tg-hint)', fontSize: 16,
              transform: archiveExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s',
            }}>
              ▶
            </span>
          </div>
          {archiveExpanded && (
            <div style={{ background: 'var(--tg-section-bg)' }}>
              {archived.map((s, idx) => (
                <div
                  key={s.id}
                  style={{
                    display: 'flex', alignItems: 'center',
                    padding: '12px 16px',
                    borderBottom: idx < archived.length - 1 ? '1px solid var(--tg-secondary-bg)' : 'none',
                    opacity: 0.6,
                    gap: 12,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {s.name}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 2 }}>
                      {(s.price || 0).toLocaleString()} ₽
                    </div>
                  </div>
                  <button
                    onClick={() => { haptic(); restoreMutation.mutate(s.id); }}
                    disabled={restoreMutation.isPending}
                    style={{
                      padding: '6px 12px', borderRadius: 8,
                      border: '1px solid var(--tg-accent)',
                      background: 'none', color: 'var(--tg-accent)',
                      fontSize: 13, cursor: 'pointer',
                    }}
                  >
                    Восстановить
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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

const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 10,
  border: '1px solid var(--tg-secondary-bg)',
  background: 'var(--tg-bg)', color: 'var(--tg-text)',
  fontSize: 15, boxSizing: 'border-box', display: 'block',
};
