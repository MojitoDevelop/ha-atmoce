"""Diagnostics contain parsed numeric telemetry only, with identity redacted."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .protocol import number
from .sensor import DESCRIPTIONS


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    coordinator = entry.runtime_data
    return {
        "serial": "**REDACTED**",
        "available": coordinator.last_update_success,
        "expire_after": coordinator.expire_after,
        "telemetry": {
            key: value
            for key, value in coordinator.data.items()
            if key in {description.key for description in DESCRIPTIONS}
            and number(value) is not None
        },
        "last_command": coordinator.last_command,
    }
