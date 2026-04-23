# CLAUDE

Read this before working in the project.

## Goal

Maintain `Master_bot` as a Telegram Mini App CRM for private specialists with accounting, loyalty, planning, reminders, and broadcasts. The product is at the final testing and debug stage.

## Read Order

Infra map (canonical, token-light): /Users/evgenijpastusenko/Projects/agent1/docs/INFRA_MAP_LITE.yaml

1. /Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md
2. recent entries in /Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/SESSION_LOG.md
3. `main.py`
4. `PROMPT_MINIAPP_3_INTEGRATION.md`
5. `src/master_bot.py`
6. `src/client_bot.py`
7. `src/api/app.py`
8. `miniapp/`
9. `TODO.md`

## Central Context

This project uses central agent memory outside the current repository.
If `./AGENT_STATE.md` or `./SESSION_LOG.md` are missing here, that is expected.
Read and update only these registered files:

- State: `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md`
- Log: `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/SESSION_LOG.md`

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

- Project context state is centralized in /Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md.
- Project session log is centralized in /Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/SESSION_LOG.md.
- Central context lives in `agent1/project_ai_context/`, not in this repository.
- Missing local `AGENT_STATE.md` / `SESSION_LOG.md` in `Master_bot` is expected and not an error.
- Do not recreate local AGENT_STATE.md and SESSION_LOG.md in this project.
- If required facts are missing, ask the user directly.
- Do not enumerate speculative options by default.
- Use detective mode only when the user explicitly asks to find a solution or process.

- Prefer the Mini App and API as the primary master-facing flow unless code proves otherwise.
- The main user scenario starts from the Mini App home screen with dashboard and upcoming orders.
- Treat payment and subscription changes as sensitive; verify the `successful_payment` path before changing billing behavior.
- If schema or data-shape changes are made, review the matching SQL migration path.
- Prefer real code and config over documentation when they conflict.
- Work only in the files needed for the task, plan first, and keep changes small and commit-friendly.

## Skill Usage

- Do not load or invoke Superpowers or other optional skills automatically at session start.
- Before using any Superpowers skill, ask the user for permission and name the exact skill plus the reason.
- For routine tasks such as checking databases, reading logs, inspecting git status, reviewing files, or running documented deploy/diagnostic commands, use project docs and direct commands first; do not read skills unless the user approves.
- If the user explicitly asks to use a skill or plugin, use only the minimum relevant skill files and state that you are doing so.
- If higher-priority runtime instructions force a skill lookup, keep it minimal and continue without broad skill exploration.

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
3. rewrite /Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md to reflect current state;
4. append one new entry to /Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/SESSION_LOG.md;
5. keep both files short, factual, and agent-readable.

## Current Focus

Support final testing, debugging, and pilot rollout to 5 real users without destabilizing production behavior.
