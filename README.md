# 🏥 AI-Powered Health Data Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
├── whoop_data/               # Main package directory
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
├── django_whoop/             # Django project (optional)
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

### Step 1: Install Dependencies

```bash
# Create virtual environment (recommended)
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

### Step 3: Initialise Database & Load Data

The system automatically creates the database and loads your health data:

```bash
# Complete setup: Creates database + Loads fresh data + Starts API server
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
# Launches both API server (8000) + Chat interface (7860)
python start_health_chat.py
```

**💬 Option B: Chat Interface Only**
```bash
# Just the chat interface (requires API server running separately)
python chat_app.py
```

### Step 5: Start Chatting with Your Health Data! 🎉

**🤖 AI Chat Interface**: http://localhost:7860

**Example Questions to Try:**
- "Show me my tennis workouts from 2025"
- "What's my weight trend over the last 30 days?"
- "How has my recovery been this month?"
- "Get my latest sleep data and analyse my patterns"
- "Show me my running performance with TRIMP scores"

**🌐 REST API Access:**
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Sample Endpoint**: http://localhost:8000/recovery/latest

## 📊 Data Pipeline Details

### What Gets Loaded

When you run `python run_app.py`, the system loads:

**WHOOP Data:**
- 📊 **Recovery scores** (HRV, RHR, sleep quality)
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

## Development

### Testing Withings Integration

```bash
python whoop_data/tests/test_withings.py
```

### Running ETL Pipeline Only

```bash
python scripts/run_etl.py
```

### Creating Database Tables

```bash
python scripts/create_tables.py
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
