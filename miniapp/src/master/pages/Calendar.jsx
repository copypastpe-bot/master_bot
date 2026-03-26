import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMasterOrders, getMasterOrderDates } from '../../api/client';
import WeekStrip from '../components/WeekStrip';
import DaySchedule from '../components/DaySchedule';

const WebApp = window.Telegram?.WebApp;

function toYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getYearMonth(dateStr) {
  // dateStr: "2026-03-24" → { year: 2026, month: 3 }
  const [y, m] = dateStr.split('-').map(Number);
  return { year: y, month: m };
}

export default function Calendar({ onNavigate }) {
  const [selectedDate, setSelectedDate] = useState(() => toYMD(new Date()));

  const { year, month } = getYearMonth(selectedDate);

  // Fetch active dates for the current month (for dot markers)
  const {
    data: datesData,
  } = useQuery({
    queryKey: ['masterOrderDates', year, month],
    queryFn: () => getMasterOrderDates(year, month),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Fetch orders for selected date
  const {
    data: ordersData,
    isFetching: ordersLoading,
  } = useQuery({
    queryKey: ['masterOrders', selectedDate],
    queryFn: () => getMasterOrders(selectedDate),
    staleTime: 60 * 1000, // 1 minute
  });

  const activeDates = datesData?.dates || [];
  const orders = ordersData?.orders || [];

  const handleOrderClick = useCallback((orderId) => {
    onNavigate('order', orderId);
  }, [onNavigate]);

  const handleCreateOrder = useCallback(() => {
    onNavigate('create_order', { date: selectedDate });
  }, [onNavigate, selectedDate]);

  const handleFabClick = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('create_order', { date: selectedDate });
  };

  return (
    <div style={{ paddingBottom: 80, minHeight: '100vh', background: 'var(--tg-bg)' }}>
      {/* Sticky week strip */}
      <div style={{ position: 'sticky', top: 0, zIndex: 50 }}>
        <WeekStrip
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
          activeDates={activeDates}
        />
      </div>

      {/* Day schedule */}
      <DaySchedule
        dateStr={selectedDate}
        orders={orders}
        loading={ordersLoading}
        onOrderClick={handleOrderClick}
        onCreateOrder={handleCreateOrder}
      />

      {/* FAB "+" — above bottom nav (~58px high) + safe area */}
      <button
        onClick={handleFabClick}
        style={{
          position: 'fixed',
          bottom: 'calc(68px + env(safe-area-inset-bottom))',
          right: 20,
          width: 52,
          height: 52,
          borderRadius: '50%',
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          fontSize: 26,
          fontWeight: 300,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
          zIndex: 90,
          lineHeight: 1,
        }}
        aria-label="Создать заказ"
      >
        +
      </button>
    </div>
  );
}
