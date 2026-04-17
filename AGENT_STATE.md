# AGENT STATE

**Updated:** 2026-04-17

## Current Focus

Fullscreen mode shipped. Mini App runs in `requestFullscreen()` mode with forced dark theme.

## Last Session Work

1. Designed and implemented Telegram Mini App fullscreen mode (Bot API 8.0)
2. Added `AppHeader` component — floating title between Telegram's "Назад / ↓" overlay buttons
3. Removed `PageHeader` from `MasterApp.jsx`, replaced with `AppHeader title={currentTitle}`
4. Fixed CSS safe area formula: `padding-top = safeAreaInset.top + contentSafeAreaInset.top`
5. Applied CSS variables from JS (`safeAreaChanged`, `contentSafeAreaChanged`, `fullscreen_changed` events)
6. Forced dark theme via `--tg-theme-*` CSS variable overrides in `main.jsx`
7. Added onboarding lang/timezone/currency step + extracted `profileOptions.js`
8. Added missing i18n keys: `order`, `createOrder`, `requests`, `broadcast`

## Key Files Changed This Session

- `miniapp/src/main.jsx` — fullscreen, insets, dark theme
- `miniapp/src/theme.css` — padding-top calc, .app-header-title
- `miniapp/src/master/MasterApp.jsx` — AppHeader integration, PageHeader removed
- `miniapp/src/master/components/AppHeader.jsx` — new component
- `miniapp/src/master/pages/MasterOnboarding.jsx` — lang/tz/currency step
- `miniapp/src/master/pages/Profile.jsx` — refactored to use profileOptions
- `miniapp/src/master/profileOptions.js` — new shared constants
- `miniapp/src/i18n/dictionaries/ru.js` / `en.js` — added missing title keys

## Known Issues / Open

- Fullscreen layout padding still unverified on real device (user testing in progress)
- Dark theme: enterprise UI elements with hardcoded light colors may need fine-tuning
- `docs/plans/2026-04-10-miniapp-i18n-spec.md` — untracked, spec for i18n feature

## Production

- Mini App: https://app.crmfit.ru
- API: https://api.crmfit.ru
- Deploy: `bash deploy_miniapp.sh`
- BotFather: Full Screen enabled for the bot
