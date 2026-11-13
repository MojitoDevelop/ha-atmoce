"""Local command arguments: persisted, staged, and applied only on a command."""

import math
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_POWER, CONF_TARGET_SOC
from .entity import AtmoceEntity


@dataclass(frozen=True, kw_only=True)
class AtmoceNumberDescription(NumberEntityDescription):
    """A staged default, deliberately not presented as device readback."""

    default: float


DESCRIPTIONS = (
    AtmoceNumberDescription(
        key=CONF_POWER,
        translation_key=CONF_POWER,
        default=1,
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0.01,
        native_max_value=1000,
        native_step=0.01,
    ),
    AtmoceNumberDescription(
        key=CONF_TARGET_SOC,
        translation_key=CONF_TARGET_SOC,
        default=100,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        AtmoceNumber(entry.runtime_data, description) for description in DESCRIPTIONS
    )


class AtmoceNumber(AtmoceEntity, RestoreNumber):
    """Stage an argument without sending a command or resuming on restart."""

    entity_description: AtmoceNumberDescription
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, description: AtmoceNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_native_value = description.default

    @property
    def available(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (
            previous := await self.async_get_last_number_data()
        ) and previous.native_value is not None:
            value = previous.native_value
            if (
                math.isfinite(value)
                and self.native_min_value <= value <= self.native_max_value
            ):
                self._attr_native_value = value
        self.coordinator.staged[self.entity_description.key] = self.native_value

    async def async_set_native_value(self, value: float) -> None:
        if (
            not math.isfinite(value)
            or not self.native_min_value <= value <= self.native_max_value
            or (
                self.entity_description.key == CONF_TARGET_SOC
                and not float(value).is_integer()
            )
        ):
            raise ServiceValidationError("Invalid command argument")
        self._attr_native_value = value
        self.coordinator.staged[self.entity_description.key] = value
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "value_source": "home_assistant",
            "applied_by": "battery_control_command",
        }
