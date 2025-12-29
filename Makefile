.PHONY: help install dev sync run server etl chat analytics langgraph-dev test format lint typecheck clean verify

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
	@echo "  make run         - Start the CLI launcher (interactive menu)"
	@echo "  make server      - Start FastAPI server"
	@echo "  make etl         - Run ETL pipeline (incremental load)"
	@echo "  make etl-full    - Run ETL pipeline (full load)"
	@echo "  make chat        - Start chat interface"
	@echo "  make analytics   - Run analytics pipeline"
	@echo "  make langgraph-dev - Start LangGraph dev server (with LangSmith Studio)"
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
	uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

etl:
	@echo "📊 Running ETL pipeline (incremental)..."
	uv run python -c "from whoopdata.etl import run_complete_etl; from whoopdata.database.database import engine; from whoopdata.models.models import Base; Base.metadata.create_all(bind=engine); run_complete_etl(incremental=True)"

etl-full:
	@echo "📊 Running ETL pipeline (full load)..."
	uv run python -c "from whoopdata.etl import run_complete_etl; from whoopdata.database.database import engine; from whoopdata.models.models import Base; Base.metadata.create_all(bind=engine); run_complete_etl(incremental=False)"

chat:
	@echo "💬 Starting chat interface..."
	uv run python chat_app.py

analytics:
	@echo "🤖 Running analytics pipeline..."
	uv run python -c "from whoopdata.pipelines.analytics_pipeline import run_analytics_pipeline; run_analytics_pipeline(days_back=365)"

langgraph-dev:
	@echo "🎨 Starting LangGraph dev server with LangSmith Studio..."
	@echo "📍 API: http://127.0.0.1:2024"
	@echo "🎨 Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
	uv run langgraph dev --allow-blocking

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
	uv run python verify_system.py

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
