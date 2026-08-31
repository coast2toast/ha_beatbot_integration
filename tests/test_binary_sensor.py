"""Tests for Beatbot binary_sensor entities (charging indicator)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.beatbot import binary_sensor as binary_sensor_module
from custom_components.beatbot.binary_sensor import (
    BeatbotChargingSensor,
    BeatbotOnlineSensor,
)
from custom_components.beatbot.iot.category import (
    CATEGORY_MAP,
    CHARGING_STATUS_CODES_BY_CATEGORY,
)
from custom_components.beatbot.models import BeatbotDeviceData

DEVICE_ID = "test-device-1"
POOL_CODES = CHARGING_STATUS_CODES_BY_CATEGORY[CATEGORY_MAP["pool_clean_bot"]]


def _make_coordinator(work_status: int, *, is_online: bool = True) -> SimpleNamespace:
    device = BeatbotDeviceData(
        device_id=DEVICE_ID,
        product_id="pool-bot-x",
        product_category="pool_clean_bot",
        work_status=work_status,
        work_mode=0,
        error_code=0,
        battery_level=80,
        versions=[],
        is_online=is_online,
    )
    return SimpleNamespace(
        data={DEVICE_ID: device},
        last_update_success=True,
        runtime_data_available={DEVICE_ID},
    )


@pytest.mark.parametrize(
    ("work_status", "expected"),
    [
        (2, True),  # charging
        (3, False),  # charge_done — not actively charging
        (5, False),  # cleaning
        (0, False),  # standby
    ],
)
def test_charging_sensor_reflects_work_status(work_status: int, expected: bool) -> None:
    """is_on is True only when work_status is a charging code."""
    sensor = BeatbotChargingSensor(
        _make_coordinator(work_status), DEVICE_ID, POOL_CODES
    )

    assert sensor.is_on is expected


def test_charging_sensor_offline_unavailable() -> None:
    """An offline device reports unavailable, not a stale charging state."""
    sensor = BeatbotChargingSensor(
        _make_coordinator(2, is_online=False), DEVICE_ID, POOL_CODES
    )

    assert sensor.available is False


def test_clean_base_station_has_no_charging_state() -> None:
    """The station itself cannot charge and must not get a charging entity."""
    category = CATEGORY_MAP["clean_base_station"]

    assert CHARGING_STATUS_CODES_BY_CATEGORY[category] == set()


async def test_setup_creates_connectivity_and_supported_charging_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create charging only where valid and remove obsolete error-bit entities."""
    pool = _make_coordinator(2).data[DEVICE_ID]
    station = _make_coordinator(0).data[DEVICE_ID]
    station.device_id = "station-1"
    station.product_category = "clean_base_station"
    coordinator = SimpleNamespace(
        data={DEVICE_ID: pool, "station-1": station},
        last_update_success=True,
        runtime_data_available={DEVICE_ID, "station-1"},
    )
    entry = SimpleNamespace(
        entry_id="entry", runtime_data=SimpleNamespace(coordinator=coordinator)
    )
    obsolete_suffix = next(iter(binary_sensor_module._OBSOLETE_ERROR_ENTITY_SUFFIXES))
    registry = SimpleNamespace(async_remove=Mock())
    entries = [
        SimpleNamespace(
            domain="binary_sensor",
            unique_id=f"removed-device_{obsolete_suffix}",
            entity_id="binary_sensor.obsolete",
        ),
        SimpleNamespace(
            domain="binary_sensor",
            unique_id="device_online",
            entity_id="binary_sensor.keep",
        ),
        SimpleNamespace(
            domain="sensor",
            unique_id=f"removed-device_{obsolete_suffix}",
            entity_id="sensor.keep",
        ),
    ]
    monkeypatch.setattr(
        binary_sensor_module.er, "async_get", Mock(return_value=registry)
    )
    monkeypatch.setattr(
        binary_sensor_module.er,
        "async_entries_for_config_entry",
        Mock(return_value=entries),
    )
    added: list = []

    await binary_sensor_module.async_setup_entry(None, entry, added.extend)

    assert [type(entity) for entity in added] == [
        BeatbotOnlineSensor,
        BeatbotChargingSensor,
        BeatbotOnlineSensor,
    ]
    assert added[0].is_on is True
    registry.async_remove.assert_called_once_with("binary_sensor.obsolete")
