# CLAUDE

Read this before working in the project.

## Goal

Maintain `Master_bot` as a Telegram Mini App CRM for private specialists with accounting, loyalty, planning, reminders, and broadcasts. The product is at the final testing and debug stage.

## Read Order

1. `AGENT_STATE.md`
2. recent entries in `SESSION_LOG.md`
3. `main.py`
4. `PROMPT_MINIAPP_3_INTEGRATION.md`
5. `src/master_bot.py`
6. `src/client_bot.py`
7. `src/api/app.py`
8. `miniapp/`
9. `TODO.md`

## Key Sources

- `main.py`
- `src/master_bot.py`
- `src/client_bot.py`
- `src/api/`
- `src/handlers/payments.py`
- `src/config.py`
- `miniapp/`
- `deploy_miniapp.sh`
- `nginx/miniapp.conf`

## Working Rules

- Prefer the Mini App and API as the primary master-facing flow unless code proves otherwise.
- The main user scenario starts from the Mini App home screen with dashboard and upcoming orders.
- Treat payment and subscription changes as sensitive; verify the `successful_payment` path before changing billing behavior.
- If schema or data-shape changes are made, review the matching SQL migration path.
- Prefer real code and config over documentation when they conflict.
- Work only in the files needed for the task, plan first, and keep changes small and commit-friendly.

## Git Hygiene

- Run `git status --short` before editing, before committing, and before deploy.
- Commit completed logical steps in small, focused commits.
- Do not mix unrelated Mini App, backend, and agent-file changes into one commit.
- Do not deploy from a dirty worktree.

## Deploy Rules

- Backend and shared `src/` changes: commit -> push -> deploy from committed state.
- Frontend-only `miniapp/` changes: use `bash deploy_miniapp.sh` after commit.
- Changes in shared `src/` should be treated as affecting both bot and API behavior.
- Assume the path is `local -> git -> VPS` and use the documented SSH workflow only.
- Do not search for passwords, invent credentials, or guess how to gain VPS access.
- If a server step requires `sudo` and it is not already available, stop and ask the user.

## End Of Session Requirements

Before ending the session:
1. run `git status --short`;
2. commit completed work in one or more small logical commits;
3. rewrite `AGENT_STATE.md` to reflect current state;
4. append one new entry to `SESSION_LOG.md`;
5. keep both files short, factual, and agent-readable.

## Current Focus

Support final testing, debugging, and pilot rollout to 5 real users without destabilizing production behavior.
