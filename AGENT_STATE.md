# AGENT_STATE

project: master-bot
last_updated: 2026-04-16
updated_by: codex
status: active
confidence: high

## Purpose

`Master_bot` is a Telegram Mini App CRM for private specialists: customer accounting, loyalty program, planner, reminders, and client broadcasts.

## Current State

The project is in final testing and pilot rollout. NL production (`app.crmfit.ru`) is currently confirmed working from both Serbia and Russian user IPs in nginx access logs. RU proxy route (`ru.app.crmfit.ru` + `ru.api.crmfit.ru`) remains a separate test contour with unstable behavior on some networks.

## Active Focus

Continue pilot testing on `app.crmfit.ru` and monitor real-user accessibility from Russian mobile networks without destabilizing bot/API/payment flows.

## Known Risks

- RU proxy route depends on a two-server chain (RU proxy -> NL API), so edge/network-level filtering can break access before requests reach nginx.
- Some user-facing blocks can occur outside application logs (provider/WAF/routing layers), so diagnostics must include access-log presence checks by source IP and timestamp.
- Future agents must keep deploy changes small and verify both browser page load and API calls from real device sessions.

## Source Of Truth

- `CLAUDE.md`
- `main.py`
- `src/master_bot.py`
- `src/client_bot.py`
- `src/api/app.py`
- `miniapp/`
- `PROMPT_MINIAPP_3_INTEGRATION.md`
- `docs/plans/`
