#!/usr/bin/env python3
"""
Enhanced Test Script for WHOOP Health Data Agent

This script demonstrates all the available tools and capabilities of the health data agent.
Make sure your FastAPI server is running on localhost:8000 before running this test.
"""

import asyncio
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add the project root to the Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whoopdata.agent.graph import run_agent

console = Console()


async def test_recovery_queries():
    """Test recovery-related queries"""
    console.print(Panel("🔄 Testing WHOOP Recovery Queries", style="bold blue"))
    
    queries = [
        "What's my latest recovery score and HRV?",
        "Show me my best recovery days from the top 5",
        "How has my recovery been trending over the last 4 weeks?",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        try:
            result = await run_agent(query, thread_id=f"recovery-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:200]}...")
            else:
                console.print("❌ No response received")
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")


async def test_workout_queries():
    """Test workout-related queries"""
    console.print(Panel("🏃‍♂️ Testing WHOOP Workout Queries", style="bold green"))
    
    queries = [
        "What was my last workout like?",
        "Show me my recent running workouts with training loads",
        "How are my tennis sessions going?",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        try:
            result = await run_agent(query, thread_id=f"workout-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:200]}...")
            else:
                console.print("❌ No response received")
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")


async def test_sleep_queries():
    """Test sleep-related queries"""
    console.print(Panel("😴 Testing WHOOP Sleep Queries", style="bold purple"))
    
    queries = [
        "How was my sleep last night?",
        "Show me my latest sleep data with all the stages",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        try:
            result = await run_agent(query, thread_id=f"sleep-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:200]}...")
            else:
                console.print("❌ No response received")
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")


async def test_weight_queries():
    """Test weight-related queries"""
    console.print(Panel("⚖️ Testing Withings Weight Queries", style="bold cyan"))
    
    queries = [
        "What's my current weight and BMI?",
        "Show me my weight trends over the last 30 days",
        "How has my body composition changed?",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        try:
            result = await run_agent(query, thread_id=f"weight-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:200]}...")
            else:
                console.print("❌ No response received")
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")


async def test_cardiovascular_queries():
    """Test heart rate and blood pressure queries"""
    console.print(Panel("❤️ Testing Withings Cardiovascular Queries", style="bold red"))
    
    queries = [
        "What's my latest heart rate and blood pressure?",
        "Give me a complete summary of my Withings health data",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        try:
            result = await run_agent(query, thread_id=f"cardio-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:200]}...")
            else:
                console.print("❌ No response received")
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")


async def test_complex_analysis():
    """Test complex multi-metric analysis"""
    console.print(Panel("🧠 Testing Complex Health Analysis", style="bold yellow"))
    
    queries = [
        "Give me a comprehensive health overview combining my recovery, weight, and cardiovascular data",
        "How do my running workouts correlate with my recovery scores?",
        "What patterns do you see in my overall health metrics?",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        try:
            result = await run_agent(query, thread_id=f"complex-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:300]}...")
            else:
                console.print("❌ No response received")
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")


async def show_available_tools():
    """Display a table of all available tools"""
    console.print(Panel("🛠️ Available Health Data Tools", style="bold magenta"))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category", style="dim", width=15)
    table.add_column("Tool", style="cyan", width=25)
    table.add_column("Description", width=50)
    
    tools = [
        ("WHOOP Recovery", "get_latest_recovery", "Latest recovery score, HRV, resting heart rate"),
        ("WHOOP Recovery", "get_top_recoveries", "Highest recovery scores for pattern analysis"),
        ("WHOOP Recovery", "get_recovery_trends", "Weekly recovery trends over time"),
        ("WHOOP Sleep", "get_latest_sleep", "Latest sleep stages, efficiency, quality"),
        ("WHOOP Workouts", "get_latest_workout", "Latest workout strain and heart rate zones"),
        ("WHOOP Workouts", "get_running_workouts", "Running workouts with TRIMP training loads"),
        ("WHOOP Workouts", "get_tennis_workouts", "Tennis-specific workout performance"),
        ("Withings Weight", "get_latest_weight", "Latest weight, BMI, body composition"),
        ("Withings Weight", "get_weight_stats", "Weight trends and statistics over time"),
        ("Withings Cardio", "get_latest_heart_rate", "Latest heart rate and blood pressure"),
        ("Summary", "get_withings_summary", "Complete Withings health data overview"),
    ]
    
    for category, tool, description in tools:
        table.add_row(category, tool, description)
    
    console.print(table)


async def main():
    """Run all enhanced tests"""
    
    # Check environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        console.print(f"\n❌ [bold red]Missing environment variables:[/bold red] {', '.join(missing_vars)}")
        console.print("[dim]Please set these in your .env file[/dim]")
        return
    
    console.print("✅ [green]Environment variables found[/green]")
    console.print("\n🚀 [bold]Starting Enhanced WHOOP Health Agent Tests[/bold]")
    
    # Show available tools
    await show_available_tools()
    
    try:
        # Run all test categories
        await test_recovery_queries()
        await test_sleep_queries()
        await test_workout_queries()
        await test_weight_queries()
        await test_cardiovascular_queries()
        await test_complex_analysis()
        
        console.print(f"\n🎉 [bold green]All enhanced tests completed![/bold green]")
        console.print(f"\n💡 [bold]The agent now has {len(['recovery', 'sleep', 'workout', 'weight', 'heart_rate']) * 2} tools covering:")
        console.print("   • WHOOP recovery, sleep, and workout data")
        console.print("   • Withings weight and cardiovascular metrics")
        console.print("   • Training load analysis with TRIMP scores")
        console.print("   • Trend analysis and pattern recognition")
        
    except KeyboardInterrupt:
        console.print(f"\n⚠️ [yellow]Tests cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n💥 [bold red]Test failed:[/bold red] {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())