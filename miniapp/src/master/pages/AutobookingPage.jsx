import { useI18n } from '../../i18n';
import { useBookingSettings } from '../hooks/useBookingSettings';
import BookingToggleCard from '../components/autobooking/BookingToggleCard';
import PoliciesCard from '../components/autobooking/PoliciesCard';
import MissingDurationWarning from '../components/autobooking/MissingDurationWarning';
import WeeklyScheduleCard from '../components/autobooking/WeeklyScheduleCard';

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
      <MissingDurationWarning onGotoServices={() => onNavigate?.('services')} />
      <WeeklyScheduleCard settings={data} />
      <PoliciesCard settings={data} />
    </div>
  );
}
