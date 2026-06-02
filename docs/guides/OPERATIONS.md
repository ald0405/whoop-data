# Operations & Setup Guide

Detailed runbook for running the platform locally: optional shared memory, all run modes,
the Telegram adapter, rollout verification, the full command reference, and troubleshooting.
For the product overview and a lean quick start, see the [root README](../../README.md).

## Optional but recommended: shared Postgres for agent memory

If you want Telegram, API, chat UI, and LangSmith UI to share the same conversational and
long-term memory, run a local Postgres instance and add this to `.env`:

```bash
AGENT_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/whoop_agent?sslmode=disable
AGENT_PERSISTENCE_AUTO_SETUP=true
```

With `AGENT_POSTGRES_URL` set, the agent uses Postgres-backed checkpointing and long-term
memory storage. If it is not set, the agent falls back to in-memory persistence for
development/tests.

Example local startup with Docker:

```bash
docker run --name whoop-agent-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=whoop_agent \
  -p 5432:5432 \
  -d postgres:16
```

Or use the built-in helper:

```bash
make postgres-up
```

Or with Homebrew services:

```bash
brew install postgresql@16
brew services start postgresql@16
createdb whoop_agent
```

## Shared memory testing flow

Once `AGENT_POSTGRES_URL` is configured, you can test durable shared memory end-to-end:

1. Start the API:

```bash
make server
```

2. Start a client surface such as Telegram or chat UI:

```bash
make telegram-bot
# or
make chat
```

3. In a coaching conversation, tell the agent something durable such as:
   - “Remember that I’m training for a half marathon in October.”
   - “Remember that I prefer blunt feedback.”

4. In a later message or from another client surface, ask something that should use that memory:
   - “What should I focus on this week?”
   - “What do you remember about my current goal?”

5. Restart the app process and repeat the follow-up question. With Postgres configured, the
   memory and thread state should survive the restart.

For API testing, you can also hit the agent routes directly:

```bash
curl -X POST http://localhost:8000/api/v1/agent/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Remember that I am training for Hyrox in September.",
    "user_id": "manual-test-user"
  }'
```

Then ask a follow-up with the same `user_id`:

```bash
curl -X POST http://localhost:8000/api/v1/agent/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What should my training priority be?",
    "user_id": "manual-test-user"
  }'
```

## Canonical run modes

### Primary commands

- `make etl` -- Canonical incremental ingestion command
- `make etl-full` -- Canonical full-history ingestion command
- `make server` -- Canonical FastAPI server for the `data`, `insights`, and `agent` surfaces
- `make chat` -- Canonical Gradio chat UI backed by the shared conversation boundary
- `make telegram-bot` -- Telegram bot transport backed by the shared conversation boundary
- `make analytics` -- Canonical analytics materialization command
- `make langgraph-dev` -- Development-only LangGraph tooling
- `uv run whoop-withings-auth` -- Canonical Withings re-auth utility

### Convenience launchers

- `make run` / `uv run whoop-start` -- Interactive launcher that combines ETL and server flows
- `make dev-all` -- Combined FastAPI + LangGraph dev helper

Use the primary commands for docs, automation, and repeatable workflows. Treat the
convenience launchers as shortcuts rather than the canonical product entrypoints.

## Telegram bot setup

The LangChain Telegram page linked in some examples is a document loader for ingesting
Telegram data; it is not the transport used to expose this agent over Telegram. In this
repository, Telegram is an optional adapter over the same shared conversation boundary used
by the API and Gradio chat UI.

### Required configuration

Add the Telegram bot token to `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_botfather_token_here
```

The bot token is a secret. Do not paste it into chat, logs, screenshots, or source control.
If it is ever exposed, rotate it in `@BotFather` and update `.env`.

### First-run ID capture

Start the API and the Telegram bot:

```bash
make server
make telegram-bot
```

Message the bot in a private Telegram chat, then use `/whoami` to see your Telegram `user_id`
and `chat_id`. In a 1:1 bot chat these values may be identical — that is normal. After that,
restrict the bot to your account by setting:

```bash
TELEGRAM_ALLOWED_USER_IDS=123456789
TELEGRAM_ALLOWED_CHAT_IDS=123456789
```

Restart the bot after updating `.env` so the allowlists take effect.

### Runtime model

Telegram runs as a separate transport process over the shared conversation boundary:

```bash
make server
make telegram-bot
```

`make dev-all` starts FastAPI and LangGraph dev tooling, but it does not start the Telegram bot.

For an always-on local setup on macOS, use the persistent service helpers instead:

```bash
make services-up
make services-test
```

That installs `launchd` jobs for the API server, Telegram bot, the scheduled morning summary
push, the proactive window evaluator, and the weakness reminder evaluator. Remove them with:

```bash
make services-down
```

### Current Telegram behavior

- Supports `/start` and `/whoami`
- Supports normal text chat with the shared health-data agent
- Reuses conversation context per Telegram chat
- Supports proactive pushes into the same shared Telegram conversation thread via `/api/v1/agent/telegram/push`
- Rejects non-private chats
- Uses Telegram-only HTML formatting for better rendering without changing Studio/API output
- Sends agent-generated image artifacts back to Telegram when available
- **Voice messages**: Send a voice note and the bot transcribes it (Whisper), processes it through the agent, and replies with both a voice note (TTS) and text
- **Photo messages**: Send a photo (with optional caption) and the bot interprets it using the vision-capable model in the context of your health data

Current limitations:

- The bot must be restarted after changing Telegram token or allowlist settings
- Voice replies use OpenAI TTS which has a ~2000 token input limit; very long responses fall back to text only

The Telegram adapter can silently ignore unauthorized users once the allowlists are set.
Rotate any token that was ever pasted into chat, logs, or source control before relying on
the bot.

### Proactive Telegram smoke test

You can send yourself a proactive Telegram message that goes through the shared conversation
service:

```bash
uv run -m scripts.telegram_hello --prompt "set me up for the day"
```

Or route the same flow through the running API server:

```bash
uv run -m scripts.telegram_hello --api --prompt "set me up for the day"
```

### Weakness reminder preview

You can send yourself a manual preview of the annual-review weakness reminder without
consuming the once-per-workday scheduled send:

```bash
uv run python scripts/telegram_weakness_preview.py
```

Optionally preview a specific top-level bullet from `weakness.md`:

```bash
uv run python scripts/telegram_weakness_preview.py --point-number 2
```

If you prefer richer Telegram formatting (bold/italics/bullets), you can request HTML
formatting for the preview:

```bash
uv run python scripts/telegram_weakness_preview.py --point-number 2 --format html
```

To enable HTML formatting for all proactive pushes by default, set
`TELEGRAM_PROACTIVE_FORMAT=html` in `.env`. To rename the coach in proactive prompts, set
`COACH_NAME` in `.env`.

## Rollout verification checklist

1. Run the focused validation slices for the migration work before cutting over.
2. Start the API with `make server` and confirm `/docs` shows the `data`, `insights`, and `agent` OpenAPI tags.
3. Smoke the canonical public flows:
   - `GET /api/v1/data/recovery`
   - `GET /api/v1/insights/dashboard/daily`
   - `POST /api/v1/agent/conversations`
   - `POST /api/v1/agent/messages`
4. Smoke representative compatibility adapters such as `/workouts/latest`, `/recovery/latest`, `/dashboard/daily`, and `/api/daily-plan`, and confirm the `Deprecation`, `Sunset`, and `X-Canonical-Route` headers advertise the canonical replacement.
5. Launch `make chat`, send an initial message, then send a follow-up message and confirm the conversation resumes cleanly instead of starting a new thread.
6. Keep `make langgraph-dev` scoped to development/debugging workflows rather than rollout verification of the public product surface.

## Make commands

```text
Setup:
  make install        Install production dependencies
  make dev            Install with dev dependencies
  make sync           Sync/update dependencies

Run:
  make run            Convenience launcher (interactive ETL + server menu)
  make server         Primary FastAPI server command
  make etl            Primary ETL pipeline (incremental)
  make etl-full       Primary ETL pipeline (full load)
  make chat           Primary chat interface command
  make telegram-bot   Telegram bot adapter command
  make analytics      Primary analytics pipeline command
  make langgraph-dev  Development-only LangGraph dev server
  make dev-all        Convenience FastAPI + LangGraph dev launcher
  make proactive-now  Run the proactive window evaluator immediately
  make weakness-now   Run the weakness reminder evaluator immediately
  make weakness-preview Send a manual weakness reminder preview to Telegram

Development:
  make test           Run tests with pytest
  make test-cov       Run tests with coverage report
  make format         Format code with black
  make lint           Lint with ruff (including docstrings) and flake8
  make typecheck      Type check with mypy
  make verify         Run system verification

Maintenance:
  make clean          Clean cache files and build artifacts
  make clean-all      Clean everything including .venv
```

## Troubleshooting

- **WHOOP 401 errors** -- Delete `.whoop_tokens.json` and re-authenticate
- **Withings re-auth** -- Run `uv run whoop-withings-auth`
- **Telegram token rejected** -- Re-copy the current token from `@BotFather`, make sure `.env` contains the full token with no quotes or truncation, then restart `make telegram-bot`
- **`/whoami` or formatting errors in Telegram** -- Restart the bot after pulling the latest code; Telegram formatting is handled adapter-side and should not affect Studio/API output
- **Telegram access control not working** -- Confirm `TELEGRAM_ALLOWED_USER_IDS` and `TELEGRAM_ALLOWED_CHAT_IDS` are set in `.env`, then restart the bot
- **Looking for the right API?** -- Use `/api/v1/data/*` for raw records, `/api/v1/insights/*` for interpreted outputs, and `/api/v1/agent/*` for conversational requests
- **Need detailed implementation notes?** -- Start in [`docs/README.md`](../README.md)
