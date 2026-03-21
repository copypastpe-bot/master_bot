import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import WebApp from '@twa-dev/sdk';
import { getServices, createOrderRequest } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import ErrorScreen from '../components/ErrorScreen';

export default function Booking({ onNavigate }) {
  const [selectedService, setSelectedService] = useState(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [validationError, setValidationError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: services = [], isLoading, error, refetch } = useQuery({
    queryKey: ['services'],
    queryFn: getServices,
  });

  // Manage Telegram MainButton
  useEffect(() => {
    if (!WebApp?.MainButton) return;
    if (submitted) {
      WebApp.MainButton.hide();
      return;
    }

    WebApp.MainButton.setText('Отправить заявку');
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleSubmit);
    return () => {
      WebApp.MainButton.offClick(handleSubmit);
      WebApp.MainButton.hide();
    };
  }, [selectedService, comment, submitted]);

  async function handleSubmit() {
    if (!selectedService) {
      setValidationError(true);
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('error');
      }
      return;
    }
    setIsSubmitting(true);
    try {
      await createOrderRequest({ service_name: selectedService.name, comment: comment || undefined });
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
      setSubmitted(true);
    } catch {
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('error');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (error) return <ErrorScreen message={error.message} onRetry={refetch} />;

  // Success screen
  if (submitted) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 24px' }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%',
          background: 'rgba(76,175,80,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 20px',
          fontSize: 36, color: '#4caf50',
        }}>✓</div>
        <h2 style={{ marginBottom: 12 }}>Заявка отправлена!</h2>
        <p style={{ color: 'var(--tg-hint)', marginBottom: 32, lineHeight: 1.6 }}>
          Мастер свяжется с вами в ближайшее время.
        </p>
        <button
          onClick={() => onNavigate('home')}
          style={{
            background: 'var(--tg-button)', color: 'var(--tg-button-text)',
            border: 'none', borderRadius: 'var(--radius-btn)',
            padding: '14px 32px', fontSize: 16, cursor: 'pointer',
          }}
        >
          На главную
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px 16px 0' }}>
      <h2 style={{ marginBottom: 20 }}>Запись к мастеру</h2>

      {/* Services grid */}
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gap)', marginBottom: 20 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} height={80} radius={16} />)}
        </div>
      ) : services.length === 0 ? (
        <p style={{ color: 'var(--tg-hint)', marginBottom: 20 }}>Услуги не найдены</p>
      ) : (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: 'var(--gap)', marginBottom: 20,
          outline: validationError && !selectedService ? '1.5px solid #f44336' : 'none',
          borderRadius: 16,
          padding: validationError && !selectedService ? 8 : 0,
        }}>
          {services.map(service => {
            const isSelected = selectedService?.id === service.id;
            return (
              <button
                key={service.id}
                onClick={() => {
                  setSelectedService(service);
                  setValidationError(false);
                  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
                    WebApp.HapticFeedback.impactOccurred('light');
                  }
                }}
                style={{
                  background: 'var(--tg-surface)',
                  border: isSelected ? '2px solid var(--tg-accent)' : '2px solid transparent',
                  borderRadius: 16, padding: '16px 12px',
                  cursor: 'pointer', textAlign: 'left', color: 'var(--tg-text)',
                  transition: 'border-color 0.15s',
                }}
              >
                <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{service.name}</p>
                {service.price != null && (
                  <p style={{ color: 'var(--tg-accent)', fontSize: 13 }}>{service.price} ₽</p>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Comment */}
      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Адрес, пожелания..."
        rows={3}
        style={{
          width: '100%', background: 'var(--tg-surface)',
          border: 'none', borderRadius: 'var(--radius-card)',
          padding: '12px 16px', color: 'var(--tg-text)',
          fontSize: 15, resize: 'none', fontFamily: 'inherit', outline: 'none',
        }}
      />

      {/* Fallback button when MainButton unavailable (e.g. browser dev) */}
      {!WebApp?.MainButton && (
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          style={{
            marginTop: 16, width: '100%',
            background: 'var(--tg-button)', color: 'var(--tg-button-text)',
            border: 'none', borderRadius: 'var(--radius-btn)',
            padding: '14px', fontSize: 16, cursor: 'pointer',
            opacity: isSubmitting ? 0.7 : 1,
          }}
        >
          {isSubmitting ? 'Отправка...' : 'Отправить заявку'}
        </button>
      )}
    </div>
  );
}
