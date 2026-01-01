# Experimental Features

This document outlines experimental features in the WHOOP Data Platform that are still under development or have known limitations.

## Analytics Engine (⚠️ EXPERIMENTAL)

The advanced analytics engine provides ML-based insights and predictions, but some features are still experimental.

### What Works Well
✅ **Cycle Data Loading** - Physiological days (sleep-to-sleep) with daily strain and energy expenditure  
✅ **Sport Name Mapping** - Workouts now show "Tennis" instead of "sport_id: 34"  
✅ **Workout-Recovery Linking** - Workouts connected to next-day recovery via cycles  
✅ **Recovery Factor Analysis** - Identifies which factors (HRV, sleep duration, etc.) most impact your recovery  
✅ **Sleep Impact on Recovery** - Shows how sleep quality affects next-day recovery  
✅ **Correlation Analysis** - Finds relationships between health metrics  
✅ **Trend Detection** - Tracks 30-day trends in recovery, HRV, and other metrics  
✅ **Weekly Insights Generator** - Automatically generates personalized, actionable health insights

### Known Limitations

#### 1. Workout-Based Analytics Endpoints (Coming Soon)
The following API endpoints are planned but not yet implemented:
- `GET /analytics/recovery/by-sport` - Recovery analysis by sport type
- `GET /analytics/recovery/by-timing` - Recovery by workout time of day
- `GET /analytics/recovery/by-intensity` - Recovery by workout intensity

**Status**: ✅ Data infrastructure is complete (cycles are loading)
**Next**: API endpoints will be added in a future release
**Workaround**: Use the analytics data prep functions directly:
```python
from whoopdata.analytics.data_prep import get_workouts_with_recovery
from whoopdata.database.database import SessionLocal

db = SessionLocal()
df = get_workouts_with_recovery(db, days_back=365)

# Analyze recovery by sport
recovery_by_sport = df.groupby('sport_name')['recovery_score'].mean()
print(recovery_by_sport.sort_values(ascending=False))
```

#### 2. Sleep Quality Model Interpretation
The sleep quality analyzer predicts **recovery score** from sleep factors. Some metrics may show high importance percentages. This can occur when:
- Sleep metrics are highly correlated (e.g., sleep efficiency and time awake are mathematically related)
- The model is identifying the strongest predictor in your specific data
- There's limited variation in other sleep metrics

**Expected behavior**: The model should stabilize with more diverse data over time. Focus on the top 2-3 factors rather than exact percentages.

#### 3. Model Accuracy and Overfitting
With limited data (< 100 records), models may show very high R² scores (> 0.95) which could indicate overfitting. The analytics engine includes:
- Cross-validation to detect overfitting
- Warnings when data is insufficient
- Conservative feature selection

**Recommendation**: Re-run analytics (CLI option 6) after collecting more data to improve model reliability.

### Data Requirements

For best results, the analytics engine requires:
- ✅ Minimum 30 days of recovery data
- ✅ Minimum 50 recovery records for factor analysis
- ✅ Cycle data (automatically loaded via ETL pipeline)
- ✅ Consistent data collection (sleep, recovery, workouts, cycles)

### Future Improvements

Planned enhancements:
1. **Direct workout-to-recovery matching** - Bypass cycle dependency by matching on dates
2. **Sport name mapping** - Show sport names instead of sport_id numbers
3. **Better missing data handling** - Graceful degradation when data is sparse
4. **Confidence intervals** - Show prediction uncertainty
5. **Model versioning** - Track model performance over time
6. **Comparison with population data** - Benchmark against aggregate statistics

## How to Use Experimental Features Safely

1. **Treat insights as suggestions, not medical advice**
2. **Cross-reference with your own observations** - You know your body best
3. **Report unexpected results** - Help improve the analytics by reporting issues
4. **Re-run analytics after data updates** - Use CLI option 6 to recompute with new data
5. **Check the console/logs for warnings** - Browser console (F12) may show data quality warnings

## Interpreting Results

### Factor Importance Percentages
- **> 50%**: Dominant factor - this metric has the strongest relationship with recovery
- **20-50%**: Significant factor - meaningfully contributes to recovery prediction
- **10-20%**: Moderate factor - has some predictive value
- **< 10%**: Minor factor - weak relationship in your data

### Correlation Strength
- **> 0.7**: Strong correlation - metrics move together consistently
- **0.5-0.7**: Moderate correlation - noticeable relationship
- **0.3-0.5**: Weak correlation - slight tendency to move together
- **< 0.3**: No significant correlation

### Trend Directions
- **Up/Down > 5%**: Significant trend worth noting
- **2-5%**: Minor trend - may be noise
- **< 2%**: Stable - no meaningful trend

## Reporting Issues

If you encounter problems with experimental features:
1. Note which specific feature is affected
2. Check if you meet the minimum data requirements
3. Look for error messages in the browser console (F12)
4. Verify that analytics were computed (run CLI option 6)
5. Check when analytics were last computed (timestamp in API response)

## Version Information

- **Analytics Engine Version**: 1.2.1
- **Status**: Experimental (Active Development)
- **Last Updated**: 2025-12-29

## Privacy & Data

All analytics are computed locally on your machine:
- ✅ No data is sent to external servers
- ✅ Models are trained on your data only
- ✅ Results are stored in your local database
- ✅ No telemetry or tracking

Your health data never leaves your computer.
