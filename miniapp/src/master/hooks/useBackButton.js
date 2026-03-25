import { useEffect } from 'react';

const WebApp = window.Telegram?.WebApp;

/**
 * Hook to show/hide Telegram BackButton on nested screens.
 *
 * @param {Function} onBack - callback to invoke when back button is pressed
 * @param {boolean} active - whether to show the back button (default: true)
 */
export function useBackButton(onBack, active = true) {
  useEffect(() => {
    if (!active) return;
    if (typeof WebApp?.BackButton?.show !== 'function') return;

    WebApp.BackButton.show();
    WebApp.BackButton.onClick(onBack);

    return () => {
      if (typeof WebApp?.BackButton?.hide === 'function') {
        WebApp.BackButton.hide();
      }
      if (typeof WebApp?.BackButton?.offClick === 'function') {
        WebApp.BackButton.offClick(onBack);
      }
    };
  }, [onBack, active]);
}
