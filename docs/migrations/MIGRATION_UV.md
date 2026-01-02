# UV Migration Guide

## Overview

The WHOOP Data Platform has migrated from traditional pip/venv to **UV**, a fast, modern Python package manager. This guide helps you migrate your existing installation.

## What Changed

### Package Management
- ✅ **Before**: `pip` + `requirements.txt` + `venv/`
- ✅ **After**: `uv` + `pyproject.toml` + `.venv/`

### Key Benefits
- ⚡ **10-100x faster** dependency resolution and installation
- 🔒 **Reproducible builds** with `uv.lock`
- 📦 **Single source of truth** in `pyproject.toml`
- 🎯 **Modern Python standards** (PEP 621)
- 🛠️ **Better developer experience** with Makefile

### Python Version Update
- ⚠️ **Breaking Change**: Python >=3.10 required (was >=3.8)
- Reason: Gradio 5.9.1 requires Python 3.10+

## Migration Steps

### 1. Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Or with pip
pip install uv

# Verify installation
uv --version
```

### 2. Remove Old Virtual Environment (Optional)

```bash
# Deactivate if active
deactivate

# Remove old venv
rm -rf venv/

# Or use make
make clean-all
```

### 3. Install Dependencies with UV

```bash
# Install all dependencies (creates .venv automatically)
uv sync

# Or install with dev dependencies
make dev

# Or production only
make install
```

### 4. Verify Installation

```bash
# Run system verification
make verify

# Or directly
uv run python verify_system.py
```

### 5. Update Your Workflow

**Old Commands:**
```bash
source venv/bin/activate
python run_app.py
pip install <package>
```

**New Commands:**
```bash
# No activation needed!
make run
uv run whoop-start
uv add <package>
```

## Command Reference

### Common Tasks

| Task | Old Command | New Command |
|------|------------|-------------|
| Activate env | `source venv/bin/activate` | Not needed! UV manages it |
| Install deps | `pip install -r requirements.txt` | `uv sync` or `make dev` |
| Run CLI | `python run_app.py` | `make run` or `uv run whoop-start` |
| Start server | `python -m uvicorn main:app` | `make server` |
| Run ETL | `python -m whoopdata.etl` | `make etl` |
| Run tests | `pytest` | `make test` |
| Format code | `black .` | `make format` |
| Add package | `pip install <pkg>` | `uv add <pkg>` |

### New Make Commands

```bash
# See all available commands
make help

# Setup
make install     # Production dependencies
make dev         # Dev dependencies
make sync        # Update dependencies

# Run
make run         # CLI launcher
make server      # FastAPI server
make etl         # ETL pipeline
make chat        # Chat interface

# Development
make test        # Run tests
make format      # Format code
make lint        # Lint code
make verify      # System check

# Maintenance
make clean       # Clean cache
make clean-all   # Full cleanup
```

## How UV Works

### Virtual Environment Management

UV automatically creates and manages `.venv/` for you:

```bash
# UV creates .venv on first sync
uv sync

# Run commands - UV uses .venv automatically
uv run python script.py
uv run whoop-start

# No activation needed!
```

### Dependency Management

```bash
# Add a package
uv add requests

# Add dev dependency
uv add --dev pytest

# Remove a package
uv remove requests

# Update all dependencies
uv sync --upgrade

# Lock dependencies (creates/updates uv.lock)
uv lock
```

### Project Commands

```bash
# Run Python script
uv run python script.py

# Run console script (from pyproject.toml [project.scripts])
uv run whoop-start
uv run whoop-etl

# Run module
uv run -m whoopdata.cli

# Run with specific Python
uv run --python 3.11 python script.py
```

## Troubleshooting

### "uv: command not found"

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (restart shell after)
export PATH="$HOME/.local/bin:$PATH"
```

### "Python version mismatch"

```bash
# Check Python version
python3 --version

# Should be 3.10 or higher
# Update if needed (macOS with Homebrew):
brew install python@3.11
```

### "Module not found" errors

```bash
# Resync dependencies
uv sync

# Or clean and reinstall
rm -rf .venv
uv sync
```

### "Old venv still active"

```bash
# Deactivate old venv
deactivate

# UV doesn't need activation!
uv run whoop-start
```

## Backward Compatibility

### Still Using pip?

The project still supports traditional pip installation:

```bash
# Still works
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_app.py
```

However, we **strongly recommend** migrating to UV for better performance and developer experience.

### Console Scripts

Entry points work the same way:

```bash
# After uv sync, these are available:
whoop-start      # CLI launcher
whoop-etl        # ETL runner

# Can also use:
uv run whoop-start
uv run whoop-etl
```

## FAQ

### Do I need to activate the virtual environment?

No! UV automatically uses `.venv/` when you run commands with `uv run`.

### What happened to requirements.txt?

It's kept for reference and pip compatibility, but `pyproject.toml` is now the source of truth.

### Can I still use pip?

Yes, but we recommend UV. If you need to use pip:
```bash
source .venv/bin/activate
pip install <package>
```

### Where are dependencies locked?

In `uv.lock` (similar to `package-lock.json` for npm).

### Should I commit uv.lock?

We've added it to `.gitignore` for now. For production deployments, you might want to commit it for reproducible builds.

### How do I update dependencies?

```bash
# Update all
uv sync --upgrade

# Update specific package
uv add <package>@latest

# Or edit pyproject.toml and sync
uv sync
```

## Resources

- **UV Documentation**: https://docs.astral.sh/uv/
- **UV GitHub**: https://github.com/astral-sh/uv
- **PEP 621**: https://peps.python.org/pep-0621/
- **Project README**: See main README.md for usage examples

## Need Help?

If you encounter issues during migration:

1. Check this guide's Troubleshooting section
2. Run `make verify` to check system status
3. Check UV docs: https://docs.astral.sh/uv/
4. Open an issue on GitHub

---

**Migration Date**: December 29, 2025  
**Version**: 1.4.0  
**Python Requirement**: >=3.10
