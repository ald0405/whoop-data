# Advanced Analytics & Insights

ML-powered health analytics with explainability. Understand what drives your recovery, predict future performance, and get actionable insights.

## Quick Start

### 1. Start the API
```bash
python run_app.py
```

### 2. Access Analytics
- **API Docs**: http://localhost:8000/docs (scroll to "analytics" section)
- **Direct Endpoints**: http://localhost:8000/analytics/...

## Features

### 📊 Factor Importance Analysis
**What drives my recovery?**

```bash
curl http://localhost:8000/analytics/recovery/factors
```

**Returns:**
- Ranked factors (e.g., Sleep Duration: 32%, HRV: 24%, Sleep Efficiency: 18%)
- Plain English explanation for each factor
- Actionable thresholds (e.g., ">= 8.2 hours sleep")
- Model accuracy (R² score)

**Example Response:**
```json
{
  "factors": [
    {
      "factor_name": "Sleep Duration",
      "importance_percentage": 32.4,
      "explanation": "Sleep duration accounts for 32% of your recovery variation. Your best recoveries average 8.2 hours of sleep.",
      "direction": "positive",
      "actionable_threshold": ">= 8.2 hours"
    }
  ],
  "top_lever": "Sleep duration is your biggest lever (32% of recovery) - aim for 8.2+ hours",
  "model_accuracy": 0.78,
  "explanation": "This model explains 78% of your recovery variation with high accuracy - predictions are reliable"
}
```

### 🔗 Correlation Analysis
**How do metrics relate to each other?**

```bash
curl http://localhost:8000/analytics/correlations
```

**Returns:**
- Statistically significant correlations only (p < 0.05)
- Strength categorization (strong/moderate/weak)
- Real examples from your data
- Plain English explanations

**Example Response:**
```json
{
  "correlations": [
    {
      "metric_1": "Sleep Duration",
      "metric_2": "Recovery Score",
      "correlation": 0.72,
      "p_value": 0.001,
      "significance": "strong",
      "explanation": "Strong positive relationship (0.72) - when Sleep Duration increases, Recovery Score tends to increase significantly",
      "example": "Your highest Sleep Duration days show Recovery Score averaging 75.3 vs 58.1 on lowest Sleep Duration days"
    }
  ],
  "summary": "Strongest relationship: Sleep Duration and Recovery Score (0.72 correlation)"
}
```

### 🔮 Recovery Prediction
**What recovery can I expect tomorrow?**

```bash
curl -X POST http://localhost:8000/analytics/predict/recovery \
  -H "Content-Type: application/json" \
  -d '{
    "sleep_hours": 8.0,
    "sleep_efficiency": 85,
    "strain": 12.0,
    "hrv": 75,
    "rhr": 55
  }'
```

**Returns:**
- Predicted recovery score (0-100%)
- Confidence interval (±5%)
- Recovery category (Green/Yellow/Red)
- Explanation of prediction
- Factor contributions

**Example Response:**
```json
{
  "predicted_recovery": 68.5,
  "confidence_interval": [63.2, 73.8],
  "recovery_category": "Green",
  "explanation": "Sleep duration +25%, Sleep efficiency +20%, HRV +18%",
  "contributing_factors": {
    "sleep_hours": 25.3,
    "sleep_efficiency_percentage": 19.8,
    "hrv_rmssd_milli": 17.6
  },
  "model_accuracy": "This model is correct within 8% on 78% of predictions"
}
```

### 💤 Sleep Performance Prediction

```bash
curl -X POST http://localhost:8000/analytics/predict/sleep \
  -H "Content-Type: application/json" \
  -d '{
    "total_sleep_hours": 8.0,
    "rem_sleep_hours": 1.8,
    "awake_time_hours": 0.5
  }'
```

### 💡 Weekly Insights
**What should I focus on this week?**

```bash
curl http://localhost:8000/analytics/insights/weekly
```

**Returns:**
- 3-5 priority-ranked insights
- Categories: success (📈), alert (⚠️), opportunity (💡)
- Actionable recommendations
- Weekly summary

**Example Response:**
```json
{
  "insights": [
    {
      "insight_text": "📈 Recovery up 12% - 72% avg this period vs 64% before. Keep it up!",
      "category": "success",
      "priority": 1,
      "emoji": "📈"
    },
    {
      "insight_text": "💤 Your best recoveries: 8.2+ hours sleep with 87%+ efficiency",
      "category": "success",
      "priority": 2,
      "emoji": "💤"
    },
    {
      "insight_text": "⚠️ High strain week (avg 16.2) - schedule recovery days to optimize performance",
      "category": "alert",
      "priority": 2,
      "emoji": "⚠️"
    }
  ],
  "summary": "Past 1 week(s): Strong performance - 2 positive trend(s) detected"
}
```

### 📈 Trend Analysis
**How is my HRV/recovery trending?**

```bash
# Analyze any metric: recovery, hrv, rhr, sleep
curl http://localhost:8000/analytics/patterns/hrv?days=30
```

**Returns:**
- Trend direction (up/down/stable)
- Trend percentage
- Data points with values
- Detected anomalies
- Plain English description

**Example Response:**
```json
{
  "metric_name": "HRV",
  "trend_direction": "up",
  "trend_percentage": 8.3,
  "trend_description": "HRV trending up 8% over the past 30 days",
  "data_points": [
    {"date": "2025-01-01", "value": 72.5, "annotation": null},
    {"date": "2025-01-02", "value": 75.1, "annotation": null}
  ],
  "anomalies": [
    "2025-01-15: Unusual hrv value (52.3)"
  ]
}
```

### 🎯 Dashboard Summary
**Get everything in one call**

```bash
curl http://localhost:8000/analytics/summary
```

Returns:
- Factor importance
- Top 7 correlations
- Weekly insights
- Recovery trend (30 days)
- HRV trend (30 days)

Perfect for dashboard/UI that needs all analytics data.

## API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/analytics/recovery/factors` | GET | Factor importance analysis |
| `/analytics/correlations` | GET | Correlation matrix |
| `/analytics/predict/recovery` | POST | Predict recovery score |
| `/analytics/predict/sleep` | POST | Predict sleep performance |
| `/analytics/insights/weekly` | GET | Weekly insights |
| `/analytics/patterns/{metric}` | GET | Trend analysis |
| `/analytics/summary` | GET | Dashboard summary |

## Query Parameters

### `/analytics/recovery/factors`
- `days_back` (int, default: 365): Days of historical data to analyze

### `/analytics/correlations`
- `days_back` (int, default: 365): Days of historical data
- `significance_threshold` (float, default: 0.05): P-value threshold

### `/analytics/insights/weekly`
- `weeks` (int, default: 1, range: 1-12): Number of weeks to analyze

### `/analytics/patterns/{metric}`
- `days` (int, default: 30, range: 7-365): Days to analyze
- `metric`: One of `recovery`, `hrv`, `rhr`, `sleep`

### `/analytics/summary`
- `days_back` (int, default: 365): Days of historical data

## Data Requirements

- **Factor Analysis**: Minimum 50 recovery records
- **Correlation Analysis**: Minimum 30 records
- **Predictions**: Minimum 50 recovery records (recovery), 30 sleep records (sleep)
- **Insights**: Minimum 7 days of data
- **Trends**: Minimum 7 days of data

## Interpreting Results

### Factor Importance %
- **30%+**: Major driver - focus here for biggest impact
- **15-30%**: Significant factor - worth optimizing
- **<15%**: Minor factor - less critical

### Correlation Strength
- **0.7+**: Strong relationship - highly predictive
- **0.5-0.7**: Moderate relationship - meaningful connection
- **0.3-0.5**: Weak relationship - some connection
- **<0.3**: Very weak - may be noise

### R² Score (Model Accuracy)
- **0.7+**: High accuracy - predictions reliable
- **0.5-0.7**: Moderate accuracy - predictions useful but not perfect
- **<0.5**: Low accuracy - other unmeasured factors important

### Recovery Categories
- **Green (67-100%)**: Well recovered, ready for high strain
- **Yellow (34-66%)**: Moderate recovery, medium strain appropriate
- **Red (0-33%)**: Low recovery, prioritize rest

## Tips for Best Results

1. **More data = better insights**: 365+ days recommended
2. **Clean data matters**: Ensure WHOOP is worn consistently
3. **Context is key**: Insights are personalized to YOUR data patterns
4. **Act on insights**: Use top 2-3 insights, don't try to optimize everything at once
5. **Track changes**: Re-run analysis monthly to see if patterns shift

## Troubleshooting

### "Insufficient data for analysis"
- Need 50+ recovery records for factor analysis
- Ensure WHOOP data is being synced properly
- Check database: `sqlite3 whoopdata/database/whoop.db "SELECT COUNT(*) FROM recovery;"`

### Models seem inaccurate
- Check R² score in response - below 0.5 means other factors matter
- Try increasing `days_back` parameter for more training data
- Some recovery variation is inherently random/unmeasured

### Slow response times
- Factor analysis trains model on-demand (can take 10-30 seconds first call)
- Consider caching results for dashboard use
- Use `/analytics/summary` instead of multiple individual calls

## Next Steps

- Review factor importance to identify your #1 lever
- Check weekly insights for immediate action items
- Use recovery predictor to plan training schedule
- Monitor trends to catch early warning signs
