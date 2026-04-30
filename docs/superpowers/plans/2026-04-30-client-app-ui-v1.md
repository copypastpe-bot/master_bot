# Client App UI V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build compact expandable order cards for client Home/History and harden notification toggles on Settings.

**Architecture:** Keep the existing client Mini App structure. `OrderCard.jsx` remains the single shared card component, page files only pass handlers and activity limits, and backend settings endpoints remain unchanged.

**Tech Stack:** React 19, Vite, axios, TanStack Query, FastAPI client app endpoints, SQLite-backed database helpers.

---

## Files

- Modify: `miniapp/src/components/OrderCard.jsx`
- Modify: `miniapp/src/pages/Home.jsx`
- Modify: `miniapp/src/pages/Settings.jsx`
- Modify: `miniapp/src/theme.css`
- Verify: `tests/test_client_app_database.py`
- Verify: `tests/test_client_app_api_import.py`

## Tasks

### Task 1: Compact Expandable Order Card

- [ ] Update `miniapp/src/components/OrderCard.jsx` to add `useState`, internal `expanded`, collapsed summary, expanded detail body, chevron, and event-safe action buttons.
- [ ] Keep `onConfirm`, `onReview`, `onRepeat`, and `onContact` prop names unchanged.
- [ ] Render `amount_total` first, falling back to existing `price`.
- [ ] Show `address`, `bonus_accrued`, `bonus_spent`, review marker, and action buttons only in the expanded area.
- [ ] Ensure `done + has_review` still shows `Повторить`.
- [ ] Ensure `cancelled` shows `Повторить`.

### Task 2: Home Activity Count

- [ ] Change `getClientMasterActivity(activeMasterId, 3)` to `getClientMasterActivity(activeMasterId, 4)` in `miniapp/src/pages/Home.jsx`.
- [ ] Keep the existing Activity title and History navigation link.

### Task 3: Settings Toggle Hardening

- [ ] In `miniapp/src/pages/Settings.jsx`, reset `settings` to `null` and `loading` to `true` when `activeMasterId` changes.
- [ ] Add an early return in `handleToggle` when `saving === key`.
- [ ] Keep optimistic update and rollback behavior.

### Task 4: CSS Polish

- [ ] Update `miniapp/src/theme.css` order-card rules for compact spacing, ellipsis, chevron, expanded body animation, address row, and action spacing.
- [ ] Keep the existing dark theme variables and status badge colors.

### Task 5: Verification

- [ ] Run `python -m unittest tests.test_client_app_database tests.test_client_app_api_import`.
- [ ] Run `npm --prefix miniapp run lint`.
- [ ] Run `npm --prefix miniapp run build`.
- [ ] Run `git status --short` and review the diff.

## Self-Review

- Spec coverage: Order cards, Activity block, Settings toggles, styling, and verification are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: plan uses existing component props and API function names.
