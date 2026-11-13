"""Configure HA MQTT, discover gateways, or enter an Atmoce serial manually."""

import asyncio
from typing import Any

import probatio as vol
from homeassistant.components import mqtt
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from .broker import async_setup_broker
from .const import (
    CONF_EXPIRE_AFTER,
    CONF_SERIAL,
    DEFAULT_EXPIRE_AFTER,
    DISCOVERY_SECONDS,
    DISCOVERY_TOPIC,
    DOMAIN,
)
from .protocol import normalize_serial, parse_monitor


class AtmoceConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per gateway and one shared HA MQTT connection."""

    VERSION = 1

    def __init__(self) -> None:
        self._scan_task: asyncio.Task | None = None
        self._found: list[str] = []
        self._serial: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AtmoceOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if await mqtt.async_wait_for_mqtt_client(self.hass):
            return await self.async_step_scan()
        return await self.async_step_mqtt_setup()

    async def async_step_mqtt_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            if user_input["method"] == "manual":
                return await self.async_step_broker()
            if user_input["method"] == "existing":
                error = None
            else:
                error = await async_setup_broker(self.hass)
            if error is None and await mqtt.async_wait_for_mqtt_client(self.hass):
                return await self.async_step_scan()
            errors["base"] = error or "mqtt_not_ready"
        return self.async_show_form(
            step_id="mqtt_setup",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "method", default="automatic"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["automatic", "manual", "existing"],
                            translation_key="mqtt_method",
                        )
                    )
                }
            ),
        )

    async def async_step_broker(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            error = await async_setup_broker(self.hass, user_input)
            if error is None and await mqtt.async_wait_for_mqtt_client(self.hass):
                return await self.async_step_scan()
            errors["base"] = error or "mqtt_not_ready"
        return self.async_show_form(
            step_id="broker",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("host", default="core-mosquitto"): str,
                    vol.Required("port", default=1883): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Optional("username", default=""): str,
                    vol.Optional(
                        vol.Secret("password"), default=""
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                    vol.Required("tls", default=False): bool,
                }
            ),
        )

    async def _async_scan(self) -> None:
        found: set[str] = set()

        @callback
        def received(message: mqtt.ReceiveMessage) -> None:
            try:
                serial, _ = parse_monitor(message.topic, message.payload)
            except ValueError:
                return
            found.add(serial)

        unsubscribe = await mqtt.async_subscribe(
            self.hass, DISCOVERY_TOPIC, received, qos=1
        )
        try:
            await asyncio.sleep(DISCOVERY_SECONDS)
        finally:
            unsubscribe()
        configured = {entry.unique_id for entry in self._async_current_entries()}
        self._found = sorted(found - configured)

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._scan_task is None:
            self._scan_task = self.hass.async_create_task(self._async_scan())
        if not self._scan_task.done():
            return self.async_show_progress(
                step_id="scan",
                progress_action="discover",
                progress_task=self._scan_task,
            )
        await self._scan_task
        self._scan_task = None
        return self.async_show_progress_done(
            next_step_id="select_gateway" if self._found else "manual"
        )

    async def async_step_select_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input[CONF_SERIAL] == "_manual":
                return await self.async_step_manual()
            if user_input[CONF_SERIAL] not in self._found:
                return self.async_abort(reason="invalid_discovery_info")
            return await self._async_finish(user_input[CONF_SERIAL])
        return self.async_show_form(
            step_id="select_gateway",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": sn, "label": f"Atmoce {sn}"}
                                for sn in self._found
                            ]
                            + [
                                {
                                    "value": "_manual",
                                    "label": "Enter a serial number manually",
                                }
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            try:
                serial = normalize_serial(user_input[CONF_SERIAL])
            except ValueError:
                errors[CONF_SERIAL] = "invalid_serial"
            else:
                return await self._async_finish(serial)
        return self.async_show_form(
            step_id="manual",
            errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_SERIAL): str}),
        )

    async def _async_finish(self, serial: str) -> ConfigFlowResult:
        await self.async_set_unique_id(serial, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Atmoce {serial}", data={CONF_SERIAL: serial}
        )

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo
    ) -> ConfigFlowResult:
        try:
            self._serial, _ = parse_monitor(
                discovery_info.topic, discovery_info.payload
            )
        except ValueError:
            return self.async_abort(reason="invalid_discovery_info")
        if any(
            flow["context"]["source"] == "user" for flow in self._async_in_progress()
        ):
            return self.async_abort(reason="discovery_in_progress")
        await self.async_set_unique_id(self._serial)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"serial": self._serial}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            assert self._serial is not None
            return await self._async_finish(self._serial)
        return self.async_show_form(
            step_id="confirm", description_placeholders={"serial": self._serial or ""}
        )

    @callback
    def async_remove(self) -> None:
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
        super().async_remove()


class AtmoceOptionsFlow(OptionsFlow):
    """Tune the data expiry to the actual gateway publishing interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EXPIRE_AFTER,
                        default=self.config_entry.options.get(
                            CONF_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                }
            ),
        )
