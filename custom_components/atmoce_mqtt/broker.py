"""Bootstrap the official HA MQTT integration; credentials stay owned by MQTT."""

from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.hassio import is_hassio


async def async_setup_broker(
    hass: HomeAssistant, settings: dict[str, Any] | None = None
) -> str | None:
    """Run HA's broker validation, discovery and credential storage, never edit storage."""
    if hass.config_entries.async_entries("mqtt"):
        return None
    in_progress = [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["handler"] == "mqtt"
    ]
    if in_progress:
        # Supervisor commonly offers MQTT discovery before a user adds Atmoce.
        # Its flow already contains the broker's managed credentials.
        if settings is None:
            for flow in in_progress:
                if (
                    flow["context"].get("source") == "hassio"
                    and flow.get("step_id") == "hassio_confirm"
                ):
                    result = await hass.config_entries.flow.async_configure(
                        flow["flow_id"], {}
                    )
                    return (
                        None
                        if result["type"] is FlowResultType.CREATE_ENTRY
                        else "cannot_connect_mqtt"
                    )
        return "mqtt_setup_in_progress"
    if settings is None:
        if not is_hassio(hass):
            return "automatic_mqtt_unavailable"
        from homeassistant.components.hassio import AddonError, AddonState
        from homeassistant.components.mqtt.addon import get_addon_manager

        try:
            info = await get_addon_manager(hass).async_get_addon_info()
        except AddonError:
            return "automatic_mqtt_unavailable"
        if info.state is not AddonState.RUNNING:
            return "automatic_mqtt_unavailable"

    result = await hass.config_entries.flow.async_init(
        "mqtt", context={"source": SOURCE_USER}
    )
    flow_id = result["flow_id"]
    try:
        if result["type"] is FlowResultType.MENU:
            result = await hass.config_entries.flow.async_configure(
                flow_id, {"next_step_id": "broker" if settings is not None else "addon"}
            )
        if settings is not None and result["type"] is FlowResultType.FORM:
            result = await hass.config_entries.flow.async_configure(
                flow_id,
                {
                    "broker": settings["host"],
                    "port": settings["port"],
                    "username": settings.get("username", ""),
                    "password": settings.get("password", ""),
                    "protocol": "3.1.1",
                    "other_settings": {
                        "set_ca_cert": "auto" if settings.get("tls") else "off",
                        "set_client_cert": False,
                        "transport": "tcp",
                    },
                },
            )
        if result["type"] is FlowResultType.CREATE_ENTRY:
            return None
        return "cannot_connect_mqtt"
    finally:
        if result["type"] not in (FlowResultType.CREATE_ENTRY, FlowResultType.ABORT):
            hass.config_entries.flow.async_abort(flow_id)
