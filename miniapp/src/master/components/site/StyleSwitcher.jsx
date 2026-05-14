const WebApp = window.Telegram?.WebApp;

export default function StyleSwitcher({ styles, currentIndex, onChange }) {
  if (!styles || styles.length === 0) return null;

  const current = styles[currentIndex];
  const total = styles.length;
  const label = current?.name || '';

  function prev() {
    WebApp?.HapticFeedback?.selectionChanged?.();
    onChange((currentIndex - 1 + total) % total);
  }

  function next() {
    WebApp?.HapticFeedback?.selectionChanged?.();
    onChange((currentIndex + 1) % total);
  }

  return (
    <div className="style-switcher">
      <button
        type="button"
        className="style-switcher__arrow"
        onClick={prev}
        aria-label="Предыдущий стиль"
      >
        ‹
      </button>

      <div className="style-switcher__chip">
        <span className="style-switcher__name">{label}</span>
      </div>

      <button
        type="button"
        className="style-switcher__arrow"
        onClick={next}
        aria-label="Следующий стиль"
      >
        ›
      </button>

      <style>{`
        .style-switcher {
          position: absolute;
          left: 12px;
          right: 12px;
          bottom: 12px;
          z-index: 5;
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
          justify-content: center;
          gap: 8px;
          padding: 6px 14px;
          min-height: 32px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.72);
          -webkit-backdrop-filter: blur(18px) saturate(140%);
                  backdrop-filter: blur(18px) saturate(140%);
          border: 1px solid rgba(255, 255, 255, 0.65);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
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
        .style-switcher__arrow {
          pointer-events: auto;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 1px solid rgba(255, 255, 255, 0.65);
          background: rgba(255, 255, 255, 0.72);
          -webkit-backdrop-filter: blur(18px) saturate(140%);
                  backdrop-filter: blur(18px) saturate(140%);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
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
      `}</style>
    </div>
  );
}
