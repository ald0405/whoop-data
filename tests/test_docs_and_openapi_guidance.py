from __future__ import annotations

from pathlib import Path

from main import app
from whoopdata.api.public_surface_contract import PUBLIC_SURFACE_CONTRACT


ROOT = Path(__file__).resolve().parents[1]


def test_openapi_publishes_top_level_surface_tag_metadata():
    schema = app.openapi()
    tag_index = {tag["name"]: tag for tag in schema["tags"]}

    assert set(tag_index) == {"data", "insights", "agent"}

    for surface in ("data", "insights", "agent"):
        definition = PUBLIC_SURFACE_CONTRACT[surface]
        description = tag_index[definition.openapi_tag]["description"]
        assert definition.summary in description
        for example in definition.examples:
            assert example in description


def test_readme_and_makefile_distinguish_surfaces_and_run_modes():
    readme_text = (ROOT / "README.md").read_text()
    makefile_text = (ROOT / "Makefile").read_text()

    assert "## Public Surface Model" in readme_text
    assert "/api/v1/data/*" in readme_text
    assert "/api/v1/insights/*" in readme_text
    assert "/api/v1/agent/*" in readme_text
    assert "/dashboard" in readme_text
    assert "## Canonical Run Modes" in readme_text
    assert "### Primary Commands" in readme_text
    assert "### Convenience Launchers" in readme_text
    assert "`make server`" in readme_text
    assert "`make run`" in readme_text
    assert "convenience" in readme_text.lower()
    assert "Primary FastAPI server command" in makefile_text
    assert "Convenience launcher" in makefile_text
