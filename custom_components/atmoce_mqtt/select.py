"""Explicit battery commands, with local intent separated from device telemetry."""

from typing import Any

import probatio as vol
from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_POWER, CONF_TARGET_SOC, CONTROL_OPTIONS, DOMAIN
from .entity import AtmoceEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AtmoceControl(entry.runtime_data)])
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "set_battery_control",
        entity_domain="select",
        schema={
            vol.Required("mode"): vol.In(CONTROL_OPTIONS),
            vol.Optional("power"): vol.Coerce(float),
            vol.Optional("target_soc"): vol.Coerce(float),
        },
        func="async_set_battery_control",
    )


class AtmoceControl(AtmoceEntity, SelectEntity):
    """The last command sent by this HA instance; never an acknowledgement."""

    _attr_translation_key = "requested_battery_control"
    _attr_options = list(CONTROL_OPTIONS)

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "requested_battery_control")

    @property
    def available(self) -> bool:
        # Automatic/Pause must remain usable when device telemetry is stale.
        return mqtt.is_connected(self.hass)

    @property
    def current_option(self) -> str | None:
        if self.coordinator.last_command is None:
            return None
        value = self.coordinator.last_command["batteryForcedControl"]
        return next(
            (key for key, code in CONTROL_OPTIONS.items() if code == value), None
        )

    async def async_select_option(self, option: str) -> None:
        await self.async_set_battery_control(option)

    async def async_set_battery_control(
        self, mode: str, power: float | None = None, target_soc: float | None = None
    ) -> None:
        await self.coordinator.async_control(
            mode,
            self.coordinator.staged.get(CONF_POWER) if power is None else power,
            self.coordinator.staged.get(CONF_TARGET_SOC)
            if target_soc is None
            else target_soc,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "value_source": "home_assistant",
            "device_acknowledgement": "not_available_in_documented_mqtt_protocol",
            "last_command": self.coordinator.last_command,
            "last_command_time": self.coordinator.last_command_time,
        }
