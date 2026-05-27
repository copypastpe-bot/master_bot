import { useI18n } from '../../i18n';
import { useBookingSettings } from '../hooks/useBookingSettings';
import BookingToggleCard from '../components/autobooking/BookingToggleCard';
import PoliciesCard from '../components/autobooking/PoliciesCard';
import MissingDurationWarning from '../components/autobooking/MissingDurationWarning';
import WeeklyScheduleCard from '../components/autobooking/WeeklyScheduleCard';
import ExceptionsCard from '../components/autobooking/ExceptionsCard';

// AppHeader (from MasterApp) renders the back button + the
// `masterApp.titles.autobooking` page title. This page renders only the
// scrollable body content. Subsequent tasks (6-9) add more cards under
// the toggle: MissingDurationWarning, WeeklyScheduleCard, ExceptionsCard,
// PoliciesCard.
export default function AutobookingPage({ onNavigate }) {
  const { t } = useI18n();
  const { data, isLoading, isError } = useBookingSettings();

  if (isLoading) return <div style={{ padding: 16 }}>{t('common.loading')}</div>;
  if (isError || !data) {
    return <div style={{ padding: 16 }}>{t('autobooking.saveFailed')}</div>;
  }

  return (
    <div style={{ padding: 16 }}>
      <BookingToggleCard settings={data} />
      {/* When the master flips the toggle off the rest of the screen
          stays editable (so they can pre-configure schedule before
          turning self-booking on) but visually dimmed as a hint that
          nothing is currently exposed publicly. */}
      <div style={{ opacity: data.enabled ? 1 : 0.65 }}>
        <MissingDurationWarning onGotoServices={() => onNavigate?.('services')} />
        <WeeklyScheduleCard settings={data} />
        <ExceptionsCard settings={data} />
        <PoliciesCard settings={data} />
      </div>
    </div>
  );
}
