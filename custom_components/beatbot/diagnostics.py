"""Diagnostics support for the Beatbot integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BeatbotConfigEntry

TO_REDACT = {
    "access_token",
    "account_id",
    "device_id",
    "id_token",
    "refresh_token",
    "sub",
    "token",
}


def _serialize_device(device: Any) -> dict[str, Any]:
    """Return useful non-identifying diagnostics for one device."""
    return {
        "product_id": device.product_id,
        "product_category": device.product_category,
        "model": device.model,
        "work_status": device.work_status,
        "work_mode": device.work_mode,
        "error_code": device.error_code,
        "battery_level": device.battery_level,
        "is_online": device.is_online,
        "child_lock": device.child_lock,
        "voice_disturb": device.voice_disturb,
        "firmware_versions": [
            {"channel": version.channel, "version": version.version}
            for version in device.versions
        ],
        "work_mode_options": dict(device.work_mode_options),
        "capabilities": {
            key: {
                "retrievable": capability.retrievable,
                "proactively_reported": capability.proactively_reported,
                "non_controllable": capability.non_controllable,
            }
            for key, capability in sorted(device.capabilities.items())
        },
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BeatbotConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a Beatbot config entry."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    task = runtime.event_client._task
    return {
        "entry": {
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "device_count": len(coordinator.data),
            "runtime_data_available_count": len(coordinator.runtime_data_available),
        },
        "event_stream": {
            "running": task is not None and not task.done(),
        },
        "devices": [
            _serialize_device(device) for _, device in sorted(coordinator.data.items())
        ],
    }
