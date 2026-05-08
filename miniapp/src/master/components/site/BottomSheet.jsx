import { useEffect, useRef } from 'react';

export default function BottomSheet({ onClose, title, children }) {
  const sheetRef = useRef(null);

  // Animate in on mount
  useEffect(() => {
    const el = sheetRef.current;
    if (!el) return;
    el.style.transform = 'translateY(100%)';
    requestAnimationFrame(() => {
      el.style.transition = 'transform 250ms ease-out';
      el.style.transform = 'translateY(0)';
    });
  }, []);

  return (
    <>
      <div className="sheet-overlay" onClick={onClose} />
      <div className="sheet-container" ref={sheetRef}>
        <div className="sheet-handle" />
        {title && <div className="sheet-title">{title}</div>}
        <div className="sheet-content">
          {children}
        </div>
      </div>

      <style>{`
        .sheet-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.4);
          z-index: 100;
        }
        .sheet-container {
          position: fixed;
          bottom: 0;
          left: 0;
          width: 100%;
          background: var(--tg-theme-bg-color, #fff);
          border-radius: 16px 16px 0 0;
          padding: 12px 20px 32px;
          z-index: 101;
          max-height: 80vh;
          overflow-y: auto;
        }
        .sheet-handle {
          width: 40px;
          height: 4px;
          border-radius: 2px;
          background: var(--tg-theme-hint-color, #ccc);
          margin: 0 auto 16px;
          opacity: 0.5;
        }
        .sheet-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--tg-theme-text-color, #000);
          margin-bottom: 16px;
        }
        .sheet-content {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
      `}</style>
    </>
  );
}
