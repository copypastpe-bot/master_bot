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
          background: rgba(7, 12, 18, 0.46);
          backdrop-filter: blur(2px);
          z-index: 200;
        }
        .sheet-container {
          position: fixed;
          bottom: 0;
          left: 0;
          width: 100%;
          background: linear-gradient(180deg, var(--master-bg-card), var(--master-bg-surface));
          border-top: 1px solid var(--master-border);
          border-radius: 16px 16px 0 0;
          padding: 12px 20px calc(90px + env(safe-area-inset-bottom, 0px));
          z-index: 201;
          max-height: calc(85vh - env(safe-area-inset-bottom, 0px));
          overflow-y: auto;
          box-shadow: 0 -16px 44px rgba(0, 0, 0, 0.22);
        }
        .sheet-handle {
          width: 40px;
          height: 4px;
          border-radius: 2px;
          background: var(--master-border);
          margin: 0 auto 16px;
          opacity: 0.5;
        }
        .sheet-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--master-text-primary);
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
