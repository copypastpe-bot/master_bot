import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMasterRequests,
  closeMasterRequest,
  getMasterRequestMedia,
  getMasterRequestMediaUrl,
} from '../../api/client';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const iconProps = {
  width: 14,
  height: 14,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
};

const TYPE_ICONS = {
  order_request: (
    <svg {...iconProps}>
      <path d="M4 4h16l-2 10H6L4 4Z" />
      <circle cx="10" cy="19" r="1.6" />
      <circle cx="16" cy="19" r="1.6" />
    </svg>
  ),
  question: (
    <svg {...iconProps}>
      <path d="M20.9 11.4a8.4 8.4 0 0 1-.9 3.8A8.5 8.5 0 0 1 12.5 20H4l1.9-3.8a8.5 8.5 0 1 1 15-4.8Z" />
      <path d="M12 16h.01" />
      <path d="M10.5 9.4a2 2 0 1 1 2.8 1.8c-.9.4-1.3.9-1.3 1.8" />
    </svg>
  ),
  media: (
    <svg {...iconProps}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="1.5" />
      <path d="m21 15-4.8-4.8a1 1 0 0 0-1.4 0L8 17" />
    </svg>
  ),
  default: (
    <svg {...iconProps}>
      <path d="M20 8v8a2 2 0 0 1-2 2H6l-4 3V6a2 2 0 0 1 2-2h9" />
      <path d="M17 2v6" />
      <path d="M14 5h6" />
    </svg>
  ),
};

function formatDate(isoString, locale, tr) {
  if (!isoString) return '';
  const d = new Date(isoString);
  const now = new Date();
  const time = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  if (d.toDateString() === now.toDateString()) return `${tr('сегодня', 'today')} ${time}`;
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return `${tr('вчера', 'yesterday')} ${time}`;
  return d.toLocaleString(locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function FilterTabs({ active, onChange, tr }) {
  const filters = [
    { key: 'new', label: tr('Новые', 'New') },
    { key: 'all', label: tr('Все', 'All') },
    { key: 'closed', label: tr('Закрытые', 'Closed') },
  ];

  return (
    <div className="requests-filter-wrap">
      <div className="requests-filter">
        {filters.map(({ key, label }) => {
          const isActive = key === active;
          return (
            <button
              key={key}
              type="button"
              onClick={() => { haptic(); onChange(key); }}
              className={`requests-filter-btn${isActive ? ' is-active' : ''}`}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ActionBtn({ children, onClick, accent, small }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`requests-action-btn${accent ? ' is-accent' : ''}${small ? ' is-small' : ''}`}
    >
      {children}
    </button>
  );
}

function MediaPreview({ reqId, legacyFileId, tr }) {
  const [viewerIndex, setViewerIndex] = useState(null);
  const [zoom, setZoom] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['request-media', reqId],
    queryFn: () => getMasterRequestMedia(reqId),
    staleTime: 10 * 60_000,
    retry: false,
  });

  const hasResolvedMedia = Array.isArray(data?.media) && data.media.length > 0;
  const { data: legacyMediaData } = useQuery({
    queryKey: ['request-media-legacy-url', reqId, legacyFileId],
    queryFn: () => getMasterRequestMediaUrl(reqId),
    enabled: !hasResolvedMedia && Boolean(legacyFileId),
    staleTime: 10 * 60_000,
    retry: false,
  });

  const media = hasResolvedMedia
    ? data.media
    : (legacyMediaData?.url
      ? [{ file_id: legacyFileId, media_type: 'photo', url: legacyMediaData.url }]
      : []);
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

  if (isLoading) {
    return (
      <div className="requests-media-loading">
        <span>{tr('Загрузка вложений...', 'Loading attachments...')}</span>
      </div>
    );
  }

  if (!media.length) return null;

  return (
    <>
      <div className="requests-media-grid">
        {media.map((item, index) => {
          const isPhoto = item.media_type !== 'video';
          if (isPhoto) {
            return (
              <button
                type="button"
                key={`${item.file_id}-${index}`}
                onClick={() => openViewer(index)}
                className="requests-media-photo"
              >
                <img
                  src={item.url}
                  alt={tr(`фото ${index + 1}`, `photo ${index + 1}`)}
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
              className="requests-media-video"
            />
          );
        })}
      </div>

      {activeMedia && activeMedia.media_type !== 'video' && (
        <div onClick={closeViewer} className="requests-viewer-overlay">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); closeViewer(); }}
            className="requests-viewer-btn-close"
          >
            {tr('Закрыть', 'Close')}
          </button>

          {media.length > 1 && (
            <>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); prevMedia(); }}
                className="requests-viewer-nav prev"
              >
                {'<'}
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); nextMedia(); }}
                className="requests-viewer-nav next"
              >
                {'>'}
              </button>
            </>
          )}

          <img
            onClick={(e) => e.stopPropagation()}
            src={activeMedia.url}
            alt={tr(`фото ${viewerIndex + 1}`, `photo ${viewerIndex + 1}`)}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              transform: `scale(${zoom})`,
              transformOrigin: 'center',
              transition: 'transform 0.15s ease-out',
            }}
          />

          <div onClick={(e) => e.stopPropagation()} className="requests-viewer-zoom">
            <button
              type="button"
              onClick={() => { haptic(); setZoom((z) => Math.max(1, +(z - 0.25).toFixed(2))); }}
              className="requests-viewer-zoom-btn"
            >
              -
            </button>
            <div className="requests-viewer-zoom-value">{Math.round(zoom * 100)}%</div>
            <button
              type="button"
              onClick={() => { haptic(); setZoom((z) => Math.min(4, +(z + 0.25).toFixed(2))); }}
              className="requests-viewer-zoom-btn"
            >
              +
            </button>
            <button
              type="button"
              onClick={() => { haptic(); setZoom(1); }}
              className="requests-viewer-zoom-btn"
            >
              1:1
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function RequestCard({ req, onClose, onNavigate, locale, tr }) {
  const [showMedia, setShowMedia] = useState(false);
  const isClosed = req.status === 'closed';
  const typeTitles = {
    order_request: tr('Заявка на заказ', 'Order request'),
    question: tr('Вопрос от клиента', 'Client question'),
    media: tr('Медиафайл', 'Media file'),
    default: tr('Заявка', 'Request'),
  };
  const typeInfo = { title: typeTitles[req.type] || typeTitles.default };
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

  const typeIcon = TYPE_ICONS[req.type] || TYPE_ICONS.default;

  return (
    <article className={`requests-card${isClosed ? ' is-closed' : ''}`}>
      <div className="requests-card-head">
        <div className="requests-card-type">
          <span className="requests-card-type-icon">{typeIcon}</span>
          <span>{typeInfo.title}</span>
        </div>
        <span className="requests-card-time">{formatDate(req.created_at, locale, tr)}</span>
      </div>

      <div className="requests-card-client">{req.client_name}</div>

      {req.client_phone && <div className="requests-card-meta">{tr('Тел', 'Phone')}: {req.client_phone}</div>}
      {req.service_name && <div className="requests-card-meta">{tr('Услуга', 'Service')}: {req.service_name}</div>}
      {req.desired_date && (
        <div className="requests-card-meta">
          {tr('Когда', 'When')}: {req.desired_date}{req.desired_time ? tr(` в ${req.desired_time}`, ` at ${req.desired_time}`) : ''}
        </div>
      )}
      {req.text && <div className="requests-card-message">"{req.text}"</div>}

      {hasMedia && (
        <div>
          <button
            type="button"
            onClick={() => { haptic(); setShowMedia(v => !v); }}
            className="requests-media-toggle"
          >
            {tr('Вложения', 'Attachments')}{mediaCount > 0 ? ` (${mediaCount})` : ''} {showMedia ? '▲' : '▼'}
          </button>
          {showMedia && <MediaPreview reqId={req.id} legacyFileId={req.file_id} tr={tr} />}
        </div>
      )}

      <div className="requests-actions">
        <div className="requests-actions-row">
          <ActionBtn onClick={handleContact} accent>{tr('Написать', 'Message')}</ActionBtn>
          {req.client_id && <ActionBtn onClick={handleOpenClient}>{tr('Клиент', 'Client')}</ActionBtn>}
        </div>
        {req.type === 'order_request' && !isClosed && (
          <ActionBtn onClick={handleCreateOrder}>{tr('Создать заказ', 'Create order')}</ActionBtn>
        )}
        {!isClosed && (
          <ActionBtn onClick={() => { haptic(); onClose(req.id); }} small>
            {tr('Закрыть заявку', 'Close request')}
          </ActionBtn>
        )}
      </div>
    </article>
  );
}

export default function Requests({ onNavigate, onBadgeChange }) {
  const { tr, locale } = useI18n();
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
          requests: old.requests.map(r => (
            r.id === requestId ? { ...r, status: 'closed' } : r
          )),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['master-requests'] });
    },
  });

  const requests = data?.requests || [];
  const unreadCount = data?.unread_count ?? 0;

  const handleNavigate = useCallback(
    (type, params) => {
      if (onNavigate) onNavigate(type, params);
    },
    [onNavigate],
  );

  return (
    <div className="requests-page">
      <div className="requests-header">
        <h1>{tr('Заявки', 'Requests')}</h1>
        {unreadCount > 0 && <span className="requests-unread-pill">{tr('Новых', 'New')}: {unreadCount}</span>}
      </div>

      <FilterTabs active={filter} onChange={setFilter} tr={tr} />

      <div className="requests-list-wrap">
        {isLoading && (
          <div className="requests-screen-state">
            <p>{tr('Загрузка...', 'Loading...')}</p>
          </div>
        )}

        {isError && (
          <div className="requests-screen-state">
            <p>{tr('Не удалось загрузить заявки', 'Failed to load requests')}</p>
            <button type="button" onClick={() => refetch()} className="requests-retry-btn">
              {tr('Повторить', 'Retry')}
            </button>
          </div>
        )}

        {!isLoading && !isError && requests.length === 0 && (
          <div className="requests-screen-state">
            <p>{filter === 'new' ? tr('Новых заявок нет', 'No new requests') : tr('Заявок нет', 'No requests')}</p>
          </div>
        )}

        {!isLoading && !isError && requests.map((req) => (
          <RequestCard
            key={req.id}
            req={req}
            onClose={(id) => closeMutation.mutate(id)}
            onNavigate={handleNavigate}
            locale={locale}
            tr={tr}
          />
        ))}
      </div>
    </div>
  );
}
