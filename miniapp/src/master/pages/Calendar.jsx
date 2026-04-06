import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMasterOrders, getMasterOrderDates } from '../../api/client';
import MonthCalendar from '../components/MonthCalendar';
import DaySchedule from '../components/DaySchedule';

const WebApp = window.Telegram?.WebApp;

function toYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function Calendar({ onNavigate }) {
  const today = new Date();
  const todayStr = toYMD(today);

  const [selectedDate, setSelectedDate] = useState(todayStr);
  const [viewYear, setViewYear]   = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1);

  // Fetch active dates for the displayed month (dot markers)
  const { data: datesData } = useQuery({
    queryKey: ['masterOrderDates', viewYear, viewMonth],
    queryFn: () => getMasterOrderDates(viewYear, viewMonth),
    staleTime: 2 * 60 * 1000,
  });

  // Fetch orders for selected date
  const { data: ordersData, isFetching: ordersLoading } = useQuery({
    queryKey: ['masterOrders', selectedDate],
    queryFn: () => getMasterOrders(selectedDate),
    staleTime: 60 * 1000,
  });

  const activeDates = datesData?.dates || [];
  const orders = ordersData?.orders || [];

  // When user taps a date — if it's in a different month, jump there
  const handleSelectDate = useCallback((dateStr) => {
    setSelectedDate(dateStr);
    const y = parseInt(dateStr.slice(0, 4), 10);
    const m = parseInt(dateStr.slice(5, 7), 10);
    setViewYear(y);
    setViewMonth(m);
  }, []);

  const handleGoToToday = useCallback(() => {
    const t = new Date();
    setSelectedDate(todayStr);
    setViewYear(t.getFullYear());
    setViewMonth(t.getMonth() + 1);
  }, [todayStr]);

  const handlePrevMonth = useCallback(() => {
    if (viewMonth === 1) {
      setViewYear(y => y - 1);
      setViewMonth(12);
    } else {
      setViewMonth(m => m - 1);
    }
  }, [viewMonth]);

  const handleNextMonth = useCallback(() => {
    if (viewMonth === 12) {
      setViewYear(y => y + 1);
      setViewMonth(1);
    } else {
      setViewMonth(m => m + 1);
    }
  }, [viewMonth]);

  const handleOrderClick = useCallback((orderId) => {
    onNavigate('order', { id: orderId });
  }, [onNavigate]);

  const handleCreateOrder = useCallback(() => {
    onNavigate('create_order', { date: selectedDate });
  }, [onNavigate, selectedDate]);

  return (
    <div style={{ paddingBottom: 80, minHeight: '100vh', background: 'var(--tg-bg)' }}>

      {/* Sticky month calendar */}
      <div style={{ position: 'sticky', top: 0, zIndex: 50 }}>
        <MonthCalendar
          selectedDate={selectedDate}
          onSelectDate={handleSelectDate}
          viewYear={viewYear}
          viewMonth={viewMonth}
          onPrevMonth={handlePrevMonth}
          onNextMonth={handleNextMonth}
          onGoToToday={handleGoToToday}
          activeDates={activeDates}
          todayStr={todayStr}
        />
      </div>

      {/* Orders for selected day */}
      <DaySchedule
        dateStr={selectedDate}
        orders={orders}
        loading={ordersLoading}
        onOrderClick={handleOrderClick}
        onCreateOrder={handleCreateOrder}
      />

      {/* FAB "+" */}
      <button
        onClick={() => {
          if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
            WebApp.HapticFeedback.impactOccurred('light');
          }
          onNavigate('create_order', { date: selectedDate });
        }}
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
