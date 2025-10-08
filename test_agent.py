#!/usr/bin/env python3
"""
Test script for the WHOOP Health Data Agent

This script tests the basic agent functionality by asking about recovery data.
Make sure your FastAPI server is running on localhost:8000 before running this test.
"""

import asyncio
import os
from rich.console import Console
from rich.panel import Panel

# Add the project root to the Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whoopdata.agent.graph import run_agent

console = Console()


async def test_basic_agent():
    """Test the agent with a simple health data query."""
    
    console.print(Panel.fit(
        "🤖 Testing WHOOP Health Data Agent 🤖\n"
        "This will test the basic agent functionality with a recovery data query.",
        style="bold blue"
    ))
    
    # Test query
    test_message = "What's my latest recovery data? How am I doing?"
    
    console.print(f"\n💬 [bold]User Query:[/bold] {test_message}")
    console.print("\n🔄 [yellow]Processing...[/yellow]")
    
    try:
        # Run the agent
        result = await run_agent(test_message, thread_id="test-123")
        
        # Extract the final response
        messages = result.get("messages", [])
        if messages:
            final_response = messages[-1].content
            console.print(f"\n🤖 [bold green]Agent Response:[/bold green]\n{final_response}")
        else:
            console.print("\n❌ [bold red]No response received from agent[/bold red]")
            
        # Show full state for debugging
        console.print(f"\n📊 [dim]Full state:[/dim]")
        console.print(f"[dim]- Messages count: {len(messages)}[/dim]")
        console.print(f"[dim]- User ID: {result.get('user_id', 'Not set')}[/dim]")
        
    except Exception as e:
        console.print(f"\n❌ [bold red]Error running agent:[/bold red] {str(e)}")
        console.print(f"\n[dim]Make sure your FastAPI server is running on localhost:8000[/dim]")
        raise


async def test_non_health_query():
    """Test the agent with a non-health query to see how it responds."""
    
    console.print("\n" + "="*60)
    console.print("🧪 Testing with non-health query...")
    
    test_message = "What's the weather like today?"
    
    console.print(f"\n💬 [bold]User Query:[/bold] {test_message}")
    console.print("\n🔄 [yellow]Processing...[/yellow]")
    
    try:
        result = await run_agent(test_message, thread_id="test-456")
        messages = result.get("messages", [])
        if messages:
            final_response = messages[-1].content
            console.print(f"\n🤖 [bold green]Agent Response:[/bold green]\n{final_response}")
            
    except Exception as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {str(e)}")


async def main():
    """Run all tests."""
    
    # Check environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        console.print(f"\n❌ [bold red]Missing environment variables:[/bold red] {', '.join(missing_vars)}")
        console.print("[dim]Please set these in your .env file[/dim]")
        return
    
    console.print("✅ [green]Environment variables found[/green]")
    
    try:
        # Test 1: Basic health query
        await test_basic_agent()
        
        # Test 2: Non-health query  
        await test_non_health_query()
        
        console.print(f"\n🎉 [bold green]All tests completed![/bold green]")
        
    except KeyboardInterrupt:
        console.print(f"\n⚠️ [yellow]Tests cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n💥 [bold red]Test failed:[/bold red] {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())