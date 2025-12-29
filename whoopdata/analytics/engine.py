"""Analytics engine with explainability focus.

All analyzers return plain English explanations alongside statistical results.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.stats import pearsonr
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import RecoveryPredictor, SleepPredictor
from .data_prep import (
    get_recovery_with_features,
    get_sleep_quality_features,
    calculate_rolling_features,
)


class RecoveryFactorAnalyzer:
    """Analyze what factors influence recovery with explainability."""

    def __init__(self, db: Session):
        """Initialize analyzer with database session."""
        self.db = db
        self.predictor = None
        self.feature_importance = None

    def analyze(self, days_back: int = 365) -> Dict:
        """Analyze recovery factors with plain language explanations.

        Args:
            days_back: Days of historical data to analyze

        Returns:
            Dictionary with factors, explanations, and actionable insights
        """
        # Get data
        df = get_recovery_with_features(self.db, days_back=days_back)

        if len(df) < 50:
            return {"error": "Insufficient data for analysis (need at least 50 recovery records)"}

        # Train model to get feature importance
        from .data_prep import get_training_data

        feature_cols = [
            "hrv_rmssd_milli",
            "resting_heart_rate",
            "sleep_hours",
            "sleep_efficiency_percentage",
            "rem_sleep_hours",
            "slow_wave_sleep_hours",
            "strain",
            "sleep_quality_score",
        ]

        # Remove rows with missing features
        df_clean = df[feature_cols + ["recovery_score"]].dropna()

        X_train, X_test, y_train, y_test, scaler, imputer = get_training_data(
            df_clean,
            target_col="recovery_score",
            feature_cols=feature_cols,
            scale_features=False,  # RandomForest doesn't need scaling
        )

        # Train predictor
        self.predictor = RecoveryPredictor()
        self.predictor.train(X_train, y_train, X_test, y_test)

        # Get feature importance
        self.feature_importance = self.predictor.get_feature_importance()

        # Sort by importance
        sorted_factors = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)

        # Generate explanations
        factors = []
        for feat, importance in sorted_factors:
            factor_data = self._explain_factor(feat, importance, df_clean)
            factors.append(factor_data)

        # Top lever explanation
        top_factor = sorted_factors[0]
        top_lever = self._generate_top_lever_explanation(top_factor[0], top_factor[1], df_clean)

        return {
            "factors": factors,
            "top_lever": top_lever,
            "model_accuracy": float(self.predictor.model_accuracy),
            "model_r2": float(self.predictor.model_accuracy),
            "explanation": self._generate_overall_explanation(self.predictor.model_accuracy),
        }

    def _explain_factor(self, factor_name: str, importance: float, df: pd.DataFrame) -> Dict:
        """Generate plain English explanation for a factor."""
        friendly_names = {
            "sleep_hours": "Sleep Duration",
            "sleep_efficiency_percentage": "Sleep Efficiency",
            "hrv_rmssd_milli": "Heart Rate Variability (HRV)",
            "resting_heart_rate": "Resting Heart Rate",
            "rem_sleep_hours": "REM Sleep",
            "slow_wave_sleep_hours": "Deep Sleep",
            "strain": "Strain Level",
            "sleep_quality_score": "Overall Sleep Quality",
        }

        friendly = friendly_names.get(factor_name, factor_name)

        # Calculate correlation direction
        corr, _ = pearsonr(df[factor_name], df["recovery_score"])
        direction = "positive" if corr > 0 else "negative"

        # Find actionable threshold (compare top 25% vs bottom 25% recoveries)
        top_recoveries = df.nlargest(int(len(df) * 0.25), "recovery_score")
        bottom_recoveries = df.nsmallest(int(len(df) * 0.25), "recovery_score")

        top_avg = top_recoveries[factor_name].mean()
        bottom_avg = bottom_recoveries[factor_name].mean()
        diff_pct = ((top_avg - bottom_avg) / bottom_avg) * 100 if bottom_avg != 0 else 0

        # Generate explanation
        if factor_name == "sleep_hours":
            explanation = f"Sleep duration accounts for {importance:.1f}% of your recovery variation. Your best recoveries average {top_avg:.1f} hours of sleep."
            threshold = f">= {top_avg:.1f} hours"
        elif factor_name == "sleep_efficiency_percentage":
            explanation = f"Sleep efficiency accounts for {importance:.1f}% of your recovery. Your top recoveries have {top_avg:.0f}% efficiency."
            threshold = f">= {top_avg:.0f}%"
        elif factor_name == "hrv_rmssd_milli":
            explanation = f"HRV accounts for {importance:.1f}% of recovery variation. Higher HRV ({top_avg:.0f}ms) correlates with better recovery."
            threshold = f">= {top_avg:.0f}ms"
        elif factor_name == "resting_heart_rate":
            explanation = f"Resting heart rate accounts for {importance:.1f}% of recovery. Lower RHR ({top_avg:.0f}bpm) indicates better recovery."
            threshold = f"<= {top_avg:.0f}bpm"
        elif factor_name == "strain":
            explanation = f"Strain accounts for {importance:.1f}% of recovery. Lower strain days ({bottom_avg:.1f}) lead to better recovery."
            threshold = f"< {(top_avg + bottom_avg)/2:.1f}"
        else:
            explanation = f"{friendly} accounts for {importance:.1f}% of your recovery variation."
            threshold = None

        return {
            "factor_name": friendly,
            "importance_percentage": float(importance),
            "explanation": explanation,
            "direction": direction,
            "actionable_threshold": threshold,
            "top_quartile_avg": float(top_avg),
            "bottom_quartile_avg": float(bottom_avg),
        }

    def _generate_top_lever_explanation(
        self, factor_name: str, importance: float, df: pd.DataFrame
    ) -> str:
        """Generate explanation for the #1 factor."""
        friendly_names = {
            "sleep_hours": "sleep duration",
            "sleep_efficiency_percentage": "sleep efficiency",
            "hrv_rmssd_milli": "HRV",
        }
        friendly = friendly_names.get(factor_name, factor_name)

        if factor_name == "sleep_hours":
            top_avg = df.nlargest(int(len(df) * 0.25), "recovery_score")[factor_name].mean()
            return f"Sleep duration is your biggest lever ({importance:.0f}% of recovery) - aim for {top_avg:.1f}+ hours"
        elif factor_name == "sleep_efficiency_percentage":
            top_avg = df.nlargest(int(len(df) * 0.25), "recovery_score")[factor_name].mean()
            return f"Sleep efficiency is your biggest lever ({importance:.0f}% of recovery) - target {top_avg:.0f}%+ efficiency"
        elif factor_name == "hrv_rmssd_milli":
            return f"HRV is your biggest recovery driver ({importance:.0f}%) - focus on stress management and recovery practices"
        else:
            return f"{friendly} is your biggest recovery driver at {importance:.0f}%"

    def _generate_overall_explanation(self, r2: float) -> str:
        """Generate overall model explanation."""
        pct = r2 * 100
        if r2 >= 0.7:
            return f"This model explains {pct:.0f}% of your recovery variation with high accuracy - predictions are reliable"
        elif r2 >= 0.5:
            return (
                f"This model explains {pct:.0f}% of your recovery variation with moderate accuracy"
            )
        else:
            return f"This model explains {pct:.0f}% of recovery variation - other unmeasured factors may be important"


class SleepQualityAnalyzer:
    """Analyze how sleep factors affect next-day recovery."""

    def __init__(self, db: Session):
        """Initialize analyzer with database session."""
        self.db = db
        self.predictor = None
        self.feature_importance = None

    def analyze(self, days_back: int = 365) -> Dict:
        """Analyze sleep quality factors with plain language explanations.

        Args:
            days_back: Days of historical data to analyze

        Returns:
            Dictionary with factors, explanations, and actionable insights
        """
        # Get recovery data which includes sleep features
        df = get_recovery_with_features(self.db, days_back=days_back)

        if len(df) < 30:
            return {
                "error": "Insufficient data for sleep analysis (need at least 30 sleep records)"
            }

        # Train model to get feature importance
        from .data_prep import get_training_data
        from sklearn.ensemble import RandomForestRegressor

        feature_cols = [
            "sleep_hours",
            "rem_sleep_hours",
            "slow_wave_sleep_hours",
            "sleep_efficiency_percentage",
            "bedtime_hour",
            "day_of_week",
            "respiratory_rate",
            "sleep_debt_hours",
            "sleep_deficit",
            "disturbance_count",
        ]

        # Filter to records with complete rolling features
        df_with_history = df[df["has_rolling_features"] == True].copy()

        if len(df_with_history) == 0:
            return {"error": "No records with sufficient history for sleep analysis"}

        # Remove rows with missing features - TARGET IS RECOVERY
        df_clean = df_with_history[feature_cols + ["recovery_score"]].dropna()

        if len(df_clean) < 30:
            return {
                "error": f"Insufficient clean data. Only {len(df_clean)} records after removing missing values."
            }

        X_train, X_test, y_train, y_test, _, _ = get_training_data(
            df_clean, target_col="recovery_score", feature_cols=feature_cols, scale_features=False
        )

        # Train RandomForest model
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        # Calculate R² score
        from sklearn.metrics import r2_score

        y_pred = model.predict(X_test)
        model_r2 = r2_score(y_test, y_pred)

        # Get feature importance
        feature_importance = dict(zip(feature_cols, model.feature_importances_ * 100))
        sorted_factors = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        # Generate explanations
        factors = []
        for feat, importance in sorted_factors:
            factor_data = self._explain_factor(feat, importance, df_clean)
            factors.append(factor_data)

        # Top lever explanation
        top_factor = sorted_factors[0]
        top_lever = self._generate_top_lever_explanation(top_factor[0], top_factor[1], df_clean)

        # Day of week insights
        dow_insights = self._analyze_day_of_week_patterns(df_clean)

        # Bedtime insights
        bedtime_insights = self._analyze_bedtime_patterns(df_clean)

        return {
            "factors": factors,
            "top_lever": top_lever,
            "model_accuracy": float(model_r2),
            "model_r2": float(model_r2),
            "explanation": self._generate_overall_explanation(model_r2),
            "day_of_week_insights": dow_insights,
            "bedtime_insights": bedtime_insights,
        }

    def _explain_factor(self, factor_name: str, importance: float, df: pd.DataFrame) -> Dict:
        """Generate plain English explanation for a sleep quality factor."""
        friendly_names = {
            "total_sleep_hours": "Sleep Duration",
            "rem_sleep_hours": "REM Sleep",
            "slow_wave_sleep_hours": "Deep Sleep",
            "awake_time_hours": "Time Awake",
            "bedtime_hour": "Bedtime",
            "day_of_week": "Day of Week",
            "respiratory_rate": "Respiratory Rate",
            "prev_strain": "Previous Day Strain",
            "prev_recovery_score": "Previous Day Recovery",
            "sleep_debt_hours": "Sleep Debt",
            "sleep_deficit": "Sleep Deficit",
            "disturbance_count": "Sleep Disturbances",
            "bedtime_consistency_score": "Bedtime Consistency",
        }

        friendly = friendly_names.get(factor_name, factor_name)

        # Calculate correlation with RECOVERY not sleep efficiency
        corr, _ = pearsonr(df[factor_name], df["recovery_score"])
        direction = "positive" if corr > 0 else "negative"

        # Find actionable threshold (top 25% vs bottom 25% RECOVERY)
        top_recovery = df.nlargest(int(len(df) * 0.25), "recovery_score")
        bottom_recovery = df.nsmallest(int(len(df) * 0.25), "recovery_score")

        top_avg = top_recovery[factor_name].mean()
        bottom_avg = bottom_recovery[factor_name].mean()

        # Generate explanation - explaining impact on RECOVERY
        if factor_name == "sleep_hours":
            explanation = f"Sleep duration accounts for {importance:.1f}% of recovery. Your best recoveries average {top_avg:.1f} hours."
            threshold = f">= {top_avg:.1f}h"
        elif factor_name == "sleep_efficiency_percentage":
            explanation = f"Sleep efficiency accounts for {importance:.1f}% of recovery. Your best recoveries have {top_avg:.0f}% efficiency."
            threshold = f">= {top_avg:.0f}%"
        elif factor_name == "bedtime_hour":
            explanation = f"Bedtime accounts for {importance:.1f}% of recovery. Your best recoveries occur after going to bed around {top_avg:.0f}:00."
            threshold = f"Around {int(top_avg):02d}:00"
        elif factor_name == "day_of_week":
            explanation = f"Day of week accounts for {importance:.1f}% of recovery variation."
            threshold = None
        elif factor_name == "sleep_debt_hours":
            explanation = f"Sleep debt accounts for {importance:.1f}% of recovery. Less debt ({top_avg:.1f}h) = better recovery."
            threshold = f"< {top_avg:.1f}h"
        elif factor_name == "disturbance_count":
            explanation = f"Disturbances account for {importance:.1f}% of recovery. Fewer disturbances ({int(top_avg)}) = better recovery."
            threshold = f"< {int(top_avg)}"
        elif factor_name == "bedtime_consistency_score":
            explanation = f"Bedtime consistency accounts for {importance:.1f}% of recovery. Higher consistency ({top_avg:.0f}) improves recovery."
            threshold = f"> {top_avg:.0f}"
        elif factor_name == "rem_sleep_hours" or factor_name == "slow_wave_sleep_hours":
            explanation = f"{friendly} accounts for {importance:.1f}% of recovery. Your best recoveries average {top_avg:.1f} hours."
            threshold = f">= {top_avg:.1f}h"
        else:
            explanation = f"{friendly} accounts for {importance:.1f}% of your recovery variation (from sleep factors)."
            threshold = None

        return {
            "factor_name": friendly,
            "importance_percentage": float(importance),
            "explanation": explanation,
            "direction": direction,
            "actionable_threshold": threshold,
            "top_quartile_avg": float(top_avg),
            "bottom_quartile_avg": float(bottom_avg),
        }

    def _generate_top_lever_explanation(
        self, factor_name: str, importance: float, df: pd.DataFrame
    ) -> str:
        """Generate explanation for the #1 sleep factor driving recovery."""
        if factor_name == "sleep_hours":
            top_recovery = df.nlargest(int(len(df) * 0.25), "recovery_score")
            avg_hours = top_recovery[factor_name].mean()
            return f"Sleep duration is your biggest recovery lever from sleep ({importance:.0f}%) - aim for {avg_hours:.1f}+ hours"
        elif factor_name == "sleep_efficiency_percentage":
            top_recovery = df.nlargest(int(len(df) * 0.25), "recovery_score")
            avg_eff = top_recovery[factor_name].mean()
            return f"Sleep efficiency is your biggest recovery lever from sleep ({importance:.0f}%) - target {avg_eff:.0f}%+"
        elif factor_name == "bedtime_hour":
            top_recovery = df.nlargest(int(len(df) * 0.25), "recovery_score")
            avg_bedtime = top_recovery[factor_name].mean()
            return f"Bedtime is your biggest recovery lever from sleep ({importance:.0f}%) - aim for {int(avg_bedtime):02d}:00"
        elif factor_name == "bedtime_consistency_score":
            return f"Bedtime consistency is your biggest recovery lever from sleep ({importance:.0f}%) - stick to a regular sleep schedule"
        else:
            return f"{factor_name.replace('_', ' ').title()} is your biggest recovery driver from sleep at {importance:.0f}%"

    def _generate_overall_explanation(self, r2: float) -> str:
        """Generate overall model explanation."""
        pct = r2 * 100
        if r2 >= 0.5:
            return f"Sleep factors explain {pct:.0f}% of your recovery variation with good accuracy"
        elif r2 >= 0.3:
            return f"Sleep factors explain {pct:.0f}% of your recovery variation with moderate accuracy"
        else:
            return f"Sleep factors explain {pct:.0f}% of recovery variation - other factors like strain may be more important"

    def _analyze_day_of_week_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze sleep quality by day of week."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        dow_data = []
        for dow in range(7):
            dow_records = df[df["day_of_week"] == dow]
            if len(dow_records) > 0:
                avg_efficiency = dow_records["sleep_efficiency_percentage"].mean()
                dow_data.append(
                    {
                        "day": day_names[dow],
                        "avg_efficiency": float(avg_efficiency),
                        "count": len(dow_records),
                    }
                )

        # Find best and worst days
        if dow_data:
            best_day = max(dow_data, key=lambda x: x["avg_efficiency"])
            worst_day = min(dow_data, key=lambda x: x["avg_efficiency"])

            return {
                "by_day": dow_data,
                "best_day": best_day["day"],
                "best_efficiency": best_day["avg_efficiency"],
                "worst_day": worst_day["day"],
                "worst_efficiency": worst_day["avg_efficiency"],
                "insight": f"Best sleep on {best_day['day']} ({best_day['avg_efficiency']:.1f}%), worst on {worst_day['day']} ({worst_day['avg_efficiency']:.1f}%)",
            }

        return {"by_day": [], "insight": "Insufficient data for day-of-week analysis"}

    def _analyze_bedtime_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze sleep quality by bedtime."""
        # Group by bedtime hour
        bedtime_data = []
        for hour in range(20, 28):  # 8pm to 4am (next day)
            display_hour = hour if hour < 24 else hour - 24
            hour_records = df[df["bedtime_hour"] == display_hour]
            if len(hour_records) >= 3:  # Need at least 3 samples
                avg_efficiency = hour_records["sleep_efficiency_percentage"].mean()
                bedtime_data.append(
                    {
                        "hour": display_hour,
                        "display_time": f"{display_hour:02d}:00",
                        "avg_efficiency": float(avg_efficiency),
                        "count": len(hour_records),
                    }
                )

        if bedtime_data:
            best_time = max(bedtime_data, key=lambda x: x["avg_efficiency"])
            return {
                "by_hour": bedtime_data,
                "optimal_bedtime": best_time["display_time"],
                "optimal_efficiency": best_time["avg_efficiency"],
                "insight": f"Optimal bedtime: {best_time['display_time']} ({best_time['avg_efficiency']:.1f}% efficiency)",
            }

        return {"by_hour": [], "insight": "Insufficient data for bedtime analysis"}


class RecoveryDeepDiveAnalyzer:
    """Deep dive analysis of recovery factors including workout types, timing, and HR zones."""

    def __init__(self, db: Session):
        """Initialize analyzer."""
        self.db = db

    def analyze(self, days_back: int = 365) -> Dict:
        """Perform comprehensive recovery analysis.

        Args:
            days_back: Days of historical data

        Returns:
            Dictionary with recovery insights by sport, time-of-day, HR zones, and strain patterns
        """
        df = get_recovery_with_features(self.db, days_back=days_back)

        if len(df) < 30:
            return {"error": "Insufficient data for recovery deep dive"}

        results = {
            "by_sport": self._analyze_by_sport(df),
            "by_time_of_day": self._analyze_by_time_of_day(df),
            "by_hr_zones": self._analyze_by_hr_zones(df),
            "strain_patterns": self._analyze_strain_patterns(df),
            "day_of_week_recovery": self._analyze_day_of_week_recovery(df),
            "timestamp": datetime.now(),
        }

        return results

    def _analyze_by_sport(self, df: pd.DataFrame) -> Dict:
        """Analyze recovery by workout sport type."""
        if "sport_id" not in df.columns:
            return {"error": "No workout data available"}

        # Filter to records with workouts
        workout_df = df[df["sport_id"] > 0].copy()

        if len(workout_df) < 10:
            return {"error": "Insufficient workout data"}

        # Analyze recovery by sport
        sport_stats = (
            workout_df.groupby("sport_id")
            .agg(
                {
                    "recovery_score": ["mean", "std", "count"],
                    "workout_strain": "mean",
                    "high_intensity_pct": "mean",
                }
            )
            .reset_index()
        )

        sport_stats.columns = [
            "sport_id",
            "avg_recovery",
            "recovery_std",
            "count",
            "avg_strain",
            "avg_high_intensity_pct",
        ]

        # Filter sports with at least 5 occurrences
        sport_stats = sport_stats[sport_stats["count"] >= 5]

        if len(sport_stats) == 0:
            return {"error": "Insufficient data per sport"}

        # Sort by average recovery
        sport_stats = sport_stats.sort_values("avg_recovery", ascending=False)

        sports_list = []
        for _, row in sport_stats.iterrows():
            sports_list.append(
                {
                    "sport_id": int(row["sport_id"]),
                    "avg_recovery": float(row["avg_recovery"]),
                    "recovery_std": float(row["recovery_std"]),
                    "count": int(row["count"]),
                    "avg_strain": float(row["avg_strain"]),
                    "avg_high_intensity_pct": float(row["avg_high_intensity_pct"]),
                }
            )

        # Generate insights
        best_sport = sports_list[0]
        worst_sport = sports_list[-1]

        insight = f"Sport {best_sport['sport_id']} yields best recovery ({best_sport['avg_recovery']:.0f}%), while sport {worst_sport['sport_id']} yields lowest ({worst_sport['avg_recovery']:.0f}%)"

        return {
            "sports": sports_list,
            "best_sport_id": best_sport["sport_id"],
            "worst_sport_id": worst_sport["sport_id"],
            "insight": insight,
        }

    def _analyze_by_time_of_day(self, df: pd.DataFrame) -> Dict:
        """Analyze recovery by workout time of day."""
        if "workout_start_hour" not in df.columns:
            return {"error": "No workout timing data available"}

        # Filter to records with workouts
        workout_df = df[df["sport_id"] > 0].copy()

        if len(workout_df) < 10:
            return {"error": "Insufficient workout data"}

        # Analyze by time period
        time_periods = [
            ("Morning", "workout_is_morning"),
            ("Afternoon", "workout_is_afternoon"),
            ("Evening", "workout_is_evening"),
        ]

        time_stats = []
        for period_name, period_col in time_periods:
            if period_col in workout_df.columns:
                period_data = workout_df[workout_df[period_col] == True]
                if len(period_data) >= 5:
                    avg_recovery = period_data["recovery_score"].mean()
                    count = len(period_data)
                    time_stats.append(
                        {
                            "period": period_name,
                            "avg_recovery": float(avg_recovery),
                            "count": int(count),
                        }
                    )

        if not time_stats:
            return {"error": "Insufficient data per time period"}

        # Sort by recovery
        time_stats.sort(key=lambda x: x["avg_recovery"], reverse=True)

        best_time = time_stats[0]
        worst_time = time_stats[-1]

        insight = f"{best_time['period']} workouts yield best recovery ({best_time['avg_recovery']:.0f}%), {worst_time['period']} workouts yield lowest ({worst_time['avg_recovery']:.0f}%)"

        return {
            "by_period": time_stats,
            "best_time": best_time["period"],
            "worst_time": worst_time["period"],
            "insight": insight,
        }

    def _analyze_by_hr_zones(self, df: pd.DataFrame) -> Dict:
        """Analyze recovery impact of HR zone distribution."""
        if "high_intensity_pct" not in df.columns:
            return {"error": "No HR zone data available"}

        # Filter to records with workouts
        workout_df = df[df["sport_id"] > 0].copy()

        if len(workout_df) < 10:
            return {"error": "Insufficient workout data"}

        # Categorize by high intensity percentage
        workout_df["intensity_category"] = pd.cut(
            workout_df["high_intensity_pct"],
            bins=[-1, 10, 30, 100],
            labels=["Low", "Moderate", "High"],
        )

        intensity_stats = (
            workout_df.groupby("intensity_category", observed=True)
            .agg({"recovery_score": ["mean", "count"], "high_intensity_pct": "mean"})
            .reset_index()
        )

        intensity_stats.columns = ["intensity", "avg_recovery", "count", "avg_high_intensity"]

        intensity_list = []
        for _, row in intensity_stats.iterrows():
            if row["count"] >= 3:
                intensity_list.append(
                    {
                        "intensity_level": str(row["intensity"]),
                        "avg_recovery": float(row["avg_recovery"]),
                        "count": int(row["count"]),
                        "avg_high_intensity_pct": float(row["avg_high_intensity"]),
                    }
                )

        if not intensity_list:
            return {"error": "Insufficient data per intensity level"}

        # Find optimal intensity
        best_intensity = max(intensity_list, key=lambda x: x["avg_recovery"])

        insight = f"{best_intensity['intensity_level']} intensity workouts yield best recovery ({best_intensity['avg_recovery']:.0f}%)"

        return {
            "by_intensity": intensity_list,
            "optimal_intensity": best_intensity["intensity_level"],
            "insight": insight,
        }

    def _analyze_strain_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze multi-day strain accumulation patterns."""
        if "strain_3d_sum" not in df.columns:
            return {"error": "No strain pattern data available"}

        # Categorize by 3-day cumulative strain
        df["strain_load"] = pd.cut(
            df["strain_3d_sum"], bins=[-1, 20, 35, 100], labels=["Light", "Moderate", "Heavy"]
        )

        strain_stats = (
            df.groupby("strain_load", observed=True)
            .agg({"recovery_score": ["mean", "count"], "strain_3d_sum": "mean"})
            .reset_index()
        )

        strain_stats.columns = ["load", "avg_recovery", "count", "avg_strain"]

        strain_list = []
        for _, row in strain_stats.iterrows():
            if row["count"] >= 5:
                strain_list.append(
                    {
                        "load_level": str(row["load"]),
                        "avg_recovery": float(row["avg_recovery"]),
                        "count": int(row["count"]),
                        "avg_3d_strain": float(row["avg_strain"]),
                    }
                )

        if not strain_list:
            return {"error": "Insufficient data per load level"}

        # Find optimal load
        best_load = max(strain_list, key=lambda x: x["avg_recovery"])

        insight = f"{best_load['load_level']} 3-day load yields best recovery ({best_load['avg_recovery']:.0f}%)"

        return {"by_load": strain_list, "optimal_load": best_load["load_level"], "insight": insight}

    def _analyze_day_of_week_recovery(self, df: pd.DataFrame) -> Dict:
        """Analyze recovery by day of week."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        dow_data = []
        for dow in range(7):
            dow_records = df[df["day_of_week"] == dow]
            if len(dow_records) > 0:
                avg_recovery = dow_records["recovery_score"].mean()
                avg_strain = dow_records["strain"].mean()
                dow_data.append(
                    {
                        "day": day_names[dow],
                        "avg_recovery": float(avg_recovery),
                        "avg_strain": float(avg_strain),
                        "count": len(dow_records),
                    }
                )

        # Find best and worst days
        if dow_data:
            best_day = max(dow_data, key=lambda x: x["avg_recovery"])
            worst_day = min(dow_data, key=lambda x: x["avg_recovery"])

            return {
                "by_day": dow_data,
                "best_day": best_day["day"],
                "best_recovery": best_day["avg_recovery"],
                "worst_day": worst_day["day"],
                "worst_recovery": worst_day["avg_recovery"],
                "insight": f"Best recovery on {best_day['day']} ({best_day['avg_recovery']:.0f}%), worst on {worst_day['day']} ({worst_day['avg_recovery']:.0f}%)",
            }

        return {"by_day": [], "insight": "Insufficient data for day-of-week analysis"}


class CorrelationAnalyzer:
    """Analyze correlations between health metrics with plain English explanations."""

    def __init__(self, db: Session):
        """Initialize analyzer."""
        self.db = db

    def analyze(self, days_back: int = 365, significance_threshold: float = 0.05) -> Dict:
        """Analyze correlations with statistical significance.

        Args:
            days_back: Days of historical data
            significance_threshold: P-value threshold (default 0.05)

        Returns:
            Dictionary with correlations and explanations
        """
        df = get_recovery_with_features(self.db, days_back=days_back)

        if len(df) < 30:
            return {"error": "Insufficient data for correlation analysis"}

        # Define metric pairs to analyze
        metric_pairs = [
            ("sleep_hours", "recovery_score", "Sleep Duration", "Recovery Score"),
            ("sleep_efficiency_percentage", "recovery_score", "Sleep Efficiency", "Recovery Score"),
            ("hrv_rmssd_milli", "recovery_score", "HRV", "Recovery Score"),
            ("resting_heart_rate", "recovery_score", "Resting Heart Rate", "Recovery Score"),
            ("strain", "recovery_score", "Strain", "Recovery Score"),
            ("rem_sleep_hours", "recovery_score", "REM Sleep", "Recovery Score"),
            ("sleep_hours", "hrv_rmssd_milli", "Sleep Duration", "HRV"),
            ("strain", "hrv_rmssd_milli", "Strain", "HRV"),
        ]

        correlations = []
        for col1, col2, name1, name2 in metric_pairs:
            if col1 in df.columns and col2 in df.columns:
                # Remove NaN values
                valid_data = df[[col1, col2]].dropna()
                if len(valid_data) < 30:
                    continue

                corr, p_value = pearsonr(valid_data[col1], valid_data[col2])

                # Only include significant correlations
                if p_value < significance_threshold:
                    corr_data = self._explain_correlation(
                        name1, name2, corr, p_value, valid_data, col1, col2
                    )
                    correlations.append(corr_data)

        # Sort by absolute correlation strength
        correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        summary = self._generate_summary(correlations)

        return {"correlations": correlations, "summary": summary, "timestamp": datetime.now()}

    def _explain_correlation(
        self,
        name1: str,
        name2: str,
        corr: float,
        p_value: float,
        data: pd.DataFrame,
        col1: str,
        col2: str,
    ) -> Dict:
        """Generate plain English explanation for correlation."""
        # Determine significance level
        abs_corr = abs(corr)
        if abs_corr >= 0.7:
            significance = "strong"
        elif abs_corr >= 0.5:
            significance = "moderate"
        elif abs_corr >= 0.3:
            significance = "weak"
        else:
            significance = "not_significant"

        # Generate explanation
        direction = "positive" if corr > 0 else "negative"

        if significance == "strong":
            if direction == "positive":
                explanation = f"Strong positive relationship ({corr:.2f}) - when {name1} increases, {name2} tends to increase significantly"
            else:
                explanation = f"Strong negative relationship ({corr:.2f}) - when {name1} increases, {name2} tends to decrease significantly"
        elif significance == "moderate":
            if direction == "positive":
                explanation = f"Moderate positive relationship ({corr:.2f}) - {name1} and {name2} tend to move together"
            else:
                explanation = f"Moderate negative relationship ({corr:.2f}) - {name1} and {name2} tend to move in opposite directions"
        else:
            if direction == "positive":
                explanation = f"Weak positive relationship ({corr:.2f}) - slight tendency for {name1} and {name2} to move together"
            else:
                explanation = f"Weak negative relationship ({corr:.2f}) - slight tendency for {name1} and {name2} to move oppositely"

        # Generate real example from data
        example = self._generate_example(data, col1, col2, name1, name2, direction)

        return {
            "metric_1": name1,
            "metric_2": name2,
            "correlation": float(corr),
            "p_value": float(p_value),
            "significance": significance,
            "explanation": explanation,
            "example": example,
        }

    def _generate_example(
        self, data: pd.DataFrame, col1: str, col2: str, name1: str, name2: str, direction: str
    ) -> str:
        """Generate a real example from user's data."""
        if direction == "positive":
            # Find high values of col1
            top_records = data.nlargest(int(len(data) * 0.25), col1)
            avg_col2_high = top_records[col2].mean()

            bottom_records = data.nsmallest(int(len(data) * 0.25), col1)
            avg_col2_low = bottom_records[col2].mean()

            return f"Your highest {name1} days show {name2} averaging {avg_col2_high:.1f} vs {avg_col2_low:.1f} on lowest {name1} days"
        else:
            # Negative correlation
            top_records = data.nlargest(int(len(data) * 0.25), col1)
            avg_col2_high = top_records[col2].mean()

            return (
                f"When {name1} is high, {name2} averages {avg_col2_high:.1f} (inverse relationship)"
            )

    def _generate_summary(self, correlations: List[Dict]) -> str:
        """Generate overall summary of correlation findings."""
        if not correlations:
            return "No significant correlations found in your data"

        top_corr = correlations[0]
        return f"Strongest relationship: {top_corr['metric_1']} and {top_corr['metric_2']} ({top_corr['correlation']:.2f} correlation)"


class InsightGenerator:
    """Generate actionable, personalized insights from health data."""

    def __init__(self, db: Session):
        """Initialize insight generator."""
        self.db = db

    def generate_weekly_insights(self, weeks: int = 1) -> Dict:
        """Generate insights for the past N weeks.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Dictionary with insights, summary, and timestamp
        """
        df = get_recovery_with_features(self.db, days_back=weeks * 7 + 7)

        if len(df) < 7:
            return {
                "insights": [],
                "summary": "Insufficient data for weekly insights",
                "timestamp": datetime.now(),
            }

        insights = []

        # Insight 1: Recovery trend
        recovery_insight = self._analyze_recovery_trend(df, weeks)
        if recovery_insight:
            insights.append(recovery_insight)

        # Insight 2: Sleep pattern
        sleep_insight = self._analyze_sleep_pattern(df)
        if sleep_insight:
            insights.append(sleep_insight)

        # Insight 3: Strain analysis
        strain_insight = self._analyze_strain(df)
        if strain_insight:
            insights.append(strain_insight)

        # Insight 4: HRV trend
        hrv_insight = self._analyze_hrv_trend(df, weeks)
        if hrv_insight:
            insights.append(hrv_insight)

        # Insight 5: Best recovery pattern
        pattern_insight = self._find_best_recovery_pattern(df)
        if pattern_insight:
            insights.append(pattern_insight)

        # Sort by priority
        insights.sort(key=lambda x: x["priority"])

        summary = self._generate_weekly_summary(insights, weeks)

        return {
            "insights": insights[:5],  # Top 5 insights
            "summary": summary,
            "timestamp": datetime.now(),
        }

    def _analyze_recovery_trend(self, df: pd.DataFrame, weeks: int) -> Optional[Dict]:
        """Analyze recovery trend."""
        recent = df.head(weeks * 7)
        older = df.iloc[weeks * 7 : weeks * 14] if len(df) >= weeks * 14 else df.tail(weeks * 7)

        if len(recent) < 3 or len(older) < 3:
            return None

        recent_avg = recent["recovery_score"].mean()
        older_avg = older["recovery_score"].mean()
        change = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0

        if abs(change) < 3:  # Less than 3% change is not significant
            return None

        if change > 0:
            return {
                "insight_text": f"📈 Recovery up {change:.0f}% - {recent_avg:.0f}% avg this period vs {older_avg:.0f}% before. Keep it up!",
                "category": "success",
                "priority": 1,
                "emoji": "📈",
            }
        else:
            return {
                "insight_text": f"📉 Recovery down {abs(change):.0f}% - consider more rest or lighter training",
                "category": "alert",
                "priority": 1,
                "emoji": "📉",
            }

    def _analyze_sleep_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Analyze sleep patterns."""
        top_recoveries = df.nlargest(int(len(df) * 0.25), "recovery_score")
        avg_sleep = top_recoveries["sleep_hours"].mean()
        avg_efficiency = top_recoveries["sleep_efficiency_percentage"].mean()

        if pd.isna(avg_sleep):
            return None

        return {
            "insight_text": f"💤 Your best recoveries: {avg_sleep:.1f}+ hours sleep with {avg_efficiency:.0f}%+ efficiency",
            "category": "success",
            "priority": 2,
            "emoji": "💤",
        }

    def _analyze_strain(self, df: pd.DataFrame) -> Optional[Dict]:
        """Analyze strain patterns."""
        recent = df.head(7)
        avg_strain = recent["strain"].mean()

        if pd.isna(avg_strain) or avg_strain == 0:
            return None

        if avg_strain > 15:
            return {
                "insight_text": f"⚠️ High strain week (avg {avg_strain:.1f}) - schedule recovery days to optimize performance",
                "category": "alert",
                "priority": 2,
                "emoji": "⚠️",
            }
        elif avg_strain < 8:
            return {
                "insight_text": f"💡 Light training week (avg strain {avg_strain:.1f}) - opportunity to increase activity",
                "category": "opportunity",
                "priority": 3,
                "emoji": "💡",
            }

        return None

    def _analyze_hrv_trend(self, df: pd.DataFrame, weeks: int) -> Optional[Dict]:
        """Analyze HRV trends."""
        if "hrv_rmssd_milli" not in df.columns:
            return None

        recent = df.head(weeks * 7)
        older = df.iloc[weeks * 7 : weeks * 14] if len(df) >= weeks * 14 else df.tail(weeks * 7)

        if len(recent) < 3 or len(older) < 3:
            return None

        recent_avg = recent["hrv_rmssd_milli"].mean()
        older_avg = older["hrv_rmssd_milli"].mean()
        change = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0

        if change > 5:
            return {
                "insight_text": f"🎯 HRV trending up {change:.0f}% - sign of improving fitness and recovery",
                "category": "success",
                "priority": 2,
                "emoji": "🎯",
            }
        elif change < -5:
            return {
                "insight_text": f"📊 HRV down {abs(change):.0f}% - may indicate fatigue or stress. Prioritize recovery.",
                "category": "alert",
                "priority": 1,
                "emoji": "📊",
            }

        return None

    def _find_best_recovery_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Find patterns in best recoveries."""
        top_recoveries = df.nlargest(10, "recovery_score")

        # Check bedtime consistency
        if "bedtime_hour" in df.columns:
            avg_bedtime = top_recoveries["bedtime_hour"].mean()
            if not pd.isna(avg_bedtime):
                # Convert to readable time
                bedtime_readable = f"{int(avg_bedtime):02d}:00"
                return {
                    "insight_text": f"🌙 Your top recoveries: bedtime around {bedtime_readable} - consistency matters",
                    "category": "success",
                    "priority": 3,
                    "emoji": "🌙",
                }

        return None

    def _generate_weekly_summary(self, insights: List[Dict], weeks: int) -> str:
        """Generate overall weekly summary."""
        if not insights:
            return f"Past {weeks} week(s): Stable metrics, no major changes detected"

        alerts = [i for i in insights if i["category"] == "alert"]
        successes = [i for i in insights if i["category"] == "success"]

        if alerts:
            return f"Past {weeks} week(s): {len(alerts)} area(s) need attention - prioritize recovery and sleep"
        elif successes:
            return f"Past {weeks} week(s): Strong performance - {len(successes)} positive trend(s) detected"
        else:
            return f"Past {weeks} week(s): Stable performance, opportunities for optimization"


class TimeSeriesAnalyzer:
    """Analyze time series patterns and trends."""

    def __init__(self, db: Session):
        """Initialize analyzer."""
        self.db = db

    def analyze_metric(self, metric: str, days: int = 30) -> Dict:
        """Analyze trend for a specific metric.

        Args:
            metric: Metric name (recovery, hrv, rhr, sleep)
            days: Days to analyze

        Returns:
            Dictionary with trend analysis and data points
        """
        df = get_recovery_with_features(self.db, days_back=days + 30)

        if len(df) < 7:
            return {"error": f"Insufficient data for {metric} analysis"}

        # Map metric name to column
        metric_map = {
            "recovery": "recovery_score",
            "hrv": "hrv_rmssd_milli",
            "rhr": "resting_heart_rate",
            "sleep": "sleep_hours",
        }

        col = metric_map.get(metric)
        if not col or col not in df.columns:
            return {"error": f"Metric {metric} not available"}

        # Calculate rolling average for trend
        df = calculate_rolling_features(df, col, window_sizes=[7])
        df = df.sort_values("created_at")
        recent = df.head(days)

        # Calculate trend
        first_week = recent.tail(days).head(7)[col].mean()
        last_week = recent.head(7)[col].mean()

        if pd.isna(first_week) or pd.isna(last_week) or first_week == 0:
            trend_pct = 0
        else:
            trend_pct = ((last_week - first_week) / first_week) * 100

        # Determine trend direction
        if abs(trend_pct) < 2:
            trend_direction = "stable"
            trend_desc = f"{metric.upper()} is stable over the past {days} days"
        elif trend_pct > 0:
            trend_direction = "up"
            trend_desc = f"{metric.upper()} trending up {trend_pct:.0f}% over the past {days} days"
        else:
            trend_direction = "down"
            trend_desc = (
                f"{metric.upper()} trending down {abs(trend_pct):.0f}% over the past {days} days"
            )

        # Create data points
        data_points = []
        for _, row in recent.iterrows():
            data_points.append(
                {
                    "date": row["created_at"].strftime("%Y-%m-%d"),
                    "value": float(row[col]) if not pd.isna(row[col]) else 0,
                    "annotation": None,
                }
            )

        # Detect anomalies (values > 2 std from mean)
        mean_val = recent[col].mean()
        std_val = recent[col].std()
        anomalies = []

        if not pd.isna(std_val) and std_val > 0:
            for _, row in recent.iterrows():
                if abs(row[col] - mean_val) > 2 * std_val:
                    anomalies.append(
                        f"{row['created_at'].strftime('%Y-%m-%d')}: Unusual {metric} value ({row[col]:.1f})"
                    )

        return {
            "metric_name": metric.upper(),
            "trend_direction": trend_direction,
            "trend_percentage": float(trend_pct),
            "trend_description": trend_desc,
            "data_points": data_points[-days:],  # Last N days
            "anomalies": anomalies,
            "timestamp": datetime.now(),
        }
