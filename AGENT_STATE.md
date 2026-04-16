# AGENT_STATE

project: master-bot
last_updated: 2026-04-16
updated_by: codex
status: active
confidence: high

## Purpose

`Master_bot` is a Telegram Mini App CRM for private specialists: customer accounting, loyalty program, planner, reminders, and client broadcasts.

## Current State

The project is in final testing and pilot rollout. RU access path for Mini App is now configured through `ru.app.crmfit.ru` + `ru.api.crmfit.ru` on the RU server, with CORS fixed on NL nginx for both `app.crmfit.ru` and `ru.app.crmfit.ru`. Bot containers on NL were restarted with `MINIAPP_URL=https://ru.app.crmfit.ru?v=3`.

## Active Focus

Validate stable Mini App opening from Russian networks and continue pilot testing with 5 real users without destabilizing bot/API/payment flows.

## Known Risks

- RU route depends on two-server chain (RU proxy -> NL API), so nginx/CORS regressions can break browser requests quickly.
- DNS behavior for `ru.*` should be periodically checked from multiple networks, not only from VPS.
- Future agents must keep deploy changes small and verify both `app` and `ru.app` preflight responses.

## Source Of Truth

- `CLAUDE.md`
- `main.py`
- `src/master_bot.py`
- `src/client_bot.py`
- `src/api/app.py`
- `miniapp/`
- `PROMPT_MINIAPP_3_INTEGRATION.md`
- `docs/plans/`
