# Changelog

All notable changes to the WHOOP Data Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-12-29

### ✨ Added - Advanced Analytics Engine (PR #13)

#### Core Analytics Features
- **Recovery Factor Analysis** - ML-based feature importance analysis identifies which factors (HRV, sleep, strain) most impact your recovery
- **Sleep Quality Impact** - Analyzes how sleep factors affect next-day recovery scores
- **Correlation Analysis** - Discovers statistically significant relationships between health metrics
- **Time Series Analysis** - 30-day trend detection with anomaly identification for recovery, HRV, RHR, and sleep
- **Weekly Insights Generator** - Automatically generates personalized, actionable health insights
- **Interactive Analytics Dashboard** - Beautiful Chart.js visualizations at `/analytics`

#### Technical Implementation
- Random Forest models for recovery and sleep prediction with cross-validation
- Pre-computed analytics stored in database for fast API responses
- Analytics pipeline (`whoopdata/pipelines/analytics_pipeline.py`) for batch processing
- Model persistence and management system
- Comprehensive analytics API endpoints (`/analytics/*`)

#### New API Endpoints
- `GET /analytics/summary` - Aggregated analytics overview
- `GET /analytics/recovery/factors` - Recovery factor importance rankings
- `GET /analytics/sleep/factors` - Sleep quality factor analysis
- `GET /analytics/correlations` - Health metric correlation matrix
- `GET /analytics/insights/weekly` - Personalized weekly insights
- `GET /analytics/patterns/{metric}` - Trend analysis for specific metrics
- `GET /analytics/recovery/deep-dive` - Comprehensive recovery analysis
- `POST /analytics/predict/recovery` - Predict recovery from input metrics
- `POST /analytics/predict/sleep` - Predict sleep quality

#### Agent Tools
- Conversational analytics through agent interface
- Natural language queries for health insights
- Integration with existing chat system

### 🐛 Fixed
- Sleep quality analyzer now correctly predicts recovery from sleep factors (not circular logic)
- Analytics dashboard UI now matches API response structure
- Added proper error messages when insufficient data for workout-based analytics
- Fixed missing `bedtime_consistency_score` feature in recovery dataset

### 📚 Documentation
- Comprehensive analytics documentation (`docs/features/ANALYTICS.md`)
- Implementation summary (`ANALYTICS_SUMMARY.md`)
- Experimental features guide (`docs/EXPERIMENTAL_FEATURES.md`)
- Result interpretation guidelines
- Privacy and data handling documentation

### ⚠️ Known Limitations (Experimental Features)
- **Workout-based analytics** require cycle data from WHOOP API
  - Recovery by sport/activity
  - Recovery by workout timing
  - Recovery by intensity
- **Reason**: Database has 2,126 workouts but 0 cycles (workouts linked via cycles)
- **Fix**: Sync cycle data through ETL process

### 🔒 Privacy
- All analytics computed locally on your machine
- No data sent to external servers
- Models trained on your data only
- No telemetry or tracking

### 📦 Dependencies
- scikit-learn for ML models
- Chart.js for visualizations
- Rich for CLI progress reporting

### 🚀 Performance
- Analytics pre-computation reduces dashboard load time
- Model caching for repeated predictions
- Efficient rolling feature calculations

### 🎯 Model Accuracy
- Recovery predictor: R² = 0.88
- Sleep efficiency predictor: R² = 0.96
- Factor analyzer: R² = 0.88

### 💡 Usage
Run analytics pipeline from CLI:
```bash
python -m whoopdata.cli
# Select option 6: Run analytics pipeline
```

View analytics dashboard:
```
http://localhost:8000/analytics
```

## [1.2.1] - 2025-12-XX

### 🐛 Fixed
- ETL datatype mismatch errors (#12)

## [1.2.0] - 2025-12-XX

### ✨ Added
- Incremental ETL loading for faster data updates (#11)

## [1.1.1] - 2025-12-XX

### 🐛 Fixed
- Upsert logic for WHOOP data to prevent duplicates (#10)

## [1.1.0] - 2025-12-XX

### ✨ Added
- Interactive health dashboard with real-time metrics visualization (#9)

## [1.0.0] - 2025-11-XX

### 🎉 Initial Release
- WHOOP data extraction and loading
- PostgreSQL database with SQLAlchemy models
- FastAPI REST API
- Basic health metrics visualization

---

[1.3.0]: https://github.com/ald0405/whoop-data/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/ald0405/whoop-data/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/ald0405/whoop-data/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/ald0405/whoop-data/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ald0405/whoop-data/compare/v1.0.0...v1.1.0
