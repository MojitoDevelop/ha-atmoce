"""Shared device identity."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AtmoceCoordinator


class AtmoceEntity(CoordinatorEntity[AtmoceCoordinator]):
    """An entity on a serial-numbered Atmoce gateway."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AtmoceCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)},
            manufacturer="Atmoce",
            name=f"Atmoce {coordinator.serial}",
            model="MQTT gateway",
            serial_number=coordinator.serial,
        )
