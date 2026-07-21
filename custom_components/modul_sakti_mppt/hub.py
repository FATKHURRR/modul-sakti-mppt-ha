"""MQTT hub handling one Modul Sakti MPPT module (one config entry)."""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

try:
    import paho.mqtt.client as mqtt
except ImportError:
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
        self._available: bool = False  # Menggunakan backing variable internal
        self._known_alarm_keys: set[str] = set()
        self._known_fault_keys: set[str] = set()

        self._client: mqtt.Client | None = None

    @property
    def available(self) -> bool:
        """Return if the MQTT connection is active and has received data."""
        return self._available

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
        
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                clean_session=True
            )
        except AttributeError:
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
            _LOGGER.debug("MQTT Connected, subscribed to %s", topic)
            # Jalankan update ketersediaan secara thread-safe di event loop HA
            self.hass.loop.call_soon_threadsafe(self._set_availability, True)
        else:
            _LOGGER.warning("MQTT connect failed for %s, rc=%s", self.module_id, rc)

    def _on_disconnect(self, client, userdata, rc):
        _LOGGER.warning("MQTT disconnected for %s, rc=%s", self.module_id, rc)
        self.hass.loop.call_soon_threadsafe(self._set_availability, False)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8", errors="ignore"))
            _LOGGER.debug("MQTT received payload on %s: %s", msg.topic, payload)
        except (ValueError, UnicodeDecodeError):
            _LOGGER.debug("Ignoring non-JSON payload on %s", msg.topic)
            return
            
        # Panggil secara thread-safe ke metode async di event loop HA
        self.hass.create_task(self.async_handle_payload(payload))

    # -- runs on the HA event loop -----------------------------------------

    def _set_availability(self, available: bool) -> None:
        """Set availability state and trigger update."""
        self._available = available
        async_dispatcher_send(self.hass, self.signal_update)

    async def async_handle_payload(self, payload: dict[str, Any]) -> None:
        """Handle incoming MQTT payload inside HA Event Loop."""
        
        # Proteksi otomatis jika payload bertipe FLAT (tanpa bungkus "data")
        if "data" not in payload and "device" not in payload:
            self.data = {
                "data": payload,
                "device": payload
            }
        else:
            self.data = payload

        self._available = True

        # Ambil alarm & fault secara aman
        data_block = self.data.get("data", {})
        alarm = data_block.get("alarm", {}) if isinstance(data_block, dict) else {}
        fault = data_block.get("fault", {}) if isinstance(data_block, dict) else {}
        
        # Ekstrak keys dengan aman
        alarm_keys = set(alarm.keys()) if isinstance(alarm, dict) else (set(alarm) if isinstance(alarm, list) else set())
        fault_keys = set(fault.keys()) if isinstance(fault, dict) else (set(fault) if isinstance(fault, list) else set())

        new_alarm_keys = alarm_keys - self._known_alarm_keys
        new_fault_keys = fault_keys - self._known_fault_keys

        if new_alarm_keys or new_fault_keys:
            self._known_alarm_keys |= new_alarm_keys
            self._known_fault_keys |= new_fault_keys
            async_dispatcher_send(
                self.hass,
                self.signal_new_keys,
                {"alarm": sorted(self._known_alarm_keys), "fault": sorted(self._known_fault_keys)},
            )

        # Picu entitas untuk membaca ulang state terbaru
        async_dispatcher_send(self.hass, self.signal_update)

    def get(self, *path: str, default: Any = None) -> Any:
        """Safely fetch a nested value, e.g. hub.get('data', 'volt_battery')."""
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node if node is not None else default