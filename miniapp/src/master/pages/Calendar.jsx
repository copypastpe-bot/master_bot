import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMasterOrders, getMasterOrderDates } from '../../api/client';
import MonthCalendar from '../components/MonthCalendar';
import DaySchedule from '../components/DaySchedule';

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
  const handleSelectDate = (dateStr) => {
    setSelectedDate(dateStr);
    const y = parseInt(dateStr.slice(0, 4), 10);
    const m = parseInt(dateStr.slice(5, 7), 10);
    setViewYear(y);
    setViewMonth(m);
  };

  const handleGoToToday = () => {
    const t = new Date();
    setSelectedDate(todayStr);
    setViewYear(t.getFullYear());
    setViewMonth(t.getMonth() + 1);
  };

  const handlePrevMonth = () => {
    if (viewMonth === 1) {
      setViewYear(y => y - 1);
      setViewMonth(12);
    } else {
      setViewMonth(m => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (viewMonth === 12) {
      setViewYear(y => y + 1);
      setViewMonth(1);
    } else {
      setViewMonth(m => m + 1);
    }
  };

  const handleOrderClick = (orderId) => {
    onNavigate('order', { id: orderId });
  };

  const handleCreateOrder = () => {
    onNavigate('create_order', { date: selectedDate });
  };

  return (
    <div style={{ paddingBottom: 88, minHeight: '100vh', background: 'var(--tg-bg)' }}>

      {/* Sticky month calendar */}
      <div style={{ position: 'sticky', top: 0, zIndex: 50, padding: '4px 12px 6px', background: 'var(--tg-bg)' }}>
        <div
          style={{
            background: 'var(--tg-surface)',
            border: '1px solid var(--tg-enterprise-border)',
            borderRadius: 16,
            boxShadow: 'var(--tg-enterprise-shadow)',
            overflow: 'hidden',
          }}
        >
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
      </div>

      {/* Orders for selected day */}
      <DaySchedule
        dateStr={selectedDate}
        orders={orders}
        loading={ordersLoading}
        onOrderClick={handleOrderClick}
        onCreateOrder={handleCreateOrder}
      />
    </div>
  );
}
