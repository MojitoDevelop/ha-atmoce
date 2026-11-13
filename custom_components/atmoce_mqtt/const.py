"""Constants for Atmoce MQTT."""

DOMAIN = "atmoce_mqtt"
DISCOVERY_TOPIC = "atmoce/gateway/+/monitor"
CONF_SERIAL = "serial"
CONF_EXPIRE_AFTER = "expire_after"
DEFAULT_EXPIRE_AFTER = 180
DISCOVERY_SECONDS = 10
CONTROL_OPTIONS = {"charge": 0, "discharge": 1, "automatic": 2, "pause": 99}
CONF_POWER = "requested_power"
CONF_TARGET_SOC = "target_soc"
