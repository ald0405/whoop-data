from __future__ import annotations

from whoopdata.api.public_surface_contract import (
    AGENT_SURFACE_GUARDRAILS,
    CAPABILITY_PLACEMENT_RULES,
    PUBLIC_SURFACE_CONTRACT,
    SURFACE_ORDER,
    surface_accepts_target,
    surface_allows_entrypoint_role,
    surface_allows_route_kind,
    surface_allows_route_role,
)
from whoopdata.api.public_surface_inventory import (
    ENTRYPOINT_MIGRATION_MATRIX,
    ROUTE_MIGRATION_MATRIX,
)


def test_contract_defines_expected_surfaces_and_namespaces():
    assert SURFACE_ORDER == ("data", "insights", "agent", "web")
    assert PUBLIC_SURFACE_CONTRACT["data"].namespace_prefix == "/api/v1/data"
    assert PUBLIC_SURFACE_CONTRACT["insights"].namespace_prefix == "/api/v1/insights"
    assert PUBLIC_SURFACE_CONTRACT["agent"].namespace_prefix == "/api/v1/agent"
    assert PUBLIC_SURFACE_CONTRACT["web"].namespace_prefix is None
    assert PUBLIC_SURFACE_CONTRACT["web"].openapi_tag is None


def test_route_inventory_conforms_to_public_surface_contract():
    for entry in ROUTE_MIGRATION_MATRIX:
        surface = entry["canonical_surface"]
        assert surface_allows_route_kind(surface, entry["current_kind"])
        assert surface_allows_route_role(surface, entry["current_role"])
        assert surface_accepts_target(surface, entry["target_path"])


def test_runtime_entrypoints_conform_to_surface_contract():
    for entry in ENTRYPOINT_MIGRATION_MATRIX:
        assert surface_allows_entrypoint_role(entry["primary_surface"], entry["current_role"])


def test_contract_exposes_rules_for_all_surfaces():
    assert len(AGENT_SURFACE_GUARDRAILS) >= 4
    covered_surfaces = {rule.surface for rule in CAPABILITY_PLACEMENT_RULES}
    assert covered_surfaces == set(SURFACE_ORDER)
