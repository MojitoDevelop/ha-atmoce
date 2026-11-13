"""Monitoring, statistics, command safety and lifecycle acceptance tests."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.atmoce_mqtt.const import DOMAIN
from custom_components.atmoce_mqtt.diagnostics import async_get_config_entry_diagnostics

from .conftest import SERIAL, TOPIC
from .helpers import async_fire_mqtt_message


def entity_id(hass, domain, key):
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{key}")


async def feed(hass, payload, retain=False):
    async_fire_mqtt_message(hass, TOPIC, json.dumps(payload), retain=retain)
    await hass.async_block_till_done()


async def test_monitor_units_statistics_and_device(hass, integration, payload):
    assert (
        hass.states.get(entity_id(hass, "sensor", "batterySOC")).state
        == STATE_UNAVAILABLE
    )
    await feed(hass, payload)
    power = hass.states.get(entity_id(hass, "sensor", "solarGenerationPower"))
    assert power.state == "0.855"
    assert power.attributes["unit_of_measurement"] == "kW"
    assert power.attributes["device_class"] == "power"
    assert power.attributes["state_class"] == "measurement"
    assert power.attributes["friendly_name"].endswith("Solar power")
    assert (
        hass.states.get(entity_id(hass, "sensor", "dailySolarGeneration")).attributes[
            "state_class"
        ]
        == "total_increasing"
    )
    assert (
        hass.states.get(
            entity_id(hass, "sensor", "lifetimeSolarGeneration")
        ).attributes["state_class"]
        == "total"
    )
    assert hass.states.get(entity_id(hass, "sensor", "batterySOC")).state == "46.0"
    assert (
        hass.states.get(entity_id(hass, "sensor", "systemTime")).state
        == dt_util.utc_from_timestamp(payload["systemTime"]).isoformat()
    )
    identifiers = {
        e.device_id
        for e in er.async_entries_for_config_entry(
            er.async_get(hass), integration.entry_id
        )
    }
    assert len(identifiers) == 1 and None not in identifiers


async def test_malformed_partial_and_nonfinite_data(hass, integration, payload):
    await feed(hass, payload)
    async_fire_mqtt_message(hass, TOPIC, "{broken")
    await hass.async_block_till_done()
    assert integration.runtime_data.data["batterySOC"] == 46
    for key in ("dailySolarGeneration", "batterySOC"):
        payload.pop(key)
    payload["solarGenerationPower"] = float("nan")
    # gridActivePower still identifies a monitor message. Missing/invalid fields aren't zero.
    await feed(hass, payload)
    assert (
        hass.states.get(entity_id(hass, "sensor", "dailySolarGeneration")).state
        == STATE_UNKNOWN
    )
    assert (
        hass.states.get(entity_id(hass, "sensor", "solarGenerationPower")).state
        == STATE_UNKNOWN
    )


async def test_expiry_retained_data_and_recovery(hass, integration, payload):
    old = dict(payload, systemTime=payload["systemTime"] - 3600)
    await feed(hass, old, retain=True)
    assert not integration.runtime_data.last_update_success
    integration.runtime_data.expire_after = 0.02
    payload.pop("systemTime")
    await feed(hass, payload)
    await asyncio.sleep(0.04)
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "batterySOC")).state
        == STATE_UNAVAILABLE
    )
    await feed(hass, payload)
    assert integration.runtime_data.last_update_success


async def test_staged_settings_and_exact_node_red_commands(hass, integration, payload):
    await feed(hass, payload)
    power_id = entity_id(hass, "number", "requested_power")
    soc_id = entity_id(hass, "number", "target_soc")
    control_id = entity_id(hass, "select", "requested_battery_control")
    with patch(
        "custom_components.atmoce_mqtt.coordinator.mqtt.async_publish",
        new_callable=AsyncMock,
    ) as publish:
        await hass.services.async_call(
            "number", "set_value", {"entity_id": power_id, "value": 3.5}, blocking=True
        )
        await hass.services.async_call(
            "number", "set_value", {"entity_id": soc_id, "value": 80}, blocking=True
        )
        publish.assert_not_called()
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": control_id, "option": "charge"},
            blocking=True,
        )
        args, kwargs = publish.call_args
        assert args[1] == f"atmoce/gateway/{SERIAL}/config"
        assert json.loads(args[2]) == {
            "batteryForcedControl": 0,
            "batteryForcedMode": 0,
            "batteryForcedTargetSOC": 80,
            "batteryForcedControlPower": 3.5,
        }
        assert kwargs == {"qos": 1, "retain": False}
        assert integration.runtime_data.data["batteryStatus"] == 2
        assert (
            hass.states.get(control_id).attributes["value_source"] == "home_assistant"
        )
        await hass.services.async_call(
            DOMAIN,
            "set_battery_control",
            {
                "entity_id": control_id,
                "mode": "discharge",
                "power": 2.1,
                "target_soc": 20,
            },
            blocking=True,
        )
        assert json.loads(publish.call_args.args[2]) == {
            "batteryForcedControl": 1,
            "batteryForcedMode": 0,
            "batteryForcedTargetSOC": 20,
            "batteryForcedControlPower": 2.1,
        }
        for mode, code in [("automatic", 2), ("pause", 99)]:
            await hass.services.async_call(
                DOMAIN,
                "set_battery_control",
                {"entity_id": control_id, "mode": mode},
                blocking=True,
            )
            assert json.loads(publish.call_args.args[2]) == {
                "batteryForcedControl": code
            }


@pytest.mark.parametrize(
    "mode,power,target",
    [
        ("charge", 7.37, 90),
        ("discharge", 9.86, 20),
        ("charge", -1, 90),
        ("charge", float("nan"), 90),
        ("discharge", 2, 20.5),
    ],
)
async def test_invalid_command_never_published(
    hass, integration, payload, mode, power, target
):
    await feed(hass, payload)
    with patch(
        "custom_components.atmoce_mqtt.coordinator.mqtt.async_publish",
        new_callable=AsyncMock,
    ) as publish:
        with pytest.raises(ServiceValidationError):
            await integration.runtime_data.async_control(mode, power, target)
        publish.assert_not_called()


async def test_reached_target_returns_to_automatic(hass, integration, payload):
    await feed(hass, payload)
    with patch(
        "custom_components.atmoce_mqtt.coordinator.mqtt.async_publish",
        new_callable=AsyncMock,
    ) as publish:
        await integration.runtime_data.async_control("charge", 2, 45)
        assert json.loads(publish.call_args.args[2]) == {"batteryForcedControl": 2}


async def test_stale_and_disconnected_command_guards(hass, integration, payload):
    await feed(hass, payload)
    hub = integration.runtime_data
    with patch(
        "custom_components.atmoce_mqtt.coordinator.mqtt.async_publish",
        new_callable=AsyncMock,
    ) as publish:
        hub._expired(dt_util.utcnow())
        with pytest.raises(ServiceValidationError):
            await hub.async_control("charge", 2, 80)
        publish.assert_not_called()
        await hub.async_control("automatic")
        assert json.loads(publish.call_args.args[2]) == {"batteryForcedControl": 2}
        hub._connection_changed(False)
        hub._connection_changed(True)
        assert not hub.last_update_success
        with patch(
            "custom_components.atmoce_mqtt.coordinator.mqtt.is_connected",
            return_value=False,
        ):
            with pytest.raises(ServiceValidationError):
                await hub.async_control("pause")


async def test_no_command_on_start_reload_or_unload(hass, integration, payload):
    await feed(hass, payload)
    with patch(
        "custom_components.atmoce_mqtt.coordinator.mqtt.async_publish",
        new_callable=AsyncMock,
    ) as publish:
        await integration.runtime_data.async_control("charge", 2, 80)
        publish.reset_mock()
        assert await hass.config_entries.async_reload(integration.entry_id)
        await hass.async_block_till_done()
        assert integration.runtime_data.last_command is None
        hub = integration.runtime_data
        assert await hass.config_entries.async_unload(integration.entry_id)
        await hass.async_block_till_done()
        publish.assert_not_called()
        assert hub._unsubscribe is None
        assert hub._expire_cancel is None


async def test_diagnostics_redact_identity_and_unknown_fields(
    hass, integration, payload
):
    payload["password"] = "never-export-me"
    payload["account_id"] = 123456
    await feed(hass, payload)
    result = await async_get_config_entry_diagnostics(hass, integration)
    text = json.dumps(result)
    assert SERIAL not in text
    assert "never-export-me" not in text
    assert "account_id" not in text
    assert result["telemetry"]["batterySOC"] == 46


async def test_readback_is_only_taken_from_device_monitor(hass, integration, payload):
    registry = er.async_get(hass)
    readback_id = entity_id(hass, "sensor", "batteryForcedTargetSOC")
    registry.async_update_entity(readback_id, disabled_by=None)
    await hass.config_entries.async_reload(integration.entry_id)
    await hass.async_block_till_done()
    await feed(hass, payload)
    assert hass.states.get(readback_id).state == STATE_UNKNOWN
    async_fire_mqtt_message(
        hass,
        f"atmoce/gateway/{SERIAL}/config",
        json.dumps({"batteryForcedTargetSOC": 80}),
    )
    await hass.async_block_till_done()
    assert hass.states.get(readback_id).state == STATE_UNKNOWN
    await feed(hass, dict(payload, batteryForcedTargetSOC=80))
    assert hass.states.get(readback_id).state == "80.0"
