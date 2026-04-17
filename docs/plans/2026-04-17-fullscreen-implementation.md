# Fullscreen Mode — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch the Mini App from `WebApp.expand()` to true fullscreen mode with a transparent floating title ("Master_bot" on root, screen name on sub-screens) centered between Telegram's native "< Назад" and "↓ ···" overlay buttons.

**Architecture:** Single new `AppHeader` component renders a `position:absolute` title div inside `.master-shell`. CSS variables `--tg-safe-area-inset-top` and `--tg-content-safe-area-inset-top` (set by Telegram) define the geometry. `MasterApp` derives the title from `navStack` and passes it as a prop. Old `PageHeader` is removed.

**Tech Stack:** React 18, Vite, Telegram WebApp JS API (Bot API 8.0+), CSS custom properties

---

### Task 1: Enable fullscreen in BotFather (manual step)

**Files:** none

**Step 1: Open BotFather in Telegram**

Go to @BotFather → `/mybots` → select your bot → `Bot Settings` → `Mini Apps` → toggle **Full Screen** ON.

This makes the app open in fullscreen by default so there is no flicker on launch.

**Step 2: Verify**

Open the mini app. The native "Закрыть / Master_bot / ⋯" top bar should be gone. You should see "< Назад" and "↓ ···" overlay buttons instead.

> If the setting is not yet available in your BotFather version, skip and rely on the JS call in Task 2.

---

### Task 2: Call `requestFullscreen()` in `main.jsx`

**Files:**
- Modify: `miniapp/src/main.jsx`

**Step 1: Open `miniapp/src/main.jsx`**

Current lines 13–15:
```js
if (typeof WebApp?.expand === 'function') {
  WebApp.expand();
}
```

**Step 2: Add `requestFullscreen()` call right after**

Replace those lines with:
```js
if (typeof WebApp?.expand === 'function') {
  WebApp.expand();
}
if (typeof WebApp?.requestFullscreen === 'function') {
  WebApp.requestFullscreen();
}
```

**Step 3: Commit**

```bash
git add miniapp/src/main.jsx
git commit -m "feat(miniapp): request fullscreen on launch"
```

---

### Task 3: Add CSS for fullscreen layout

**Files:**
- Modify: `miniapp/src/theme.css`

**Step 1: Add `padding-top` to `.master-shell` in enterprise block**

Find the existing rule (around line 67):
```css
body.typeui-enterprise-body .master-shell {
  min-height: 100dvh;
  animation: enterprise-fade-in 220ms ease-out;
}
```

Add `padding-top` and `position: relative`:
```css
body.typeui-enterprise-body .master-shell {
  min-height: 100dvh;
  animation: enterprise-fade-in 220ms ease-out;
  padding-top: var(--tg-content-safe-area-inset-top, env(safe-area-inset-top));
  position: relative;
}
```

`position: relative` is required so the `AppHeader`'s `position: absolute` is anchored to `.master-shell`.

**Step 2: Add `.app-header-title` class**

Add after the `.master-shell` rule:
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

Why `pointer-events: none`: the title floats in the same zone as Telegram's "Назад" / "↓ ···" buttons. Without this, the title div would intercept taps meant for those buttons.

**Step 3: Commit**

```bash
git add miniapp/src/theme.css
git commit -m "feat(miniapp): add fullscreen CSS layout and app-header-title"
```

---

### Task 4: Create `AppHeader` component

**Files:**
- Create: `miniapp/src/master/components/AppHeader.jsx`

**Step 1: Create the file**

```jsx
export default function AppHeader({ title }) {
  return (
    <div className="app-header-title">
      {title}
    </div>
  );
}
```

That's the entire component. No state, no effects.

**Step 2: Commit**

```bash
git add miniapp/src/master/components/AppHeader.jsx
git commit -m "feat(miniapp): add AppHeader component for fullscreen title"
```

---

### Task 5: Integrate `AppHeader` into `MasterApp` and remove `PageHeader`

**Files:**
- Modify: `miniapp/src/master/MasterApp.jsx`

**Step 1: Add import at top of file**

```jsx
import AppHeader from './components/AppHeader';
```

**Step 2: Add title derivation logic**

After the line `const current = navStack[navStack.length - 1];` (around line 111), add:

```jsx
const titleMap = {
  order:         t('masterApp.titles.order'),
  create_order:  t('masterApp.titles.createOrder'),
  clients:       t('masterApp.titles.clients'),
  client:        t('masterApp.titles.client'),
  profile:       t('masterApp.titles.profile'),
  bonus:         t('masterApp.titles.bonus'),
  bonus_message: current?.kind === 'birthday'
                   ? t('masterApp.titles.bonusBirthday')
                   : t('masterApp.titles.bonusWelcome'),
  services:      t('masterApp.titles.services'),
  promos:        t('masterApp.titles.promos'),
  promo_new:     t('masterApp.titles.promoNew'),
  promo:         t('masterApp.titles.promo'),
  reports:       t('masterApp.titles.reports'),
  requests:      t('masterApp.titles.requests'),
  subscription:  t('masterApp.titles.subscription'),
  broadcast:     t('masterApp.titles.broadcast'),
};

const currentTitle = current ? (titleMap[current.type] ?? 'Master_bot') : 'Master_bot';
```

**Step 3: Replace all `<PageHeader ... />` with `<AppHeader title={currentTitle} />`**

Every branch in the `if (current)` block currently has:
```jsx
<PageHeader title={t('masterApp.titles.XXX')} onBack={handleBack} />
```

Replace ALL of them with a single `<AppHeader title={currentTitle} />` placed just inside `<div className="master-shell">`.

Pattern for each branch — before:
```jsx
return (
  <div className="master-shell">
    <PageHeader title={t('masterApp.titles.clients')} onBack={handleBack} />
    <ClientsList ... />
  </div>
);
```

After:
```jsx
return (
  <div className="master-shell">
    <AppHeader title={currentTitle} />
    <ClientsList ... />
  </div>
);
```

Apply to ALL branches: `clients`, `client`, `profile`, `bonus`, `bonus_message`, `services`, `promos`, `promo_new`, `promo`, `reports`, `subscription`.

Branches that already have no `PageHeader` (`order`, `create_order`, `requests`, `broadcast`, fallback): just add `<AppHeader title={currentTitle} />` as the first child inside `.master-shell`.

**Step 4: Add `AppHeader` to the tab root render**

In the `return` at the bottom (tab root screens):
```jsx
return (
  <div className="master-shell">
    <AppHeader title={currentTitle} />
    {renderTab()}
    <MasterNav active={tab} onNavigate={switchTab} requestsBadge={requestsBadge} />
  </div>
);
```

**Step 5: Delete the `PageHeader` function**

Remove the entire function at the bottom of the file (lines ~310–327):
```jsx
function PageHeader({ title, onBack }) {
  ...
}
```

**Step 6: Commit**

```bash
git add miniapp/src/master/MasterApp.jsx
git commit -m "feat(miniapp): integrate AppHeader, remove PageHeader"
```

---

### Task 6: Build and deploy

**Step 1: Build**

```bash
cd miniapp && npm run build
```

Expected: no errors, `dist/` produced.

**Step 2: Deploy**

```bash
cd .. && bash deploy_miniapp.sh
```

**Step 3: Verify in Telegram**

Open the mini app on a real device:

| Check | Expected |
|---|---|
| App opens | No "Закрыть / Master_bot / ⋯" bar |
| Status bar visible | App content doesn't overlap time/battery |
| Root screen | "Master_bot" text visible in center between Назад/↓ |
| Navigate to Клиенты | "Клиенты" appears in center |
| Tap "< Назад" | Goes back, title returns to "Master_bot" |
| Tap "↓" | App minimizes normally |
| Bottom nav | Correct padding, not cut off |

---

### Notes

- `--tg-content-safe-area-inset-top` is set by Telegram on `document.documentElement`. On older clients it may be `0px`. The `env(safe-area-inset-top)` fallback handles this gracefully.
- If the title is not visible: check that `--tg-content-safe-area-inset-top` differs from `--tg-safe-area-inset-top` in DevTools. If both are `0px`, fullscreen is not active.
- Translation keys for titles that might be missing (e.g. `masterApp.titles.order`, `masterApp.titles.broadcast`): add them to `miniapp/src/i18n/dictionaries/ru.js` and `en.js` if they don't exist.
