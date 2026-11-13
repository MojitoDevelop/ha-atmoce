"""Exercise the integration in a real HA core with only the MQTT network mocked."""

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.util import dt as dt_util

from custom_components.atmoce_mqtt.const import DOMAIN

from .helpers import TestConfigEntry as MockConfigEntry

SERIAL = "EXAMPLE12345"
TOPIC = f"atmoce/gateway/{SERIAL}/monitor"


@pytest.fixture
def payload():
    return {
        "sn": SERIAL,
        "systemTime": int(dt_util.utcnow().timestamp()),
        "systemTimeZone": -3600,
        "systemLocalTime": int(dt_util.utcnow().timestamp()) + 3600,
        "plantStationStatus": 0,
        "solarGenerationPower": 0.855,
        "dailySolarGeneration": 0.7,
        "lifetimeSolarGeneration": 8037.31,
        "gridActivePower": 0,
        "dailyToGrid": 0.02,
        "dailyFromGrid": 26.9,
        "lifetimeToGrid": 2525.37,
        "lifetimeFromGrid": 2593.14,
        "chargeMaxPower": 7.36,
        "dischargeMaxPower": 9.85,
        "batteryPower": 0.517,
        "batterySOC": 46,
        "batteryStatus": 2,
        "batteryMode": 1,
        "dailyBatteryCharged": 12.32,
        "dailyBatteryDischarged": 7.11,
        "lifetimeBatteryCharged": 2840.25,
        "lifetimeBatteryDischarged": 2336.47,
    }


@pytest.fixture
async def integration(hass, mqtt_mock):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SERIAL,
        data={"serial": SERIAL},
        title=f"Atmoce {SERIAL}",
    )
    entry.add_to_hass(hass)
    assert await asyncio.wait_for(
        hass.config_entries.async_setup(entry.entry_id), timeout=10
    )
    await asyncio.wait_for(hass.async_block_till_done(), timeout=10)
    return entry


@pytest.fixture
async def hass(tmp_path):
    from pathlib import Path

    from homeassistant import config_entries, loader
    from homeassistant.core import CoreState, HomeAssistant
    from homeassistant.helpers import (
        area_registry,
        category_registry,
        condition,
        device_registry,
        entity,
        entity_registry,
        floor_registry,
        frame,
        issue_registry,
        label_registry,
        translation,
        trigger,
    )
    from homeassistant.util.unit_system import METRIC_SYSTEM

    instance = HomeAssistant(str(tmp_path))
    instance.config.skip_pip = True
    instance.config.units = METRIC_SYSTEM
    instance.config_entries = config_entries.ConfigEntries(instance, {"test": {}})
    instance.config_entries._initialized.set()
    loader.async_setup(instance)
    import json

    component_path = (
        Path(__file__).resolve().parents[1] / "custom_components/atmoce_mqtt"
    )
    instance.data[loader.DATA_CUSTOM_COMPONENTS] = {
        DOMAIN: loader.Integration(
            instance,
            "custom_components.atmoce_mqtt",
            component_path,
            json.loads((component_path / "manifest.json").read_text()),
            top_level_files={path.name for path in component_path.iterdir()},
        )
    }
    entity.async_setup(instance)
    frame.async_setup(instance)
    translation.async_setup(instance)
    await condition.async_setup(instance)
    await trigger.async_setup(instance)
    device_registry.async_setup(instance)
    for registry in (
        area_registry,
        category_registry,
        device_registry,
        entity_registry,
        floor_registry,
        label_registry,
        issue_registry,
    ):
        await registry.async_load(instance, load_empty=True)
    instance.set_state(CoreState.running)
    try:
        yield instance
    finally:
        for entry in instance.config_entries.async_entries():
            if entry.state is config_entries.ConfigEntryState.LOADED:
                await instance.config_entries.async_unload(entry.entry_id)
        await instance.async_stop(force=True)


@pytest.fixture
def mqtt_mock(hass):
    from unittest.mock import AsyncMock

    hass.config.components.add("mqtt")
    subscriptions = hass.data["test_mqtt_subscriptions"] = []

    async def subscribe(hass, topic, callback, qos=0):
        item = (topic, callback)
        subscriptions.append(item)

        def unsubscribe():
            subscriptions.remove(item)

        return unsubscribe

    with (
        patch(
            "homeassistant.components.mqtt.async_wait_for_mqtt_client",
            return_value=True,
        ),
        patch("homeassistant.components.mqtt.async_subscribe", side_effect=subscribe),
        patch(
            "homeassistant.components.mqtt.async_subscribe_connection_status",
            return_value=lambda: None,
        ),
        patch("homeassistant.components.mqtt.is_connected", return_value=True),
        patch(
            "homeassistant.components.mqtt.async_publish", new_callable=AsyncMock
        ) as publish,
    ):
        yield publish
