const WebApp = window.Telegram?.WebApp;

export default function EditableBlock({ id, label, onTap, children }) {
  function handleClick() {
    WebApp?.HapticFeedback?.selectionChanged?.();
    onTap(id);
  }

  return (
    <div
      className="editable-block"
      onClick={handleClick}
      role="button"
      aria-label={`Редактировать: ${label}`}
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
    >
      {children}
      <div className="editable-block__indicator" aria-hidden="true">
        <span className="editable-block__icon">✏️</span>
      </div>
    </div>
  );
}
