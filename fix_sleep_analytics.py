#!/usr/bin/env python3
"""
Quick script to re-run the sleep quality analytics after fixing the circular logic issue.

The SleepQualityAnalyzer was predicting sleep efficiency FROM sleep metrics (circular).
Now it should predict recovery FROM sleep metrics.
"""

from whoopdata.pipelines.analytics_pipeline import AnalyticsPipeline

if __name__ == "__main__":
    print("Re-running sleep quality analytics with fixed model...")
    print("This will predict recovery from sleep factors (not sleep efficiency from sleep metrics)")

    pipeline = AnalyticsPipeline(days_back=365)

    # Just recompute sleep factors and summary
    from whoopdata.database.database import SessionLocal
    from whoopdata.analytics.engine import SleepQualityAnalyzer
    from rich.console import Console

    console = Console()
    console.print("[cyan]Computing Sleep Quality Factors (fixed)...[/cyan]")

    db = SessionLocal()
    analyzer = SleepQualityAnalyzer(db)
    result = analyzer.analyze(days_back=365)
    db.close()

    if "error" not in result:
        pipeline._save_result("sleep_quality_factors", result)
        console.print("[green]✅ Sleep Quality Factors recomputed[/green]")

        # Also update summary
        from whoopdata.pipelines.analytics_pipeline import AnalyticsPipeline

        pipeline._compute_summary(None, None)
        console.print("[green]✅ Summary updated[/green]")

        print("\nDone! Refresh your browser to see the corrected results.")
    else:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
