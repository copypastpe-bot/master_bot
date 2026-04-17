# SESSION LOG

---

## 2026-04-17 — Fullscreen mode + dark theme

**Goal:** Перевести Mini App в полноэкранный режим Telegram (Bot API 8.0).

**Done:**
- BotFather: включён Full Screen для бота
- `main.jsx`: `requestFullscreen()`, принудительная тёмная тема (`--tg-theme-*`), `applyInsets()` с событиями `safeAreaChanged` / `contentSafeAreaChanged` / `fullscreen_changed`
- `theme.css`: `padding-top = safeAreaInset.top + contentSafeAreaInset.top`, новый `.app-header-title`
- `AppHeader.jsx`: новый компонент, плавающий заголовок между кнопками Telegram
- `MasterApp.jsx`: `titleMap` + `currentTitle`, `AppHeader` вместо `PageHeader` во всех ветках
- i18n: добавлены ключи `order`, `createOrder`, `requests`, `broadcast`, `feedbackSettings`
- Онбординг: шаг 0 — выбор языка, шаг 3 — таймзона/валюта; `profileOptions.js` вынесен отдельно

**Commits:** e28e6d5 → d73c221 (8 коммитов)

**Status:** задеплоено, layout верифицируется на устройстве. Тёмная тема работает.

**Open:** точная геометрия safe area на iOS требует проверки — `contentSafeAreaInset` может быть 0 на старых клиентах Telegram.
