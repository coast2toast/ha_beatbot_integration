"""Contract tests for Beatbot icon translations."""

import json
from pathlib import Path

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "beatbot"


def test_semantic_icons_exist_for_entities_without_device_class_icons() -> None:
    """Give translation-key entities semantic frontend icons."""
    icons_path = INTEGRATION_DIR / "icons.json"
    assert icons_path.exists()
    icons = json.loads(icons_path.read_text(encoding="utf-8"))["entity"]

    assert icons["sensor"]["work_status"]["default"] == "mdi:robot-vacuum"
    assert icons["sensor"]["error"] == {
        "default": "mdi:alert-circle-outline",
        "state": {"none": "mdi:check-circle-outline"},
    }
    assert icons["select"]["work_mode"]["default"] == "mdi:format-list-bulleted"
    assert icons["switch"]["child_lock"]["default"] == "mdi:account-lock"
    assert icons["switch"]["voice_disturb"]["default"] == "mdi:volume-off"
    assert set(icons["vacuum"]) == {
        "beatbot_clean_base_station_vacuum",
        "beatbot_lawn_mower_vacuum",
        "beatbot_pool_vacuum",
    }
