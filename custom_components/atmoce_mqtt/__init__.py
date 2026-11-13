"""Atmoce solar and battery monitoring and control through Home Assistant MQTT."""

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import AtmoceCoordinator

type AtmoceConfigEntry = ConfigEntry[AtmoceCoordinator]
PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: AtmoceConfigEntry) -> bool:
    """Start MQTT and forward platforms using typed entry runtime data."""
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("The Home Assistant MQTT client is not available")
    coordinator = AtmoceCoordinator(hass, entry)
    registry = er.async_get(hass)
    if old_entity_id := registry.async_get_entity_id(
        Platform.SENSOR, DOMAIN, f"{coordinator.serial}_systemTime"
    ):
        if registry.async_get(old_entity_id).config_entry_id == entry.entry_id:
            registry.async_remove(old_entity_id)
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AtmoceConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: AtmoceConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
