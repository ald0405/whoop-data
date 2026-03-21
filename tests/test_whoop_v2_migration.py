from __future__ import annotations
import inspect

from pathlib import Path

import pandas as pd
import yaml

from whoopdata.analysis.whoop_client import Whoop as AnalysisWhoop
from whoopdata.analysis.whoop_client_fast import WhoopFast
from whoopdata.analysis.whoop_client_nodes import WhoopNodes
from whoopdata.analysis.whoop_simple import WhoopSimple
from whoopdata.clients.whoop_client import Whoop as LegacyWhoop
from whoopdata.model_transformation import transform_sleep, transform_workout


ROOT = Path(__file__).resolve().parents[1]


def test_all_maintained_whoop_clients_use_v2_endpoints():
    client_classes = [AnalysisWhoop, WhoopFast, WhoopNodes, LegacyWhoop]

    for client_cls in client_classes:
        for endpoint in client_cls.ENDPOINTS.values():
            assert "/developer/v2/" in endpoint
            assert "/developer/v1/" not in endpoint

    whoop_simple_source = inspect.getsource(WhoopSimple)
    assert "/developer/v2/" in whoop_simple_source
    assert "/developer/v1/" not in whoop_simple_source


def test_legacy_client_maps_v2_zone_durations_fields():
    client = LegacyWhoop(client_id="x", client_secret="y")
    df = pd.DataFrame(
        [
            {
                "score.zone_durations.zone_zero_milli": 60000,
                "score.zone_durations.zone_one_milli": 120000,
                "score.zone_durations.zone_two_milli": 180000,
                "score.zone_durations.zone_three_milli": 240000,
                "score.zone_durations.zone_four_milli": 300000,
                "score.zone_durations.zone_five_milli": 360000,
            }
        ]
    )

    transformed = client._transform_workout_fields(df)

    assert transformed.loc[0, "zone_zero_minutes"] == 1.0
    assert transformed.loc[0, "zone_one_minutes"] == 2.0
    assert transformed.loc[0, "zone_two_minutes"] == 3.0
    assert transformed.loc[0, "zone_three_minutes"] == 4.0
    assert transformed.loc[0, "zone_four_minutes"] == 5.0
    assert transformed.loc[0, "zone_five_minutes"] == 6.0


def test_transform_sleep_handles_v2_uuid_ids():
    item = {
        "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
        "user_id": "user-1",
        "created_at": "2026-03-20T10:00:00Z",
        "updated_at": "2026-03-20T10:05:00Z",
        "start": "2026-03-19T22:00:00Z",
        "end": "2026-03-20T06:00:00Z",
    }

    transformed = transform_sleep(item)

    assert transformed["whoop_id"] == item["id"]


def test_transform_workout_handles_v2_uuid_ids():
    item = {
        "id": "7bfc6a15-5521-612f-b9a4-e274dd7afae9",
        "user_id": "user-1",
        "created_at": "2026-03-20T10:00:00Z",
        "updated_at": "2026-03-20T10:05:00Z",
        "start": "2026-03-20T07:00:00Z",
        "end": "2026-03-20T08:00:00Z",
    }

    transformed = transform_workout(item)

    assert transformed["whoop_id"] == item["id"]


def test_custom_gpt_workout_spec_uses_v2_and_uuid_ids():
    spec_path = ROOT / "custom_gpt" / "get_workout.yaml"
    spec = yaml.safe_load(spec_path.read_text())

    assert "/v2/activity/workout" in spec["paths"]
    workout_schema = spec["paths"]["/v2/activity/workout"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["properties"]["records"]["items"]["properties"]["id"]
    assert workout_schema["type"] == "string"
    assert workout_schema["format"] == "uuid"
