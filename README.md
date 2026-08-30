# Beatbot Home Assistant Integration

A custom Home Assistant integration for supported Beatbot cloud-connected pool cleaners and cleaning base stations.

The integration uses Beatbot OAuth 2.0 with PKCE, the `beatbot-cloud` Python client, WebSocket push events for near-real-time state, and a low-frequency cloud refresh for discovery and reconciliation.

## Features

Entities are created only when the device and its advertised cloud capabilities support them:

- Vacuum entity with status and supported start, pause, and return-to-base actions
- Battery, work-status, and error sensors
- Online and charging binary sensors
- Cleaning-mode selector
- Child-lock and voice-disturb switches
- Device metadata, firmware version, and Home Assistant device-registry integration
- Dynamic device discovery and removal reconciliation

## Requirements

- Home Assistant 2026.7.0 or newer
- A supported Beatbot device associated with a Beatbot cloud account
- Home Assistant must have internet access and a valid external callback URL for OAuth
- A Beatbot account in a supported region: North America (`na`), Europe (`eu`), or mainland China (`cn`)

The integration depends on `beatbot-cloud==0.4.1`; Home Assistant installs this dependency from `manifest.json`.

## Installation

### HACS custom repository

1. Open HACS in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add this repository as an **Integration** repository.
5. Download **Beatbot** and restart Home Assistant.

### Manual installation

1. Copy `custom_components/beatbot` into the `custom_components` directory in your Home Assistant configuration directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & services**.
2. Select **Add integration**.
3. Search for **Beatbot**.
4. Follow the Beatbot authorization link and approve Home Assistant access.
5. Return to Home Assistant after authorization completes.

The access token must contain an account identifier (`sub`) and a supported `region` claim. The account identifier prevents duplicate configuration entries. The integration does not silently fall back to another region.

## Removing the integration

1. Go to **Settings > Devices & services**.
2. Open the Beatbot integration entry.
3. Select **Delete** and confirm.

Home Assistant unloads all Beatbot platforms, stops the WebSocket client, and cancels pending refresh tasks.

## Development and validation

The repository includes unit tests for OAuth setup, API handling, coordinator reconciliation, event-stream behavior, and every entity platform.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python \
  "homeassistant==2026.8.3" \
  "pytest-homeassistant-custom-component==0.13.361"
.venv/bin/python -m pytest -q
```

Static validation without the Home Assistant test dependencies:

```bash
python3 -m compileall -q custom_components/beatbot tests
python3 -m json.tool custom_components/beatbot/manifest.json >/dev/null
python3 -m json.tool custom_components/beatbot/strings.json >/dev/null
```

## Upstream

The implementation is based on the official Beatbot Robotics custom integration at <https://github.com/Beatbot-Robotics/ha_beatbot> and uses the official Apache-2.0 `beatbot-cloud` client. The related Home Assistant Core contribution is <https://github.com/home-assistant/core/pull/177108>.
