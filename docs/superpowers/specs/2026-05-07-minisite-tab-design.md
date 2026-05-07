# Minisite Tab Design

Date: 2026-05-07
Status: approved for implementation planning

## Context

The master Mini App currently has a bottom navigation tab named "Requests". The product no longer allows clients to create order requests: clients should contact the master directly in Telegram. The requests feature should not be deleted yet, but it must be detached from the visible master Mini App UI.

The promo page constructor already exists in `miniapp/src/master/pages/PromoPageBuilder.jsx` and is currently reachable from `More -> Marketing -> Promo page`. This feature is becoming a primary product surface and should move into the bottom navigation as "Minisite".

## Goals

- Replace the bottom navigation "Requests" tab with "Minisite".
- Use a planet-style icon and the label "Минисайт" / "Minisite".
- Remove visible entry points to requests from the master Mini App.
- Remove the promo page entry from `More -> Marketing` so the minisite has one primary path.
- Show an intro screen before the editor until the master explicitly starts creating a minisite.
- Remember "started creation" at the account level, not in local browser storage.

## Non-Goals

- Do not delete `Requests.jsx`, request API endpoints, or database objects.
- Do not create a default promo page draft with placeholder content when the user taps "Create".
- Do not change the public `/m/{slug}` rendering behavior except as needed by existing constructor flow.
- Do not redesign the full constructor in this change.

## Navigation

Bottom navigation becomes:

- Home
- Calendar
- Minisite
- More

The old requests tab is removed from `MasterNav`. The request badge is removed because there is no visible requests tab. `MasterApp` should stop fetching unread request counts at startup.

The dashboard should stop showing the "New requests" action button, even if `pending_requests` is returned by the backend.

The `More -> Marketing` section keeps broadcasts and promos, but removes the promo page/minisite cell. The minisite is intentionally promoted to the bottom navigation.

## Minisite First-Run State

The first-run intro is controlled by server state:

- If the master has no promo page and `promo_page_started_at` is empty, show the intro screen.
- If the master taps "Create minisite", call a backend start endpoint that sets `promo_page_started_at`.
- After the start endpoint succeeds, show the existing constructor.
- If the master exits without saving a page, later visits still show the constructor because `promo_page_started_at` is set.
- If the master has an existing promo page, skip intro and use the current constructor/manage behavior.

The start action must not create a row in `promo_pages`. This avoids showing or persisting low-quality placeholder data.

## Backend

Add a nullable `promo_page_started_at` timestamp to `masters`.

Expose `promo_page_started_at` in `GET /api/master/me`.

Add an authenticated endpoint for the start action:

- `POST /api/promo/page/start`

The endpoint sets `promo_page_started_at` for the current master if it is not already set and returns `{ "promo_page_started_at": "<timestamp>" }`. It should be idempotent.

## Frontend

Add a minisite root screen `miniapp/src/master/pages/Minisite.jsx` around `PromoPageBuilder`:

- It loads the current promo page and the account-level started state.
- It renders the intro only when no page exists and creation has not started.
- It calls the start endpoint from the intro CTA.
- It then renders `PromoPageBuilder`.

`PromoPageBuilder` should remain responsible for the existing wizard/manage flow. The wrapper should avoid duplicating constructor logic.

Intro copy should be concise and product-focused:

- explain that the minisite is a public page for the master;
- mention services, photo, advantages, link/QR, and Telegram contact;
- include one primary button: "Создать минисайт".

## Error Handling

- If loading state fails, show the existing retry-style state.
- If the start endpoint fails, keep the intro visible and show an error.
- If the page exists but profile state cannot load, prefer showing the constructor rather than blocking a master who already has a page.

## Testing

Targeted frontend checks:

- Bottom navigation renders "Минисайт" instead of "Заявки".
- Tapping the minisite tab opens intro for a master with no page and no started flag.
- Tapping "Создать минисайт" calls the start endpoint and opens the constructor.
- A master with `promo_page_started_at` but no page opens the constructor directly.
- A master with an existing page opens the current manage/editor flow.
- `More -> Marketing` no longer contains the promo page/minisite entry.
- Dashboard does not render the "New requests" action.

Backend checks:

- Migration adds `promo_page_started_at`.
- Start endpoint is authenticated and idempotent.
- `GET /api/master/me` exposes the started state.

Manual smoke checks:

- Open master Mini App and verify bottom navigation order and labels.
- Start minisite creation, close/reopen Mini App, verify constructor opens directly.
- Save/publish an actual minisite and verify `/m/{slug}` still works.
