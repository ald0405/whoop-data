# WHOOP Health Data Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![UV](https://img.shields.io/badge/package%20manager-UV-orange.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A health data platform that integrates WHOOP and Withings devices. Includes ETL pipelines, a REST API, analytics (including multiple linear regression), and a conversational agent for querying your data.

## Features

- **Data Integration** -- ETL pipelines for WHOOP (recovery, sleep, workouts, cycles) and Withings (weight, body composition, heart rate)
- **REST API** -- FastAPI backend with interactive Swagger docs
- **Analytics Pipeline** -- Trend analysis, correlation analysis, and multiple linear regression models for recovery and HRV
- **Chat Agent** -- LangGraph-based agent for natural language queries against your health data
- **Dashboard** -- Web UI with charts, MLR coefficient tables, partial correlation charts, and correlation heatmaps

## Quick Start

### 1. Install UV and Dependencies

```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates .venv automatically)
uv sync
```

### 2. Set up Environment Variables

Create a `.env` file with your API credentials:

```bash
# WHOOP OAuth 2.0
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret

# Withings OAuth
WITHINGS_CLIENT_ID=your_withings_client_id
WITHINGS_CLIENT_SECRET=your_withings_client_secret
WITHINGS_CALLBACK_URL=http://localhost:8766/callback

# OpenAI (required for the chat agent)
OPENAI_API_KEY=your_openai_api_key
```

WHOOP uses OAuth 2.0 browser authentication -- you will be redirected to log in through their website when first running the ETL.

### 3. Initialise Database and Load Data

```bash
make run
```

The interactive CLI will walk you through creating tables, authenticating with WHOOP and Withings, loading data, and starting the API server.

### 4. Start the Chat Interface (optional)

```bash
make chat
```

Chat UI runs at http://localhost:7860. You can ask questions like:
- "Show me my tennis workouts from 2025"
- "What's my weight trend over the last 30 days?"
- "How has my recovery been this month?"

### 5. Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Make Commands

```
Setup:
  make install        Install production dependencies
  make dev            Install with dev dependencies
  make sync           Sync/update dependencies

Run:
  make run            Start the interactive CLI launcher
  make server         Start FastAPI server
  make etl            Run ETL pipeline (incremental)
  make etl-full       Run ETL pipeline (full load)
  make chat           Start chat interface
  make analytics      Run analytics pipeline
  make langgraph-dev  Start LangGraph dev server with LangSmith Studio

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
- See [docs/technical/](docs/technical/) for detailed guides

## Documentation

Documentation is in the [`docs/`](docs/README.md) directory:

- [Technical Documentation](docs/technical/) -- Development logs, API changes, troubleshooting
- [Features Documentation](docs/features/) -- Feature specs and configuration

## Acknowledgements

The multiple linear regression module was inspired by [idossha/whoop-insights](https://github.com/idossha/whoop-insights/blob/main/src/whoop_sync/mlr.py).

## License

MIT License. See [LICENSE](LICENSE) for details.
