import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterRequests, closeMasterRequest } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const REQUEST_TYPES = {
  order_request: { emoji: '🛎', title: 'Заявка на заказ' },
  question:      { emoji: '❓', title: 'Вопрос' },
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

function RequestCard({ req, onClose, onNavigate }) {
  const isClosed = req.status === 'closed';
  const typeInfo = REQUEST_TYPES[req.type] || { emoji: '📩', title: 'Заявка' };

  const handleContact = () => {
    haptic();
    if (req.client_tg_id) {
      if (typeof WebApp?.openTelegramLink === 'function') {
        WebApp.openTelegramLink(`tg://user?id=${req.client_tg_id}`);
      } else {
        window.open(`tg://user?id=${req.client_tg_id}`);
      }
    }
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
          {typeInfo.emoji} {typeInfo.title}
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
          {req.client_phone}
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
      {req.file_id && (
        <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 4 }}>
          {req.media_type === 'photo' ? '🖼 Фото' : '🎥 Видео'} · отправлено в бот
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <ActionBtn onClick={handleContact} accent>💬 Написать</ActionBtn>
          {req.type === 'order_request' && !isClosed && (
            <ActionBtn onClick={handleCreateOrder}>📋 Создать заказ</ActionBtn>
          )}
        </div>
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
        const newUnread = Math.max(0, (old.unread_count ?? 0) - 1);
        if (onBadgeChange) onBadgeChange(newUnread);
        return {
          ...old,
          unread_count: newUnread,
          requests: old.requests.map(r =>
            r.id === requestId ? { ...r, status: 'closed' } : r
          ),
        };
      });
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
