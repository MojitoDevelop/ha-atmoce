"""Small test adapters for HA entries and the MQTT network boundary."""

from types import MappingProxyType

from homeassistant import config_entries
from homeassistant.components.mqtt import ReceiveMessage


class TestConfigEntry(config_entries.ConfigEntry):
    """Supply explicit defaults without depending on a version-pinned HA test plugin."""

    __test__ = False

    def __init__(self, *, domain, data, title="Test", unique_id=None, options=None):
        super().__init__(
            version=1,
            minor_version=1,
            domain=domain,
            data=data,
            title=title,
            unique_id=unique_id,
            options=options or {},
            source="user",
            discovery_keys=MappingProxyType({}),
            subentries_data=(),
        )

    def add_to_hass(self, hass):
        hass.config_entries._entries[self.entry_id] = self


def async_fire_mqtt_message(hass, topic, payload, retain=False):
    """Deliver a broker message to registered HA MQTT callbacks."""
    for subscribed, callback in list(hass.data["test_mqtt_subscriptions"]):
        parts, pattern = topic.split("/"), subscribed.split("/")
        if len(parts) == len(pattern) and all(
            a == b or b == "+" for a, b in zip(parts, pattern, strict=True)
        ):
            callback(ReceiveMessage(topic, payload, 1, retain, subscribed, 0))
