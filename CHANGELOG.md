# Changelog

## 0.1.0

- HACS integration for Home Assistant 2026.10+, using HA's shared MQTT connection.
- Setup through native MQTT validation, automatic running Mosquitto discovery, gateway selection and manual SN fallback.
- English solar, grid, battery, energy and diagnostic entities.
- Explicit battery control with staged power and target SOC, and an atomic service action.
- Wire commands from the supplied working Node-RED flow, with current device power limits and telemetry freshness checks.
- Clear separation between requested settings and actual monitor telemetry; no command echo is treated as acknowledgement.
- Availability expiry, unload cleanup, redacted diagnostics and validation workflows.

Validated locally on HA 2026.10.0 and 2026.11.1. Physical device commissioning remains to be confirmed.
