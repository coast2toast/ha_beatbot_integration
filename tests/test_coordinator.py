"""Tests for the Beatbot coordinator (productId allow-list gating)."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.beatbot.api import BeatbotAuthError, BeatbotConnectionError
from custom_components.beatbot.coordinator import BeatbotCoordinator
from custom_components.beatbot.models import BeatbotDeviceData

SUPPORTED_PRODUCT = "sblekiy3t188s9ql"


def _entry() -> SimpleNamespace:
    return SimpleNamespace(entry_id="entry", async_on_unload=Mock())


def _device(device_id: str, product_id: str) -> BeatbotDeviceData:
    return BeatbotDeviceData(
        device_id=device_id,
        product_id=product_id,
        product_category="pool_clean_bot",
        work_status=0,
        work_mode=0,
        error_code=0,
        battery_level=80,
        versions=[],
        is_online=True,
    )


async def test_coordinator_only_keeps_supported_products(hass: HomeAssistant) -> None:
    """Devices whose productId is not on the allow-list are dropped."""
    supported = _device("dev-supported", SUPPORTED_PRODUCT)
    unsupported = _device("dev-unsupported", "other-product-id")
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[supported, unsupported]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api)

    data = await coordinator._async_update_data()

    assert "dev-supported" in data
    assert "dev-unsupported" not in data
    # Batch state endpoint still runs; unsupported device's state is simply ignored.
    api.get_device_states.assert_awaited_once()


async def test_coordinator_auth_failure_requests_reauth(
    hass: HomeAssistant,
) -> None:
    """Auth failures during first refresh become ConfigEntryAuthFailed."""
    api = SimpleNamespace(
        get_devices=AsyncMock(side_effect=BeatbotAuthError),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_connection_failure_is_retryable(
    hass: HomeAssistant,
) -> None:
    """Connection failures during first refresh remain retryable setup failures."""
    api = SimpleNamespace(
        get_devices=AsyncMock(side_effect=BeatbotConnectionError),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_discovery_failure_clears_all_runtime_freshness_before_event(
    hass: HomeAssistant,
) -> None:
    """A later event must revive only its own device after discovery fails."""
    first = _device("dev-1", SUPPORTED_PRODUCT)
    second = _device("dev-2", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(side_effect=BeatbotConnectionError("offline")),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api)
    coordinator.async_set_updated_data({"dev-1": first, "dev-2": second})
    coordinator.runtime_data_available = {"dev-1", "dev-2"}

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    coordinator.async_apply_device_event("dev-1", {"vacuum.battery": 42})

    assert coordinator.runtime_data_available == {"dev-1"}


async def test_state_service_logs_one_outage_and_one_recovery(
    hass: HomeAssistant, caplog
) -> None:
    """Repeated state failures must not spam logs and recovery is announced once."""
    device = _device("dev-supported", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[device]),
        get_device_states=AsyncMock(
            side_effect=[
                BeatbotConnectionError,
                BeatbotConnectionError,
                {"dev-supported": {"states": {}, "is_online": True}},
            ]
        ),
    )
    coordinator = BeatbotCoordinator(hass, api)

    with caplog.at_level(logging.INFO, logger="custom_components.beatbot.coordinator"):
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        await coordinator._async_update_data()

    assert caplog.messages.count("Beatbot state service is unavailable") == 1
    assert caplog.messages.count("Beatbot state service is available again") == 1
    assert coordinator.runtime_data_available == {"dev-supported"}


async def test_coordinator_empty_allow_list_drops_everything(
    hass: HomeAssistant, monkeypatch
) -> None:
    """With an empty allow-list no device is retained."""
    from custom_components.beatbot import coordinator as coord_mod

    monkeypatch.setattr(coord_mod, "SUPPORTED_PRODUCT_IDS", set())
    supported = _device("dev-supported", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[supported]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api)

    data = await coordinator._async_update_data()

    assert data == {}


async def test_device_event_overlays_state_without_resetting_poll(
    hass: HomeAssistant,
    caplog,
) -> None:
    """A push updates the existing device and only notifies listeners."""
    coordinator = BeatbotCoordinator(hass, SimpleNamespace())
    device = _device("dev-1", SUPPORTED_PRODUCT)
    coordinator.async_set_updated_data({"dev-1": device})
    listener = Mock()
    remove_listener = coordinator.async_add_listener(listener)
    next_poll = coordinator._unsub_refresh
    coordinator.last_update_success = False

    with caplog.at_level(logging.INFO, logger="custom_components.beatbot.coordinator"):
        coordinator.async_apply_device_event(
            "dev-1", {"vacuum.battery": 42}, is_online=False
        )

    assert device.battery_level == 42
    assert device.is_online is False
    assert "source=websocket" in caplog.text
    assert "interfaceInfo=vacuum.battery, old=80, new=42" in caplog.text
    assert "interfaceInfo=online, old=True, new=False" in caplog.text
    assert coordinator.last_update_success
    assert coordinator.runtime_data_available == {"dev-1"}
    assert coordinator._unsub_refresh is next_poll
    listener.assert_called_once()
    remove_listener()


async def test_device_event_ignores_unknown_device(hass: HomeAssistant) -> None:
    coordinator = BeatbotCoordinator(hass, SimpleNamespace())
    coordinator.async_set_updated_data({})

    coordinator.async_apply_device_event(
        "unknown", {"vacuum.battery": 42}, is_online=False
    )

    assert coordinator.data == {}


async def test_post_control_refresh_fetches_only_target_device(
    hass: HomeAssistant, monkeypatch, caplog
) -> None:
    """A delayed fallback GET applies state for the controlled device."""
    from custom_components.beatbot import coordinator as coord_mod

    monkeypatch.setattr(coord_mod, "POST_CONTROL_REFRESH_DELAY", 0)
    device = _device("dev-1", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_device_state=AsyncMock(
            return_value={
                "states": {"vacuum.state": 5},
                "is_online": True,
            }
        )
    )
    coordinator = BeatbotCoordinator(hass, api)
    coordinator.async_set_updated_data({"dev-1": device})

    with caplog.at_level(logging.INFO, logger="custom_components.beatbot.coordinator"):
        coordinator.async_schedule_device_state_refresh("dev-1")
        task = coordinator._refresh_tasks["dev-1"]
        await task

    api.get_device_state.assert_awaited_once_with("dev-1")
    assert device.work_status == 5
    assert "source=post_control" in caplog.text
    assert "states={'vacuum.state': 5}" in caplog.text
    assert "interfaceInfo=vacuum.state, old=0, new=5" in caplog.text
    assert coordinator._refresh_tasks == {}
    assert coordinator.runtime_data_available == {"dev-1"}


async def test_post_control_refresh_debounces_per_device(
    hass: HomeAssistant,
) -> None:
    """A later command cancels the older pending refresh for that device."""
    coordinator = BeatbotCoordinator(hass, SimpleNamespace())
    started = asyncio.Event()
    release = asyncio.Event()

    async def _refresh(_device_id: str) -> None:
        started.set()
        await release.wait()

    refresh = AsyncMock(side_effect=_refresh)
    coordinator.async_refresh_device_state = refresh

    coordinator.async_schedule_device_state_refresh("dev-1")
    first = coordinator._refresh_tasks["dev-1"]
    await started.wait()
    coordinator.async_schedule_device_state_refresh("dev-1")
    second = coordinator._refresh_tasks["dev-1"]
    release.set()
    await second
    await asyncio.gather(first, return_exceptions=True)

    assert first.cancelled()
    assert refresh.await_count == 2
    refresh.assert_awaited_with("dev-1")
    assert coordinator._refresh_tasks == {}


async def test_cancel_pending_post_control_refreshes(
    hass: HomeAssistant,
) -> None:
    """Unload cancellation prevents delayed requests from outliving the API."""
    coordinator = BeatbotCoordinator(hass, SimpleNamespace())

    coordinator.async_schedule_device_state_refresh("dev-1")
    coordinator.async_schedule_device_state_refresh("dev-2")
    tasks = list(coordinator._refresh_tasks.values())

    coordinator.async_cancel_pending_refreshes()
    await asyncio.gather(*tasks, return_exceptions=True)

    assert all(task.cancelled() for task in tasks)
    assert coordinator._refresh_tasks == {}


async def test_poll_keeps_device_until_three_successful_discovery_misses(
    hass: HomeAssistant,
) -> None:
    device = _device("dev-1", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({"dev-1": device})
    coordinator._remove_device_from_registries = Mock()
    coordinator._schedule_entry_reload = Mock()

    first = await coordinator._async_update_data()
    second = await coordinator._async_update_data()

    assert first == {"dev-1": device}
    assert second == {"dev-1": device}
    coordinator._remove_device_from_registries.assert_not_called()
    coordinator._schedule_entry_reload.assert_not_called()

    third = await coordinator._async_update_data()

    assert third == {"dev-1": device}
    coordinator._remove_device_from_registries.assert_called_once_with("dev-1")
    coordinator._schedule_entry_reload.assert_called_once()


async def test_poll_missing_counter_resets_when_device_returns(
    hass: HomeAssistant,
) -> None:
    device = _device("dev-1", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(side_effect=[[], [device], [], []]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({"dev-1": device})
    coordinator._remove_device_from_registries = Mock()
    coordinator._schedule_entry_reload = Mock()

    for _ in range(4):
        await coordinator._async_update_data()

    coordinator._remove_device_from_registries.assert_not_called()
    coordinator._schedule_entry_reload.assert_not_called()


async def test_poll_new_device_schedules_platform_reload(
    hass: HomeAssistant,
) -> None:
    device = _device("dev-new", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[device]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({})
    coordinator._schedule_entry_reload = Mock()

    data = await coordinator._async_update_data()

    assert data == {"dev-new": device}
    coordinator._schedule_entry_reload.assert_called_once()


async def test_initial_poll_does_not_reload_discovered_devices(
    hass: HomeAssistant,
) -> None:
    """Do not reload platforms for devices found during initial setup."""
    device = _device("dev-new", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[device]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator._registered_device_ids = Mock(return_value=set())
    coordinator._schedule_entry_reload = Mock()

    data = await coordinator._async_update_data()

    assert data == {"dev-new": device}
    coordinator._schedule_entry_reload.assert_not_called()


async def test_poll_preserves_state_missing_from_batch(
    hass: HomeAssistant,
) -> None:
    """Keep runtime values when discovery returns no state for a device."""
    previous = _device("dev-1", SUPPORTED_PRODUCT)
    previous.work_status = 5
    previous.work_mode = 2
    previous.error_code = 4
    previous.battery_level = 42
    previous.is_online = False
    previous.child_lock = True
    previous.voice_disturb = True
    discovered = _device("dev-1", SUPPORTED_PRODUCT)
    discovered.name = "Updated name"
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[discovered]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({"dev-1": previous})

    data = await coordinator._async_update_data()

    assert data["dev-1"].name == "Updated name"
    assert data["dev-1"].work_status == 5
    assert data["dev-1"].work_mode == 2
    assert data["dev-1"].error_code == 4
    assert data["dev-1"].battery_level == 42
    assert data["dev-1"].is_online is False
    assert data["dev-1"].child_lock is True
    assert data["dev-1"].voice_disturb is True


async def test_poll_preserves_state_when_batch_request_fails(
    hass: HomeAssistant,
) -> None:
    """Keep last-known values during a best-effort state request failure."""
    previous = _device("dev-1", SUPPORTED_PRODUCT)
    previous.battery_level = 42
    previous.work_status = 5
    discovered = _device("dev-1", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[discovered]),
        get_device_states=AsyncMock(side_effect=BeatbotConnectionError("offline")),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({"dev-1": previous})

    data = await coordinator._async_update_data()

    assert data["dev-1"].battery_level == 42
    assert data["dev-1"].work_status == 5
    assert coordinator.runtime_data_available == set()


async def test_poll_overlays_partial_state_on_previous_values(
    hass: HomeAssistant,
) -> None:
    """Update only fields present in a partial batch response."""
    previous = _device("dev-1", SUPPORTED_PRODUCT)
    previous.work_status = 5
    previous.battery_level = 42
    discovered = _device("dev-1", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[discovered]),
        get_device_states=AsyncMock(
            return_value={"dev-1": {"states": {"vacuum.battery": 75}}}
        ),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({"dev-1": previous})

    data = await coordinator._async_update_data()

    assert data["dev-1"].work_status == 5
    assert data["dev-1"].battery_level == 75


async def test_batch_runtime_availability_is_scoped_per_device(
    hass: HomeAssistant,
) -> None:
    """A partial successful batch refreshes only devices present in its response."""
    first = _device("dev-1", SUPPORTED_PRODUCT)
    second = _device("dev-2", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[first, second]),
        get_device_states=AsyncMock(
            return_value={"dev-1": {"states": {}, "is_online": True}}
        ),
    )
    coordinator = BeatbotCoordinator(hass, api)

    await coordinator._async_update_data()

    assert coordinator.runtime_data_available == {"dev-1"}


async def test_poll_removes_registry_only_stale_device_after_three_misses(
    hass: HomeAssistant,
) -> None:
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api, _entry())
    coordinator.async_set_updated_data({})
    coordinator._registered_device_ids = Mock(return_value={"dev-stale"})
    coordinator._remove_device_from_registries = Mock()
    coordinator._schedule_entry_reload = Mock()

    await coordinator._async_update_data()
    await coordinator._async_update_data()
    coordinator._remove_device_from_registries.assert_not_called()

    await coordinator._async_update_data()

    coordinator._remove_device_from_registries.assert_called_once_with("dev-stale")
    coordinator._schedule_entry_reload.assert_called_once()


def test_registry_removal_detaches_only_this_config_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve a device shared by another config entry."""
    from custom_components.beatbot import coordinator as coord_mod

    registry_device = SimpleNamespace(
        id="registry-device",
        identifiers={(coord_mod.DOMAIN, "dev-1"), ("other", "shared")},
    )
    device_registry = SimpleNamespace(
        async_get_device=Mock(return_value=registry_device),
        async_update_device=Mock(),
    )
    entity_registry = SimpleNamespace(async_remove=Mock())
    monkeypatch.setattr(coord_mod.dr, "async_get", Mock(return_value=device_registry))
    monkeypatch.setattr(coord_mod.er, "async_get", Mock(return_value=entity_registry))
    monkeypatch.setattr(
        coord_mod.er,
        "async_entries_for_device",
        Mock(
            return_value=[
                SimpleNamespace(config_entry_id="entry", entity_id="sensor.beatbot"),
                SimpleNamespace(config_entry_id="other", entity_id="sensor.shared"),
            ]
        ),
    )
    coordinator = BeatbotCoordinator(hass, SimpleNamespace(), _entry())

    coordinator._remove_device_from_registries("dev-1")

    device_registry.async_get_device.assert_called_once_with(
        identifiers={(coord_mod.DOMAIN, "dev-1")}
    )
    entity_registry.async_remove.assert_called_once_with("sensor.beatbot")
    device_registry.async_update_device.assert_called_once_with(
        "registry-device", remove_config_entry_id="entry"
    )


def test_entry_reload_is_scheduled_once(hass: HomeAssistant) -> None:
    """Use Home Assistant's scheduler and coalesce topology reloads."""
    hass.config_entries.async_schedule_reload = Mock()
    coordinator = BeatbotCoordinator(hass, SimpleNamespace(), _entry())

    coordinator._schedule_entry_reload()
    coordinator._schedule_entry_reload()

    hass.config_entries.async_schedule_reload.assert_called_once_with("entry")


async def test_unknown_product_category_is_logged_and_skipped(
    hass: HomeAssistant, caplog
) -> None:
    """Explain why devices from unsupported product lines do not appear."""
    device = _device("dev-unknown", SUPPORTED_PRODUCT)
    device.product_category = "lawn_mower"
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[device]),
        get_device_states=AsyncMock(return_value={}),
    )
    coordinator = BeatbotCoordinator(hass, api)

    with caplog.at_level(logging.INFO, logger="custom_components.beatbot.coordinator"):
        data = await coordinator._async_update_data()

    assert data == {}
    assert "product category 'lawn_mower' is not supported" in caplog.text


async def test_state_auth_failure_requests_reauthentication(
    hass: HomeAssistant,
) -> None:
    """Escalate auth failure and clear freshness before any later event."""
    first = _device("dev-1", SUPPORTED_PRODUCT)
    second = _device("dev-2", SUPPORTED_PRODUCT)
    api = SimpleNamespace(
        get_devices=AsyncMock(return_value=[first, second]),
        get_device_states=AsyncMock(side_effect=BeatbotAuthError),
    )
    coordinator = BeatbotCoordinator(hass, api)
    coordinator.async_set_updated_data({"dev-1": first, "dev-2": second})
    coordinator.runtime_data_available = {"dev-1", "dev-2"}

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()

    coordinator.async_apply_device_event("dev-1", {"vacuum.battery": 42})

    assert coordinator.runtime_data_available == {"dev-1"}


def test_registered_device_ids_filters_registry_identifiers(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return only Beatbot identifiers tied to this config entry."""
    from custom_components.beatbot import coordinator as coord_mod

    coordinator = BeatbotCoordinator(hass, SimpleNamespace())
    assert coordinator._registered_device_ids() == set()

    registry = object()
    monkeypatch.setattr(coord_mod.dr, "async_get", Mock(return_value=registry))
    monkeypatch.setattr(
        coord_mod.dr,
        "async_entries_for_config_entry",
        Mock(
            return_value=[
                SimpleNamespace(identifiers={(coord_mod.DOMAIN, "dev-1")}),
                SimpleNamespace(identifiers={("other", "dev-2")}),
            ]
        ),
    )
    coordinator = BeatbotCoordinator(hass, SimpleNamespace(), _entry())

    assert coordinator._registered_device_ids() == {"dev-1"}


def test_registry_and_reload_guards_are_noops(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not touch registries or reload without a usable entry/device."""
    from custom_components.beatbot import coordinator as coord_mod

    coordinator = BeatbotCoordinator(hass, SimpleNamespace())
    coordinator._remove_device_from_registries("dev-1")
    coordinator._schedule_entry_reload()

    device_registry = SimpleNamespace(async_get_device=Mock(return_value=None))
    monkeypatch.setattr(coord_mod.dr, "async_get", Mock(return_value=device_registry))
    coordinator = BeatbotCoordinator(hass, SimpleNamespace(), _entry())
    coordinator._remove_device_from_registries("dev-1")

    device_registry.async_get_device.assert_called_once()


async def test_single_device_refresh_connection_and_missing_device_paths(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep refresh failures best-effort and ignore removed target devices."""
    from custom_components.beatbot import coordinator as coord_mod

    monkeypatch.setattr(coord_mod, "POST_CONTROL_REFRESH_DELAY", 0)
    api = SimpleNamespace(
        get_device_state=AsyncMock(
            side_effect=[
                BeatbotConnectionError("offline"),
                {"states": {}, "is_online": True},
            ]
        )
    )
    coordinator = BeatbotCoordinator(hass, api)
    coordinator.async_set_updated_data({})

    await coordinator.async_refresh_device_state("dev-1")
    await coordinator.async_refresh_device_state("dev-1")

    assert api.get_device_state.await_count == 2
    assert not coordinator.runtime_data_available


async def test_scheduled_refresh_auth_failure_starts_reauthentication(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Convert delayed refresh auth failures into a config-entry reauth flow."""
    from custom_components.beatbot import coordinator as coord_mod

    monkeypatch.setattr(coord_mod, "POST_CONTROL_REFRESH_DELAY", 0)
    entry = _entry()
    entry.async_start_reauth_if_available = Mock()
    api = SimpleNamespace(get_device_state=AsyncMock(side_effect=BeatbotAuthError))
    coordinator = BeatbotCoordinator(hass, api, entry)
    coordinator.async_set_updated_data({"dev-1": _device("dev-1", SUPPORTED_PRODUCT)})

    coordinator.async_schedule_device_state_refresh("dev-1")
    await coordinator._refresh_tasks["dev-1"]

    entry.async_start_reauth_if_available.assert_called_once_with(hass)


def test_unknown_state_field_is_ignored() -> None:
    """Ignore cloud fields that are not mapped to the integration model."""
    device = _device("dev-1", SUPPORTED_PRODUCT)

    BeatbotCoordinator._apply_state_with_logging(
        "dev-1", device, {"unknown.field": 123}, None, source="batch"
    )

    assert device.battery_level == 80
