.PHONY: help install dev sync run server etl chat telegram-bot analytics langgraph-dev dev-all dev-full dev-full-stop postgres-up postgres-down postgres-logs test format lint typecheck clean verify schedule-up schedule-down schedule-test morning-now services-up services-down services-test

# Default target
help:
	@echo "🏥 WHOOP Data Platform - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install project with production dependencies"
	@echo "  make dev         - Install project with dev dependencies"
	@echo "  make sync        - Sync dependencies (update lockfile)"
	@echo ""
	@echo "Run:"
	@echo "  make run         - Convenience launcher (interactive ETL + server menu)"
	@echo "  make server      - Primary FastAPI server command"
	@echo "  make etl         - Primary ETL pipeline (incremental load)"
	@echo "  make etl-full    - Primary ETL pipeline (full load)"
	@echo "  make chat        - Primary chat interface command"
	@echo "  make telegram-bot - Telegram bot adapter for the shared agent boundary"
	@echo "  make analytics   - Primary analytics pipeline command"
	@echo "  make langgraph-dev - Development-only LangGraph dev server"
	@echo "  make dev-all     - Convenience FastAPI + LangGraph dev launcher"
	@echo "  make dev-full    - FastAPI + Telegram bot + LangGraph dev launcher"
	@echo "  make dev-full-stop - Stop FastAPI, Telegram bot, and LangGraph dev leftovers"
	@echo "  make postgres-up - Start local Docker Postgres for shared agent memory"
	@echo "  make postgres-down - Stop local Docker Postgres container"
	@echo "  make postgres-logs - Tail local Docker Postgres logs"
	@echo "  make services-up   - Install persistent launchd services for API + Telegram bot + morning job"
	@echo "  make services-down - Uninstall persistent launchd services"
	@echo "  make services-test - Check persistent service status"
	@echo "  make schedule-up   - Install launchd schedule (daily morning ETL + push)"
	@echo "  make schedule-down - Uninstall launchd schedule"
	@echo "  make schedule-test - Check if the schedule is loaded"
	@echo "  make morning-now   - Run the morning ETL + push immediately"
	@echo ""
	@echo "Development:"
	@echo "  make test        - Run tests with pytest"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make format      - Format code with black"
	@echo "  make lint        - Lint code with flake8"
	@echo "  make typecheck   - Type check with mypy"
	@echo "  make verify      - Run system verification checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       - Clean cache files and build artifacts"
	@echo "  make clean-all   - Clean everything including venv"
	@echo ""

# Installation targets
install:
	@echo "📦 Installing whoop-data..."
	uv sync --no-dev

dev:
	@echo "📦 Installing whoop-data with dev dependencies..."
	uv sync

sync:
	@echo "🔄 Syncing dependencies..."
	uv sync

# Run targets
run:
	@echo "🚀 Starting CLI launcher..."
	uv run whoop-start

server:
	@echo "🌐 Starting FastAPI server..."
	@launchctl unload ~/Library/LaunchAgents/com.whoopdata.server.plist 2>/dev/null || true
	uv run uvicorn main:app --host localhost --port 8000 --reload

etl:
	@echo "📊 Running ETL pipeline (incremental)..."
	uv run python -c "from whoopdata.etl import run_complete_etl; from whoopdata.database.database import engine; from whoopdata.models.models import Base; Base.metadata.create_all(bind=engine); run_complete_etl(incremental=True)"

etl-full:
	@echo "📊 Running ETL pipeline (full load)..."
	uv run python -c "from whoopdata.etl import run_complete_etl; from whoopdata.database.database import engine; from whoopdata.models.models import Base; Base.metadata.create_all(bind=engine); run_complete_etl(incremental=False)"

chat:
	@echo "💬 Starting chat interface..."
	uv run python chat_app.py

telegram-bot:
	@echo "📨 Starting Telegram bot adapter..."
	uv run whoop-telegram-bot

analytics:
	@echo "🤖 Running analytics pipeline..."
	uv run python -c "from whoopdata.pipelines.analytics_pipeline import run_analytics_pipeline; run_analytics_pipeline(days_back=365)"

langgraph-dev:
	@echo "🎨 Starting LangGraph dev server with LangSmith Studio..."
	@echo "📍 API: http://127.0.0.1:2024"
	@echo "🎨 Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
	uv run langgraph dev --allow-blocking

dev-all:
	@echo "🚀 Starting FastAPI server + LangGraph dev server..."
	@launchctl unload ~/Library/LaunchAgents/com.whoopdata.server.plist 2>/dev/null || true
	uv run uvicorn main:app --host localhost --port 8000 --reload &
	@sleep 3
	@echo "📍 FastAPI: http://0.0.0.0:8000"
	@echo "📍 LangGraph API: http://127.0.0.1:2024"
	@echo "🎨 Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
	uv run langgraph dev --allow-blocking

dev-full:
	@echo "🚀 Starting FastAPI server + Telegram bot + LangGraph dev server..."
	@launchctl unload ~/Library/LaunchAgents/com.whoopdata.server.plist 2>/dev/null || true
	@echo "  (paused launchd server for dev mode)"
	uv run uvicorn main:app --host localhost --port 8000 --reload &
	@echo $$! > .dev-full-server.pid
	@sleep 3
	uv run whoop-telegram-bot &
	@echo $$! > .dev-full-telegram.pid
	@sleep 3
	@echo "📍 FastAPI: http://localhost:8000"
	@echo "📍 LangGraph API: http://localhost:2024"
	@echo "🎨 Studio: https://smith.langchain.com/studio/?baseUrl=http://localhost:2024"
	@echo "📨 Telegram bot started in background"
	uv run langgraph dev --allow-blocking

dev-full-stop:
	@echo "🛑 Stopping local dev processes..."
	@for pidfile in .dev-full-server.pid .dev-full-telegram.pid; do \
		if [ -f $$pidfile ] && [ -s $$pidfile ]; then \
			pid=$$(tr -d '[:space:]' < $$pidfile); \
			if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
				kill $$pid 2>/dev/null || true; \
			fi; \
		fi; \
		rm -f $$pidfile; \
	done
	@pkill -f 'uv run whoop-telegram-bot' 2>/dev/null || true
	@pkill -f '/.venv/bin/whoop-telegram-bot' 2>/dev/null || true
	@pkill -f 'uvicorn main:app --host localhost --port 8000 --reload' 2>/dev/null || true
	@pkill -f 'langgraph dev --allow-blocking' 2>/dev/null || true
	@echo "✅ Local dev processes stopped"
	@if [ -f ~/Library/LaunchAgents/com.whoopdata.server.plist ]; then \
		launchctl load ~/Library/LaunchAgents/com.whoopdata.server.plist 2>/dev/null || true; \
		echo "  (resumed launchd server)"; \
	fi

postgres-up:
	@echo "🐘 Ensuring local Postgres container is running..."
	@if docker ps -a --format '{{.Names}}' | grep -qx 'whoop-agent-postgres'; then \
		docker start whoop-agent-postgres; \
	else \
		docker run --name whoop-agent-postgres \
			-e POSTGRES_USER=postgres \
			-e POSTGRES_PASSWORD=postgres \
			-e POSTGRES_DB=whoop_agent \
			-p 5432:5432 \
			-d postgres:16; \
	fi
	@echo "✅ Postgres available for AGENT_POSTGRES_URL on localhost:5432"

postgres-down:
	@echo "🛑 Stopping local Postgres container..."
	@docker stop whoop-agent-postgres

postgres-logs:
	@docker logs -f whoop-agent-postgres

schedule-up:
	@echo "📅 Installing launchd services..."
	@mkdir -p logs
	@cp schedules/com.whoopdata.server.plist ~/Library/LaunchAgents/com.whoopdata.server.plist
	@cp schedules/com.whoopdata.telegram.plist ~/Library/LaunchAgents/com.whoopdata.telegram.plist
	@cp schedules/com.whoopdata.morning.plist ~/Library/LaunchAgents/com.whoopdata.morning.plist
	@launchctl load ~/Library/LaunchAgents/com.whoopdata.server.plist
	@launchctl load ~/Library/LaunchAgents/com.whoopdata.telegram.plist
	@launchctl load ~/Library/LaunchAgents/com.whoopdata.morning.plist
	@echo "✅ Installed: persistent FastAPI server + Telegram bot + daily 07:30 morning job"
	@echo "   Check with: make schedule-test"

schedule-down:
	@echo "🛑 Removing launchd services..."
	@launchctl unload ~/Library/LaunchAgents/com.whoopdata.server.plist 2>/dev/null || true
	@launchctl unload ~/Library/LaunchAgents/com.whoopdata.telegram.plist 2>/dev/null || true
	@launchctl unload ~/Library/LaunchAgents/com.whoopdata.morning.plist 2>/dev/null || true
	@rm -f ~/Library/LaunchAgents/com.whoopdata.server.plist
	@rm -f ~/Library/LaunchAgents/com.whoopdata.telegram.plist
	@rm -f ~/Library/LaunchAgents/com.whoopdata.morning.plist
	@echo "✅ All whoopdata services removed"

schedule-test:
	@echo "📋 Checking schedule status..."
	@launchctl list | grep whoopdata || echo "No whoopdata schedules loaded"

services-up: schedule-up

services-down: schedule-down

services-test: schedule-test

morning-now:
	@echo "☀️ Running morning ETL + push now..."
	uv run python scripts/scheduled_morning.py

# Development targets
test:
	@echo "🧪 Running tests..."
	uv run pytest

test-cov:
	@echo "🧪 Running tests with coverage..."
	uv run pytest --cov=whoopdata --cov-report=html --cov-report=term

format:
	@echo "💄 Formatting code with black..."
	uv run black .

lint:
	@echo "🔍 Linting with flake8..."
	uv run flake8 whoopdata tests

typecheck:
	@echo "🔍 Type checking with mypy..."
	uv run mypy whoopdata

verify:
	@echo "✅ Running system verification..."
	uv run python scripts/verify_system.py

# Cleanup targets
clean:
	@echo "🧹 Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cache cleaned"

clean-all: clean
	@echo "🧹 Removing virtual environment..."
	rm -rf .venv
	rm -rf venv
	@echo "✅ Full cleanup complete"
