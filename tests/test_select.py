"""Tests for Beatbot select entities."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.beatbot import select as select_module
from custom_components.beatbot.models import BeatbotDeviceData
from custom_components.beatbot.select import BeatbotWorkModeSelect

DEVICE_ID = "test-device-1"


def _make_coordinator() -> SimpleNamespace:
    """Build a minimal coordinator carrying a work-mode capable device."""
    device = BeatbotDeviceData(
        device_id=DEVICE_ID,
        product_id="pool-bot-x",
        product_category="pool_clean_bot",
        work_status=0,
        work_mode=2,
        error_code=0,
        battery_level=80,
        versions=[],
        is_online=True,
        work_mode_options={0: "fast", 2: "custom", 7: "ai"},
    )
    coordinator = SimpleNamespace(
        data={DEVICE_ID: device},
        last_update_success=True,
        runtime_data_available={DEVICE_ID},
        api=SimpleNamespace(set_work_mode=AsyncMock()),
        async_apply_device_event=MagicMock(
            side_effect=lambda _device_id, states: setattr(
                device, "work_mode", states["select.work_mode"]
            )
        ),
        async_schedule_device_state_refresh=MagicMock(),
    )
    return coordinator


def test_work_mode_select_exposes_capability_options() -> None:
    """Work mode is exposed as a select, not a vacuum fan speed."""
    select = BeatbotWorkModeSelect(_make_coordinator(), DEVICE_ID)

    assert select.unique_id == f"{DEVICE_ID}_work_mode"
    assert select.options == ["fast", "custom", "ai"]
    assert select.current_option == "custom"


@pytest.mark.parametrize("option", ["fast", "ai"])
async def test_work_mode_select_sends_backend_label(option: str) -> None:
    """Selecting an option sends the option label to the backend.

    The backend resolves the work mode by `label` (the same string advertised
    in the capability's `configuration.options`); the integer value is no
    longer sent.
    """
    coordinator = _make_coordinator()
    select = BeatbotWorkModeSelect(coordinator, DEVICE_ID)

    await select.async_select_option(option)

    coordinator.api.set_work_mode.assert_awaited_once_with(DEVICE_ID, option)
    coordinator.async_apply_device_event.assert_called_once_with(
        DEVICE_ID, {"select.work_mode": select._option_to_value[option]}
    )
    assert select.current_option == option
    coordinator.async_schedule_device_state_refresh.assert_called_once_with(DEVICE_ID)


async def test_unknown_work_mode_raises_validation_error() -> None:
    """Reject a label the device did not advertise with a translated error."""
    coordinator = _make_coordinator()
    select = BeatbotWorkModeSelect(coordinator, DEVICE_ID)

    with pytest.raises(ServiceValidationError) as exc_info:
        await select.async_select_option("unsupported")

    coordinator.api.set_work_mode.assert_not_awaited()
    coordinator.async_apply_device_event.assert_not_called()
    coordinator.async_schedule_device_state_refresh.assert_not_called()
    assert exc_info.value.translation_domain == "beatbot"
    assert exc_info.value.translation_key == "invalid_work_mode"


async def test_setup_only_creates_selects_for_devices_with_options() -> None:
    """Skip devices that do not advertise work-mode choices."""
    coordinator = _make_coordinator()
    without_options = _make_coordinator().data[DEVICE_ID]
    without_options.device_id = "without-options"
    without_options.work_mode_options = {}
    coordinator.data["without-options"] = without_options
    entry = SimpleNamespace(runtime_data=SimpleNamespace(coordinator=coordinator))
    added: list = []

    await select_module.async_setup_entry(
        None, entry, lambda entities: added.extend(entities)
    )

    assert [entity.unique_id for entity in added] == [f"{DEVICE_ID}_work_mode"]
