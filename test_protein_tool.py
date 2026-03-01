"""Test script for protein recommendation tool."""

import asyncio
from whoopdata.agent.tools import get_protein_recommendation_tool, get_weight_data_tool


async def test_protein_recommendation():
    """Test the protein recommendation tool."""
    
    print("=" * 60)
    print("Testing Protein Recommendation Tool")
    print("=" * 60)
    
    # Test 1: Check weight data availability
    print("\n1. Testing weight data retrieval...")
    weight_result = await get_weight_data_tool(latest=True)
    print(f"Weight data result (first 200 chars):\n{weight_result[:200]}...")
    
    # Test 2: Normal activity level
    print("\n2. Testing protein recommendation - Normal activity...")
    result_normal = await get_protein_recommendation_tool(activity_level="normal")
    print(f"Result: {result_normal}")
    
    # Test 3: Endurance training
    print("\n3. Testing protein recommendation - Endurance training...")
    result_endurance = await get_protein_recommendation_tool(activity_level="endurance training")
    print(f"Result: {result_endurance}")
    
    # Test 4: Resistance training
    print("\n4. Testing protein recommendation - Resistance training...")
    result_resistance = await get_protein_recommendation_tool(activity_level="resistance/strength training")
    print(f"Result: {result_resistance}")
    
    # Test 5: Invalid activity level
    print("\n5. Testing protein recommendation - Invalid activity level...")
    result_invalid = await get_protein_recommendation_tool(activity_level="invalid")
    print(f"Result: {result_invalid}")
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_protein_recommendation())
