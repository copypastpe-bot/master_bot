const WebApp = window.Telegram?.WebApp;

export default function StyleSwitcher({ styles, currentIndex, onChange }) {
  if (!styles || styles.length === 0) return null;

  const current = styles[currentIndex];
  const total = styles.length;

  function prev() {
    WebApp?.HapticFeedback?.selectionChanged?.();
    onChange((currentIndex - 1 + total) % total);
  }

  function next() {
    WebApp?.HapticFeedback?.selectionChanged?.();
    onChange((currentIndex + 1) % total);
  }

  const label = current?.is_suggested
    ? `${current.name} · для вас`
    : current?.name || '';

  return (
    <div className="style-switcher">
      <div className="style-switcher__row">
        <button
          type="button"
          className="style-switcher__arrow"
          onClick={prev}
          aria-label="Предыдущий стиль"
        >
          ‹
        </button>
        <span className="style-switcher__name">{label}</span>
        <button
          type="button"
          className="style-switcher__arrow"
          onClick={next}
          aria-label="Следующий стиль"
        >
          ›
        </button>
      </div>

      {total <= 10 ? (
        <div className="style-switcher__dots" aria-hidden="true">
          {styles.map((_, i) => (
            <span
              key={i}
              className={`style-switcher__dot${i === currentIndex ? ' is-active' : ''}`}
              onClick={() => { WebApp?.HapticFeedback?.selectionChanged?.(); onChange(i); }}
            />
          ))}
        </div>
      ) : (
        <div className="style-switcher__counter">
          {currentIndex + 1} / {total}
        </div>
      )}

      <style>{`
        .style-switcher {
          position: sticky;
          top: 0;
          z-index: 10;
          background: linear-gradient(180deg, var(--master-bg-card), var(--master-bg-surface));
          border-bottom: 1px solid var(--master-border);
          backdrop-filter: blur(14px);
          padding: 8px 16px 6px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }
        .style-switcher__row {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 100%;
          justify-content: center;
        }
        .style-switcher__arrow {
          background: none;
          border: none;
          font-size: 24px;
          color: var(--master-text-secondary);
          cursor: pointer;
          padding: 0 8px;
          line-height: 1;
          transition: color 150ms;
        }
        .style-switcher__arrow:active {
          color: var(--master-accent);
        }
        .style-switcher__name {
          flex: 1;
          text-align: center;
          font-size: 14px;
          font-weight: 500;
          color: var(--master-text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .style-switcher__dots {
          display: flex;
          gap: 4px;
          align-items: center;
        }
        .style-switcher__dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--master-text-secondary);
          opacity: 0.3;
          cursor: pointer;
          transition: opacity 200ms, background 200ms;
        }
        .style-switcher__dot.is-active {
          background: var(--master-accent);
          opacity: 1;
        }
        .style-switcher__counter {
          font-size: 12px;
          color: var(--master-text-secondary);
        }
      `}</style>
    </div>
  );
}
