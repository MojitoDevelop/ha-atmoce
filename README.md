# Atmoce for Home Assistant

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MojitoDevelop&repository=ha-atmoce&category=integration)
[![Latest release](https://img.shields.io/github/v/release/MojitoDevelop/ha-atmoce)](https://github.com/MojitoDevelop/ha-atmoce/releases)

Local monitoring and battery control for Atmoce solar and storage systems. Connect your gateway to Home Assistant through MQTT to track solar generation, grid import and export, battery energy and state of charge, and control charging and discharging.

[Instrukcja po polsku](README.pl.md)

## Features

- Solar, grid and battery power, battery state of charge and current power limits.
- Daily and lifetime energy counters compatible with Home Assistant's Energy dashboard.
- Battery charging, discharging, automatic operation and pause, with configurable power and target state of charge.
- Gateway discovery, selection between multiple installations and manual serial number entry.
- Setup through Home Assistant's existing MQTT connection, automatic configuration of a running official Mosquitto app, or manual broker credentials.
- English entity names, availability monitoring and diagnostic data.
- Local communication without an Atmoce cloud account.

## Requirements

- **Home Assistant 2026.10.0 or newer.** Tested on 2026.10.0 and 2026.11.1.
- HACS on HA 2026.10, or the built-in Marketplace on HA 2026.11+.
- An Atmoce gateway publishing telemetry to the same MQTT broker as Home Assistant.

Supported telemetry uses `systemTime`, `gridActivePower`, power values in kW and energy counters in kWh. Firmware using a different payload format may need additional support.

## Installation

Click **Add to HACS** above and select **Download**, then restart Home Assistant.

To add the repository manually:

1. Open HACS / Marketplace → **⋮ → Custom repositories**.
2. Add `https://github.com/MojitoDevelop/ha-atmoce`, type **Integration**.
3. Download **Atmoce** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Atmoce**.

For a manual installation, extract the release's `atmoce_mqtt.zip` into `/config/custom_components/atmoce_mqtt/`, then restart Home Assistant. The ZIP contains `manifest.json` at its root.

## Configuration

The setup form reuses the MQTT connection already configured in Home Assistant, including its stored credentials.

When MQTT is not configured, choose automatic setup to use a running official Mosquitto app and its managed credentials, or enter a broker address, port, username and password. Verified TLS is supported. Custom certificates and WebSocket connections can be configured in Home Assistant's native MQTT form. Automatic setup does not install a broker or change the gateway's MQTT settings.

Setup listens for gateways for 10 seconds and lets you select an installation. If your gateway is not listed, enter its **serial number (SN)** manually. You can add multiple gateways. Adding an integration does not send battery commands.

## Entities

Each gateway appears as a device named `Atmoce <SN>`. Entity names are in English. Home Assistant generates entity IDs according to your naming preferences.

Icons distinguish solar generation, grid import/export, battery energy, limits and settings. Status and battery control icons follow their current state; the state of charge icon follows the battery level. Icons selected manually in Home Assistant take precedence.

| Entities | Unit |
| --- | --- |
| Solar power, Grid power, Battery power | kW |
| Charge power limit, Discharge power limit | kW |
| Battery state of charge | % |
| Solar energy today / total | kWh |
| Grid import today / total | kWh |
| Grid export today / total | kWh |
| Battery charged today / total | kWh |
| Battery discharged today / total | kWh |
| Battery status, Battery operating mode, Plant status | Text status |

Status sensors display lowercase English descriptions:

| Sensor | Reported code → displayed state |
| --- | --- |
| Battery status | `1` → `charging`, `2` → `discharging`, `99` → `idle` |
| Battery operating mode | `1` → `self consumption`, `2` → `time of use`, `10` → `remote control` |
| Plant status | `0` → `normal`, `1` → `fault` |

Mappings follow the manufacturer's [MQTT protocol](https://api.library.loxone.com/downloader/file/2323/Atmoce%20Gateway%20MQTT_Protocol%20Interface%20Description_en.pdf); operating mode `10` is additionally documented in the [Modbus protocol](https://api.library.loxone.com/downloader/file/2322/Atmoce%20Gateway%20Modbus_Protocol%20Interface%20Description_en.pdf). Unsupported codes remain unknown, with the reported number available in the `raw_code` attribute. Automations use the native states `self_consumption`, `time_of_use` and `remote_control` for operating mode. An update preserves existing entity IDs and history; IDs previously ending in `_code` remain valid.

For the **Energy dashboard**, select the lifetime solar, grid import/export and battery charge/discharge counters. Power sensors use the `measurement` state class, daily energy counters use `total_increasing`, and lifetime counters use `total`.

Monitoring entities become unavailable when the MQTT connection is lost or telemetry expires. The default expiry is **180 seconds**; change it under **Configure** to match your gateway's publishing interval. Missing or invalid values remain unknown.

## Battery control

1. Set **Requested forced power** in kW.
2. Set **Requested target state of charge** in whole percent.
3. Choose **Charge**, **Discharge**, **Automatic** or **Pause** in **Requested battery control**.

Changing the number entities prepares the parameters in Home Assistant. Select a control option to apply them. Parameters are restored after a restart; battery commands are not replayed.

Charge and discharge require fresh telemetry, valid battery SOC and power within the gateway's current reported limit. An already reached target returns the battery to Automatic. Automatic and Pause remain usable with stale telemetry while MQTT is connected.

Use one active controller to send commands to a gateway, so other automations do not overwrite your settings.

### Automations

The **Atmoce: Set battery control** action sends mode, power and target SOC together:

```yaml
action: atmoce_mqtt.set_battery_control
target:
  entity_id: select.atmoce_example12345_requested_battery_control
data:
  mode: charge
  power: 3.5
  target_soc: 80
```

Replace the example entity ID with the command entity from your device. Modes are `charge`, `discharge`, `automatic` and `pause`. For charging and discharging, omitted parameters use the prepared number values. Automatic and Pause ignore power and target SOC.

### Requested settings and device readback

**Requested…** entities show commands prepared or sent by Home Assistant. They are not a confirmation that the gateway applied them. Actual mode/status descriptions and power limits come from the gateway's telemetry.

The documented MQTT interface does not provide a separate settings query or acknowledgement. Optional **Reported forced power**, **Reported target state of charge** and **Reported forced control code** sensors are disabled by default. They provide readback only when the gateway firmware includes those values in its telemetry. Otherwise they remain unknown.

## Releases and updates

Releases are numbered **vMAJOR.MINOR.PATCH**, for example **v0.1.1**. Each tag matches the version in the integration manifest. Select a release in HACS / Marketplace to install or update it, then restart Home Assistant.

Each release includes installation files in `atmoce_mqtt.zip`, a SHA-256 checksum and [release notes](CHANGELOG.md). New versions are published automatically after the tests, Hassfest and HACS validation pass. To publish a new version, update the manifest version and add a matching changelog entry, then push to `main`. Existing releases are not overwritten.

## Troubleshooting

- **Gateway not found:** check that the gateway and HA use the same broker. A gateway publishing less often than every 10 seconds may require manual SN entry.
- **Sensors unavailable:** check the MQTT connection, gateway clock, publishing interval and telemetry expiry setting.
- **Command rejected:** inspect current SOC, power limit and telemetry freshness. Unknown power limits are not replaced with an assumed rating.
- **Settings change unexpectedly:** check for other controllers sending commands to the gateway.
- **MQTT setup already in progress:** finish native MQTT setup, then return and choose **Use configured MQTT**.

The integration is tested against the real Home Assistant core with a simulated MQTT connection. Physical device commissioning remains to be confirmed. Start by checking the reported readings, then verify battery control with a modest power setting.

## Development

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements_test.txt
.venv/bin/python scripts/test.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python scripts/build_release.py
```

The included artwork comes from materials published by Atmoce; [source and export details](custom_components/atmoce_mqtt/brand/SOURCE.md). This is an independent custom integration.
