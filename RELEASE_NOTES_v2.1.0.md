# Release Notes - v2.1.0

**Release Date:** March 1, 2026

## 🎯 Overview

Major agent architecture improvements with new nutrition capabilities, enhanced personality system, and improved multi-metric data handling.

## ✨ New Features

### Protein Recommendation Tool
- **Automatic protein target calculation** based on Withings weight data and activity level
- Evidence-based recommendations:
  - Normal activity: 1.2-1.4g per kg bodyweight
  - Endurance training: 1.2-1.4g per kg bodyweight
  - Resistance/strength training: 1.6-2.2g per kg bodyweight
- No manual weight input required - automatically fetches from Withings
- Direct supervisor access for quick queries
- Dedicated nutrition specialist agent for detailed guidance

### Enhanced Agent Personality System
- **Personality blend**: Hannah Fry (precision) + David Goggins (intensity) + Joe Rogan (curiosity) + Bob Mortimer (absurdity) + Andrew Huberman (protocols)
- Natural, conversational responses - no more rigid templates
- Context-aware date/time injection (knows "today", "this week", etc.)
- Sharp, entertaining communication style with actionable insights

### Agent Architecture Improvements
- **Specialist system** with dedicated routing for:
  - `health_data` - All WHOOP/Withings metric retrieval
  - `analytics` - ML predictions, correlations, factor analysis
  - `nutrition` - Protein recommendations and dietary guidance
  - `exercise` - Training plans and programming
  - `behaviour_change` - Habit formation and adherence coaching
- Clear routing distinction between "show me" vs "why/predict" queries
- Better multi-metric query handling with parallel tool calls
- Improved date range handling for comprehensive data pulls

## 🔧 Technical Improvements

### Tool System Enhancements
- Fixed tool invocation to use `.ainvoke()` for proper async handling
- Added dynamic date context injection to supervisor prompt
- Enhanced weight data parsing to handle multiple response formats
- Better error handling and user feedback

### Data Retrieval Optimization
- Health data specialist now intelligently calls multiple tools for comprehensive queries
- Appropriate limit defaults for different query types (latest, trends, historical)
- Support for `get_recovery_trends` and `get_weight_stats` for long-term analysis

## 📚 Documentation

- Complete integration guide: `docs/PROTEIN_RECOMMENDATION_INTEGRATION.md`
- Usage examples: `examples/protein_recommendation_example.py`
- Test suite: `test_protein_tool.py`

## 🔄 Breaking Changes

None - all changes are additive and backward compatible.

## 🐛 Bug Fixes

- Fixed tool-to-tool invocation (weight data tool called from protein tool)
- Corrected weight data response format handling
- Improved error messages for missing weight data

## 📝 Files Changed

- **Core agent files**: `graph.py`, `prompts.py`, `registry.py`, `specialists.py`
- **Tools**: Enhanced `tools.py` with protein recommendation
- **Configuration**: Updated `settings.py` for specialist configuration
- **Documentation**: New integration guide and examples
- **Tests**: Added comprehensive test coverage

## 🚀 Upgrade Instructions

1. Pull latest changes from `main`
2. Restart your agent server
3. Try the new protein recommendation: "What's my protein target for strength training?"

## 🙏 Contributors

- Co-Authored-By: Oz <oz-agent@warp.dev>

---

**Full Changelog**: v2.0.0...v2.1.0
