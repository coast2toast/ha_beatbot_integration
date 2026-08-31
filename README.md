# Beatbot Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Quality Scale](https://img.shields.io/badge/Quality%20Scale-Silver-C0C0C0.svg)](https://developers.home-assistant.io/docs/core/integration-quality-scale/)

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

## Notable key changes from Beatbot's official integration

This community-maintained version is derived from the
[official Beatbot integration](https://github.com/Beatbot-Robotics/ha_beatbot),
with the following notable changes relative to upstream commit `b9bfe125`
(`v0.0.2`):

- Adds Home Assistant OAuth reauthentication for expired or revoked credentials
  without requiring users to delete and recreate the integration.
- Verifies the JWT account identifier (`sub`) during reauthentication and rejects
  authorization with a different Beatbot account.
- Validates replacement credentials against the regional device API before
  updating the config entry, preserving existing credentials if validation fails.
- Maps clean-base-station work status `0` to `cleaning` instead of exposing an
  unknown status.
- Adds reauthentication, account-mismatch, availability, action-error,
  status-mapping, and translation contract tests with per-module coverage gates.
- Validates this custom integration against Home Assistant 2026.8.3 while
  retaining compatibility coverage for Home Assistant 2026.2.3, and provides
  HACS-specific documentation, release notes, licensing, and attribution.

Upstream may evolve independently. The related
[Home Assistant Core contribution](https://github.com/home-assistant/core/pull/177108)
remains the proposed path toward a built-in Beatbot integration.

## Requirements

- Home Assistant 2026.2.3 or newer (GitHub Actions validates against 2026.8.3;
  compatibility is also tested against 2026.2.3)
- A supported Beatbot device associated with a Beatbot cloud account
- Home Assistant must have internet access and a valid external callback URL for OAuth
- A Beatbot account in a supported region: North America (`na`), Europe (`eu`), or mainland China (`cn`)

The integration depends on `beatbot-cloud==0.4.1`; Home Assistant installs this dependency from `manifest.json`.

## HACS and quality readiness

- **HACS custom-repository ready** — the repository includes `hacs.json`, a
  versioned integration manifest, local brand assets, a public release, and
  automated HACS Action validation.
- **Home Assistant validation** — hassfest runs with the HACS Action on pushes
  to `main`, pull requests, a daily schedule, and manual dispatch.
- **Integration Quality Scale: Silver (self-assessed)** — all Bronze and Silver rules in
  `custom_components/beatbot/quality_scale.yaml` are marked complete or exempt
  with an explanation. CI requires every non-empty integration module to exceed
  95 percent statement coverage and enforces a 96 percent aggregate floor.
  This is a community assessment, not a Home Assistant Core review or endorsement.
- **Catalog status** — installable as a HACS custom repository; inclusion in
  the default HACS catalog requires a separate submission and acceptance.

## Installation

Current release: **2026.08.31**. See [CHANGELOG.md](CHANGELOG.md) for release notes.

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

### Installation and configuration parameters

There are no manual installation parameters or YAML settings. Beatbot OAuth
supplies the account identity and service region; the integration validates
both before creating the config entry. Expired or revoked credentials are
replaced through Home Assistant's **Reauthenticate** flow. Changing to another
Beatbot account requires a separate config entry.

## Removing the integration

1. Go to **Settings > Devices & services**.
2. Open the Beatbot integration entry.
3. Select **Delete** and confirm.

Home Assistant unloads all Beatbot platforms, stops the WebSocket client, and cancels pending refresh tasks.

## Development and validation

The repository includes unit tests for OAuth setup, API handling, coordinator reconciliation, event-stream behavior, and every entity platform.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest -q \
  --cov=custom_components.beatbot \
  --cov-report=term-missing \
  --cov-fail-under=96
```

Static validation without the Home Assistant test dependencies:

```bash
python3 -m compileall -q custom_components/beatbot tests
python3 -m json.tool custom_components/beatbot/manifest.json >/dev/null
python3 -m json.tool custom_components/beatbot/strings.json >/dev/null
```

## Upstream

The implementation is based on the official Beatbot Robotics custom integration at <https://github.com/Beatbot-Robotics/ha_beatbot> and uses the official Apache-2.0 `beatbot-cloud` client. The related Home Assistant Core contribution is <https://github.com/home-assistant/core/pull/177108>.

## License and trademarks

This project is distributed under the [Apache License 2.0](LICENSE). See
[NOTICE](NOTICE) for upstream attribution. Beatbot names, product names, and
logos are trademarks of their respective owners and are used only to identify
compatible products. This is an independent community integration.
