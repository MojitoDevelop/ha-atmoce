"""Configuration flow acceptance tests on the current Home Assistant core."""

import asyncio
import json
from unittest.mock import patch

from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from custom_components.atmoce_mqtt.const import DOMAIN

from .conftest import SERIAL, TOPIC
from .helpers import async_fire_mqtt_message


def discovery(payload):
    return MqttServiceInfo(
        topic=TOPIC,
        qos=1,
        retain=False,
        timestamp=0,
        payload=json.dumps(payload),
        subscribed_topic="atmoce/gateway/+/monitor",
    )


async def test_choose_between_discovered_gateways(hass, mqtt_mock, payload):
    with patch("custom_components.atmoce_mqtt.config_flow.DISCOVERY_SECONDS", 0.02):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] is FlowResultType.SHOW_PROGRESS
        await asyncio.sleep(0)
        async_fire_mqtt_message(hass, TOPIC, json.dumps(payload))
        other = dict(payload, sn="SECOND123")
        async_fire_mqtt_message(
            hass, "atmoce/gateway/SECOND123/monitor", json.dumps(other)
        )
        await asyncio.sleep(0.04)
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["step_id"] == "select_gateway"
        options = result["data_schema"].schema["serial"].config["options"]
        assert {item["value"] for item in options} == {SERIAL, "SECOND123", "_manual"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"serial": SERIAL}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {"serial": SERIAL}
        await hass.async_block_till_done()


async def test_no_discovery_manual_serial_validation_and_duplicates(hass, mqtt_mock):
    with patch("custom_components.atmoce_mqtt.config_flow.DISCOVERY_SECONDS", 0.001):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        await asyncio.sleep(0.01)
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        assert result["step_id"] == "manual"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"serial": "invalid/+"}
        )
        assert result["errors"] == {"serial": "invalid_serial"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"serial": "  example12345  "}
        )
        assert result["data"] == {"serial": SERIAL}
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        await asyncio.sleep(0.01)
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"serial": SERIAL}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_mqtt_discovery_confirm_and_identity(hass, mqtt_mock, payload):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "mqtt"}, data=discovery(payload)
    )
    assert result["step_id"] == "confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "mqtt"}, data=discovery(payload)
    )
    assert duplicate["reason"] == "already_configured"
    payload["sn"] = "WRONG"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "mqtt"}, data=discovery(payload)
    )
    assert result["reason"] == "invalid_discovery_info"


async def test_missing_mqtt_broker_form_and_auto_failure(hass, mqtt_mock):
    with patch(
        "homeassistant.components.mqtt.async_wait_for_mqtt_client", return_value=False
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["step_id"] == "mqtt_setup"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"method": "automatic"}
        )
        assert result["errors"] == {"base": "automatic_mqtt_unavailable"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"method": "manual"}
        )
        assert result["step_id"] == "broker"
        with patch(
            "custom_components.atmoce_mqtt.config_flow.async_setup_broker",
            return_value="cannot_connect_mqtt",
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "broker.example",
                    "port": 1883,
                    "username": "ha",
                    "password": "secret",
                    "tls": False,
                },
            )
        assert result["errors"] == {"base": "cannot_connect_mqtt"}
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_cancel_scan_releases_subscription(hass, mqtt_mock):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    await asyncio.sleep(0)
    assert len(hass.data["test_mqtt_subscriptions"]) == 1
    hass.config_entries.flow.async_abort(result["flow_id"])
    await asyncio.sleep(0)
    assert not hass.data["test_mqtt_subscriptions"]


async def test_options_expiry(hass, integration):
    result = await hass.config_entries.options.async_init(integration.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"expire_after": 300}
    )
    assert result["data"] == {"expire_after": 300}
    await hass.async_block_till_done()
    assert integration.runtime_data.expire_after == 300
