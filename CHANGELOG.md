# Changelog

## 0.1.3

- Show Battery status, Battery operating mode and Plant status as lowercase English text instead of numeric codes.
- Preserve existing entity IDs and history, with the reported status number available as `raw_code`.
- Leave unsupported or invalid status codes unknown instead of assigning a misleading description.

## 0.1.2

- Use the white ATMOCE wordmark on the coral gradient as the integration icon.
- Keep the plain wordmark for wide logos and remove the obsolete emblem artwork.

## 0.1.1

- Use the original Atmoce emblem and wordmark, with light and dark theme assets.
- Display the integration as **Atmoce** in Home Assistant and HACS.
- Provide installation, configuration and battery control documentation focused on the integration.
- Remove the Device time sensor and clean up its registry entry when upgrading.
- Publish numbered releases with a matching manifest version, installation ZIP and SHA-256 checksum after validation passes.

## 0.1.0

- Local solar, grid and battery monitoring for Home Assistant 2026.10+.
- MQTT setup, gateway discovery and manual serial number configuration.
- English entities and Energy dashboard counters.
- Battery control with power and target SOC settings, current device limits and telemetry freshness checks.
- Separate requested settings from device readback, with diagnostic data and availability monitoring.
