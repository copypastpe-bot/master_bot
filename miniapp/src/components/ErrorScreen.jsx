export default function ErrorScreen({ message, onRetry = () => {} }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 24px' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <p style={{ color: 'var(--tg-text)', marginBottom: 8 }}>Что-то пошло не так</p>
      <p style={{ color: 'var(--tg-hint)', fontSize: 14, marginBottom: 24 }}>{message}</p>
      <button
        onClick={onRetry}
        style={{
          background: 'var(--tg-button)',
          color: 'var(--tg-button-text)',
          border: 'none',
          borderRadius: 'var(--radius-btn)',
          padding: '12px 24px',
          fontSize: 16,
          cursor: 'pointer'
        }}
      >
        Попробовать снова
      </button>
    </div>
  );
}
