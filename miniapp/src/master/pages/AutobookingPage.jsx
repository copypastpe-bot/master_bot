import { useBookingSettings } from '../hooks/useBookingSettings';

// AppHeader (from MasterApp) already renders the back button + the
// `masterApp.titles.autobooking` page title. This page renders only the
// scrollable body content. Subsequent tasks (5-9) replace the JSON debug
// dump below with four cards: BookingToggle, MissingDurationWarning,
// WeeklyScheduleCard, ExceptionsCard, PoliciesCard.
export default function AutobookingPage() {
  const { data, isLoading } = useBookingSettings();

  return (
    <div style={{ padding: 16 }}>
      {isLoading
        ? <div>…</div>
        : <pre style={{ fontSize: 11 }}>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
