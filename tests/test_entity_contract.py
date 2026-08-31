"""Regression tests for the public Beatbot entity contract."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

from custom_components.beatbot.api import BeatbotAuthError, BeatbotConnectionError
from custom_components.beatbot.binary_sensor import (
    BeatbotChargingSensor,
    BeatbotOnlineSensor,
)
from custom_components.beatbot.iot.category import (
    CATEGORY_MAP,
    CHARGING_STATUS_CODES_BY_CATEGORY,
    ERROR_BITS_BY_CATEGORY,
)
from custom_components.beatbot.iot.const import (
    INTERFACE_START,
    SUPPORTED_PLATFORMS,
)
from custom_components.beatbot.models import BeatbotDeviceData
from custom_components.beatbot.select import BeatbotWorkModeSelect
from custom_components.beatbot.sensor import (
    BeatbotBatterySensor,
    BeatbotErrorSensor,
    BeatbotStatusSensor,
)
from custom_components.beatbot.switch import SWITCH_DESCRIPTIONS, BeatbotSwitch
from custom_components.beatbot.vacuum import BeatbotPoolVacuum

DEVICE_ID = "test-device-1"


def _coordinator(
    *, is_online: bool = True, runtime_data_available: bool = True
) -> SimpleNamespace:
    """Build a coordinator with every currently exposed entity capability."""
    device = BeatbotDeviceData(
        device_id=DEVICE_ID,
        product_id="sblekiy3t188s9ql",
        product_category="pool_clean_bot",
        work_status=2,
        work_mode=2,
        error_code=0,
        battery_level=80,
        versions=[],
        is_online=is_online,
        work_mode_options={0: "fast", 2: "custom"},
    )
    return SimpleNamespace(
        data={DEVICE_ID: device},
        last_update_success=True,
        runtime_data_available={DEVICE_ID} if runtime_data_available else set(),
        api=SimpleNamespace(
            send_action=AsyncMock(),
            set_work_mode=AsyncMock(),
            set_switch=AsyncMock(),
        ),
        async_apply_device_event=Mock(),
        async_schedule_device_state_refresh=Mock(),
    )


def _entities(coordinator: SimpleNamespace) -> list:
    """Return one instance of every existing entity kind."""
    category = CATEGORY_MAP["pool_clean_bot"]
    return [
        BeatbotPoolVacuum(coordinator, DEVICE_ID),
        BeatbotStatusSensor(coordinator, DEVICE_ID),
        BeatbotBatterySensor(coordinator, DEVICE_ID),
        BeatbotErrorSensor(coordinator, DEVICE_ID, ERROR_BITS_BY_CATEGORY[category]),
        BeatbotOnlineSensor(coordinator, DEVICE_ID),
        BeatbotChargingSensor(
            coordinator,
            DEVICE_ID,
            CHARGING_STATUS_CODES_BY_CATEGORY[category],
        ),
        BeatbotWorkModeSelect(coordinator, DEVICE_ID),
        *(BeatbotSwitch(coordinator, DEVICE_ID, item) for item in SWITCH_DESCRIPTIONS),
    ]


def test_supported_platforms_are_unchanged() -> None:
    """Keep every custom-integration platform while Core remains sensor-only."""
    assert SUPPORTED_PLATFORMS == [
        Platform.BINARY_SENSOR,
        Platform.SELECT,
        Platform.SENSOR,
        Platform.SWITCH,
        Platform.VACUUM,
    ]


def test_secondary_diagnostics_are_disabled_by_default() -> None:
    """Avoid recording noisy or redundant diagnostic entities unless requested."""
    entities = _entities(_coordinator())
    defaults = {
        type(entity).__name__: entity.entity_registry_enabled_default
        for entity in entities
    }

    assert defaults["BeatbotStatusSensor"] is False
    assert defaults["BeatbotOnlineSensor"] is False
    assert defaults["BeatbotChargingSensor"] is False
    for primary_or_actionable in (
        "BeatbotPoolVacuum",
        "BeatbotBatterySensor",
        "BeatbotErrorSensor",
        "BeatbotWorkModeSelect",
        "BeatbotSwitch",
    ):
        assert defaults[primary_or_actionable] is True


def test_entity_unique_ids_and_translation_keys_are_unchanged() -> None:
    """Prevent infrastructure updates from migrating or renaming entities."""
    entities = _entities(_coordinator())

    assert [(entity.unique_id, entity.translation_key) for entity in entities] == [
        (DEVICE_ID, "beatbot_pool_vacuum"),
        (f"{DEVICE_ID}_status", "work_status"),
        (f"{DEVICE_ID}_battery", "battery"),
        (f"{DEVICE_ID}_error", "error"),
        (f"{DEVICE_ID}_online", "online"),
        (f"{DEVICE_ID}_charging", "charging"),
        (f"{DEVICE_ID}_work_mode", "work_mode"),
        (f"{DEVICE_ID}_child_lock", "child_lock"),
        (f"{DEVICE_ID}_voice_disturb", "voice_disturb"),
    ]


def test_offline_availability_preserves_connectivity_and_diagnostics() -> None:
    """Report offline explicitly while disabling only stateful controls."""
    coordinator = _coordinator(is_online=False)
    entities = _entities(coordinator)
    (
        vacuum,
        status,
        battery,
        error,
        online,
        charging,
        work_mode,
        child_lock,
        voice_disturb,
    ) = entities

    assert online.available
    assert online.is_on is False
    assert status.available
    assert battery.available
    assert error.available
    assert not vacuum.available
    assert not charging.available
    assert not work_mode.available
    assert not child_lock.available
    assert not voice_disturb.available


def test_removed_device_is_unavailable_without_key_error() -> None:
    """Short-circuit availability when topology changes before reload."""
    coordinator = _coordinator()
    entities = _entities(coordinator)
    coordinator.data = {}

    assert all(not entity.available for entity in entities)


def test_failed_coordinator_update_marks_all_entities_unavailable() -> None:
    """Honor coordinator health independently from device connectivity."""
    coordinator = _coordinator()
    entities = _entities(coordinator)
    coordinator.last_update_success = False

    assert all(not entity.available for entity in entities)


def test_failed_runtime_state_fetch_marks_all_entities_unavailable() -> None:
    """Do not expose stale runtime values as available after a state outage."""
    entities = _entities(_coordinator(runtime_data_available=False))

    assert all(not entity.available for entity in entities)


def test_runtime_state_availability_is_scoped_to_one_device() -> None:
    """A fresh event for one device must not revive another device's stale state."""
    coordinator = _coordinator()
    second = _coordinator().data[DEVICE_ID]
    second.device_id = "test-device-2"
    coordinator.data[second.device_id] = second
    coordinator.runtime_data_available = {DEVICE_ID}

    assert BeatbotStatusSensor(coordinator, DEVICE_ID).available
    assert not BeatbotStatusSensor(coordinator, second.device_id).available


async def test_offline_command_is_not_created() -> None:
    """Reject an offline action before constructing its API coroutine."""
    coordinator = _coordinator(is_online=False)
    vacuum = BeatbotPoolVacuum(coordinator, DEVICE_ID)

    with pytest.raises(HomeAssistantError):
        await vacuum.async_start()

    coordinator.api.send_action.assert_not_called()
    coordinator.async_schedule_device_state_refresh.assert_not_called()


async def test_online_command_is_awaited_once() -> None:
    """Keep the existing vacuum command and reconciliation behavior."""
    coordinator = _coordinator()
    vacuum = BeatbotPoolVacuum(coordinator, DEVICE_ID)

    await vacuum.async_start()

    coordinator.api.send_action.assert_awaited_once_with(DEVICE_ID, INTERFACE_START)
    coordinator.async_schedule_device_state_refresh.assert_called_once_with(DEVICE_ID)


async def test_command_errors_are_translated_for_home_assistant() -> None:
    """Convert library auth and transport failures to Home Assistant errors."""
    coordinator = _coordinator()
    coordinator.hass = object()
    coordinator._config_entry = SimpleNamespace(async_start_reauth_if_available=Mock())
    entity = BeatbotStatusSensor(coordinator, DEVICE_ID)

    with pytest.raises(HomeAssistantError) as auth_exc_info:
        await entity._async_send_command(AsyncMock(side_effect=BeatbotAuthError))

    assert not isinstance(auth_exc_info.value, ConfigEntryAuthFailed)
    assert auth_exc_info.value.translation_domain == "beatbot"
    assert auth_exc_info.value.translation_key == "control_authentication_error"
    coordinator._config_entry.async_start_reauth_if_available.assert_called_once_with(
        coordinator.hass
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await entity._async_send_command(
            AsyncMock(side_effect=BeatbotConnectionError("network"))
        )

    assert exc_info.value.translation_domain == "beatbot"
    assert exc_info.value.translation_key == "control_connection_error"


def test_device_info_exposes_registry_metadata() -> None:
    """Expose stable identifiers and all non-empty firmware channels."""
    coordinator = _coordinator()
    device = coordinator.data[DEVICE_ID]
    device.name = "AquaSense"
    device.model = "AquaSense 2 Ultra"
    device.versions = [
        SimpleNamespace(channel=1, version="1.2.3"),
        SimpleNamespace(channel=2, version=""),
    ]

    info = BeatbotStatusSensor(coordinator, DEVICE_ID).device_info

    assert info["identifiers"] == {("beatbot", DEVICE_ID)}
    assert info["name"] == "AquaSense"
    assert info["manufacturer"] == "Beatbot"
    assert info["model"] == "AquaSense 2 Ultra"
    assert info["sw_version"] == "ch1:1.2.3"


def test_device_info_falls_back_to_product_id_without_model() -> None:
    """Keep useful registry metadata when the cloud omits a marketing model."""
    coordinator = _coordinator()
    coordinator.data[DEVICE_ID].model = ""

    info = BeatbotStatusSensor(coordinator, DEVICE_ID).device_info

    assert info["model"] == "sblekiy3t188s9ql"
