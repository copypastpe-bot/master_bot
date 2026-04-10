import { useState, useEffect, useRef, useCallback } from 'react';
import { getMasterClients } from '../../api/client';
import ClientAddSheet from '../components/ClientAddSheet';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function haptic(type = 'light') {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred(type);
  }
}

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const ClearIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

export default function ClientsList({ onNavigate }) {
  const { tr } = useI18n();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [clients, setClients] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const [showAddSheet, setShowAddSheet] = useState(false);

  const sentinelRef = useRef(null);
  const debounceRef = useRef(null);

  // Debounce search query
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  // Reset list when query changes
  useEffect(() => {
    setClients([]);
    setPage(1);
    setTotalPages(1);
    setLoading(true);
    setError(null);
  }, [debouncedQuery]);

  // Fetch clients
  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        if (page === 1) setLoading(true);
        else setLoadingMore(true);

        const data = await getMasterClients(debouncedQuery, page);
        if (!cancelled) {
          setClients(prev => page === 1 ? (data.clients || []) : [...prev, ...(data.clients || [])]);
          setTotalPages(data.pages || 1);
        }
      } catch (e) {
        if (!cancelled) setError(tr('Не удалось загрузить клиентов', 'Failed to load clients'));
      } finally {
        if (!cancelled) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    };
    fetch();
    return () => { cancelled = true; };
  }, [debouncedQuery, page]);

  // Infinite scroll via IntersectionObserver
  const handleObserver = useCallback((entries) => {
    const [entry] = entries;
    if (entry.isIntersecting && !loadingMore && !loading && page < totalPages) {
      setPage(p => p + 1);
    }
  }, [loadingMore, loading, page, totalPages]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(handleObserver, { rootMargin: '100px' });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [handleObserver]);

  const handleClear = () => {
    haptic();
    setQuery('');
  };

  const handleClientAdded = (client) => {
    haptic('medium');
    setShowAddSheet(false);
    setQuery('');
    setDebouncedQuery('');
    setClients([]);
    setPage(1);
    setTotalPages(1);
    onNavigate('client', { id: client.id });
  };

  const handleClientClick = (client) => {
    haptic();
    onNavigate('client', { id: client.id });
  };

  const formatPhone = (phone) => phone || tr('—', '—');

  const formatBalance = (balance) => {
    if (!balance) return null;
    return `🎁 ${balance}`;
  };

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Search bar */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        background: 'var(--tg-bg)',
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'var(--tg-secondary-bg)',
          borderRadius: 12,
          padding: '8px 12px',
          transition: 'box-shadow 0.15s',
        }}>
          <span style={{ color: 'var(--tg-hint)', flexShrink: 0 }}>
            <SearchIcon />
          </span>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={tr('Имя или телефон...', 'Name or phone...')}
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              fontSize: 15,
              color: 'var(--tg-text)',
            }}
          />
          {query && (
            <button
              onClick={handleClear}
              style={{
                background: 'none',
                border: 'none',
                padding: 2,
                cursor: 'pointer',
                color: 'var(--tg-hint)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <ClearIcon />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {loading && (
        <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
          {tr('Загрузка...', 'Loading...')}
        </div>
      )}

      {error && !loading && (
        <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
          {error}
        </div>
      )}

      {!loading && !error && clients.length === 0 && (
        <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
          {debouncedQuery
            ? tr(`Никого не нашли по запросу «${debouncedQuery}»`, `No clients found for “${debouncedQuery}”`)
            : tr('У вас пока нет клиентов. Отправьте инвайт-ссылку!', 'You have no clients yet. Share your invite link!')}
        </div>
      )}

      {!loading && clients.length > 0 && (
        <div style={{ background: 'var(--tg-section-bg)' }}>
          {clients.map((client, idx) => (
            <div
              key={client.id}
              onClick={() => handleClientClick(client)}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '12px 16px',
                cursor: 'pointer',
                borderBottom: idx < clients.length - 1
                  ? '1px solid var(--tg-secondary-bg)'
                  : 'none',
                gap: 12,
              }}
            >
              {/* Avatar */}
              <div style={{
                width: 42,
                height: 42,
                borderRadius: '50%',
                background: 'var(--tg-accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 600,
                fontSize: 16,
                flexShrink: 0,
              }}>
                {(client.name || '?')[0].toUpperCase()}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 15,
                  fontWeight: 500,
                  color: 'var(--tg-text)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {client.name || '—'}
                </div>
                <div style={{ fontSize: 13, color: 'var(--tg-hint)', marginTop: 2, display: 'flex', gap: 8 }}>
                  <span>{formatPhone(client.phone)}</span>
                  {client.order_count > 0 && (
                    <span>{tr(`· ${client.order_count} заказов`, `· ${client.order_count} orders`)}</span>
                  )}
                </div>
              </div>

              {/* Bonus balance */}
              {client.bonus_balance > 0 && (
                <div style={{
                  fontSize: 13,
                  color: 'var(--tg-accent)',
                  fontWeight: 500,
                  flexShrink: 0,
                }}>
                  {formatBalance(client.bonus_balance)}
                </div>
              )}

              {/* Chevron */}
              <span style={{ color: 'var(--tg-hint)', fontSize: 18 }}>›</span>
            </div>
          ))}
        </div>
      )}

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} style={{ height: 1 }} />

      {loadingMore && (
        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13 }}>
          {tr('Загрузка...', 'Loading...')}
        </div>
      )}

      {/* FAB: Add client */}
      <button
        onClick={() => { haptic(); setShowAddSheet(true); }}
        style={{
          position: 'fixed',
          bottom: 90,
          right: 20,
          width: 52,
          height: 52,
          borderRadius: '50%',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          fontSize: 26,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          boxShadow: '0 2px 12px rgba(0,0,0,0.25)',
          zIndex: 20,
        }}
      >
        +
      </button>

      {showAddSheet && (
        <ClientAddSheet
          onSuccess={handleClientAdded}
          onClose={() => setShowAddSheet(false)}
        />
      )}
    </div>
  );
}
