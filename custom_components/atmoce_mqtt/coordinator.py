"""Push telemetry and send explicit, non-retained battery commands."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_EXPIRE_AFTER, CONF_SERIAL, DEFAULT_EXPIRE_AFTER, DOMAIN
from .protocol import build_command, parse_monitor, sample_age

_LOGGER = logging.getLogger(__name__)


class AtmoceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One MQTT subscription and freshness timer per gateway."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self.serial = entry.data[CONF_SERIAL]
        self.expire_after = entry.options.get(CONF_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER)
        self.data = {}
        self.last_update_success = False
        self.last_seen: datetime | None = None
        self.last_command: dict[str, Any] | None = None
        self.last_command_time: datetime | None = None
        self.staged: dict[str, float] = {}
        self._expire_cancel = None
        self._unsubscribe = None
        self._connection_unsubscribe = None
        self._command_lock = asyncio.Lock()

    async def async_start(self) -> None:
        """Wait for MQTT before subscribing; do not wait for the first sample."""
        self._connection_unsubscribe = mqtt.async_subscribe_connection_status(
            self.hass, self._connection_changed
        )
        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, f"atmoce/gateway/{self.serial}/monitor", self._message, qos=1
        )

    @callback
    def _message(self, message: mqtt.ReceiveMessage) -> None:
        try:
            _, data = parse_monitor(message.topic, message.payload)
        except ValueError:
            _LOGGER.debug("Ignoring invalid Atmoce monitor message")
            return
        now = dt_util.utcnow()
        age = sample_age(data, now.timestamp())
        if (age is not None and (age < -120 or age >= self.expire_after)) or (
            message.retain and age is None
        ):
            return
        old_stamp = self.data.get("systemTime")
        new_stamp = data.get("systemTime")
        if (
            isinstance(old_stamp, (int, float))
            and isinstance(new_stamp, (int, float))
            and new_stamp < old_stamp
        ):
            return
        self.last_seen = now
        if self._expire_cancel:
            self._expire_cancel()
        self._expire_cancel = async_call_later(
            self.hass, self.expire_after - max(age or 0, 0), self._expired
        )
        self.async_set_updated_data(data)

    @callback
    def _expired(self, _now: datetime) -> None:
        self._expire_cancel = None
        self.async_set_update_error(HomeAssistantError("Atmoce telemetry expired"))

    @callback
    def _connection_changed(self, connected: bool) -> None:
        if not connected:
            self.async_set_update_error(HomeAssistantError("MQTT disconnected"))
        else:
            self.async_update_listeners()
        # A reconnect alone is not proof that the gateway is still online.

    async def async_control(
        self, mode: str, power: float | None = None, target_soc: float | None = None
    ) -> None:
        """Serialize commands and validate limits immediately before publishing."""
        async with self._command_lock:
            if not mqtt.is_connected(self.hass):
                raise ServiceValidationError("MQTT is disconnected")
            if mode in ("charge", "discharge"):
                age = sample_age(self.data, dt_util.utcnow().timestamp())
                if (
                    not self.last_update_success
                    or self.last_seen is None
                    or (dt_util.utcnow() - self.last_seen).total_seconds()
                    >= self.expire_after
                    or (age is not None and (age < -120 or age >= self.expire_after))
                ):
                    raise ServiceValidationError("Fresh Atmoce telemetry is required")
            try:
                command = build_command(mode, power, target_soc, self.data)
            except ValueError as err:
                raise ServiceValidationError(str(err)) from err
            await mqtt.async_publish(
                self.hass,
                f"atmoce/gateway/{self.serial}/config",
                json.dumps(command, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            self.last_command = command
            self.last_command_time = dt_util.utcnow()
            self.async_update_listeners()

    @callback
    def async_stop(self) -> None:
        """Release all subscriptions and timers, including after failed setup."""
        for cancel in (
            self._unsubscribe,
            self._connection_unsubscribe,
            self._expire_cancel,
        ):
            if cancel:
                cancel()
        self._unsubscribe = self._connection_unsubscribe = self._expire_cancel = None
