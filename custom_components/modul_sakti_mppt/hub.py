"""MQTT hub handling one Modul Sakti MPPT module (one config entry)."""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Callable

try:
    # Prefer an already-installed paho-mqtt (e.g. the one Home Assistant's
    # core mqtt integration already depends on), if one is importable.
    import paho.mqtt.client as mqtt
except ImportError:
    # Fall back to the copy vendored inside this integration, so setup does
    # not depend on internet/PyPI access to pip-install a dependency.
    _VENDOR_DIR = os.path.join(os.path.dirname(__file__), "vendor")
    if _VENDOR_DIR not in sys.path:
        sys.path.append(_VENDOR_DIR)
    import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SERVERS, TOPIC_DATA, SIGNAL_UPDATE, SIGNAL_NEW_KEYS

_LOGGER = logging.getLogger(__name__)


class ModulSaktiMpptHub:
    """Owns the MQTT connection for a single module_id."""

    def __init__(self, hass: HomeAssistant, entry_id: str, server_key: str, module_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.module_id = module_id
        self.server = SERVERS[server_key]

        self.data: dict[str, Any] = {}
        self.available: bool = False
        self._known_alarm_keys: set[str] = set()
        self._known_fault_keys: set[str] = set()

        self._client: mqtt.Client | None = None

    @property
    def signal_update(self) -> str:
        return SIGNAL_UPDATE.format(entry_id=self.entry_id)

    @property
    def signal_new_keys(self) -> str:
        return SIGNAL_NEW_KEYS.format(entry_id=self.entry_id)

    async def async_connect(self) -> None:
        """Set up and start the MQTT client in the executor."""
        await self.hass.async_add_executor_job(self._setup_client)

    async def async_disconnect(self) -> None:
        if self._client is not None:
            await self.hass.async_add_executor_job(self._client.loop_stop)
            await self.hass.async_add_executor_job(self._client.disconnect)

    # -- internal, runs paho's own thread ---------------------------------

    def _setup_client(self) -> None:
        client_id = f"ha_modul_sakti_{self.module_id}_{id(self)}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        client.username_pw_set(self.server["username"], self.server["password"])
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.connect_async(self.server["host"], self.server["port"], keepalive=60)
        client.loop_start()
        self._client = client

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            topic = TOPIC_DATA.format(module_id=self.module_id)
            client.subscribe(topic)
            _LOGGER.debug("Connected, subscribed to %s", topic)
            self.available = True
            self.hass.add_job(self._push_update)
        else:
            _LOGGER.warning("MQTT connect failed for %s, rc=%s", self.module_id, rc)

    def _on_disconnect(self, client, userdata, rc):
        self.available = False
        self.hass.add_job(self._push_update)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8", errors="ignore"))
        except (ValueError, UnicodeDecodeError):
            _LOGGER.debug("Ignoring non-JSON payload on %s", msg.topic)
            return
        self.hass.add_job(self._handle_payload, payload)

    # -- runs on the HA event loop -----------------------------------------

    def _handle_payload(self, payload: dict[str, Any]) -> None:
        self.data = payload
        self.available = True

        alarm = (payload.get("data") or {}).get("alarm") or {}
        fault = (payload.get("data") or {}).get("fault") or {}
        new_alarm_keys = set(alarm.keys()) - self._known_alarm_keys
        new_fault_keys = set(fault.keys()) - self._known_fault_keys

        if new_alarm_keys or new_fault_keys:
            self._known_alarm_keys |= new_alarm_keys
            self._known_fault_keys |= new_fault_keys
            async_dispatcher_send(
                self.hass,
                self.signal_new_keys,
                {"alarm": sorted(self._known_alarm_keys), "fault": sorted(self._known_fault_keys)},
            )

        self._push_update()

    def _push_update(self) -> None:
        async_dispatcher_send(self.hass, self.signal_update)

    def get(self, *path: str, default: Any = None) -> Any:
        """Safely fetch a nested value, e.g. hub.get('data', 'volt_battery')."""
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node if node is not None else default
