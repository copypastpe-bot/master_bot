import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterRequests, markAllRequestsRead } from '../../api/client';
import { useBackButton } from '../hooks/useBackButton';
import { useCallback } from 'react';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const TYPE_LABEL = {
  order_request: { icon: '📅', label: 'Заявка на запись' },
  question: { icon: '💬', label: 'Вопрос' },
};

function formatDate(str) {
  if (!str) return '';
  try {
    const d = new Date(str);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  } catch { return str; }
}

export default function Requests({ onBack }) {
  const queryClient = useQueryClient();

  const stableOnBack = useCallback(() => onBack(), [onBack]);
  useBackButton(stableOnBack);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['master-requests'],
    queryFn: getMasterRequests,
    staleTime: 30_000,
  });

  const markAllMutation = useMutation({
    mutationFn: markAllRequestsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['master-requests'] });
      queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    },
  });

  const requests = data?.requests || [];
  const unreadCount = requests.filter(r => !r.is_read).length;

  if (isLoading) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)', marginTop: 48 }}>
        Загрузка...
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: '16px', textAlign: 'center' }}>
        <p style={{ color: 'var(--tg-hint)', marginBottom: 12 }}>Не удалось загрузить заявки</p>
        <button onClick={refetch}
          style={{ color: 'var(--tg-button)', background: 'none', border: 'none', fontSize: 14, cursor: 'pointer' }}>
          Повторить
        </button>
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div style={{ padding: '48px 24px', textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
        <p style={{ color: 'var(--tg-text)', fontWeight: 600, marginBottom: 6 }}>Заявок пока нет</p>
        <p style={{ color: 'var(--tg-hint)', fontSize: 14 }}>
          Когда клиент отправит заявку или вопрос — они появятся здесь
        </p>
      </div>
    );
  }

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px 0',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12,
      }}>
        <h2 style={{ color: 'var(--tg-text)', fontSize: 20, fontWeight: 700, margin: 0 }}>
          Новые заявки{unreadCount > 0 && (
            <span style={{
              display: 'inline-block', background: '#e74c3c', color: '#fff',
              borderRadius: 10, fontSize: 11, fontWeight: 700,
              padding: '1px 6px', marginLeft: 6, verticalAlign: 'middle',
            }}>{unreadCount}</span>
          )}
        </h2>
        {unreadCount > 0 && (
          <button
            onClick={() => { haptic(); markAllMutation.mutate(); }}
            style={{ background: 'none', border: 'none', color: 'var(--tg-button)', fontSize: 13, cursor: 'pointer' }}>
            Прочитать все
          </button>
        )}
      </div>

      {/* Request cards */}
      <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {requests.map(req => {
          const meta = TYPE_LABEL[req.type] || { icon: '📋', label: req.type };
          return (
            <div
              key={req.id}
              style={{
                background: 'var(--tg-surface)',
                borderRadius: 14,
                padding: '14px 16px',
                borderLeft: req.is_read ? 'none' : '3px solid var(--tg-button)',
              }}
            >
              {/* Type + date */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--tg-button)' }}>
                  {meta.icon} {meta.label}
                </span>
                <span style={{ fontSize: 11, color: 'var(--tg-hint)' }}>
                  {formatDate(req.created_at)}
                </span>
              </div>

              {/* Client */}
              <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--tg-text)', marginBottom: 4 }}>
                {req.client_name}
              </div>
              {req.client_phone && (
                <a href={`tel:${req.client_phone}`}
                  style={{ fontSize: 13, color: 'var(--tg-button)', display: 'block', marginBottom: 6 }}>
                  {req.client_phone}
                </a>
              )}

              {/* Service */}
              {req.service_name && (
                <div style={{ fontSize: 14, color: 'var(--tg-text)', marginBottom: 4 }}>
                  🛠 {req.service_name}
                </div>
              )}

              {/* Desired date/time */}
              {req.desired_date && (
                <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginBottom: 4 }}>
                  📅 {req.desired_date}{req.desired_time ? ` в ${req.desired_time}` : ''}
                </div>
              )}

              {/* Text */}
              {req.text && (
                <div style={{
                  fontSize: 14, color: 'var(--tg-text)', marginTop: 6,
                  padding: '8px 10px', background: 'var(--tg-bg)', borderRadius: 8,
                  lineHeight: 1.4,
                }}>
                  {req.text}
                </div>
              )}

              {/* Media indicator */}
              {req.file_id && (
                <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 6 }}>
                  {req.media_type === 'photo' ? '🖼️ Фото в Telegram' : '🎥 Видео в Telegram'}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
