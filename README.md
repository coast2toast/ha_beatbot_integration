# Beatbot Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Quality Scale](https://img.shields.io/badge/Quality%20Scale-Gold-FFD700.svg)](https://developers.home-assistant.io/docs/core/integration-quality-scale/)

A custom Home Assistant integration for supported Beatbot cloud-connected pool cleaners and cleaning base stations.

The integration uses Beatbot OAuth 2.0 with PKCE, the `beatbot-cloud` Python client, WebSocket push events for near-real-time state, and a low-frequency cloud refresh for discovery and reconciliation.

## Features

Controls are created only when advertised by the device. Read-only state,
battery, fault, connectivity, and charging entities are derived from the
verified product category when that category defines the data:

- Vacuum entity with status and supported start, pause, and return-to-base actions
- Battery, work-status, and error sensors
- Online and charging binary sensors
- Cleaning-mode selector
- Child-lock and voice-disturb switches
- Device metadata, firmware version, and Home Assistant device-registry integration
- Dynamic device discovery and removal reconciliation

## Supported devices

Beatbot support is validated from the cloud product category and product ID, not
from the marketing name shown in the mobile app. A device must match both an
accepted category and one of the verified product IDs below.

| Cloud category | Support | Exposed functions |
| --- | --- | --- |
| `pool_clean_bot` | Supported when the product ID is verified | Vacuum state and advertised controls, battery, charging, status, errors, online state, work mode, child lock, and voice disturbance |
| `clean_base_station` | Supported when the product ID is verified | Base-station state and advertised controls, status, errors, online state, and capability-dependent controls |
| `lawn_mower` | Not currently supported | Reserved mappings exist, but this category is not accepted during discovery |

Verified cloud product IDs:

```text
sblekiy3t188s9ql
khepk01dtgj3udq0
xvwp9zj6bgsmk9tv
8fbwsy7h49c8hrzy
0sjj9a0jwq8z3ljz
s34unj9n9wfo737h
d0jf1j3bl6ql94g1
tz8vjwgcdle3w2lj
```

Marketing model names are supplied dynamically by the Beatbot cloud and appear
on the Home Assistant device. A new model may therefore be omitted until its
cloud product ID has been verified. To request support, open a GitHub issue with
the model name, product category, and product ID from redacted diagnostics. Do
not include OAuth tokens, account identifiers, device identifiers, or complete
raw cloud responses.

## Supported functions

The integration combines capability-gated controls with observational entities
defined for each verified product category:

- State vacuum with start, pause, and return-to-base actions when advertised
- Battery percentage and charging state for battery-powered categories
- Translated work-status and decoded error sensors
- Connectivity state
- Work-mode selection using the cloud-provided choices
- Child-lock and voice-disturbance switches when controllable
- Device-registry model and firmware information
- Dynamic addition and confirmed stale-device removal

Controls absent from the device's cloud capability list are intentionally not
created. Read-only vacuum state, status, error, connectivity, battery, and
charging entities are category-derived where applicable and become unavailable
when their source data is not fresh.

To limit recorder noise and duplicate status surfaces, the detailed work-status,
online-connectivity, and charging binary sensors are disabled by default for
new entity registrations. Enable any of them from **Settings > Devices &
services > Entities** when they are useful for a dashboard or automation.

## Data updates

- A WebSocket connection provides near-real-time property, online-status, and
  device-topology events.
- Every 10 minutes, a full cloud refresh reconciles devices and recovers state
  changes that may have been missed while the WebSocket was disconnected.
- Five seconds after a successful control command, the integration fetches that
  device's state to avoid reading the cloud before the command has settled.
- A newly added or removed device schedules a config-entry reload so all entity
  platforms reflect the new topology.
- A device missing from three consecutive successful full discoveries is
  removed from this config entry. Failed cloud requests do not count as misses.
- Runtime freshness is tracked per device. Entities become unavailable when
  their device data is stale and recover only after fresh data arrives for that
  device.

## Use cases

- Show cleaning state, battery, connectivity, and faults on a pool dashboard.
- Notify the household when the cleaner reports a fault or finishes charging.
- Start a cleaning run on a schedule only when the cleaner is online.
- Coordinate child lock or voice disturbance with household routines.
- Monitor base-station cleaning and maintenance notices.

## Automation examples

Replace the example entity IDs with the IDs created for your device.

Notify when Beatbot reports an error:

```yaml
automation:
  - alias: Beatbot fault notification
    triggers:
      - trigger: state
        entity_id: sensor.your_beatbot_error
    conditions:
      - condition: template
        value_template: >-
          {{ trigger.to_state.state not in ['none', 'unknown', 'unavailable'] }}
    actions:
      - action: persistent_notification.create
        data:
          title: Beatbot needs attention
          message: >-
            Beatbot reported {{ trigger.to_state.state }}.
```

Start cleaning only while the device is online:

```yaml
automation:
  - alias: Start scheduled Beatbot cleaning
    triggers:
      - trigger: time
        at: "09:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.your_beatbot_online
        state: "on"
    actions:
      - action: vacuum.start
        target:
          entity_id: vacuum.your_beatbot
```

## Known limitations

- Operation is cloud-only; there is no local control path when Beatbot's cloud
  service or the internet connection is unavailable.
- OAuth setup requires a callback URL reachable by the browser completing
  authorization; a reachable Home Assistant URL or My Home Assistant can supply it.
- Only North America (`na`), Europe (`eu`), and mainland China (`cn`) regions
  are recognized.
- New devices require a verified product category and product ID before entities
  are created.
- Entity and action availability depends on capabilities advertised by the
  individual device. Features present only in the Beatbot app are not inferred.
- Push events are normally near real time, but reconciliation after a missed
  event can take until the next 10-minute full refresh.
- The integration relies on Beatbot cloud behavior that may change independently
  of this project.

## Troubleshooting

### Beatbot does not appear when adding an integration

Confirm that HACS downloaded `2026.08.31.2` or newer, restart Home Assistant,
and clear the browser cache before searching for **Beatbot** again.

### OAuth callback, rejection, or timeout

Verify that the browser completing authorization can reach Home Assistant, or
enable My Home Assistant to provide the callback. Start the flow again and
complete authorization in the same browser session. OAuth tokens and callback
contents must not be pasted into an issue or chat.

### Unsupported or unknown region

The access token must contain one of the supported region claims: `na`, `eu`, or
`cn`. Confirm that the Beatbot account and device use the expected regional app.
The integration does not fall back to another regional service.

### Reauthentication says the account is wrong

Use the same Beatbot account that originally created the Home Assistant config
entry. Changing accounts requires a separate config entry; reauthentication
will not silently replace the account identity.

### A device is missing

Download redacted diagnostics and compare its product category and product ID
with the supported-device list above. Capability-dependent entities may be
absent even when the device itself is supported.

### Entities are unavailable or updates are delayed

Check Home Assistant's internet access and **Settings > System > Logs** for
`beatbot`. During a cloud outage, stale runtime entities intentionally become
unavailable. They recover when fresh data arrives through WebSocket or the full
refresh.

### Downloading diagnostics

Open **Settings > Devices & services > Beatbot**, use the config entry's
three-dot menu, and select **Download diagnostics**. Review the output before
sharing it; the integration redacts OAuth and account identifiers and omits
unique device IDs and device names.

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
- Home Assistant must have internet access, and the authorizing browser must be
  able to reach the callback through Home Assistant directly or My Home Assistant
- A Beatbot account in a supported region: North America (`na`), Europe (`eu`), or mainland China (`cn`)

The integration depends on `beatbot-cloud==0.4.1`; Home Assistant installs this dependency from `manifest.json`.

## HACS and quality readiness

- **HACS custom-repository ready** — the repository includes `hacs.json`, a
  versioned integration manifest, local brand assets, a public release, and
  automated HACS Action validation.
- **Home Assistant validation** — hassfest runs with the HACS Action on pushes
  to `main`, pull requests, a daily schedule, and manual dispatch.
- **Integration Quality Scale: Gold (self-assessed)** — all Bronze, Silver, and Gold rules in
  `custom_components/beatbot/quality_scale.yaml` are marked complete or exempt
  with an explanation. CI requires every non-empty integration module to exceed
  95 percent statement coverage and enforces a 96 percent aggregate floor.
  This is a community assessment, not a Home Assistant Core review or endorsement.
- **Catalog status** — installable as a HACS custom repository; inclusion in
  the default HACS catalog requires a separate submission and acceptance.

## Installation

Current release: **2026.08.31.3**. See [CHANGELOG.md](CHANGELOG.md) for release notes.

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
