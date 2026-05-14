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
      <button
        type="button"
        className="style-switcher__arrow style-switcher__arrow--left"
        onClick={prev}
        aria-label="Предыдущий стиль"
      >
        ‹
      </button>

      <div className="style-switcher__chip">
        <span className="style-switcher__name">{label}</span>
        {total > 10 && (
          <span className="style-switcher__counter">{currentIndex + 1}/{total}</span>
        )}
      </div>

      {total <= 10 && (
        <div className="style-switcher__dots" aria-hidden="true">
          {styles.map((_, i) => (
            <span
              key={i}
              className={`style-switcher__dot${i === currentIndex ? ' is-active' : ''}`}
              onClick={() => { WebApp?.HapticFeedback?.selectionChanged?.(); onChange(i); }}
            />
          ))}
        </div>
      )}

      <button
        type="button"
        className="style-switcher__arrow style-switcher__arrow--right"
        onClick={next}
        aria-label="Следующий стиль"
      >
        ›
      </button>

      <style>{`
        .style-switcher {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          z-index: 50;
          padding-top: calc(var(--tg-safe-area-inset-top, env(safe-area-inset-top)) + 50px);
          padding-left: 12px;
          padding-right: 12px;
          padding-bottom: 8px;
          display: grid;
          grid-template-columns: 36px 1fr 36px;
          column-gap: 10px;
          align-items: center;
          pointer-events: none;
        }
        .style-switcher__chip {
          pointer-events: auto;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 14px;
          min-height: 32px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.72);
          -webkit-backdrop-filter: blur(18px) saturate(140%);
                  backdrop-filter: blur(18px) saturate(140%);
          border: 1px solid rgba(255, 255, 255, 0.65);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
          justify-self: center;
          max-width: 100%;
        }
        .style-switcher__name {
          font-size: 13px;
          font-weight: 600;
          color: #1f2937;
          letter-spacing: 0.01em;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 60vw;
        }
        .style-switcher__counter {
          font-size: 11px;
          font-weight: 600;
          color: #6b7280;
          font-variant-numeric: tabular-nums;
        }
        .style-switcher__arrow {
          pointer-events: auto;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 1px solid rgba(255, 255, 255, 0.65);
          background: rgba(255, 255, 255, 0.72);
          -webkit-backdrop-filter: blur(18px) saturate(140%);
                  backdrop-filter: blur(18px) saturate(140%);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
          color: #1f2937;
          font-size: 22px;
          font-weight: 600;
          line-height: 1;
          cursor: pointer;
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 140ms ease, background 140ms ease;
        }
        .style-switcher__arrow:active {
          transform: scale(0.92);
          background: rgba(255, 255, 255, 0.92);
        }
        .style-switcher__dots {
          position: absolute;
          left: 50%;
          transform: translateX(-50%);
          top: calc(var(--tg-safe-area-inset-top, env(safe-area-inset-top)) + 50px + 38px);
          display: flex;
          gap: 5px;
          padding: 4px 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.45);
          -webkit-backdrop-filter: blur(10px);
                  backdrop-filter: blur(10px);
          pointer-events: auto;
        }
        .style-switcher__dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: rgba(31, 41, 55, 0.35);
          cursor: pointer;
          transition: background 180ms ease, transform 180ms ease;
        }
        .style-switcher__dot.is-active {
          background: var(--master-accent, #3390ec);
          transform: scale(1.3);
        }
      `}</style>
    </div>
  );
}
