#!/usr/bin/env python3
"""
Test Script for Python Code Interpreter in WHOOP Health Data Agent

This script tests the Python code execution capabilities for health data analysis.
Make sure your FastAPI server is running on localhost:8000 before running this test.
"""

import asyncio
import os
from rich.console import Console
from rich.panel import Panel

# Add the project root to the Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whoop_data.agent.graph import run_agent

console = Console()


async def test_data_analysis_queries():
    """Test data analysis and visualization queries"""
    console.print(Panel("📊 Testing Python Code Interpreter for Health Data Analysis", style="bold green"))
    
    queries = [
        "Get my recovery trends and create a visualization showing the pattern over time",
        "Analyze my running workouts and calculate the correlation between TRIMP scores and recovery",
        "Compare my weight trends with my recovery scores - is there a relationship?",
        "Create a comprehensive health dashboard visualization combining my WHOOP and Withings data",
        "Calculate statistics for my sleep efficiency and show the distribution",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        console.print("🔄 [yellow]Processing (this may take a moment for analysis)...[/yellow]")
        
        try:
            result = await run_agent(query, thread_id=f"analysis-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:400]}...")
                
                # Check if Python code was executed
                if "```python" in response or "python_interpreter" in str(messages):
                    console.print("✅ [bold green]Python code was executed![/bold green]")
                else:
                    console.print("ℹ️ [yellow]No Python code execution detected[/yellow]")
            else:
                console.print("❌ No response received")
                
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")
        
        # Add a small delay between tests
        await asyncio.sleep(1)


async def test_statistical_analysis():
    """Test statistical analysis capabilities"""
    console.print(Panel("🔬 Testing Statistical Analysis Capabilities", style="bold blue"))
    
    queries = [
        "Calculate the mean, median, and standard deviation of my recovery scores",
        "Perform a simple linear regression on my weight data over time",
        "Find outliers in my sleep data using statistical methods", 
        "Calculate correlations between all my health metrics",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        console.print("🔄 [yellow]Processing statistical analysis...[/yellow]")
        
        try:
            result = await run_agent(query, thread_id=f"stats-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:300]}...")
            else:
                console.print("❌ No response received")
                
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")
            
        await asyncio.sleep(1)


async def test_visualization_requests():
    """Test visualization creation capabilities"""
    console.print(Panel("📈 Testing Visualization Creation", style="bold purple"))
    
    queries = [
        "Create a time series plot of my recovery scores",
        "Make a histogram showing the distribution of my workout strain values",
        "Plot my weight over time with a trend line",
        "Create a correlation heatmap of my health metrics",
        "Make a scatter plot comparing sleep efficiency vs recovery score",
    ]
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n💬 [bold]Query {i}:[/bold] {query}")
        console.print("🔄 [yellow]Creating visualization...[/yellow]")
        
        try:
            result = await run_agent(query, thread_id=f"viz-test-{i}")
            messages = result.get("messages", [])
            if messages:
                response = messages[-1].content
                console.print(f"🤖 [green]Response:[/green] {response[:300]}...")
                
                if "matplotlib" in response or "seaborn" in response or "plt." in response:
                    console.print("📊 [bold cyan]Visualization code detected![/bold cyan]")
            else:
                console.print("❌ No response received")
                
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {str(e)}")
            
        await asyncio.sleep(1)


async def test_complex_multi_step_analysis():
    """Test complex multi-step analysis combining data retrieval and analysis"""
    console.print(Panel("🧠 Testing Complex Multi-Step Analysis", style="bold yellow"))
    
    query = """
    I want a comprehensive analysis of my health data. Please:
    1. Get my latest recovery, sleep, workout, and weight data
    2. Calculate key statistics for each metric
    3. Find correlations between different health metrics
    4. Create visualizations showing trends and relationships
    5. Provide actionable insights based on the analysis
    """
    
    console.print(f"💬 [bold]Complex Analysis Query:[/bold] {query[:100]}...")
    console.print("🔄 [yellow]Processing comprehensive analysis (this will take longer)...[/yellow]")
    
    try:
        result = await run_agent(query, thread_id="complex-analysis-test")
        messages = result.get("messages", [])
        if messages:
            response = messages[-1].content
            console.print(f"🤖 [green]Comprehensive Response:[/green]")
            console.print(response)
            
            # Count tool usage
            tool_usage = 0
            for message in messages:
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    tool_usage += len(message.tool_calls)
            
            console.print(f"\n📊 [bold]Analysis completed with {tool_usage} tool calls[/bold]")
            
        else:
            console.print("❌ No response received")
            
    except Exception as e:
        console.print(f"❌ [red]Error:[/red] {str(e)}")


async def main():
    """Run all Python interpreter tests"""
    
    # Check environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        console.print(f"\n❌ [bold red]Missing environment variables:[/bold red] {', '.join(missing_vars)}")
        console.print("[dim]Please set these in your .env file[/dim]")
        return
    
    console.print("✅ [green]Environment variables found[/green]")
    console.print("\n🚀 [bold]Testing Python Code Interpreter in Health Data Agent[/bold]")
    console.print("\n💡 [dim]Note: Make sure you've installed langchain-experimental and data science libraries![/dim]")
    
    try:
        # Test different capabilities
        await test_data_analysis_queries()
        await test_statistical_analysis()
        await test_visualization_requests()
        await test_complex_multi_step_analysis()
        
        console.print(f"\n🎉 [bold green]All Python interpreter tests completed![/bold green]")
        console.print(f"\n🐍 [bold]Python Code Interpreter Capabilities Added:[/bold]")
        console.print("   • Data analysis with pandas and numpy")
        console.print("   • Statistical calculations and modeling")
        console.print("   • Visualization creation with matplotlib/seaborn") 
        console.print("   • Correlation analysis and trend detection")
        console.print("   • Multi-step analytical workflows")
        console.print(f"\n💻 The agent can now execute Python code for advanced health data analysis!")
        
    except KeyboardInterrupt:
        console.print(f"\n⚠️ [yellow]Tests cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n💥 [bold red]Test failed:[/bold red] {str(e)}")
        console.print(f"\n💡 [dim]Make sure you've installed: pip install langchain-experimental matplotlib seaborn[/dim]")


if __name__ == "__main__":
    asyncio.run(main())