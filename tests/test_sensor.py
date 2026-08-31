"""Tests for Beatbot sensor entities."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.beatbot import sensor as sensor_module
from custom_components.beatbot.iot.category import (
    BATTERY_CATEGORIES,
    CATEGORY_MAP,
    STATUS_DISPLAY_MAP_BY_CATEGORY,
    STATUS_MAP_BY_CATEGORY,
)
from custom_components.beatbot.models import BeatbotDeviceData
from custom_components.beatbot.sensor import (
    BeatbotBatterySensor,
    BeatbotErrorSensor,
    BeatbotStatusSensor,
)

DEVICE_ID = "test-device-1"


def _device(device_id: str, category: str) -> BeatbotDeviceData:
    return BeatbotDeviceData(
        device_id=device_id,
        product_id="synthetic-product",
        product_category=category,
        work_status=5,
        work_mode=0,
        error_code=5,
        battery_level=73,
        versions=[],
        is_online=True,
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


def test_sensor_values_decode_device_runtime_state() -> None:
    """Expose status, battery, and every active error bit from runtime data."""
    device = _device(DEVICE_ID, "pool_clean_bot")
    coordinator = SimpleNamespace(
        data={DEVICE_ID: device},
        last_update_success=True,
        runtime_data_available={DEVICE_ID},
    )
    category = CATEGORY_MAP[device.product_category]
    bits = sensor_module.ERROR_BITS_BY_CATEGORY[category]

    status = BeatbotStatusSensor(coordinator, DEVICE_ID)
    battery = BeatbotBatterySensor(coordinator, DEVICE_ID)
    error = BeatbotErrorSensor(coordinator, DEVICE_ID, bits)

    expected_active = [key for key, bit in bits if device.error_code & bit]
    assert status.native_value == "cleaning"
    assert battery.native_value == 73
    assert error.native_value == expected_active[0]
    assert [
        key for key, active in error.extra_state_attributes.items() if active
    ] == expected_active


async def test_setup_creates_category_entities_and_cleans_stale_registry_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set up supported sensors while removing superseded firmware and battery IDs."""
    pool = _device("pool-1", "pool_clean_bot")
    station = _device("station-1", "clean_base_station")
    coordinator = SimpleNamespace(data={"pool-1": pool, "station-1": station})
    entry = SimpleNamespace(
        entry_id="entry", runtime_data=SimpleNamespace(coordinator=coordinator)
    )
    registry = SimpleNamespace(async_remove=Mock())
    registry_entries = [
        SimpleNamespace(
            domain="sensor",
            unique_id="removed-device_firmware",
            entity_id="sensor.old_fw",
        ),
        SimpleNamespace(
            domain="sensor",
            unique_id="station-1_battery",
            entity_id="sensor.old_battery",
        ),
        SimpleNamespace(
            domain="sensor", unique_id="pool-1_battery", entity_id="sensor.pool_battery"
        ),
        SimpleNamespace(
            domain="binary_sensor",
            unique_id="station-1_battery",
            entity_id="binary_sensor.keep",
        ),
    ]
    monkeypatch.setattr(sensor_module.er, "async_get", Mock(return_value=registry))
    monkeypatch.setattr(
        sensor_module.er,
        "async_entries_for_config_entry",
        Mock(return_value=registry_entries),
    )
    added: list = []

    await sensor_module.async_setup_entry(None, entry, added.extend)

    assert [type(entity) for entity in added] == [
        BeatbotStatusSensor,
        BeatbotBatterySensor,
        BeatbotErrorSensor,
        BeatbotStatusSensor,
        BeatbotErrorSensor,
    ]
    assert {call.args[0] for call in registry.async_remove.call_args_list} == {
        "sensor.old_fw",
        "sensor.old_battery",
    }


def test_battery_cleanup_is_noop_without_unsupported_devices() -> None:
    """Avoid registry work when every discovered device supports a battery."""
    hass = Mock()
    sensor_module._remove_unsupported_battery_entities(
        hass, SimpleNamespace(entry_id="entry"), set()
    )

    hass.assert_not_called()
