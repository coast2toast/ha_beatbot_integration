"""Tests for Beatbot switch entities."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.beatbot import switch as switch_module
from custom_components.beatbot.iot.const import (
    INTERFACE_CHILD_LOCK,
    INTERFACE_VOICE_DISTURB,
)
from custom_components.beatbot.models import BeatbotCapability, BeatbotDeviceData
from custom_components.beatbot.switch import SWITCH_DESCRIPTIONS, BeatbotSwitch

DEVICE_ID = "base-station-1"


def _make_coordinator() -> SimpleNamespace:
    device = BeatbotDeviceData(
        device_id=DEVICE_ID,
        product_id="base-x",
        product_category="clean_base_station",
        work_status=0,
        work_mode=0,
        error_code=0,
        battery_level=0,
        versions=[],
        is_online=True,
        child_lock=True,
        voice_disturb=False,
    )
    return SimpleNamespace(
        data={DEVICE_ID: device},
        last_update_success=True,
        runtime_data_available={DEVICE_ID},
        api=SimpleNamespace(set_switch=AsyncMock()),
        async_schedule_device_state_refresh=MagicMock(),
    )


@pytest.mark.parametrize(
    ("description_index", "expected_state"),
    [(0, True), (1, False)],
)
def test_switch_reflects_device_state(
    description_index: int, expected_state: bool
) -> None:
    entity = BeatbotSwitch(
        _make_coordinator(), DEVICE_ID, SWITCH_DESCRIPTIONS[description_index]
    )

    assert entity.is_on is expected_state


@pytest.mark.parametrize(
    ("description_index", "turn_on", "interface_info", "expected_label"),
    [
        (0, True, INTERFACE_CHILD_LOCK, "on"),
        (1, False, INTERFACE_VOICE_DISTURB, "off"),
    ],
)
async def test_switch_sends_on_off_label(
    description_index: int,
    turn_on: bool,
    interface_info: str,
    expected_label: str,
) -> None:
    coordinator = _make_coordinator()
    entity = BeatbotSwitch(
        coordinator, DEVICE_ID, SWITCH_DESCRIPTIONS[description_index]
    )

    if turn_on:
        await entity.async_turn_on()
    else:
        await entity.async_turn_off()

    coordinator.api.set_switch.assert_awaited_once_with(
        DEVICE_ID, interface_info, expected_label
    )
    coordinator.async_schedule_device_state_refresh.assert_called_once_with(DEVICE_ID)


@pytest.mark.parametrize("value", [True, 1, "on"])
def test_switch_accepts_backend_enabled_representations(value: object) -> None:
    """Treat each enabled representation returned by the cloud as on."""
    coordinator = _make_coordinator()
    coordinator.data[DEVICE_ID].child_lock = value

    assert BeatbotSwitch(coordinator, DEVICE_ID, SWITCH_DESCRIPTIONS[0]).is_on


async def test_setup_only_creates_controllable_advertised_switches() -> None:
    """Do not expose missing or read-only switch capabilities as controls."""
    coordinator = _make_coordinator()
    coordinator.data[DEVICE_ID].capabilities = {
        INTERFACE_CHILD_LOCK: BeatbotCapability(
            interface_info=INTERFACE_CHILD_LOCK, non_controllable=False
        ),
        INTERFACE_VOICE_DISTURB: BeatbotCapability(
            interface_info=INTERFACE_VOICE_DISTURB, non_controllable=True
        ),
    }
    entry = SimpleNamespace(runtime_data=SimpleNamespace(coordinator=coordinator))
    added: list = []

    await switch_module.async_setup_entry(None, entry, added.extend)

    assert [entity.unique_id for entity in added] == [f"{DEVICE_ID}_child_lock"]
