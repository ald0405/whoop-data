# Release Notes - v1.7.1

**Release Date:** January 7, 2026  
**Release Type:** Feature Release - Interactive UI Enhancements

## 🎉 Overview

This release transforms the homepage and dashboard into interactive, actionable interfaces with tooltips, expandable sections, and smart recommendations. The focus is on helping you understand your health data and take action to improve.

---

## ✨ New Features

### Homepage Transformation (`/`)
- **Auto-loading Metrics**: Recovery, HRV, and Sleep metrics load automatically on page load
- **Trend Indicators**: Visual arrows (↑↓→) show if metrics are improving, declining, or stable (comparing 7-day vs 28-day averages)
- **Status Badges**: Color-coded badges (Green/Yellow/Red) indicate recovery zones
- **Mini Sparkline Charts**: 7-day trend visualizations for each key metric
- **Interactive Tooltips**: Info icons (ℹ️) with Bootstrap popovers explain what each metric means
- **Expandable "How to Improve" Sections**: Actionable tips for improving Recovery, HRV, and Sleep
- **Analytics Integration**: 
  - Weekly insights with priority indicators
  - Factor importance analysis (top 5 factors affecting recovery)
  - Correlation analysis showing relationships in your data
  - Smart error handling when analytics haven't been computed
- **Context Cards**: Weather, transport, tide, and walk recommendations in compact format
- **Progressive Disclosure**: Essential info visible, detailed data behind collapsible sections

### Dashboard Enhancements (`/dashboard`)
- **Quick Status Section**: At-a-glance view of Recovery, HRV, Sleep, and Strain with:
  - Color-coded borders (green/yellow/red)
  - Trend indicators vs 7-day average
  - Status badges
- **Smart Recommendations**: Personalized advice based on current metrics:
  - "Great status! Perfect day for challenging workout"
  - "Recovery needs attention. Prioritize sleep and light activity"
  - And 4 more context-aware recommendations
- **Section Headers**: Clear visual organization:
  - "Context & Environment" for weather, transport, tide, walk times
  - "Your Health Metrics (Last 7 Days)" for charts
- **Info Icons**: Hover tooltips on all cards explaining what each section provides
- **Better Visual Hierarchy**: Most actionable info at top, detailed metrics below

### Walk Hotspot Algorithm Improvements
- **Practical Time Constraints**: Only shows times between 7am-9pm (no more 4:45am suggestions!)
- **Daylight Requirement**: Must be during daylight hours to score points
- **Better Scoring System**:
  - 2 points: During daylight hours
  - 2 points: Near sunset/sunrise (within 1 hour)
  - 2 points: Clear skies (<30% clouds)
  - 1 point: Low wind (<10 mph)
  - 1 point: Comfortable temp (10-20°C)
  - Max score: 8 points
- **Sorted by Quality**: Best times first, then chronological
- **Configurable Parameters**: Min/max hours can be adjusted

---

## 🐛 Bug Fixes

### Data Formatting
- **Chart Heights**: Fixed mini charts expanding to multiple pages
- **Table Formatting**: 
  - Cleaned up sleep data table with better column headers
  - Milliseconds now display as hours (e.g., `7.6h` instead of `27236569.00`)
  - Removed unnecessary decimals from whole numbers
  - Cleaner date formatting (`Jan 7, 11:50 PM` instead of full ISO timestamp)
  - Better percentage formatting (no decimals for whole numbers)
- **Analytics API Integration**: Fixed field name mismatches between frontend and backend schemas:
  - `insight.insight_text` (not `message`)
  - `factor.factor_name` and `factor.importance_percentage` (not `factor` and `importance`)
  - `corr.correlation` (not `coefficient`)

### Error Handling
- **Analytics Not Computed**: Helpful blue info boxes with instructions instead of confusing error messages
- **404 Detection**: Properly detects when analytics endpoints return 404 and shows appropriate guidance
- **User-Friendly Messages**: Clear instructions on how to run analytics pipeline

---

## 🎨 UI/UX Improvements

### Visual Design
- **Consistent Color Scheme**: 
  - Green: Good/Ready status
  - Yellow: Moderate/Fair status
  - Red: Rest needed/Poor status
- **Hover Effects**: Cards lift slightly on hover for better interactivity
- **Gradient Backgrounds**: Status section has attractive gradient
- **Better Spacing**: Improved padding and margins throughout

### Interactive Elements
- **Bootstrap Popovers**: Rich tooltips with metric explanations
- **Collapsible Sections**: Hide/show detailed data on demand
- **Expandable Tips**: "How to improve" guidance under each metric
- **Smooth Animations**: Fade-ins and hover transitions

### Information Architecture
- **Progressive Disclosure**: Show essential first, details on demand
- **Visual Hierarchy**: Most important/actionable info at top
- **Section Organization**: Clear headers and logical grouping
- **Action-Oriented**: Focus on "what should I do" not just "what is"

---

## 📊 Data Display Improvements

### Homepage
- Removed button-heavy interface
- Auto-loads key metrics on page load
- Shows 7-day and 28-day averages for context
- Displays latest values with trend indicators
- Preserves deep dive section for raw data access

### Dashboard
- Quick status cards at top
- Context cards reorganized under clear header
- Charts grouped with descriptive header
- Added "Hover over charts for details" hint

### Tables
- Better header names (e.g., "Baseline Need" instead of "baseline_sleep_needed_milli")
- Proper unit conversions (milliseconds → hours)
- Cleaner number formatting
- Improved date display
- Responsive column widths

---

## 🔧 Technical Changes

### Frontend
- Added Chart.js integration for mini sparkline charts
- Implemented Bootstrap 5 popovers and collapse components
- Enhanced JavaScript with async/await for data loading
- Better error handling with try/catch blocks
- Modular functions for reusability

### Backend
- Walk hotspot algorithm updated with configurable constraints
- Better parameter handling in tide service
- Improved scoring system for recommendations

### File Changes
- `templates/index.html`: Complete restructure (1000+ lines)
- `templates/dashboard.html`: Added 200+ lines of enhancements
- `whoopdata/services/tide_service.py`: Algorithm improvements

---

## 📚 Documentation

### User-Facing
- Info icons with tooltips throughout UI
- "How to improve" sections for each metric
- Clear instructions when analytics aren't available
- Inline help text

### Code
- Better function documentation in tide service
- Clear parameter descriptions
- Updated version to 1.7.0

---

## 🚀 Migration Guide

### For Users
1. **No breaking changes** - everything works as before
2. **New homepage** loads automatically with metrics
3. **Analytics features** require running the analytics pipeline:
   ```bash
   make run  # Select option 6: Run analytics pipeline
   ```
4. **Old button grid** still available in "Deep Dive" section

### For Developers
- New interactive patterns in `templates/index.html` can be reused
- Walk hotspot algorithm has new optional parameters (`min_hour`, `max_hour`)
- Analytics error handling pattern can be applied to other features

---

## 🎯 What's Next (v1.8.0)

Potential features for next release:
- More interactive chart features (zoom, pan, export)
- Mobile-responsive improvements
- Additional analytics visualizations
- User preferences for time ranges and thresholds
- Export/share capabilities

---

## 🙏 Acknowledgments

This release focused on making health data more actionable and understandable, with inspiration from modern health tracking apps and user feedback about data overload.

---

## 📦 Installation

### New Installation
```bash
# Clone repository
git clone https://github.com/yourusername/whoop-data.git
cd whoop-data

# Install with UV
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run interactive CLI
make run
```

### Upgrading from v1.6.x
```bash
# Pull latest changes
git pull origin main

# Update dependencies
uv sync

# Restart server
make server
```

No database migrations required for this release.

---

## 📝 Full Changelog

### Features
- ✨ Transform homepage with auto-loading metrics and interactive elements
- ✨ Add quick status section to dashboard with smart recommendations
- ✨ Implement Bootstrap popovers for metric explanations
- ✨ Add expandable "How to improve" sections
- ✨ Integrate analytics insights, factors, and correlations
- ✨ Add mini sparkline charts for 7-day trends
- ✨ Improve walk hotspot algorithm with practical constraints

### Bug Fixes
- 🐛 Fix chart height issues causing excessive scrolling
- 🐛 Fix table formatting with proper units and cleaner dates
- 🐛 Fix analytics API field name mismatches
- 🐛 Improve error handling for missing analytics data

### UI/UX
- 💄 Add color-coded status badges and borders
- 💄 Implement hover effects and smooth animations
- 💄 Add section headers for better organization
- 💄 Improve visual hierarchy throughout

### Documentation
- 📚 Add inline help with info icons and tooltips
- 📚 Create comprehensive release notes

---

**Questions or Issues?** Please file an issue on GitHub or check the documentation.
