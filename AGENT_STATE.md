# AGENT_STATE

project: master-bot
last_updated: 2026-04-13
updated_by: agent1
status: active
confidence: high

## Purpose

`Master_bot` is a Telegram Mini App CRM for private specialists: customer accounting, loyalty program, planner, reminders, and client broadcasts.

## Current State

The project is in final testing and debugging. The main operational surface is the Mini App home screen with upcoming orders and dashboard data. The repository contains a dual-bot Python application (`master_bot` and `client_bot`), API server code under `src/api/`, SQL migrations, and a front-end Mini App under `miniapp/`. Registration onboarding for masters, English language support, additional timezones, and currencies were recently added.

## Active Focus

Find 5 real users and validate the system in day-to-day usage without destabilizing the existing bot, API, payment, or Mini App flows.

## Known Risks

- No active blocker is currently known, but small bugs may still surface during final testing.
- Production details and deployment specifics should still be re-checked in `CLAUDE.md` and architecture docs before environment-sensitive work.
- Future agents must work in narrow scope, in small changes, and avoid touching unrelated files.

## Source Of Truth

- `CLAUDE.md`
- `main.py`
- `src/master_bot.py`
- `src/client_bot.py`
- `src/api/app.py`
- `miniapp/`
- `PROMPT_MINIAPP_3_INTEGRATION.md`
- `docs/plans/`
