# WHOOP Health Data Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![UV](https://img.shields.io/badge/package%20manager-UV-orange.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![WHOOP Health Data Platform product snapshot](docs/assets/readme-hero.png)

This project turns fragmented personal health data into a decision-support product. It combines WHOOP and Withings data with analytics, API surfaces, and a chat layer so the user can move from “what happened?” to “what should I do next?” across training, recovery, sleep, and broader day-of planning.

## Why this project matters

The product goal is not just to collect biometrics. It is to make personal health data more actionable by:

- translating raw records into interpretable trends and coaching-style outputs
- connecting multiple systems into one consistent experience layer
- making the same underlying data accessible through API, dashboard, and conversational UX
- supporting better day-of decisions around training load, recovery, and activity planning

## Product outcomes

- **Single source of truth** for recovery, sleep, workouts, body composition, and related context
- **Faster interpretation** via dashboards, derived insights, and scenario-oriented analytics
- **More accessible exploration** through a chat interface for natural-language questions
- **More usable health decisions** by framing outputs around actions, not just raw measurements

## What it does

- **Data Integration** -- ETL pipelines for WHOOP (recovery, sleep, workouts, cycles) and Withings (weight, body composition, heart rate)
- **REST API** -- FastAPI backend with interactive Swagger docs
- **Analytics Pipeline** -- Trend analysis, correlation analysis, and multiple linear regression models for recovery and HRV
- **Chat Agent** -- LangGraph-based agent for natural language queries against your health data
- **Dashboard** -- Web UI with charts, MLR coefficient tables, partial correlation charts, and correlation heatmaps
- **Telegram Bot** -- Optional Telegram transport for the shared agent conversation boundary

## Experience at a glance

- **Dashboard** for quick review of trends and supporting visualizations
- **API** for structured access to raw and interpreted outputs
- **Chat** for question-driven exploration such as:
  - “Show me my tennis workouts from 2025”
  - “What’s my weight trend over the last 30 days?”
  - “How has my recovery been this month?”

## Public Surface Model

- **`data`** -- Raw health records, context resources, and provider status under `/api/v1/data/*`
- **`insights`** -- Derived dashboards, analytics, scenarios, plans, and reports under `/api/v1/insights/*`
- **`agent`** -- Conversational/coaching requests under `/api/v1/agent/*`
- **`web`** -- Human-facing pages at `/dashboard`, `/analytics`, and `/report`

New integrations should target the canonical namespaces above. Legacy aliases still exist in a few places as temporary compatibility adapters during the migration.

WHOOP developer integrations in this repository target the WHOOP **v2** API. The app's own route versioning under `/api/v1/*` is internal product/API namespacing and is separate from the upstream WHOOP developer API version.

## Quick Start

### 1. Install UV and dependencies

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 2. Set up environment variables

Create a `.env` file with your API credentials:

```bash
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret
WITHINGS_CLIENT_ID=your_withings_client_id
WITHINGS_CLIENT_SECRET=your_withings_client_secret
WITHINGS_CALLBACK_URL=http://localhost:8766/callback
OPENAI_API_KEY=your_openai_api_key
```

WHOOP uses OAuth 2.0 browser authentication. When first running ingestion, you may be redirected to complete the authorization-code flow in the browser.

### 2a. Optional but recommended: shared Postgres for agent memory

If you want Telegram, API, chat UI, and LangSmith UI to share the same conversational and long-term memory, run a local Postgres instance on the Mac mini and add this to `.env`:

```bash
AGENT_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/whoop_agent?sslmode=disable
AGENT_PERSISTENCE_AUTO_SETUP=true
```

With `AGENT_POSTGRES_URL` set, the agent will use Postgres-backed checkpointing and long-term memory storage. If it is not set, the agent falls back to in-memory persistence for development/tests.

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

### 3. Ingest data

```bash
make etl
# or, for a full historical backfill:
make etl-full
```

These are the canonical ingestion commands. `make run` is still available as a convenience launcher, but it mixes ETL and server startup in one interactive flow.

### 4. Start the API

```bash
make server
```

The API server exposes the canonical `data`, `insights`, and `agent` surfaces.

### 5. Run analytics (optional)

```bash
make analytics
```

Use this when you want to materialize analytics and insight outputs ahead of time.

### 6. Start the chat interface (optional)

```bash
make chat
```

Chat UI runs at `http://localhost:7860`.

### 7. Start LangGraph dev tooling (optional, development-only)

```bash
make langgraph-dev
```

This is for development and debugging workflows. It is not a separate product surface and should not be treated as the public agent API.

### 8. Access the API

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI tags**: `data`, `insights`, and `agent`

## Shared memory testing flow

Once `AGENT_POSTGRES_URL` is configured, you can test durable shared memory end-to-end like this:

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

5. Restart the app process and repeat the follow-up question. With Postgres configured, the memory and thread state should survive the restart.

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

## Canonical Run Modes

### Primary Commands

- `make etl` -- Canonical incremental ingestion command
- `make etl-full` -- Canonical full-history ingestion command
- `make server` -- Canonical FastAPI server for the `data`, `insights`, and `agent` surfaces
- `make chat` -- Canonical Gradio chat UI backed by the shared conversation boundary
- `make telegram-bot` -- Telegram bot transport backed by the shared conversation boundary
- `make analytics` -- Canonical analytics materialization command
- `make langgraph-dev` -- Development-only LangGraph tooling
- `uv run whoop-withings-auth` -- Canonical Withings re-auth utility

### Convenience Launchers

- `make run` / `uv run whoop-start` -- Interactive launcher that combines ETL and server flows
- `make dev-all` -- Combined FastAPI + LangGraph dev helper

Use the primary commands for docs, automation, and repeatable workflows. Treat the convenience launchers as shortcuts rather than the canonical product entrypoints.

## Telegram bot setup

The LangChain Telegram page linked in some examples is a document loader for ingesting Telegram data; it is not the transport used to expose this agent over Telegram. In this repository, Telegram is an optional adapter over the same shared conversation boundary used by the API and Gradio chat UI.

### Required configuration

Add the Telegram bot token to `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_botfather_token_here
```

The bot token is a secret. Do not paste it into chat, logs, screenshots, or source control. If it is ever exposed, rotate it in `@BotFather` and update `.env`.

### First-run ID capture

Start the API and the Telegram bot:

```bash
make server
make telegram-bot
```

Message the bot in a private Telegram chat, then use `/whoami` to see your Telegram `user_id` and `chat_id`. In a 1:1 bot chat these values may be identical — that is normal. After that, restrict the bot to your account by setting:

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

That installs `launchd` jobs for the API server, Telegram bot, the scheduled morning summary push, the proactive window evaluator, and the weakness reminder evaluator. Remove them with:

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

The Telegram adapter can silently ignore unauthorized users once the allowlists are set. Rotate any token that was ever pasted into chat, logs, or source control before relying on the bot.

### Proactive Telegram smoke test

You can send yourself a proactive Telegram message that goes through the shared conversation service:

```bash
uv run -m scripts.telegram_hello --prompt "set me up for the day"
```

Or route the same flow through the running API server:

```bash
uv run -m scripts.telegram_hello --api --prompt "set me up for the day"
```

### Weakness reminder preview

You can send yourself a manual preview of the annual-review weakness reminder without consuming the once-per-workday scheduled send:

```bash
uv run python scripts/telegram_weakness_preview.py
```

Optionally preview a specific top-level bullet from `weakness.md`:

```bash
uv run python scripts/telegram_weakness_preview.py --point-number 2
```

## Rollout Verification Checklist

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

## Repo notes for reviewers

- The root now prioritizes core product files and entrypoints.
- Supporting guides live under `docs/` to keep the submission easier to scan.
- Local runtime artifacts such as tokens, logs, caches, virtual environments, and local databases are gitignored and not part of the deliverable.

## Make Commands

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
  make lint           Lint with flake8
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
- **Need detailed implementation notes?** -- Start in [`docs/README.md`](docs/README.md)

## Documentation

Documentation is organized in [`docs/`](docs/README.md):

- [`docs/technical/`](docs/technical/) -- API changes, migration notes, troubleshooting, implementation detail
- [`docs/features/`](docs/features/) -- Feature specs and product behavior
- [`docs/guides/`](docs/guides/) -- Testing, plotting, and contribution workflow guides

## Acknowledgements

The multiple linear regression module was inspired by [idossha/whoop-insights](https://github.com/idossha/whoop-insights/blob/main/src/whoop_sync/mlr.py).

## License

MIT License. See [LICENSE](LICENSE) for details.
