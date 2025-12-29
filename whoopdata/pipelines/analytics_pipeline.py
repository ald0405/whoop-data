"""Analytics pipeline for training ML models and pre-computing insights.

Run this pipeline to train all models and compute analytics results
that will be served instantly by API endpoints.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from whoopdata.database.database import SessionLocal
from whoopdata.database.analytics_schema import create_analytics_results_table
from whoopdata.analytics.models import RecoveryPredictor, SleepPredictor
from whoopdata.analytics.engine import (
    RecoveryFactorAnalyzer,
    SleepQualityAnalyzer,
    RecoveryDeepDiveAnalyzer,
    CorrelationAnalyzer,
    InsightGenerator,
    TimeSeriesAnalyzer,
)
from whoopdata.analytics.data_prep import (
    get_recovery_with_features,
    get_sleep_with_features,
    get_sleep_quality_features,
    get_training_data,
)

console = Console()


class AnalyticsPipeline:
    """Pipeline for training models and computing analytics."""
    
    def __init__(self, days_back: int = 365):
        """Initialize pipeline.
        
        Args:
            days_back: Days of historical data to use
        """
        self.days_back = days_back
        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        self.db_path = Path(__file__).parent.parent / "database" / "whoop.db"
        
        self.results = {
            "models_trained": [],
            "analytics_computed": [],
            "errors": []
        }
    
    def run(self):
        """Run the complete analytics pipeline."""
        console.print("\n[bold cyan]🤖 Analytics Pipeline Starting[/bold cyan]")
        console.print(f"📊 Using {self.days_back} days of historical data\n")
        
        # Step 0: Create table if needed
        console.print("[yellow]⚙️  Setting up database...[/yellow]")
        create_analytics_results_table()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Step 1: Train models
            task1 = progress.add_task("Training ML models...", total=3)
            
            self._train_recovery_predictor(progress, task1)
            self._train_sleep_predictor(progress, task1)
            self._train_factor_analyzer(progress, task1)
            
            # Step 2: Compute analytics
            task2 = progress.add_task("Computing analytics...", total=8)
            
            self._compute_factor_importance(progress, task2)
            self._compute_sleep_factors(progress, task2)
            self._compute_recovery_deep_dive(progress, task2)
            self._compute_correlations(progress, task2)
            self._compute_insights(progress, task2)
            self._compute_trends(progress, task2)
            self._compute_summary(progress, task2)
            
            progress.update(task2, advance=1)
        
        self._print_summary()
    
    def _train_recovery_predictor(self, progress, task_id):
        """Train and save recovery predictor model."""
        try:
            console.print("[cyan]  🔄 Training Recovery Predictor...[/cyan]")
            
            db = SessionLocal()
            df = get_recovery_with_features(db, days_back=self.days_back)
            db.close()
            
            if len(df) < 50:
                raise ValueError("Insufficient data (need 50+ recovery records)")
            
            # Expanded feature set with temporal and rolling features
            feature_cols = [
                # Core vitals
                'hrv_rmssd_milli', 'resting_heart_rate', 'spo2_percentage',
                
                # Sleep duration & stages
                'sleep_hours', 'rem_sleep_hours', 'slow_wave_sleep_hours', 'light_sleep_hours',
                'sleep_efficiency_percentage', 'sleep_consistency_percentage',
                
                # Sleep stage ratios
                'rem_percentage', 'deep_sleep_percentage',
                
                # Sleep quality & debt
                'sleep_quality_score', 'sleep_deficit', 'sleep_debt_hours',
                'disturbance_count', 'respiratory_rate',
                
                # Activity & strain
                'strain', 'kilojoule', 'hr_reserve',
                
                # Previous day features (lagged)
                'prev_recovery_score', 'prev_hrv', 'prev_rhr', 'prev_strain',
                
                # Rolling averages (7-day trends)
                'hrv_rolling_7d', 'rhr_rolling_7d', 'strain_rolling_7d', 'sleep_rolling_7d',
                
                # Variability metrics
                'hrv_std_7d', 'rhr_std_7d',
                
                # Deviations from baseline
                'hrv_deviation_from_avg', 'rhr_deviation_from_avg', 'strain_deviation_from_avg',
                
                # Cumulative strain
                'strain_3d_sum',
                
                # Temporal
                'day_of_week', 'is_weekend',
            ]
            
            # Filter to records with complete rolling features (need 14+ days of history)
            df_with_history = df[df['has_rolling_features'] == True].copy()
            
            if len(df_with_history) == 0:
                raise ValueError(f"No records with sufficient history for rolling features. Need at least 14 consecutive days of data. Found {len(df)} total records.")
            
            df_clean = df_with_history[feature_cols + ['recovery_score']].dropna()
            
            if len(df_clean) == 0:
                raise ValueError(f"No valid data after cleaning. Had {len(df_with_history)} records with history, but all had missing values in required features. Check data completeness.")
            
            X_train, X_test, y_train, y_test, _, _ = get_training_data(
                df_clean, target_col='recovery_score',
                feature_cols=feature_cols, scale_features=False
            )
            
            predictor = RecoveryPredictor()
            predictor.train(X_train, y_train, X_test, y_test)
            
            model_path = self.models_dir / "recovery_predictor.pkl"
            predictor.save(str(model_path))
            
            self.results["models_trained"].append({
                "model": "RecoveryPredictor",
                "accuracy": float(predictor.model_accuracy),
                "mae": float(predictor.mae),
                "path": str(model_path)
            })
            
            console.print(f"[green]    ✅ Recovery Predictor trained (R²: {predictor.model_accuracy:.3f})[/green]")
            
        except Exception as e:
            self.results["errors"].append(f"Recovery Predictor: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _train_sleep_predictor(self, progress, task_id):
        """Train and save sleep efficiency predictor model."""
        try:
            console.print("[cyan]  🔄 Training Sleep Efficiency Predictor...[/cyan]")
            
            db = SessionLocal()
            df = get_sleep_quality_features(db, days_back=self.days_back)
            db.close()
            
            if len(df) < 30:
                raise ValueError("Insufficient sleep data (need 30+ records)")
            
            # Use enhanced feature set
            feature_cols = [
                'total_sleep_hours',
                'rem_sleep_hours',
                'slow_wave_sleep_hours',
                'awake_time_hours',
                'bedtime_hour',
                'day_of_week',
                'respiratory_rate',
                'prev_strain',
                'prev_recovery_score',
                'sleep_debt_hours',
                'sleep_deficit',
                'disturbance_count',
                'bedtime_consistency_score',
            ]
            
            # Filter to records with history
            df_with_history = df[df['has_rolling_features'] == True].copy()
            
            if len(df_with_history) == 0:
                raise ValueError("No records with sufficient history for sleep prediction")
            
            df_clean = df_with_history[feature_cols + ['sleep_efficiency_percentage']].dropna()
            
            if len(df_clean) < 30:
                raise ValueError(f"Insufficient clean data. Only {len(df_clean)} records after removing missing values.")
            
            X_train, X_test, y_train, y_test, _, _ = get_training_data(
                df_clean, target_col='sleep_efficiency_percentage',
                feature_cols=feature_cols, scale_features=False
            )
            
            predictor = SleepPredictor()
            predictor.train(X_train, y_train, X_test, y_test)
            
            model_path = self.models_dir / "sleep_predictor.pkl"
            predictor.save(str(model_path))
            
            self.results["models_trained"].append({
                "model": "SleepEfficiencyPredictor",
                "accuracy": float(predictor.model_accuracy),
                "mae": float(predictor.mae),
                "path": str(model_path)
            })
            
            console.print(f"[green]    ✅ Sleep Efficiency Predictor trained (R²: {predictor.model_accuracy:.3f})[/green]")
            
        except Exception as e:
            self.results["errors"].append(f"Sleep Predictor: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _train_factor_analyzer(self, progress, task_id):
        """Train and save factor analyzer model."""
        try:
            console.print("[cyan]  🔄 Training Factor Analyzer...[/cyan]")
            
            db = SessionLocal()
            df = get_recovery_with_features(db, days_back=self.days_back)
            db.close()
            
            if len(df) < 50:
                raise ValueError("Insufficient data for factor analysis")
            
            # Use same expanded feature set as recovery predictor
            feature_cols = [
                # Core vitals
                'hrv_rmssd_milli', 'resting_heart_rate', 'spo2_percentage',
                
                # Sleep duration & stages
                'sleep_hours', 'rem_sleep_hours', 'slow_wave_sleep_hours', 'light_sleep_hours',
                'sleep_efficiency_percentage', 'sleep_consistency_percentage',
                
                # Sleep stage ratios
                'rem_percentage', 'deep_sleep_percentage',
                
                # Sleep quality & debt
                'sleep_quality_score', 'sleep_deficit', 'sleep_debt_hours',
                'disturbance_count', 'respiratory_rate',
                
                # Activity & strain
                'strain', 'kilojoule', 'hr_reserve',
                
                # Previous day features (lagged)
                'prev_recovery_score', 'prev_hrv', 'prev_rhr', 'prev_strain',
                
                # Rolling averages (7-day trends)
                'hrv_rolling_7d', 'rhr_rolling_7d', 'strain_rolling_7d', 'sleep_rolling_7d',
                
                # Variability metrics
                'hrv_std_7d', 'rhr_std_7d',
                
                # Deviations from baseline
                'hrv_deviation_from_avg', 'rhr_deviation_from_avg', 'strain_deviation_from_avg',
                
                # Cumulative strain
                'strain_3d_sum',
                
                # Temporal
                'day_of_week', 'is_weekend',
            ]
            
            # Filter to records with complete rolling features (need 14+ days of history)
            df_with_history = df[df['has_rolling_features'] == True].copy()
            
            if len(df_with_history) == 0:
                raise ValueError(f"No records with sufficient history for rolling features. Need at least 14 consecutive days of data. Found {len(df)} total records.")
            
            df_clean = df_with_history[feature_cols + ['recovery_score']].dropna()
            
            if len(df_clean) == 0:
                raise ValueError(f"No valid data after cleaning. Had {len(df_with_history)} records with history, but all had missing values in required features. Check data completeness.")
            
            X_train, X_test, y_train, y_test, _, _ = get_training_data(
                df_clean, target_col='recovery_score',
                feature_cols=feature_cols, scale_features=False
            )
            
            predictor = RecoveryPredictor()
            predictor.train(X_train, y_train, X_test, y_test)
            
            model_path = self.models_dir / "factor_analyzer.pkl"
            predictor.save(str(model_path))
            
            self.results["models_trained"].append({
                "model": "FactorAnalyzer",
                "accuracy": float(predictor.model_accuracy),
                "path": str(model_path)
            })
            
            console.print(f"[green]    ✅ Factor Analyzer trained (R²: {predictor.model_accuracy:.3f})[/green]")
            
        except Exception as e:
            self.results["errors"].append(f"Factor Analyzer: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_factor_importance(self, progress, task_id):
        """Compute and save factor importance analysis."""
        try:
            console.print("[cyan]  🔄 Computing Factor Importance...[/cyan]")
            
            db = SessionLocal()
            analyzer = RecoveryFactorAnalyzer(db)
            result = analyzer.analyze(days_back=self.days_back)
            db.close()
            
            if "error" not in result:
                self._save_result("factor_importance", result)
                self.results["analytics_computed"].append("factor_importance")
                console.print("[green]    ✅ Factor Importance computed[/green]")
            else:
                raise ValueError(result["error"])
                
        except Exception as e:
            self.results["errors"].append(f"Factor Importance: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_sleep_factors(self, progress, task_id):
        """Compute and save sleep quality factor analysis."""
        try:
            console.print("[cyan]  🔄 Computing Sleep Quality Factors...[/cyan]")
            
            db = SessionLocal()
            analyzer = SleepQualityAnalyzer(db)
            result = analyzer.analyze(days_back=self.days_back)
            db.close()
            
            if "error" not in result:
                self._save_result("sleep_quality_factors", result)
                self.results["analytics_computed"].append("sleep_quality_factors")
                console.print("[green]    ✅ Sleep Quality Factors computed[/green]")
            else:
                raise ValueError(result["error"])
                
        except Exception as e:
            self.results["errors"].append(f"Sleep Quality Factors: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_recovery_deep_dive(self, progress, task_id):
        """Compute and save recovery deep dive analysis."""
        try:
            console.print("[cyan]  🔄 Computing Recovery Deep Dive...[/cyan]")
            
            db = SessionLocal()
            analyzer = RecoveryDeepDiveAnalyzer(db)
            result = analyzer.analyze(days_back=self.days_back)
            db.close()
            
            if "error" not in result:
                # Convert datetime to string
                result["timestamp"] = result["timestamp"].isoformat()
                self._save_result("recovery_deep_dive", result)
                self.results["analytics_computed"].append("recovery_deep_dive")
                console.print("[green]    ✅ Recovery Deep Dive computed[/green]")
            else:
                raise ValueError(result["error"])
                
        except Exception as e:
            self.results["errors"].append(f"Recovery Deep Dive: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_correlations(self, progress, task_id):
        """Compute and save correlation analysis."""
        try:
            console.print("[cyan]  🔄 Computing Correlations...[/cyan]")
            
            db = SessionLocal()
            analyzer = CorrelationAnalyzer(db)
            result = analyzer.analyze(days_back=self.days_back)
            db.close()
            
            if "error" not in result:
                # Convert datetime to string
                result["timestamp"] = result["timestamp"].isoformat()
                self._save_result("correlations", result)
                self.results["analytics_computed"].append("correlations")
                console.print("[green]    ✅ Correlations computed[/green]")
            else:
                raise ValueError(result["error"])
                
        except Exception as e:
            self.results["errors"].append(f"Correlations: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_insights(self, progress, task_id):
        """Compute and save weekly insights."""
        try:
            console.print("[cyan]  🔄 Generating Insights...[/cyan]")
            
            db = SessionLocal()
            generator = InsightGenerator(db)
            result = generator.generate_weekly_insights(weeks=1)
            db.close()
            
            # Convert datetime to string
            result["timestamp"] = result["timestamp"].isoformat()
            self._save_result("insights", result)
            self.results["analytics_computed"].append("insights")
            console.print("[green]    ✅ Insights generated[/green]")
            
        except Exception as e:
            self.results["errors"].append(f"Insights: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_trends(self, progress, task_id):
        """Compute and save trend analysis for all metrics."""
        try:
            console.print("[cyan]  🔄 Analyzing Trends...[/cyan]")
            
            db = SessionLocal()
            analyzer = TimeSeriesAnalyzer(db)
            
            trends = {}
            for metric in ['recovery', 'hrv', 'rhr', 'sleep']:
                result = analyzer.analyze_metric(metric, days=30)
                if "error" not in result:
                    # Convert datetime to string
                    result["timestamp"] = result["timestamp"].isoformat()
                    trends[metric] = result
            
            db.close()
            
            self._save_result("trends", trends)
            self.results["analytics_computed"].append("trends")
            console.print("[green]    ✅ Trends analyzed[/green]")
            
        except Exception as e:
            self.results["errors"].append(f"Trends: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _compute_summary(self, progress, task_id):
        """Generate and save analytics summary."""
        try:
            console.print("[cyan]  🔄 Building Summary...[/cyan]")
            
            # Load all computed results
            factor_importance = self._load_result("factor_importance")
            correlations = self._load_result("correlations")
            insights = self._load_result("insights")
            trends = self._load_result("trends")
            
            summary = {
                "factor_importance": factor_importance,
                "top_correlations": correlations.get("correlations", [])[:7] if correlations else [],
                "weekly_insights": insights,
                "recovery_trend": trends.get("recovery") if trends else None,
                "hrv_trend": trends.get("hrv") if trends else None,
                "timestamp": datetime.now().isoformat()
            }
            
            self._save_result("summary", summary)
            self.results["analytics_computed"].append("summary")
            console.print("[green]    ✅ Summary built[/green]")
            
        except Exception as e:
            self.results["errors"].append(f"Summary: {str(e)}")
            console.print(f"[red]    ❌ Error: {str(e)}[/red]")
        
        progress.update(task_id, advance=1)
    
    def _save_result(self, result_type: str, data: dict):
        """Save analysis result to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Delete old result of this type
        cursor.execute(
            "DELETE FROM analytics_results WHERE result_type = ? AND days_back = ?",
            (result_type, self.days_back)
        )
        
        # Insert new result
        cursor.execute(
            """INSERT INTO analytics_results (result_type, result_data, days_back, computed_at)
               VALUES (?, ?, ?, ?)""",
            (result_type, json.dumps(data), self.days_back, datetime.now())
        )
        
        conn.commit()
        conn.close()
    
    def _load_result(self, result_type: str) -> dict:
        """Load analysis result from database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT result_data FROM analytics_results 
               WHERE result_type = ? AND days_back = ?
               ORDER BY computed_at DESC LIMIT 1""",
            (result_type, self.days_back)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return {}
    
    def _print_summary(self):
        """Print pipeline execution summary."""
        console.print("\n[bold green]✨ Analytics Pipeline Complete[/bold green]\n")
        
        if self.results["models_trained"]:
            console.print("[bold]📦 Models Trained:[/bold]")
            for model in self.results["models_trained"]:
                console.print(f"  • {model['model']}: R² = {model['accuracy']:.3f}")
        
        if self.results["analytics_computed"]:
            console.print(f"\n[bold]📊 Analytics Computed:[/bold]")
            for analysis in self.results["analytics_computed"]:
                console.print(f"  • {analysis}")
        
        if self.results["errors"]:
            console.print(f"\n[bold red]❌ Errors ({len(self.results['errors'])}):[/bold red]")
            for error in self.results["errors"]:
                console.print(f"  • {error}")
        
        console.print(f"\n[dim]Results stored in database and ready for API queries[/dim]")


def run_analytics_pipeline(days_back: int = 365):
    """Run the analytics pipeline.
    
    Args:
        days_back: Days of historical data to use
    """
    pipeline = AnalyticsPipeline(days_back=days_back)
    pipeline.run()


if __name__ == "__main__":
    run_analytics_pipeline()
