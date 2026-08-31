"""Tests for Beatbot diagnostics."""

import json
from importlib.util import find_spec
from types import SimpleNamespace

from beatbot_cloud import BeatbotCapability, BeatbotDeviceData, FirmwareVersion
from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beatbot import BeatbotRuntimeData
from custom_components.beatbot import diagnostics as diagnostics_module
from custom_components.beatbot.iot.const import DOMAIN


def test_diagnostics_module_exists() -> None:
    """Provide a config-entry diagnostics module for Home Assistant."""
    assert find_spec("custom_components.beatbot.diagnostics") is not None


def test_diagnostics_function_exists() -> None:
    """Expose Home Assistant's config-entry diagnostics hook."""
    assert hasattr(diagnostics_module, "async_get_config_entry_diagnostics")


async def test_diagnostics_are_useful_and_redact_identifiers(
    hass: HomeAssistant,
) -> None:
    """Expose runtime health without account, token, device, or name identifiers."""
    device = BeatbotDeviceData(
        device_id="device-secret-123",
        product_id="S01",
        product_category="POOL_CLEANING_ROBOT",
        work_status=2,
        work_mode=3,
        error_code=0,
        battery_level=84,
        versions=[FirmwareVersion(channel=1, version="1.2.3")],
        is_online=True,
        child_lock=False,
        voice_disturb=True,
        name="Private Pool Robot Name",
        model="AquaSense 2 Ultra",
        work_mode_options={3: "Floor"},
        capabilities={
            "vacuum.battery": BeatbotCapability(
                "vacuum.battery", retrievable=True, proactively_reported=True
            )
        },
    )
    coordinator = SimpleNamespace(
        data={device.device_id: device},
        last_update_success=True,
        runtime_data_available={device.device_id},
    )
    event_task = SimpleNamespace(done=lambda: False)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="account-secret-456",
        data={
            "region": "us",
            "token": {
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "sub": "account-secret-456",
            },
        },
        version=1,
        minor_version=2,
    )
    entry.runtime_data = BeatbotRuntimeData(
        coordinator=coordinator,
        api=SimpleNamespace(),
        session=SimpleNamespace(),
        event_client=SimpleNamespace(_task=event_task),
    )

    diagnostics = await diagnostics_module.async_get_config_entry_diagnostics(
        hass, entry
    )
    serialized = json.dumps(diagnostics)

    assert diagnostics["entry"] == {
        "version": 1,
        "minor_version": 2,
        "data": {"region": "us", "token": REDACTED},
    }
    assert diagnostics["coordinator"] == {
        "last_update_success": True,
        "device_count": 1,
        "runtime_data_available_count": 1,
    }
    assert diagnostics["event_stream"] == {"running": True}
    assert diagnostics["devices"] == [
        {
            "product_id": "S01",
            "product_category": "POOL_CLEANING_ROBOT",
            "model": "AquaSense 2 Ultra",
            "work_status": 2,
            "work_mode": 3,
            "error_code": 0,
            "battery_level": 84,
            "is_online": True,
            "child_lock": False,
            "voice_disturb": True,
            "firmware_versions": [{"channel": 1, "version": "1.2.3"}],
            "work_mode_options": {3: "Floor"},
            "capabilities": {
                "vacuum.battery": {
                    "retrievable": True,
                    "proactively_reported": True,
                    "non_controllable": False,
                }
            },
        }
    ]
    for secret in (
        "access-secret",
        "refresh-secret",
        "account-secret-456",
        "device-secret-123",
        "Private Pool Robot Name",
    ):
        assert secret not in serialized
