"""Verify the adapter against HA's real MQTT flow, with broker I/O mocked."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.components.hassio import AddonState

from custom_components.atmoce_mqtt.broker import async_setup_broker


def broker_settings(tls=False):
    return {
        "host": "broker.example",
        "port": 8883 if tls else 1883,
        "username": "atmoce",
        "password": "private-test-password",
        "tls": tls,
    }


async def test_native_manual_broker_validates_and_owns_credentials(hass, mqtt_mock):
    hass.config.components.update({"http", "file_upload"})
    with (
        patch(
            "homeassistant.components.mqtt.config_flow.try_connection",
            return_value=True,
        ) as connection,
        patch("homeassistant.components.mqtt.async_setup_entry", return_value=True),
        patch("homeassistant.components.mqtt.async_unload_entry", return_value=True),
    ):
        assert await async_setup_broker(hass, broker_settings(tls=True)) is None
        await hass.async_block_till_done()
        entry = hass.config_entries.async_entries("mqtt")[0]
        assert entry.data["broker"] == "broker.example"
        assert entry.data["username"] == "atmoce"
        assert entry.data["password"] == "private-test-password"
        assert entry.data["certificate"] == "auto"
        assert connection.call_count == 1
        assert not hass.config_entries.async_entries("atmoce_mqtt")
        assert not hass.config_entries.flow.async_progress()
        assert await async_setup_broker(hass, {"host": "do-not-overwrite"}) is None
        assert entry.data["broker"] == "broker.example"
        await hass.config_entries.async_unload(entry.entry_id)


async def test_native_manual_failure_does_not_store_password_or_orphan_flow(
    hass, mqtt_mock
):
    hass.config.components.update({"http", "file_upload"})
    with patch(
        "homeassistant.components.mqtt.config_flow.try_connection", return_value=False
    ):
        assert (
            await async_setup_broker(hass, broker_settings()) == "cannot_connect_mqtt"
        )
    assert not hass.config_entries.async_entries("mqtt")
    assert not hass.config_entries.flow.async_progress()


async def test_running_ha_mosquitto_uses_native_discovery_credentials(hass, mqtt_mock):
    hass.config.components.update({"http", "file_upload"})
    manager = SimpleNamespace(
        addon_name="Mosquitto broker",
        async_get_addon_info=AsyncMock(
            return_value=SimpleNamespace(state=AddonState.RUNNING)
        ),
        async_get_addon_discovery_info=AsyncMock(
            return_value={
                "host": "core-mosquitto",
                "port": 1883,
                "username": "managed-user",
                "password": "managed-secret",
            }
        ),
    )
    with (
        patch("custom_components.atmoce_mqtt.broker.is_hassio", return_value=True),
        patch("homeassistant.components.mqtt.config_flow.is_hassio", return_value=True),
        patch(
            "homeassistant.components.mqtt.addon.get_addon_manager",
            return_value=manager,
        ),
        patch(
            "homeassistant.components.mqtt.config_flow.get_addon_manager",
            return_value=manager,
        ),
        patch(
            "homeassistant.components.mqtt.config_flow.try_connection",
            return_value=True,
        ),
        patch("homeassistant.components.mqtt.async_setup_entry", return_value=True),
        patch("homeassistant.components.mqtt.async_unload_entry", return_value=True),
    ):
        assert await async_setup_broker(hass) is None
        await hass.async_block_till_done()
        entry = hass.config_entries.async_entries("mqtt")[0]
        assert entry.data["broker"] == "core-mosquitto"
        assert entry.data["password"] == "managed-secret"
        await hass.config_entries.async_unload(entry.entry_id)


async def test_automatic_finishes_supervisor_mqtt_discovery(hass, mqtt_mock):
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    hass.config.components.update({"http", "file_upload"})
    discovered = HassioServiceInfo(
        name="Mosquitto",
        slug="core_mosquitto",
        uuid="test-uuid",
        config={
            "addon": "Mosquitto",
            "host": "core-mosquitto",
            "port": 1883,
            "username": "managed-user",
            "password": "managed-secret",
        },
    )
    with (
        patch(
            "homeassistant.components.mqtt.config_flow.try_connection",
            return_value=True,
        ),
        patch("homeassistant.components.mqtt.async_setup_entry", return_value=True),
        patch("homeassistant.components.mqtt.async_unload_entry", return_value=True),
    ):
        pending = await hass.config_entries.flow.async_init(
            "mqtt", context={"source": "hassio"}, data=discovered
        )
        assert pending["step_id"] == "hassio_confirm"
        assert await async_setup_broker(hass) is None
        await hass.async_block_till_done()
        entry = hass.config_entries.async_entries("mqtt")[0]
        assert entry.data["password"] == "managed-secret"
        assert not hass.config_entries.flow.async_progress()
        await hass.config_entries.async_unload(entry.entry_id)
