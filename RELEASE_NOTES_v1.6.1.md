# Release v1.6.1 - Dependency Guidance for Analytics

**Release Date**: January 6, 2026  
**Branch**: `work` → `main`  
**Commits**: 1

## 🎯 Overview

This patch release clarifies CLI dependency validation for both the core API stack and the analytics/ML pipeline. Users now get precise installation guidance for numpy, scikit-learn, xgboost, and the optional SHAP explainability dependency before running analytics.

## ✨ Highlights

- Separate dependency checks for core API vs analytics packages in `whoopdata/cli.py`.
- Explicit coverage for numpy, scikit-learn (`sklearn` import), xgboost, and optional SHAP with install hints.
- Clear remediation steps so analysts can install only what they need to unblock the pipeline.

## 🚀 How to Upgrade

```bash
# Pull latest changes
git pull origin main

# (Recommended) Use a clean virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies, including analytics stack
default="fastapi uvicorn sqlalchemy pandas requests rich numpy scikit-learn xgboost shap"
pip install $default
```

## 🧪 Testing

- Manual verification via `python whoopdata/cli.py` > option for dependency check.

## 📝 Release Checklist

- [x] Version bumped to v1.6.1
- [x] CHANGELOG updated
- [x] Release notes added
