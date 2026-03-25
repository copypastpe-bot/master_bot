import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  searchMasterClients,
  getMasterServices,
  createMasterOrder,
  getLastClientAddress,
} from '../../api/client';

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

function formatDateRu(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const MONTHS = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  return `${d} ${MONTHS[m - 1]} ${y}`;
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

const DAY_SHORT = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

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
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const timerRef = useRef(null);

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(val), 300);
  };

  const { data, isFetching } = useQuery({
    queryKey: ['master-client-search', debouncedQuery],
    queryFn: () => searchMasterClients(debouncedQuery),
    enabled: debouncedQuery.length > 0,
    staleTime: 30 * 1000,
  });

  const clients = data?.clients || [];

  return (
    <div style={{ padding: '0 16px 16px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 13, margin: '0 0 8px' }}>
        Начните вводить имя или телефон
      </p>

      <input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder="Поиск клиента..."
        autoFocus
        style={{
          width: '100%',
          padding: '10px 12px',
          fontSize: 15,
          background: 'var(--tg-secondary-bg)',
          color: 'var(--tg-text)',
          border: '1px solid var(--tg-hint)',
          borderRadius: 10,
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />

      {selected && (
        <div style={{
          marginTop: 12,
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
            Изменить
          </button>
        </div>
      )}

      {!selected && debouncedQuery.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {isFetching && (
            <div style={{ textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13, padding: 12 }}>
              Поиск...
            </div>
          )}
          {!isFetching && clients.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13, padding: 12 }}>
              Клиенты не найдены
            </div>
          )}
          {clients.map((c) => (
            <button
              key={c.id}
              onClick={() => { haptic(); onSelect(c); setQuery(c.name); }}
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--tg-secondary-bg)',
                border: 'none',
                borderRadius: 8,
                marginBottom: 6,
                textAlign: 'left',
                cursor: 'pointer',
                display: 'block',
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--tg-text)' }}>{c.name}</div>
              <div style={{ fontSize: 12, color: 'var(--tg-hint)' }}>{c.phone}</div>
            </button>
          ))}
        </div>
      )}

      <button
        onClick={() => { haptic(); onNext(); }}
        disabled={!selected}
        style={{
          marginTop: 24,
          width: '100%',
          padding: '13px',
          background: selected ? 'var(--tg-button)' : 'var(--tg-hint)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 12,
          fontSize: 15,
          fontWeight: 600,
          cursor: selected ? 'pointer' : 'not-allowed',
          opacity: selected ? 1 : 0.5,
        }}
      >
        Далее →
      </button>
    </div>
  );
}

// ─── Step 2: Services ────────────────────────────────────────────────────────

function StepServices({ selected, onSelect, onNext, onBack }) {
  const [custom, setCustom] = useState({ name: '', price: '' });
  const [showCustom, setShowCustom] = useState(false);
  const [customList, setCustomList] = useState([]);

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
      onSelect([...selected, { service_id: svc.id, name: svc.name, price: svc.price }]);
    }
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
  const canNext = selected.length > 0;

  return (
    <div style={{ padding: '0 16px 16px' }}>
      {services.map((svc) => (
        <button
          key={svc.id}
          onClick={() => toggleService(svc)}
          style={{
            width: '100%',
            padding: '11px 12px',
            background: isSelected(svc.id) ? 'var(--tg-button)' : 'var(--tg-secondary-bg)',
            color: isSelected(svc.id) ? 'var(--tg-button-text)' : 'var(--tg-text)',
            border: 'none',
            borderRadius: 10,
            marginBottom: 6,
            textAlign: 'left',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: 14, fontWeight: isSelected(svc.id) ? 600 : 400 }}>
            {isSelected(svc.id) ? '✓ ' : ''}{svc.name}
          </span>
          <span style={{ fontSize: 13, fontWeight: 600 }}>{svc.price.toLocaleString()} ₽</span>
        </button>
      ))}

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
            <span style={{ fontSize: 13, fontWeight: 600 }}>{item.price.toLocaleString()} ₽</span>
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
            placeholder="Название услуги"
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
              placeholder="Цена ₽"
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
              Добавить
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
          + Произвольная услуга
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
          <span style={{ color: 'var(--tg-hint)', fontSize: 14 }}>Итого</span>
          <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--tg-text)' }}>
            {total.toLocaleString()} ₽
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
          ← Назад
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
          Далее →
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Date / time / address ──────────────────────────────────────────

function StepDateTime({ clientId, date, setDate, time, setTime, address, setAddress, onNext, onBack }) {
  const days14 = get14Days();

  // Prefill last address
  const { data: lastAddr } = useQuery({
    queryKey: ['last-address', clientId],
    queryFn: () => getLastClientAddress(clientId),
    enabled: !!clientId,
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (lastAddr?.address && !address) {
      setAddress(lastAddr.address);
    }
  }, [lastAddr, address, setAddress]);

  const canNext = !!date && !!time;

  return (
    <div style={{ padding: '0 16px 16px' }}>
      {/* Mini calendar: 2 weeks grid */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 6px' }}>Дата</p>
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
              <span style={{ fontSize: 9, opacity: 0.7 }}>{DAY_SHORT[dayOfWeek]}</span>
              <span style={{ fontSize: 14, fontWeight: isSelected ? 700 : 400 }}>{dayNum}</span>
            </button>
          );
        })}
      </div>

      {/* Time presets */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 6px' }}>Время</p>
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
            fontSize: 13,
            background: 'var(--tg-secondary-bg)',
            color: 'var(--tg-text)',
            border: '1px solid var(--tg-hint)',
            borderRadius: 8,
            outline: 'none',
          }}
        />
      </div>

      {/* Address */}
      <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '16px 0 6px' }}>Адрес</p>
      <input
        type="text"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder="Адрес (необязательно)"
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
          ← Назад
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
          Далее →
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: Summary ─────────────────────────────────────────────────────────

function StepSummary({ client, services, date, time, address, onBack, onCreated }) {
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
      const msg = err?.response?.data?.detail || 'Ошибка при создании заказа';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      if (typeof WebApp?.MainButton?.enable === 'function') {
        WebApp.MainButton.enable();
      }
      if (typeof WebApp?.MainButton?.setText === 'function') {
        WebApp.MainButton.setText('Создать заказ');
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
      WebApp.MainButton.setText('Создать заказ');
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
  }, [handleCreate]);

  // Loading state
  useEffect(() => {
    if (mutation.isPending) {
      if (typeof WebApp?.MainButton?.disable === 'function') WebApp.MainButton.disable();
      if (typeof WebApp?.MainButton?.setText === 'function') WebApp.MainButton.setText('Создаём...');
    } else if (!mutation.isSuccess) {
      if (typeof WebApp?.MainButton?.enable === 'function') WebApp.MainButton.enable();
      if (typeof WebApp?.MainButton?.setText === 'function') WebApp.MainButton.setText('Создать заказ');
    }
  }, [mutation.isPending, mutation.isSuccess]);

  return (
    <div style={{ padding: '0 16px 16px' }}>
      <div style={{
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}>
        <SummaryRow label="Клиент" value={client.name} />
        <SummaryRow label="Телефон" value={client.phone} />
      </div>

      <div style={{
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}>
        <p style={{ color: 'var(--tg-hint)', fontSize: 12, margin: '0 0 8px' }}>Услуги</p>
        {services.map((s, idx) => (
          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 14, color: 'var(--tg-text)' }}>{s.name}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-text)' }}>
              {s.price.toLocaleString()} ₽
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
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--tg-text)' }}>Итого</span>
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--tg-text)' }}>
            {total.toLocaleString()} ₽
          </span>
        </div>
      </div>

      <div style={{
        background: 'var(--tg-secondary-bg)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 20,
      }}>
        <SummaryRow label="Дата" value={formatDateRu(date)} />
        <SummaryRow label="Время" value={time} />
        {address && <SummaryRow label="Адрес" value={address} />}
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

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={() => { haptic(); onBack(); }}
          disabled={mutation.isPending}
          style={{
            flex: 1,
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
          ← Назад
        </button>
        <button
          onClick={() => { haptic(); handleCreate(); }}
          disabled={mutation.isPending}
          style={{
            flex: 2,
            padding: '13px',
            background: mutation.isPending ? 'var(--tg-hint)' : 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 15,
            fontWeight: 600,
            cursor: mutation.isPending ? 'not-allowed' : 'pointer',
          }}
        >
          {mutation.isPending ? 'Создаём...' : 'Создать заказ'}
        </button>
      </div>
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
        Заказ создан!
      </h2>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: '0 0 32px' }}>
        Заказ #{order?.id} успешно добавлен в расписание
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
        Вернуться к расписанию
      </button>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function OrderCreate({ params, onBack, onCreated }) {
  const [step, setStep] = useState(1);
  const [client, setClient] = useState(null);
  const [services, setServices] = useState([]);
  const [date, setDate] = useState(params?.date || toYMD(new Date()));
  const [time, setTime] = useState('');
  const [address, setAddress] = useState('');
  const [createdOrder, setCreatedOrder] = useState(null);

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

  const TITLES = ['Выбор клиента', 'Услуги', 'Дата и время', 'Подтверждение'];

  if (createdOrder) {
    return <SuccessScreen order={createdOrder} onBack={onBack} />;
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--tg-bg)', paddingBottom: 24 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px 16px 4px',
        gap: 8,
      }}>
        <button
          onClick={() => {
            haptic();
            if (step === 1) onBack();
            else setStep(step - 1);
          }}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--tg-button)',
            fontSize: 15,
            cursor: 'pointer',
            padding: '4px 0',
          }}
        >
          ← Назад
        </button>
        <h2 style={{
          flex: 1,
          textAlign: 'center',
          margin: 0,
          fontSize: 17,
          fontWeight: 600,
          color: 'var(--tg-text)',
        }}>
          {TITLES[step - 1]}
        </h2>
        <div style={{ width: 60 }} />
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
