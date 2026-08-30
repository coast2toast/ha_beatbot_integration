"""Tests for Beatbot sensor category support."""

from custom_components.beatbot.iot.category import (
    BATTERY_CATEGORIES,
    CATEGORY_MAP,
    STATUS_DISPLAY_MAP_BY_CATEGORY,
    STATUS_MAP_BY_CATEGORY,
)


def test_status_sensor_maps_every_known_work_status() -> None:
    """Every vacuum activity code must have a sensor display state."""
    for category, activity_map in STATUS_MAP_BY_CATEGORY.items():
        assert activity_map.keys() <= STATUS_DISPLAY_MAP_BY_CATEGORY[category].keys()


def test_clean_base_station_status_zero_is_cleaning() -> None:
    """Expose the station's active status instead of an unknown sensor value."""
    category = CATEGORY_MAP["clean_base_station"]

    assert STATUS_DISPLAY_MAP_BY_CATEGORY[category][0] == "cleaning"


def test_clean_base_station_has_no_battery() -> None:
    """The mains-powered clean base station must not get a battery entity."""
    category = CATEGORY_MAP["clean_base_station"]

    assert category not in BATTERY_CATEGORIES


def test_mobile_devices_have_battery() -> None:
    """Mobile product categories retain their battery entities."""
    assert CATEGORY_MAP["pool_clean_bot"] in BATTERY_CATEGORIES
    assert CATEGORY_MAP["lawn_mower"] in BATTERY_CATEGORIES
