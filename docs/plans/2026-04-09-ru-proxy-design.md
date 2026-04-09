# Design: RU Proxy via Timeweb Moscow

**Date:** 2026-04-09  
**Goal:** Allow Russian users to access the Mini App via a Moscow-based reverse proxy (Timeweb), bypassing routing issues to the NL (Contabo) server.

---

## Problem

The app (Mini App frontend + FastAPI) runs on a VPS in Netherlands (Contabo, `75.119.153.118`). Russian users experience slow load times or complete unavailability due to unstable routing from RU to NL. Telegram itself works fine — the issue is HTTP traffic to `app.crmfit.ru` and `api.crmfit.ru`.

## Solution: nginx Reverse Proxy on Timeweb Moscow

Moscow server (Timeweb) acts as a transparent proxy. RU users hit Moscow, Moscow forwards to NL. Server-to-server routing (Moscow→NL datacenter) is far more stable than end-user→NL.

### Architecture

```
RU user
  ├─→ https://ru.app.crmfit.ru  →  Timeweb nginx  →  https://app.crmfit.ru (NL)
  └─→ https://ru.api.crmfit.ru  →  Timeweb nginx  →  http://75.119.153.118:8081 (NL API)

Mini App (RU build):
  VITE_API_URL = https://ru.api.crmfit.ru
```

> **Why two subdomains?** The Mini App JS runs in the browser — when the page loads from `ru.app.crmfit.ru`, the JS still makes `fetch()` calls to wherever `VITE_API_URL` points. Without a separate RU API endpoint, API calls would still go direct to NL from the user's browser.

---

## Components

### 1. DNS (crmfit.ru zone)
Add two A-records pointing to Timeweb Moscow IP:
- `ru.app.crmfit.ru` → `<timeweb_ip>`
- `ru.api.crmfit.ru` → `<timeweb_ip>`

### 2. Timeweb nginx config
Two `server` blocks:
- `ru.app.crmfit.ru` — `proxy_pass https://app.crmfit.ru`
- `ru.api.crmfit.ru` — `proxy_pass http://75.119.153.118:8081`

Include standard proxy headers: `Host`, `X-Real-IP`, `X-Forwarded-For`.

### 3. SSL on Timeweb
```bash
certbot --nginx -d ru.app.crmfit.ru -d ru.api.crmfit.ru
```

### 4. NL FastAPI — CORS update (`src/api/app.py`)
Add `https://ru.app.crmfit.ru` to `allow_origins`.

### 5. Mini App — RU build
Create `.env.ru` (not committed):
```
VITE_API_URL=https://ru.api.crmfit.ru
```
Build: `npm run build -- --mode ru`  
Deploy static files to Timeweb (e.g., `/var/www/ru.app.crmfit.ru/`).

> Alternative: keep `proxy_pass` for the app too (no separate build needed), but then nginx must rewrite `api.crmfit.ru` → `ru.api.crmfit.ru` inside JS responses via `sub_filter` — fragile. Separate build is cleaner.

---

## What Changes

| File | Change |
|---|---|
| `src/api/app.py` | +1 line: add `ru.app.crmfit.ru` to CORS |
| `miniapp/.env.ru` | New file (not committed), `VITE_API_URL=https://ru.api.crmfit.ru` |
| Timeweb nginx | New config file (on server only) |
| DNS | 2 new A-records |

Backend code on NL: **no changes**.

---

## Testing Plan

1. Verify `ru.app.crmfit.ru` loads Mini App in browser
2. Verify API calls reach NL (`/api/me`, `/api/master/me`)
3. Test from a RU IP (or RU VPN) — compare load time vs `app.crmfit.ru`
4. Test Telegram Mini App button opening `ru.app.crmfit.ru`
5. Full order flow: create order, view calendar, broadcast

---

## Future (if test successful)

- Switch to GeoDNS: route RU IPs to Moscow automatically, everyone else to NL
- Or: migrate to Variant B (static files hosted on Moscow, only API proxied) for lower latency
