"""
Example: Using the Protein Recommendation Tool

This example demonstrates how to use the protein recommendation tool
both directly and through the agent system.
"""

import asyncio
from whoopdata.agent.tools import (
    get_protein_recommendation_tool,
    get_weight_data_tool,
)


async def example_direct_usage():
    """Example of using the tool directly."""
    print("=" * 70)
    print("EXAMPLE 1: Direct Tool Usage")
    print("=" * 70)
    
    # Scenario: User doing resistance training
    print("\n📋 Scenario: User doing resistance/strength training")
    print("-" * 70)
    
    result = await get_protein_recommendation_tool(
        activity_level="resistance/strength training"
    )
    print(f"Recommendation: {result}")
    
    # Scenario: User doing endurance training
    print("\n📋 Scenario: User doing endurance training")
    print("-" * 70)
    
    result = await get_protein_recommendation_tool(
        activity_level="endurance training"
    )
    print(f"Recommendation: {result}")
    
    # Scenario: Normal activity level
    print("\n📋 Scenario: User with normal activity level")
    print("-" * 70)
    
    result = await get_protein_recommendation_tool(
        activity_level="normal"
    )
    print(f"Recommendation: {result}")


async def example_with_weight_context():
    """Example showing weight data context."""
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: Understanding the Weight Data")
    print("=" * 70)
    
    # First, let's see what weight data looks like
    print("\n📊 Fetching current weight data...")
    print("-" * 70)
    
    weight_result = await get_weight_data_tool(latest=True)
    print(f"Latest weight data:\n{weight_result[:300]}...")
    
    print("\n💪 Now calculating protein recommendation...")
    print("-" * 70)
    
    result = await get_protein_recommendation_tool(
        activity_level="resistance/strength training"
    )
    print(f"Recommendation: {result}")


async def example_error_handling():
    """Example of error handling."""
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: Error Handling")
    print("=" * 70)
    
    # Invalid activity level
    print("\n❌ Testing with invalid activity level...")
    print("-" * 70)
    
    result = await get_protein_recommendation_tool(
        activity_level="yoga"  # Not a valid activity level
    )
    print(f"Result: {result}")


def example_agent_integration():
    """Example of how agents would use this tool."""
    print("\n\n" + "=" * 70)
    print("EXAMPLE 4: Agent Integration Flow")
    print("=" * 70)
    
    print("""
    User Query Examples:
    -------------------
    1. "How much protein should I eat?"
       → Supervisor routes to: nutrition agent
       → Agent asks: "What's your activity level?"
       → User responds: "I do strength training"
       → Agent calls: get_protein_recommendation_tool("resistance/strength training")
       → Agent provides recommendation + timing advice
    
    2. "Give me protein targets for marathon training"
       → Supervisor routes to: nutrition agent
       → Agent infers activity level from context: "endurance training"
       → Agent calls: get_protein_recommendation_tool("endurance training")
       → Agent provides recommendation + recovery context
    
    3. "What's my current weight and protein needs?"
       → Supervisor routes to: health_data agent
       → Agent calls: get_weight_data_tool()
       → Agent calls: get_protein_recommendation_tool("normal")
       → Agent provides both weight and protein recommendation
    
    Available Agents:
    ----------------
    - health_data: Has access to get_protein_recommendation
    - nutrition: Dedicated specialist for nutrition queries
    - exercise: Can reference protein needs for training plans
    """)


async def main():
    """Run all examples."""
    await example_direct_usage()
    await example_with_weight_context()
    await example_error_handling()
    example_agent_integration()
    
    print("\n" + "=" * 70)
    print("✅ All examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
