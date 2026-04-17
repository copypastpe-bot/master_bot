# Fullscreen Mode — Design Doc

**Date:** 2026-04-17
**Status:** Approved

## Goal

Switch the Telegram Mini App from default expanded mode (`WebApp.expand()`) to true fullscreen mode (`WebApp.requestFullscreen()`). The native Telegram top bar ("Закрыть / Master_bot / ⋯") is replaced by Telegram's fullscreen overlay ("< Назад" / "↓ ···") with the app's own title rendered transparently in the center zone.

## Approach

Minimal — new `AppHeader` component, no new abstractions or context. `MasterApp` already knows the current screen via `navStack` and passes the title as a prop.

## Visual Layout

```
┌─────────────────────────────────────┐
│ 13:04       ▪▪▪ WiFi  🔋           │  ← status bar (Telegram owns)
│ < Назад   [Master_bot / Screen]   ↓ ···  │  ← Telegram overlay + app title center
│─────────────────────────────────────│
│                                     │
│  content                            │
│                                     │
└─────────────────────────────────────┘
```

- Root screens (home/calendar/requests/more): title = "Master_bot"
- Sub-screens: title = localized screen name (Клиенты, Профиль, etc.)
- Header background: transparent, `pointer-events: none`

## Changes

### 1. BotFather (manual step)

BotFather → bot → Bot Settings → Mini Apps → enable **Full Screen**.
Required so the app opens in fullscreen by default without flicker.

### 2. `miniapp/src/main.jsx`

Add after existing `WebApp.expand()` call:

```js
if (typeof WebApp?.requestFullscreen === 'function') WebApp.requestFullscreen();
```

### 3. `miniapp/src/theme.css`

Add to `body.typeui-enterprise-body .master-shell`:

```css
padding-top: var(--tg-content-safe-area-inset-top, env(safe-area-inset-top));
```

Add new class for floating title:

```css
body.typeui-enterprise-body .app-header-title {
  position: absolute;
  top: var(--tg-safe-area-inset-top, env(safe-area-inset-top));
  left: 0;
  right: 0;
  height: calc(
    var(--tg-content-safe-area-inset-top, env(safe-area-inset-top))
    - var(--tg-safe-area-inset-top, env(safe-area-inset-top))
  );
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 50;
  font-size: 15px;
  font-weight: 700;
  color: var(--tg-text);
}
```

### 4. New file: `miniapp/src/master/components/AppHeader.jsx`

```jsx
export default function AppHeader({ title }) {
  return <div className="app-header-title">{title}</div>;
}
```

### 5. `miniapp/src/master/MasterApp.jsx`

- Import `AppHeader`
- Derive `currentTitle` from `navStack`:

| navStack `type` | Title (via `t()`) |
|---|---|
| *(empty — tab root)* | `"Master_bot"` |
| `order` | t('masterApp.titles.order') |
| `create_order` | t('masterApp.titles.createOrder') |
| `clients` | t('masterApp.titles.clients') |
| `client` | t('masterApp.titles.client') |
| `profile` | t('masterApp.titles.profile') |
| `bonus` | t('masterApp.titles.bonus') |
| `bonus_message` | t('masterApp.titles.bonusBirthday') or bonusWelcome |
| `services` | t('masterApp.titles.services') |
| `promos` | t('masterApp.titles.promos') |
| `promo_new` | t('masterApp.titles.promoNew') |
| `promo` | t('masterApp.titles.promo') |
| `reports` | t('masterApp.titles.reports') |
| `requests` | t('masterApp.titles.requests') |
| `subscription` | t('masterApp.titles.subscription') |
| `broadcast` | t('masterApp.titles.broadcast') |

- Replace all `<PageHeader title={...} onBack={handleBack} />` usages with just `<AppHeader title={currentTitle} />` placed once inside `.master-shell`
- Remove `PageHeader` function entirely
- `master-shell` div gets `position: relative` so `AppHeader` absolute positioning works

## CSS Variables Reference

| Variable | Meaning |
|---|---|
| `--tg-safe-area-inset-top` | Device status bar height |
| `--tg-content-safe-area-inset-top` | Status bar + Telegram controls height |

The difference between the two = height of Telegram's "Назад / ↓ ···" bar = the zone where `AppHeader` floats.

## Out of Scope

- No changes to bottom navigation, payment flows, or backend
- No animation on title change
- No custom back button — Telegram's native overlay handles it
