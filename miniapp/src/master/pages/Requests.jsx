import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterRequests, closeMasterRequest, getMasterRequestMedia } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const REQUEST_TYPES = {
  order_request: { emoji: '🛎', title: 'Заявка на заказ' },
  question:      { emoji: '', title: 'Вопрос от клиента' },
  media:         { emoji: '📸', title: 'Медиафайл' },
};

const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

function formatDate(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  const now = new Date();
  const hh = d.getHours().toString().padStart(2, '0');
  const mm = d.getMinutes().toString().padStart(2, '0');
  const time = `${hh}:${mm}`;
  if (d.toDateString() === now.toDateString()) return `сегодня ${time}`;
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return `вчера ${time}`;
  return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`;
}

function FilterTabs({ active, onChange }) {
  const filters = [
    { key: 'new', label: 'Новые' },
    { key: 'all', label: 'Все' },
    { key: 'closed', label: 'Закрытые' },
  ];
  return (
    <div style={{
      display: 'flex',
      borderBottom: '1px solid var(--tg-secondary-bg)',
      background: 'var(--tg-bg)',
      position: 'sticky',
      top: 0,
      zIndex: 10,
    }}>
      {filters.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => { haptic(); onChange(key); }}
          style={{
            flex: 1,
            padding: '12px 0',
            background: 'none',
            border: 'none',
            borderBottom: active === key
              ? '2px solid var(--tg-accent)' : '2px solid transparent',
            color: active === key ? 'var(--tg-accent)' : 'var(--tg-hint)',
            fontSize: 14,
            fontWeight: active === key ? 600 : 400,
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function ActionBtn({ children, onClick, accent, small }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: small ? '8px 10px' : '10px 12px',
        background: accent ? 'var(--tg-accent)' : 'var(--tg-secondary-bg)',
        color: accent ? '#fff' : 'var(--tg-text)',
        border: 'none',
        borderRadius: 10,
        fontSize: 13,
        fontWeight: 500,
        cursor: 'pointer',
        textAlign: 'center',
      }}
    >
      {children}
    </button>
  );
}

function MediaPreview({ reqId }) {
  const [viewerIndex, setViewerIndex] = useState(null);
  const [zoom, setZoom] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['request-media', reqId],
    queryFn: () => getMasterRequestMedia(reqId),
    staleTime: 10 * 60_000,
    retry: false,
  });

  const media = data?.media || [];
  const activeMedia = viewerIndex == null ? null : media[viewerIndex] || null;

  const openViewer = (index) => {
    haptic();
    setViewerIndex(index);
    setZoom(1);
  };
  const closeViewer = () => {
    haptic();
    setViewerIndex(null);
    setZoom(1);
  };
  const nextMedia = () => {
    if (!media.length) return;
    haptic();
    setViewerIndex((prev) => ((prev ?? 0) + 1) % media.length);
    setZoom(1);
  };
  const prevMedia = () => {
    if (!media.length) return;
    haptic();
    setViewerIndex((prev) => ((prev ?? 0) - 1 + media.length) % media.length);
    setZoom(1);
  };

  if (isLoading) return (
    <div style={{ height: 120, background: 'var(--tg-secondary-bg)', borderRadius: 8, marginTop: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ color: 'var(--tg-hint)', fontSize: 13 }}>Загрузка...</span>
    </div>
  );
  if (!media.length) return null;

  return (
    <>
      <div style={{
        marginTop: 8,
        display: 'grid',
        gridTemplateColumns: media.length === 1 ? '1fr' : 'repeat(2, minmax(0, 1fr))',
        gap: 8,
      }}>
        {media.map((item, index) => {
          const isPhoto = item.media_type === 'photo';
          if (isPhoto) {
            return (
              <button
                key={`${item.file_id}-${index}`}
                onClick={() => openViewer(index)}
                style={{
                  border: 'none',
                  padding: 0,
                  background: 'none',
                  borderRadius: 10,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  aspectRatio: '4 / 3',
                }}
              >
                <img
                  src={item.url}
                  alt={`фото ${index + 1}`}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
              </button>
            );
          }

          return (
            <video
              key={`${item.file_id}-${index}`}
              src={item.url}
              controls
              preload="metadata"
              style={{ width: '100%', borderRadius: 10, background: '#000', maxHeight: 220 }}
            />
          );
        })}
      </div>

      {activeMedia && activeMedia.media_type === 'photo' && (
        <div
          onClick={closeViewer}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'rgba(0, 0, 0, 0.92)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '56px 12px 84px',
          }}
        >
          <button
            onClick={(e) => { e.stopPropagation(); closeViewer(); }}
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              border: 'none',
              borderRadius: 10,
              background: 'rgba(255,255,255,0.16)',
              color: '#fff',
              fontSize: 14,
              padding: '8px 10px',
              cursor: 'pointer',
            }}
          >
            Закрыть
          </button>

          {media.length > 1 && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); prevMedia(); }}
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  border: 'none',
                  borderRadius: 999,
                  width: 36,
                  height: 36,
                  background: 'rgba(255,255,255,0.22)',
                  color: '#fff',
                  fontSize: 20,
                  cursor: 'pointer',
                }}
              >
                {'<'}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); nextMedia(); }}
                style={{
                  position: 'absolute',
                  right: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  border: 'none',
                  borderRadius: 999,
                  width: 36,
                  height: 36,
                  background: 'rgba(255,255,255,0.22)',
                  color: '#fff',
                  fontSize: 20,
                  cursor: 'pointer',
                }}
              >
                {'>'}
              </button>
            </>
          )}

          <img
            onClick={(e) => e.stopPropagation()}
            src={activeMedia.url}
            alt={`фото ${viewerIndex + 1}`}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              transform: `scale(${zoom})`,
              transformOrigin: 'center',
              transition: 'transform 0.15s ease-out',
            }}
          />

          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'absolute',
              bottom: 16,
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <button
              onClick={() => { haptic(); setZoom((z) => Math.max(1, +(z - 0.25).toFixed(2))); }}
              style={{
                border: 'none',
                borderRadius: 10,
                padding: '8px 12px',
                background: 'rgba(255,255,255,0.2)',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              -
            </button>
            <div style={{ color: '#fff', fontSize: 13, minWidth: 58, textAlign: 'center' }}>
              {Math.round(zoom * 100)}%
            </div>
            <button
              onClick={() => { haptic(); setZoom((z) => Math.min(4, +(z + 0.25).toFixed(2))); }}
              style={{
                border: 'none',
                borderRadius: 10,
                padding: '8px 12px',
                background: 'rgba(255,255,255,0.2)',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              +
            </button>
            <button
              onClick={() => { haptic(); setZoom(1); }}
              style={{
                border: 'none',
                borderRadius: 10,
                padding: '8px 10px',
                background: 'rgba(255,255,255,0.2)',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              1:1
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function RequestCard({ req, onClose, onNavigate }) {
  const [showMedia, setShowMedia] = useState(false);
  const isClosed = req.status === 'closed';
  const typeInfo = REQUEST_TYPES[req.type] || { emoji: '📩', title: 'Заявка' };
  const mediaCount = Number(req.media_count || 0);
  const hasMedia = mediaCount > 0 || Boolean(req.file_id);

  const handleContact = () => {
    haptic();
    if (req.client_tg_id) {
      window.open(`tg://user?id=${req.client_tg_id}`);
    }
  };

  const handleOpenClient = () => {
    haptic();
    if (!req.client_id) return;
    onNavigate('client', { id: req.client_id });
  };

  const handleCreateOrder = () => {
    haptic();
    onNavigate('create_order', {
      prefill: {
        client_id: req.client_id,
        client_name: req.client_name,
        service_name: req.service_name,
      },
    });
  };

  return (
    <div style={{
      background: 'var(--tg-section-bg)',
      borderRadius: 14,
      margin: '0 0 10px',
      padding: '14px 16px',
      opacity: isClosed ? 0.65 : 1,
      transition: 'opacity 0.2s',
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-text)' }}>
          {typeInfo.emoji ? `${typeInfo.emoji} ` : ''}{typeInfo.title}
        </span>
        <span style={{ fontSize: 12, color: 'var(--tg-hint)', flexShrink: 0, marginLeft: 8 }}>
          {formatDate(req.created_at)}
        </span>
      </div>

      {/* Client */}
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 2 }}>
        {req.client_name}
      </div>
      {req.client_phone && (
        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>
          📞 {req.client_phone}
        </div>
      )}
      {req.service_name && (
        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>
          🛠 {req.service_name}
        </div>
      )}
      {req.desired_date && (
        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>
          📅 {req.desired_date}{req.desired_time ? ` в ${req.desired_time}` : ''}
        </div>
      )}
      {req.text && (
        <div style={{
          fontSize: 14,
          color: 'var(--tg-text)',
          background: 'var(--tg-secondary-bg)',
          borderRadius: 8,
          padding: '8px 10px',
          marginTop: 6,
          marginBottom: 6,
          lineHeight: 1.4,
        }}>
          "{req.text}"
        </div>
      )}
      {hasMedia && (
        <div>
          <div
            onClick={() => { haptic(); setShowMedia(v => !v); }}
            style={{ fontSize: 13, color: 'var(--tg-accent)', marginTop: 4, cursor: 'pointer' }}
          >
            📎 Вложения{mediaCount > 0 ? ` (${mediaCount})` : ''} {showMedia ? '▲' : '▼'}
          </div>
          {showMedia && <MediaPreview reqId={req.id} />}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <ActionBtn onClick={handleContact} accent>💬 Написать</ActionBtn>
          {req.client_id && (
            <ActionBtn onClick={handleOpenClient}>👤 Клиент</ActionBtn>
          )}
        </div>
        {req.type === 'order_request' && !isClosed && (
          <ActionBtn onClick={handleCreateOrder}>📋 Создать заказ</ActionBtn>
        )}
        {!isClosed && (
          <ActionBtn onClick={() => { haptic(); onClose(req.id); }}>
            ✅ Закрыть заявку
          </ActionBtn>
        )}
      </div>
    </div>
  );
}

export default function Requests({ onNavigate, onBadgeChange }) {
  const [filter, setFilter] = useState('new');
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['master-requests', filter],
    queryFn: () => getMasterRequests(filter),
    staleTime: 30_000,
    onSuccess: (d) => {
      if (onBadgeChange) onBadgeChange(d.unread_count ?? 0);
    },
  });

  const closeMutation = useMutation({
    mutationFn: closeMasterRequest,
    onSuccess: (_, requestId) => {
      queryClient.setQueryData(['master-requests', filter], (old) => {
        if (!old) return old;
        const target = old.requests.find(r => r.id === requestId);
        const wasNew = target ? target.status !== 'closed' : false;
        const newUnread = Math.max(0, (old.unread_count ?? 0) - (wasNew ? 1 : 0));
        if (onBadgeChange) onBadgeChange(newUnread);

        if (filter === 'new') {
          return {
            ...old,
            unread_count: newUnread,
            total: Math.max(0, (old.total ?? old.requests.length) - 1),
            requests: old.requests.filter(r => r.id !== requestId),
          };
        }

        return {
          ...old,
          unread_count: newUnread,
          requests: old.requests.map(r =>
            r.id === requestId ? { ...r, status: 'closed' } : r
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['master-requests'] });
    },
  });

  const requests = data?.requests || [];
  const unreadCount = data?.unread_count ?? 0;

  const handleNavigate = useCallback(
    (type, params) => { if (onNavigate) onNavigate(type, params); },
    [onNavigate]
  );

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Header */}
      <div style={{ padding: '16px 16px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--tg-text)' }}>🔔 Заявки</div>
        {unreadCount > 0 && (
          <div style={{ fontSize: 13, color: 'var(--tg-hint)' }}>
            Новых: {unreadCount}
          </div>
        )}
      </div>

      <FilterTabs active={filter} onChange={setFilter} />

      <div style={{ padding: '12px 12px 0' }}>
        {isLoading && (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Загрузка...
          </div>
        )}

        {isError && (
          <div style={{ padding: '48px 16px', textAlign: 'center' }}>
            <p style={{ color: 'var(--tg-hint)', marginBottom: 12 }}>Не удалось загрузить заявки</p>
            <button
              onClick={() => refetch()}
              style={{ color: 'var(--tg-accent)', background: 'none', border: 'none', fontSize: 14, cursor: 'pointer' }}
            >
              Повторить
            </button>
          </div>
        )}

        {!isLoading && !isError && requests.length === 0 && (
          <div style={{ padding: '64px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
            <p style={{ color: 'var(--tg-hint)', fontSize: 15 }}>
              {filter === 'new' ? 'Новых заявок нет' : 'Заявок нет'}
            </p>
          </div>
        )}

        {!isLoading && !isError && requests.map(req => (
          <RequestCard
            key={req.id}
            req={req}
            onClose={(id) => closeMutation.mutate(id)}
            onNavigate={handleNavigate}
          />
        ))}
      </div>
    </div>
  );
}
