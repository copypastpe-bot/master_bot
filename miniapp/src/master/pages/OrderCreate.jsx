import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  searchMasterClients,
  getMasterClients,
  getMasterServices,
  createMasterOrder,
  getLastClientAddress,
  getMasterMe,
  getMasterClientAddresses,
  createMasterClientAddress,
  updateMasterProfile,
} from '../../api/client';
import { useBackButton } from '../hooks/useBackButton';
import ClientAddSheet from '../components/ClientAddSheet';
import { useI18n } from '../../i18n';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

// ─── helpers ────────────────────────────────────────────────────────────────

function toYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatDateLocal(dateStr, locale) {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' });
}

function get14Days() {
  const days = [];
  const today = new Date();
  for (let i = 0; i < 14; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    days.push(toYMD(d));
  }
  return days;
}

const TIME_PRESETS = [
  '08:00', '09:00', '10:00', '11:00', '12:00', '13:00',
  '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00',
];

// ─── Progress bar ────────────────────────────────────────────────────────────

function ProgressBar({ step }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '12px 16px',
    }}>
      {[1, 2, 3, 4].map((s) => (
        <div
          key={s}
          style={{
            width: s === step ? 24 : 8,
            height: 8,
            borderRadius: 4,
            background: s === step
              ? 'var(--tg-button)'
              : s < step
              ? 'var(--tg-button)'
              : 'var(--tg-hint)',
            opacity: s < step ? 0.45 : 1,
            transition: 'all 0.25s ease',
          }}
        />
      ))}
    </div>
  );
}

// ─── Step 1: Client search ───────────────────────────────────────────────────

function StepClient({ selected, onSelect, onNext }) {
  const { tr } = useI18n();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [showAddSheet, setShowAddSheet] = useState(false);
  const timerRef = useRef(null);

  // Clear pending debounce timer on unmount to prevent state update after unmount
  useEffect(() => () => clearTimeout(timerRef.current), []);

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(val), 300);
  };

  const { data, isFetching } = useQuery({
    queryKey: ['master-client-search', debouncedQuery],
    queryFn: () => searchMasterClients(debouncedQuery),
    enabled: debouncedQuery.length > 0,
    staleTime: 30 * 1000,
  });

  const { data: allClientsData, isFetching: allClientsFetching } = useQuery({
    queryKey: ['master-clients-all-order'],
    queryFn: () => getMasterClients('', 1),
    staleTime: 60_000,
  });

  const clients = data?.clients || [];

  const allClients = [...(allClientsData?.clients || [])].sort((a, b) =>
    a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })
  );

  const searchClients = [...clients].sort((a, b) =>
    a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })
  );

  const visibleClients = debouncedQuery.length > 0 ? searchClients : allClients;
  const isLoadingClients = debouncedQuery.length > 0 ? isFetching : allClientsFetching;

  return (
    <div style={{ padding: '0 16px 16px' }}>
      {/* Search + add-client row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          type="text"
          value={query}
          onChange={handleChange}
          placeholder={tr('Поиск клиента...', 'Search client...')}
          style={{
            flex: 1,
            padding: '10px 12px',
            fontSize: 15,
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-text)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10,
            outline: 'none',
          }}
        />
        {!selected && (
          <button
            type="button"
            onClick={() => { haptic(); setShowAddSheet(true); }}
            style={{
              flexShrink: 0,
              padding: '10px 14px',
              background: 'none',
              border: '1.5px solid var(--tg-button)',
              borderRadius: 10,
              color: 'var(--tg-button)',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {tr('+ Клиент', '+ Client')}
          </button>
        )}
      </div>

      {/* Selected client chip */}
      {selected && (
        <div style={{
          marginBottom: 12,
          padding: '10px 12px',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          borderRadius: 10,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>{selected.name}</div>
            <div style={{ fontSize: 12, opacity: 0.85 }}>{selected.phone}</div>
          </div>
          <button
            type="button"
            onClick={() => { haptic(); onSelect(null); }}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'var(--tg-button-text)',
              borderRadius: 6,
              padding: '4px 8px',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {tr('Изменить', 'Change')}
          </button>
        </div>
      )}

      {/* Client list */}
      {!selected && (
        <div className="enterprise-cell-group" style={{ marginBottom: 16 }}>
          {isLoadingClients && (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13 }}>
              {tr('Загрузка...', 'Loading...')}
            </div>
          )}
          {!isLoadingClients && visibleClients.length === 0 && (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13 }}>
              {debouncedQuery
                ? tr('Клиенты не найдены', 'No clients found')
                : tr('Нет клиентов', 'No clients')}
            </div>
          )}
          {visibleClients.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => { haptic(); onSelect(c); }}
              className="enterprise-cell is-interactive"
              style={{ borderBottom: 'none' }}
            >
              <div style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: 'var(--tg-accent)',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: 14,
                flexShrink: 0,
              }}>
                {(c.name || '?')[0].toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--tg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--tg-hint)' }}>{c.phone}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Next button */}
      <button
        type="button"
        onClick={() => { haptic(); onNext(); }}
        disabled={!selected}
        className="enterprise-btn-primary"
        style={!selected ? { opacity: 0.45, cursor: 'not-allowed' } : {}}
      >
        {tr('Далее →', 'Next ->')}
      </button>

      {showAddSheet && (
        <ClientAddSheet
          onSuccess={(client) => {
            haptic();
            setShowAddSheet(false);
            onSelect(client);
            onNext();
          }}
          onClose={() => setShowAddSheet(false)}
        />
      )}
    </div>
  );
}

// ─── Step 2: Services ────────────────────────────────────────────────────────

function StepServices({ selected, onSelect, onNext, onBack }) {
  const { tr, locale } = useI18n();
  const [custom, setCustom] = useState({ name: '', price: '' });
  const [showCustom, setShowCustom] = useState(false);
  const [customList, setCustomList] = useState([]);
  // price overrides for services without a set price
  const [priceOverrides, setPriceOverrides] = useState({});

  const { data } = useQuery({
    queryKey: ['master-services'],
    queryFn: getMasterServices,
    staleTime: 5 * 60 * 1000,
  });

  const services = data?.services || [];

  const isSelected = (id) => selected.some((s) => s.service_id === id);

  const toggleService = (svc) => {
    haptic();
    if (isSelected(svc.id)) {
      onSelect(selected.filter((s) => s.service_id !== svc.id));
    } else {
      const price = svc.price || priceOverrides[svc.id] || 0;
      onSelect([...selected, { service_id: svc.id, name: svc.name, price }]);
    }
  };

  const updateServicePrice = (svcId, rawVal) => {
    const price = parseInt(rawVal, 10) || 0;
    setPriceOverrides((prev) => ({ ...prev, [svcId]: price }));
    onSelect(selected.map((s) =>
      s.service_id === svcId ? { ...s, price } : s
    ));
  };

  const toggleCustom = (idx) => {
    haptic();
    const key = `custom_${idx}`;
    if (selected.some((s) => s._key === key)) {
      onSelect(selected.filter((s) => s._key !== key));
    } else {
      onSelect([...selected, { ...customList[idx], _key: key }]);
    }
  };

  const addCustom = () => {
    const price = parseInt(custom.price, 10);
    if (!custom.name.trim() || !price || price <= 0) return;
    haptic();
    const idx = customList.length;
    const newItem = { name: custom.name.trim(), price };
    const key = `custom_${idx}`;
    setCustomList([...customList, newItem]);
    onSelect([...selected, { ...newItem, _key: key }]);
    setCustom({ name: '', price: '' });
    setShowCustom(false);
  };

  const total = selected.reduce((sum, s) => sum + (s.price || 0), 0);
  const canNext = selected.length > 0 && selected.every((s) => s.price > 0);

  return (
    <div style={{ padding: '0 16px 16px' }}>
      {services.map((svc) => {
        const sel = isSelected(svc.id);
        const noPrice = !svc.price;
        return (
          <div key={svc.id}>
            <button
              onClick={() => toggleService(svc)}
              style={{
                width: '100%',
                padding: '11px 12px',
                background: sel ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                color: sel ? 'var(--tg-button-text)' : 'var(--tg-text)',
                border: 'none',
                borderRadius: noPrice && sel ? '10px 10px 0 0' : 10,
                marginBottom: noPrice && sel ? 0 : 6,
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: 14, fontWeight: sel ? 600 : 400 }}>
                {sel ? '✓ ' : ''}{svc.name}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>
                {svc.price ? `${svc.price.toLocaleString(locale)} ₽` : tr('цена не указана', 'price not specified')}
              </span>
            </button>
            {sel && noPrice && (
              <div style={{
                background: 'var(--tg-button)',
                borderRadius: '0 0 10px 10px',
                padding: '0 12px 10px',
                marginBottom: 6,
              }}>
                <input
                  type="number"
                  placeholder={tr('Введите цену ₽', 'Enter price ₽')}
                  value={priceOverrides[svc.id] || ''}
                  onChange={(e) => updateServicePrice(svc.id, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    width: '100%',
                    padding: '6px 10px',
                    fontSize: 14,
                    background: 'rgba(255,255,255,0.2)',
                    color: 'var(--tg-button-text)',
                    border: '1px solid rgba(255,255,255,0.4)',
                    borderRadius: 8,
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
            )}
          </div>
        );
      })}

      {customList.map((item, idx) => {
        const key = `custom_${idx}`;
        const isSel = selected.some((s) => s._key === key);
        return (
          <button
            key={key}
            onClick={() => toggleCustom(idx)}
            style={{
              width: '100%',
              padding: '11px 12px',
              background: isSel ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
              color: isSel ? 'var(--tg-button-text)' : 'var(--tg-text)',
              border: '1px dashed var(--tg-hint)',
              borderRadius: 10,
              marginBottom: 6,
              textAlign: 'left',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ fontSize: 14, fontWeight: isSel ? 600 : 400 }}>
              {isSel ? '✓ ' : ''}{item.name}
            </span>
            <span style={{ fontSize: 13, fontWeight: 600 }}>{item.price.toLocaleString(locale)} ₽</span>
          </button>
        );
      })}

      {showCustom ? (
        <div style={{
          padding: 12,
          background: 'var(--tg-secondary-bg)',
          borderRadius: 10,
          marginBottom: 8,
        }}>
          <input
            type="text"
            placeholder={tr('Название услуги', 'Service name')}
            value={custom.name}
            onChange={(e) => setCustom({ ...custom, name: e.target.value })}
            style={{
              width: '100%',
              padding: '8px 10px',
              fontSize: 14,
              background: 'var(--tg-bg)',
              color: 'var(--tg-text)',
              border: '1px solid var(--tg-hint)',
              borderRadius: 8,
              outline: 'none',
              marginBottom: 8,
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="number"
              placeholder={tr('Цена ₽', 'Price ₽')}
              value={custom.price}
              onChange={(e) => setCustom({ ...custom, price: e.target.value })}
              style={{
                flex: 1,
                padding: '8px 10px',
                fontSize: 14,
                background: 'var(--tg-bg)',
                color: 'var(--tg-text)',
                border: '1px solid var(--tg-hint)',
                borderRadius: 8,
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
            <button
              onClick={addCustom}
              disabled={!custom.name.trim() || !custom.price}
              style={{
                padding: '8px 16px',
                background: 'var(--tg-button)',
                color: 'var(--tg-button-text)',
                border: 'none',
                borderRadius: 8,
                fontSize: 14,
                cursor: 'pointer',
                opacity: (!custom.name.trim() || !custom.price) ? 0.5 : 1,
              }}
            >
              {tr('Добавить', 'Add')}
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => { haptic(); setShowCustom(true); }}
          style={{
            width: '100%',
            padding: '10px',
            background: 'none',
            color: 'var(--tg-button)',
            border: '1px dashed var(--tg-button)',
            borderRadius: 10,
            fontSize: 14,
            cursor: 'pointer',
            marginBottom: 8,
          }}
        >
          {tr('+ Произвольная услуга', '+ Custom service')}
        </button>
      )}

      {selected.length > 0 && (
        <div style={{
          padding: '10px 12px',
          background: 'var(--tg-secondary-bg)',
          borderRadius: 10,
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}>
          <span style={{ color: 'var(--tg-hint)', fontSize: 14 }}>{tr('Итого', 'Total')}</span>
          <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--tg-text)' }}>
            {total.toLocaleString(locale)} ₽
          </span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button
          onClick={() => { haptic(); onBack(); }}
          style={{
            flex: 1,
            padding: '13px',
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 15,
            cursor: 'pointer',
          }}
        >
          {tr('← Назад', '← Back')}
        </button>
        <button
          onClick={() => { haptic(); onNext(); }}
          disabled={!canNext}
          style={{
            flex: 2,
            padding: '13px',
            background: canNext ? 'var(--tg-button)' : 'var(--tg-hint)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 15,
            fontWeight: 600,
            cursor: canNext ? 'pointer' : 'not-allowed',
            opacity: canNext ? 1 : 0.5,
          }}
        >
          {tr('Далее →', 'Next ->')}
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Date / time / address ──────────────────────────────────────────

function StepDateTime({
  clientId,
  date,
  setDate,
  time,
  setTime,
  address,
  setAddress,
  onNext,
  onBack,
  workMode,
  masterDefaultAddress,
}) {
  const { tr, locale } = useI18n();
  const queryClient = useQueryClient();
  const days14 = get14Days();
  const isHomeMode = workMode === 'home';
  const [addressLabel, setAddressLabel] = useState('');
  const [addressError, setAddressError] = useState('');
  const normalizedAddress = (address || '').trim();

  // Prefill last address in travel mode.
  const { data: lastAddr } = useQuery({
    queryKey: ['last-address', clientId],
    queryFn: () => getLastClientAddress(clientId),
    enabled: !!clientId && !isHomeMode,
    staleTime: 60 * 1000,
  });

  const { data: addressesData } = useQuery({
    queryKey: ['client-addresses', clientId],
    queryFn: () => getMasterClientAddresses(clientId),
    enabled: !!clientId && !isHomeMode,
    staleTime: 60 * 1000,
  });
  const savedAddresses = addressesData?.addresses || [];

  const saveClientAddressMutation = useMutation({
    mutationFn: (payload) => createMasterClientAddress(clientId, payload),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['client-addresses', clientId] });
      if (saved?.address) {
        setAddress(saved.address);
      }
      setAddressLabel('');
      setAddressError('');
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(tr('Адрес клиента сохранён', 'Client address saved'));
      }
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || tr('Не удалось сохранить адрес', 'Failed to save address');
      setAddressError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const saveMasterDefaultAddressMutation = useMutation({
    mutationFn: (value) => updateMasterProfile({ work_address_default: value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['master-me'] });
    },
  });

  useEffect(() => {
    if (isHomeMode) {
      if (!address && masterDefaultAddress) {
        setAddress(masterDefaultAddress);
      }
      return;
    }

    if (savedAddresses.length > 0 && !address) {
      const preferred = savedAddresses.find((item) => item.is_default) || savedAddresses[0];
      if (preferred?.address) {
        setAddress(preferred.address);
        return;
      }
    }
    if (lastAddr?.address && !address) {
      setAddress(lastAddr.address);
    }
  }, [isHomeMode, masterDefaultAddress, savedAddresses, lastAddr, address, setAddress]);

  const canNext = !!date && !!time && !!normalizedAddress;

  const handleSaveClientAddress = async () => {
    haptic('medium');
    setAddressError('');
    if (!normalizedAddress) {
      setAddressError(tr('Введите адрес для сохранения', 'Enter address to save'));
      return;
    }
    try {
      await saveClientAddressMutation.mutateAsync({
        address: normalizedAddress,
        label: addressLabel || undefined,
        make_default: false,
      });
    } catch (_) {
      // Error is handled in mutation onError.
    }
  };

  const handleNext = async () => {
    haptic();
    setAddressError('');
    if (!canNext) {
      return;
    }
    if (isHomeMode) {
      const baseline = (masterDefaultAddress || '').trim();
      if (normalizedAddress !== baseline) {
        try {
          await saveMasterDefaultAddressMutation.mutateAsync(normalizedAddress);
        } catch (error) {
          const msg = error?.response?.data?.detail || tr('Не удалось сохранить ваш адрес', 'Failed to save your address');
          setAddressError(typeof msg === 'string' ? msg : JSON.stringify(msg));
          return;
        }
      }
    }
    onNext();
  };

  return (
    <div style={{ padding: '0 16px 16px' }}>
      {/* Mini calendar: 2 weeks grid */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 6px' }}>{tr('Дата', 'Date')}</p>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 4,
        marginBottom: 16,
      }}>
        {days14.map((d) => {
          const dayOfWeek = new Date(d + 'T12:00:00').getDay();
          const dayNum = parseInt(d.split('-')[2], 10);
          const isSelected = d === date;
          const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
          return (
            <button
              key={d}
              onClick={() => { haptic(); setDate(d); }}
              style={{
                padding: '6px 2px',
                background: isSelected ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                color: isSelected
                  ? 'var(--tg-button-text)'
                  : isWeekend
                  ? 'var(--tg-destructive, #e53935)'
                  : 'var(--tg-text)',
                border: 'none',
                borderRadius: 8,
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <span style={{ fontSize: 9, opacity: 0.7 }}>
                {new Date(d + 'T12:00:00').toLocaleDateString(locale, { weekday: 'short' })}
              </span>
              <span style={{ fontSize: 14, fontWeight: isSelected ? 700 : 400 }}>{dayNum}</span>
            </button>
          );
        })}
      </div>

      {/* Time presets */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 6px' }}>{tr('Время', 'Time')}</p>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 6,
        marginBottom: 8,
      }}>
        {TIME_PRESETS.map((t) => (
          <button
            key={t}
            onClick={() => { haptic(); setTime(t); }}
            style={{
              padding: '6px 10px',
              background: time === t ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
              color: time === t ? 'var(--tg-button-text)' : 'var(--tg-text)',
              border: 'none',
              borderRadius: 8,
              fontSize: 13,
              cursor: 'pointer',
              fontWeight: time === t ? 600 : 400,
            }}
          >
            {t}
          </button>
        ))}
        {/* Custom time input */}
        <input
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          style={{
            padding: '6px 10px',
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-text)',
            border: '1px solid var(--tg-hint)',
            borderRadius: 8,
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Address */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '16px 0 6px' }}>
        {isHomeMode ? tr('Ваш адрес', 'Your address') : tr('Адрес клиента', 'Client address')}
      </p>
      {!isHomeMode && savedAddresses.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
          {savedAddresses.map((item) => {
            const active = item.address === address;
            const label = item.label ? `${item.label}: ${item.address}` : item.address;
            return (
              <button
                key={item.id}
                onClick={() => { haptic(); setAddress(item.address); }}
                style={{
                  padding: '6px 10px',
                  background: active ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
                  color: active ? 'var(--tg-button-text)' : 'var(--tg-text)',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                {item.is_default ? '✓ ' : ''}{label}
              </button>
            );
          })}
        </div>
      )}
      <input
        type="text"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder={isHomeMode ? tr('Ваш адрес по умолчанию', 'Your default address') : tr('Адрес клиента', 'Client address')}
        style={{
          width: '100%',
          padding: '10px 12px',
          fontSize: 14,
          background: 'var(--tg-secondary-bg)',
          color: 'var(--tg-text)',
          border: '1px solid var(--tg-hint)',
          borderRadius: 10,
          outline: 'none',
          marginBottom: 20,
          boxSizing: 'border-box',
        }}
      />
      {!isHomeMode && (
        <div style={{ display: 'flex', gap: 8, margin: '0 0 20px' }}>
          <input
            type="text"
            value={addressLabel}
            onChange={(e) => setAddressLabel(e.target.value)}
            placeholder={tr('Метка (дом, работа...)', 'Label (home, office...)')}
            style={{
              flex: 1,
              padding: '10px 12px',
              fontSize: 13,
              background: 'var(--tg-secondary-bg)',
              color: 'var(--tg-text)',
              border: '1px solid var(--tg-hint)',
              borderRadius: 10,
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          <button
            onClick={handleSaveClientAddress}
            disabled={!normalizedAddress || saveClientAddressMutation.isPending}
            style={{
              padding: '10px 12px',
              border: 'none',
              borderRadius: 10,
              background: normalizedAddress ? 'var(--tg-button)' : 'var(--tg-hint)',
              color: 'var(--tg-button-text)',
              fontSize: 13,
              fontWeight: 600,
              cursor: normalizedAddress ? 'pointer' : 'not-allowed',
              opacity: saveClientAddressMutation.isPending ? 0.65 : 1,
            }}
          >
            {saveClientAddressMutation.isPending ? tr('Сохр...', 'Saving...') : tr('Сохранить', 'Save')}
          </button>
        </div>
      )}
      {isHomeMode && (
        <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '4px 0 20px' }}>
          {tr('Этот адрес будет использоваться по умолчанию для заказов в режиме «дома».', 'This address will be used by default for home-mode orders.')}
        </p>
      )}
      {!!addressError && (
        <p style={{ color: 'var(--tg-destructive, #e53935)', fontSize: 13, margin: '0 0 12px' }}>
          {addressError}
        </p>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={() => { haptic(); onBack(); }}
          style={{
            flex: 1,
            padding: '13px',
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 15,
            cursor: 'pointer',
          }}
        >
          {tr('← Назад', '← Back')}
        </button>
        <button
          onClick={handleNext}
          disabled={!canNext}
          style={{
            flex: 2,
            padding: '13px',
            background: canNext ? 'var(--tg-button)' : 'var(--tg-hint)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 15,
            fontWeight: 600,
            cursor: canNext ? 'pointer' : 'not-allowed',
            opacity: canNext ? 1 : 0.5,
          }}
        >
          {tr('Далее →', 'Next ->')}
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: Summary ─────────────────────────────────────────────────────────

function StepSummary({ client, services, date, time, address, onBack, onCreated }) {
  const { tr, locale } = useI18n();
  const [error, setError] = useState('');

  const total = services.reduce((sum, s) => sum + (s.price || 0), 0);

  const mutation = useMutation({
    mutationFn: createMasterOrder,
    onSuccess: (order) => {
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
      onCreated(order);
    },
    onError: (err) => {
      const msg = err?.response?.data?.detail || tr('Ошибка при создании заказа', 'Failed to create order');
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      if (typeof WebApp?.MainButton?.enable === 'function') {
        WebApp.MainButton.enable();
      }
      if (typeof WebApp?.MainButton?.setText === 'function') {
        WebApp.MainButton.setText(tr('Создать заказ', 'Create order'));
      }
    },
  });

  const handleCreate = useCallback(() => {
    if (mutation.isPending) return;
    setError('');

    const payload = {
      client_id: client.id,
      services: services.map((s) => ({
        ...(s.service_id != null ? { service_id: s.service_id } : {}),
        ...(s.service_id == null ? { name: s.name } : {}),
        price: s.price,
      })),
      scheduled_date: date,
      scheduled_time: time,
      address: address,
    };

    mutation.mutate(payload);
  }, [mutation, client, services, date, time, address]);

  // MainButton setup
  useEffect(() => {
    if (typeof WebApp?.MainButton?.setText === 'function') {
      WebApp.MainButton.setText(tr('Создать заказ', 'Create order'));
    }
    if (typeof WebApp?.MainButton?.show === 'function') {
      WebApp.MainButton.show();
    }
    if (typeof WebApp?.MainButton?.enable === 'function') {
      WebApp.MainButton.enable();
    }
    if (typeof WebApp?.MainButton?.onClick === 'function') {
      WebApp.MainButton.onClick(handleCreate);
    }
    return () => {
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
      if (typeof WebApp?.MainButton?.offClick === 'function') {
        WebApp.MainButton.offClick(handleCreate);
      }
    };
  }, [handleCreate, tr]);

  // Loading state
  useEffect(() => {
    if (mutation.isPending) {
      if (typeof WebApp?.MainButton?.disable === 'function') WebApp.MainButton.disable();
      if (typeof WebApp?.MainButton?.setText === 'function') WebApp.MainButton.setText(tr('Создаём...', 'Creating...'));
    } else if (!mutation.isSuccess) {
      if (typeof WebApp?.MainButton?.enable === 'function') WebApp.MainButton.enable();
      if (typeof WebApp?.MainButton?.setText === 'function') WebApp.MainButton.setText(tr('Создать заказ', 'Create order'));
    }
  }, [mutation.isPending, mutation.isSuccess, tr]);

  return (
    <div style={{ padding: '0 16px 16px' }}>
      <div style={{
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}>
        <SummaryRow label={tr('Клиент', 'Client')} value={client.name} />
        <SummaryRow label={tr('Телефон', 'Phone')} value={client.phone || '—'} />
      </div>

      <div style={{
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}>
        <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 8px' }}>{tr('Услуги', 'Services')}</p>
        {services.map((s, idx) => (
          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 14, color: 'var(--tg-text)' }}>{s.name}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-text)' }}>
              {s.price.toLocaleString(locale)} ₽
            </span>
          </div>
        ))}
        <div style={{
          borderTop: '1px solid var(--tg-hint)',
          marginTop: 8,
          paddingTop: 8,
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--tg-text)' }}>{tr('Итого', 'Total')}</span>
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--tg-text)' }}>
            {total.toLocaleString(locale)} ₽
          </span>
        </div>
      </div>

      <div style={{
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 20,
      }}>
        <SummaryRow label={tr('Дата', 'Date')} value={formatDateLocal(date, locale)} />
        <SummaryRow label={tr('Время', 'Time')} value={time} />
        {address && <SummaryRow label={tr('Адрес', 'Address')} value={address} />}
      </div>

      {error && (
        <div style={{
          padding: '10px 12px',
          background: 'rgba(229,57,53,0.1)',
          color: 'var(--tg-destructive, #e53935)',
          borderRadius: 10,
          fontSize: 13,
          marginBottom: 16,
        }}>
          {error}
        </div>
      )}

      <button
        onClick={() => { haptic(); onBack(); }}
        disabled={mutation.isPending}
        style={{
          width: '100%',
          padding: '13px',
          background: 'var(--tg-secondary-bg)',
          color: 'var(--tg-text)',
          border: 'none',
          borderRadius: 12,
          fontSize: 15,
          cursor: 'pointer',
          opacity: mutation.isPending ? 0.5 : 1,
        }}
      >
        {tr('← Назад', '← Back')}
      </button>
    </div>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
      <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>{label}</span>
      <span style={{ fontSize: 14, color: 'var(--tg-text)', fontWeight: 500 }}>{value}</span>
    </div>
  );
}

// ─── Success screen ──────────────────────────────────────────────────────────

function SuccessScreen({ order, onBack }) {
  const { tr } = useI18n();
  useEffect(() => {
    if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
      WebApp.HapticFeedback.notificationOccurred('success');
    }
  }, []);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      padding: '0 24px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 56, marginBottom: 16 }}>✅</div>
      <h2 style={{ margin: '0 0 8px', color: 'var(--tg-text)', fontSize: 20 }}>
        {tr('Заказ создан!', 'Order created!')}
      </h2>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: '0 0 32px' }}>
        {tr(`Заказ #${order?.id} успешно добавлен в расписание`, `Order #${order?.id} added to schedule successfully`)}
      </p>
      <button
        onClick={() => { haptic(); onBack(); }}
        style={{
          padding: '13px 32px',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 12,
          fontSize: 15,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        {tr('Вернуться к расписанию', 'Back to schedule')}
      </button>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function OrderCreate({ params, onBack, onCreated }) {
  const { tr } = useI18n();
  const prefill = params?.prefill;
  const prefillClientId = prefill?.client_id || params?.preselectedClientId || null;
  const prefillClientName = prefill?.client_name || params?.preselectedClientName || '';
  const prefillClient = prefillClientId
    ? { id: prefillClientId, name: prefillClientName }
    : null;

  const { data: masterData } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 60_000,
  });
  const workMode = masterData?.work_mode || 'travel';
  const masterDefaultAddress = masterData?.work_address_default || '';

  const [step, setStep] = useState(prefillClient ? 2 : 1);
  const [client, setClient] = useState(prefillClient);
  const [services, setServices] = useState([]);
  const [date, setDate] = useState(params?.date || toYMD(new Date()));
  const [time, setTime] = useState('');
  const [address, setAddress] = useState('');
  const [createdOrder, setCreatedOrder] = useState(null);

  const handleBack = useCallback(() => {
    if (step > 1) {
      setStep(s => s - 1);
    } else {
      onBack();
    }
  }, [step, onBack]);

  useBackButton(handleBack);

  const goToStep = (n) => {
    haptic();
    setStep(n);
  };

  const handleCreated = (order) => {
    setCreatedOrder(order);
    onCreated(order);
  };

  // Hide MainButton when not on step 4
  useEffect(() => {
    if (step !== 4) {
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
    }
  }, [step]);

  const TITLES = [
    tr('Выбор клиента', 'Client selection'),
    tr('Услуги', 'Services'),
    tr('Дата и время', 'Date and time'),
    tr('Подтверждение', 'Confirmation'),
  ];

  if (createdOrder) {
    return <SuccessScreen order={createdOrder} onBack={onBack} />;
  }

  return (
    <div style={{ paddingBottom: 24 }}>
      {/* Header — no custom back button: Telegram BackButton handles navigation */}
      <div style={{ padding: '12px 16px 4px', textAlign: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: 'var(--tg-text)' }}>
          {TITLES[step - 1]}
        </h2>
      </div>

      <ProgressBar step={step} />

      {step === 1 && (
        <StepClient
          selected={client}
          onSelect={setClient}
          onNext={() => goToStep(2)}
        />
      )}

      {step === 2 && (
        <StepServices
          selected={services}
          onSelect={setServices}
          onNext={() => goToStep(3)}
          onBack={() => goToStep(1)}
        />
      )}

      {step === 3 && (
        <StepDateTime
          clientId={client?.id}
          date={date}
          setDate={setDate}
          time={time}
          setTime={setTime}
          address={address}
          setAddress={setAddress}
          onNext={() => goToStep(4)}
          onBack={() => goToStep(2)}
          workMode={workMode}
          masterDefaultAddress={masterDefaultAddress}
        />
      )}

      {step === 4 && (
        <StepSummary
          client={client}
          services={services}
          date={date}
          time={time}
          address={address}
          onBack={() => goToStep(3)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
