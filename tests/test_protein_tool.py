"""Tests for protein recommendation tool."""

from __future__ import annotations

import pytest

from whoopdata.agent import tools as agent_tools


@pytest.mark.anyio
async def test_protein_recommendation(monkeypatch: pytest.MonkeyPatch):
    """Protein recommendations should be derived from latest weight and activity level."""

    class FakeWeightTool:
        async def ainvoke(self, _args):
            return '{"weight_kg": 70.0}'

    monkeypatch.setattr(agent_tools, "get_weight_data_tool", FakeWeightTool())

    result_normal = await agent_tools.get_protein_recommendation_tool.coroutine(
        activity_level="normal"
    )
    result_endurance = await agent_tools.get_protein_recommendation_tool.coroutine(
        activity_level="endurance training"
    )
    result_resistance = await agent_tools.get_protein_recommendation_tool.coroutine(
        activity_level="resistance/strength training"
    )
    result_invalid = await agent_tools.get_protein_recommendation_tool.coroutine(
        activity_level="invalid"
    )

    assert "70.0kg" in result_normal
    assert "84g - 98g protein per day" in result_normal
    assert "84g - 98g protein per day" in result_endurance
    assert "112g - 154g protein per day" in result_resistance
    assert "Invalid activity level" in result_invalid
