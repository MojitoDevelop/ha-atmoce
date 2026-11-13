"""Atmoce sensors with native HA units, device classes and statistics."""

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import AtmoceEntity
from .protocol import number


@dataclass(frozen=True, kw_only=True)
class AtmoceSensorDescription(SensorEntityDescription):
    """Field constraints that keep invalid samples out of statistics."""

    nonnegative: bool = False
    maximum: float | None = None
    integer: bool = False


POWER_FIELDS = {
    "solarGenerationPower": "solar_power",
    "gridActivePower": "grid_power",
    "batteryPower": "battery_power",
    "chargeMaxPower": "charge_power_limit",
    "dischargeMaxPower": "discharge_power_limit",
}
ENERGY_FIELDS = {
    "dailySolarGeneration": "solar_energy_today",
    "lifetimeSolarGeneration": "solar_energy_total",
    "dailyToGrid": "grid_export_today",
    "dailyFromGrid": "grid_import_today",
    "lifetimeToGrid": "grid_export_total",
    "lifetimeFromGrid": "grid_import_total",
    "dailyBatteryCharged": "battery_charged_today",
    "dailyBatteryDischarged": "battery_discharged_today",
    "lifetimeBatteryCharged": "battery_charged_total",
    "lifetimeBatteryDischarged": "battery_discharged_total",
}
DESCRIPTIONS = (
    *(
        AtmoceSensorDescription(
            key=field,
            translation_key=key,
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=3,
            nonnegative=field not in ("gridActivePower", "batteryPower"),
        )
        for field, key in POWER_FIELDS.items()
    ),
    *(
        AtmoceSensorDescription(
            key=field,
            translation_key=key,
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING
            if field.startswith("daily")
            else SensorStateClass.TOTAL,
            suggested_display_precision=2,
            nonnegative=True,
        )
        for field, key in ENERGY_FIELDS.items()
    ),
    AtmoceSensorDescription(
        key="batterySOC",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        nonnegative=True,
        maximum=100,
        suggested_display_precision=0,
    ),
    *(
        AtmoceSensorDescription(
            key=field,
            translation_key=key,
            entity_category=EntityCategory.DIAGNOSTIC,
            integer=True,
        )
        for field, key in {
            "batteryStatus": "battery_status_code",
            "batteryMode": "battery_mode_code",
            "plantStationStatus": "plant_status_code",
        }.items()
    ),
    AtmoceSensorDescription(
        key="systemTime",
        translation_key="device_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # These are explicitly optional firmware extensions, not command-topic echoes.
    AtmoceSensorDescription(
        key="batteryForcedControlPower",
        translation_key="reported_forced_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        nonnegative=True,
    ),
    AtmoceSensorDescription(
        key="batteryForcedTargetSOC",
        translation_key="reported_target_soc",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        nonnegative=True,
        maximum=100,
    ),
    AtmoceSensorDescription(
        key="batteryForcedControl",
        translation_key="reported_forced_control",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        integer=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up all fields; absent values remain unknown instead of becoming zero."""
    async_add_entities(
        AtmoceSensor(entry.runtime_data, description) for description in DESCRIPTIONS
    )


class AtmoceSensor(AtmoceEntity, SensorEntity):
    """One reported field from the latest complete monitor message."""

    entity_description: AtmoceSensorDescription

    def __init__(self, coordinator, description: AtmoceSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | datetime | None:
        description = self.entity_description
        value = number(self.coordinator.data.get(description.key))
        if (
            value is None
            or (description.nonnegative and value < 0)
            or (description.maximum is not None and value > description.maximum)
            or (description.integer and not value.is_integer())
        ):
            return None
        if description.device_class is SensorDeviceClass.TIMESTAMP:
            try:
                return dt_util.utc_from_timestamp(value)
            except ValueError, OverflowError, OSError:
                return None
        return int(value) if description.integer else value
