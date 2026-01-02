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


## 🚀 Quick Start

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

### 3. Initialize Database & Load Data

```bash
# Start the interactive CLI launcher
make run
```

This will:
1. 📦 **Create database tables** (SQLite in `./db/whoop.db`)
2. 🔐 **Authenticate with WHOOP** (browser popup for OAuth)
3. 🔐 **Authenticate with Withings** (browser popup for OAuth)
4. 📊 **Load your health data** (recovery, workouts, sleep, weight, etc.)
5. 🌐 **Start the API server** (http://localhost:8000)

### 4. Start the AI Chat Interface

```bash
make chat
```

### 5. Start Chatting! 🎉

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

## 🔧 Troubleshooting

For detailed troubleshooting guides, see:
- [WHOOP Authentication Issues](docs/technical/)
- [Withings Setup Guide](docs/technical/)
- Run `uv run whoop-withings-auth` to re-authenticate Withings
- Delete `.whoop_tokens.json` if you encounter 401 errors


## 🔌 API Endpoints

Explore the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Key endpoints include recovery, workouts, sleep, weight, and heart rate data.

## 🛠️ Common Commands

```bash
make help        # Show all available commands
make run         # Start interactive CLI
make server      # Start FastAPI server
make chat        # Start chat interface
make etl         # Run ETL pipeline
make verify      # System verification
```

Run `make help` to see all available commands.



## Documentation

Comprehensive documentation is available in the [`docs/`](docs/README.md) directory:

- **[Technical Documentation](docs/technical/)** - Development logs, API changes, and troubleshooting
- **[Features Documentation](docs/features/)** - Feature specifications and configurations

For API documentation, visit http://localhost:8000/docs after starting the application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
