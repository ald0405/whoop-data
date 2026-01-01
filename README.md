# 🏥 AI-Powered Health Data Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![UV](https://img.shields.io/badge/package%20manager-UV-orange.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT-green.svg)](https://openai.com/)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph-purple.svg)](https://langchain-ai.github.io/langgraph/)

A comprehensive **AI-powered health data platform** that integrates WHOOP and Withings devices with a conversational agent interface. Chat with your health data using natural language queries!

## ✨ Features

- 🤖 **AI Health Data Agent** - Chat with your data using natural language
- 📊 **Comprehensive Data Integration** - WHOOP + Withings APIs
- 🎾 **Sport-Specific Analysis** - Tennis, running, and general workout tracking
- 📈 **Trend Analysis** - Weight, recovery, sleep patterns over time
- 🌐 **REST API** - Complete FastAPI backend with documentation
- 💬 **Web Chat Interface** - Beautiful Gradio-powered chat UI

## Project Structure

```
whoop-data/
├── whoopdata/               # Main package directory
│   ├── __init__.py
│   ├── start.py              # Main application launcher
│   ├── etl.py                # ETL pipeline logic
│   ├── database.py           # Database setup utilities  
│   ├── utils.py              # Database loading utilities
│   ├── model_transformation.py # Data transformation functions
│   ├── agent/                # 🤖 AI Agent System
│   │   ├── __init__.py
│   │   ├── graph.py          # LangGraph agent orchestration
│   │   ├── nodes.py          # Agent nodes (supervisor, tools)
│   │   ├── tools.py          # Health data tools for agent
│   │   ├── schemas.py        # Agent state and configuration
│   │   └── settings.py       # Agent configuration
│   ├── api/                  # FastAPI routes
│   │   ├── __init__.py
│   │   ├── recovery_routes.py
│   │   ├── sleep_routes.py
│   │   ├── workout_routes.py
│   │   └── withings_routes.py
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── models.py
│   ├── clients/              # API clients for WHOOP and Withings
│   │   ├── __init__.py
│   │   ├── whoop_client.py
│   │   └── withings_client.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── recovery.py
│   │   ├── sleep.py
│   │   └── workout.py
│   ├── crud/                 # Database CRUD operations
│   │   ├── __init__.py
│   │   ├── recovery.py
│   │   ├── sleep.py
│   │   └── workout.py
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── db_loader.py      # Database loading utilities
│   │   ├── date_filters.py   # Date filtering utilities
│   │   └── matplotlib_config.py # Chart configuration
│   ├── tests/                # Test files
│   │   ├── __init__.py
│   │   └── test_withings.py
│   └── analysis/             # Analysis scripts and notebooks
│       ├── __init__.py
│       └── ...
├── scripts/                  # Helper scripts
│   ├── create_tables.py      # Database table creation
│   └── run_etl.py           # Standalone ETL runner
├── chat_app.py              # 💬 Gradio chat interface
├── start_health_chat.py     # 🚀 Complete system launcher
├── main.py                   # FastAPI application entry point
├── run_app.py               # Complete data pipeline + API server
├── app.py                    # Main FastAPI application
├── setup.py                 # Package configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── AGENT_PERSONALITY_GUIDE.md # AI agent coaching style guide
└── README.md

```

## 🚀 Quick Start Guide

### Step 1: Install UV and Dependencies

**Option A: Using UV (Recommended - Fast & Modern)**
```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates .venv automatically)
uv sync

# Or use make for convenience
make dev
```

**Option B: Traditional pip/venv (Still supported)**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Step 2: Set up Environment Variables

Create a `.env` file with your API credentials:

```bash
# WHOOP OAuth 2.0 (Browser-based authentication - no username/password needed!)
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret

# Withings OAuth credentials  
WITHINGS_CLIENT_ID=your_withings_client_id
WITHINGS_CLIENT_SECRET=your_withings_client_secret
WITHINGS_CALLBACK_URL=http://localhost:8766/callback

# OpenAI API for AI agent functionality
OPENAI_API_KEY=your_openai_api_key
```

**📝 Note**: WHOOP uses OAuth 2.0 browser authentication - you'll be redirected to login through their website when needed.

### Step 3: Initialize Database & Load Data

The system automatically creates the database and loads your health data:

**Using UV/Make:**
```bash
# Start the interactive CLI launcher
make run
# or
uv run whoop-start

# Or run directly
uv run python run_app.py
```

**Using traditional Python:**
```bash
python run_app.py
```

This will:
1. 📦 **Create database tables** (SQLite in `./db/whoop.db`)
2. 🔐 **Authenticate with WHOOP** (browser popup for OAuth)
3. 🔐 **Authenticate with Withings** (browser popup for OAuth)
4. 📊 **Load your health data** (recovery, workouts, sleep, weight, etc.)
5. 🌐 **Start the API server** (http://localhost:8000)

### Step 4: Start the AI Chat Interface

**🎯 Option A: Complete System (Recommended)**
```bash
# Using make
make chat

# Or using UV directly
uv run python start_health_chat.py

# Or traditional
python start_health_chat.py
```

**💬 Option B: Chat Interface Only**
```bash
make chat
# or
uv run python chat_app.py
```

### Step 5: Start Chatting with Your Health Data! 🎉

**🤖 AI Chat Interface**: http://localhost:7860

**Example Questions to Try:**
- "Show me my tennis workouts from 2025"
- "What's my weight trend over the last 30 days?"
- "How has my recovery been this month?"
- "Get my latest sleep data and analyze my patterns"
- "Show me my running performance with TRIMP scores"

**🌐 REST API Access:**
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Sample Endpoint**: http://localhost:8000/recovery/latest

## 🔧 WHOOP Troubleshooting (Quick)

- **401 Authorization errors** (especially for cycle/strain data):
  - Delete old token: `rm .whoop_tokens.json`
  - Next ETL run will re-authenticate with updated scopes (including `read:cycles`)
  - This is needed after upgrading to versions with new API scopes
- **Token refresh issues**:
  - WHOOP tokens expire - the system will automatically re-authenticate when needed
  - Browser popup will open for OAuth flow

## 🔧 Withings Troubleshooting (Quick)

- Ensure these are set in `.env` and registered in Withings dashboard:
  - `WITHINGS_CLIENT_ID`, `WITHINGS_CLIENT_SECRET`, `WITHINGS_CALLBACK_URL`
- Force re-auth if browser doesn't open or data is stale:
  - `uv run whoop-withings-auth` (or `whoop-withings-auth` after uv sync)
- If browser didn't open:
  - Copy the printed authorization URL into your browser
- If callback fails:
  - The app binds to `127.0.0.1` and will try ports 8766..8771; ensure your redirect URI allows the chosen port
- Check status:
  - `curl http://localhost:8000/auth/withings/status`

## 📊 Data Pipeline Details

### What Gets Loaded

When you run `python run_app.py`, the system loads:

**WHOOP Data:**
- 📊 **Recovery scores** (HRV, RHR, sleep quality)
- 🔄 **Cycles** (physiological days, daily strain, energy expenditure)
- 🏋️ **Workout data** (strain, heart rate zones, sports)
- 😴 **Sleep tracking** (stages, efficiency, duration)

**Withings Data:**
- ⚖️ **Weight & body composition** (BMI, fat ratio, muscle mass)
- 💗 **Heart rate & blood pressure** (systolic, diastolic)

### Database Setup

The system automatically:
1. Creates SQLite database at `./db/whoop.db`
2. Sets up all required tables
3. Handles data transformations and relationships
4. Manages duplicate prevention

### Token Management

- **WHOOP**: OAuth tokens auto-refresh, occasional re-authentication needed
- **Withings**: Long-lived tokens with automatic refresh (rarely need to re-login)
- **Tokens stored securely** in hidden files with proper permissions

## API Endpoints

### WHOOP Data
- `GET /recovery` - Recovery scores and metrics
- `GET /recovery/latest` - Most recent recovery
- `GET /workout` - Workout data and strain
- `GET /workout/latest` - Most recent workout
- `GET /sleep` - Sleep performance data  
- `GET /sleep/latest` - Most recent sleep

### Withings Data
- `GET /withings/weight` - Weight and body composition
- `GET /withings/weight/latest` - Most recent weight
- `GET /withings/weight/stats` - Weight statistics
- `GET /withings/heart-rate` - Heart rate and blood pressure
- `GET /withings/heart-rate/latest` - Most recent heart rate
- `GET /withings/summary` - Withings data summary

## 🛠️ Make Commands

Convenient commands for common tasks (requires UV):

```bash
# Setup
make help        # Show all available commands
make install     # Install production dependencies
make dev         # Install with dev dependencies
make sync        # Update dependencies

# Run
make run         # Start interactive CLI launcher
make server      # Start FastAPI server
make etl         # Run ETL pipeline (incremental)
make etl-full    # Run ETL pipeline (full load)
make chat        # Start chat interface
make analytics   # Run analytics pipeline

# Development
make test        # Run tests
make test-cov    # Run tests with coverage
make format      # Format code with black
make lint        # Lint with flake8
make typecheck   # Type check with mypy
make verify      # Run system verification

# Maintenance
make clean       # Clean cache files
make clean-all   # Clean everything including venv
```

## Development

### Testing Withings Integration

```bash
make test
# or
uv run python whoopdata/tests/test_withings.py
```

### Running ETL Pipeline Only

```bash
make etl        # Incremental load
make etl-full   # Full load
# or
uv run python scripts/run_etl.py
```

### System Verification

```bash
make verify
# or
uv run python verify_system.py
```

## WHOOP Data Summary

### Physiological Cycles
- Activity is referenced in the context of a Physiological Cycle (Cycle for short).
- **Current Cycle:** Only has a Start Time. Past Cycles have both start and end times.
- A physiological day on WHOOP begins when you fall asleep one night and ends when you fall asleep the following night.

### Recovery
- Daily measure of body preparedness to perform.
- **Recovery score:** Percentage between 0 - 100% calculated in the morning.
- Calculated using previous day's data including RHR, HRV, respiratory rate, sleep quality, etc.
- **GREEN** (67-100%): Well recovered and primed to perform.
- **YELLOW** (34-66%): Maintaining and ready for moderate strain.
- **RED** (0-33%): Indicates the need for rest.

### Sleep Tracking
- Tracks sleep duration and stages: Light, REM, and Deep sleep.
- Calculates sleep need based on Sleep Debt and previous day's activity.

### Strain
- Measurement of stress on the body, scored on a 0 to 21 scale.
- Based on [Strain Borg Scale of Perceived Exertion](https://www.cdc.gov/physicalactivity/basics/measuring/exertion.htm).
- Strain scores tracked continuously throughout the day and during workouts.

### Workout Tracking
- WHOOP tracks workouts and measures accumulated Strain over each workout.

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/README.md) directory:

- **[Technical Documentation](docs/technical/)** - Development logs, API changes, and troubleshooting
- **[Features Documentation](docs/features/)** - Feature specifications and configurations

For API documentation, visit http://localhost:8000/docs after starting the application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
