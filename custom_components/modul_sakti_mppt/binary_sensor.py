"""Binary sensor platform for Modul Sakti MPPT."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MODULE_ID, MANUFACTURER, MODEL
from .hub import ModulSaktiMpptHub


@dataclass(frozen=True)
class MpptBinaryDescription:
    key: str
    name: str
    path: tuple
    device_class: BinarySensorDeviceClass | None = None
    icon: str | None = None


STATUS_TYPES: tuple[MpptBinaryDescription, ...] = (
    MpptBinaryDescription("load_out", "Load Output", ("data", "status", "load_out"), None, "mdi:power-plug"),
    MpptBinaryDescription("charging", "Charging", ("data", "status", "charging"), BinarySensorDeviceClass.BATTERY_CHARGING),
    MpptBinaryDescription("bat_full", "Battery Full", ("data", "status", "bat_full"), None, "mdi:battery-check"),
    MpptBinaryDescription("warn", "Warning", ("data", "status", "warn"), BinarySensorDeviceClass.PROBLEM),
    MpptBinaryDescription("fault", "Fault", ("data", "status", "fault"), BinarySensorDeviceClass.PROBLEM),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: ModulSaktiMpptHub = hass.data[DOMAIN][entry.entry_id]
    module_id = entry.data[CONF_MODULE_ID]

    entities: list[BinarySensorEntity] = [
        MpptBinarySensor(hub, module_id, description) for description in STATUS_TYPES
    ]

    added_keys: set[str] = set()

    def _make_dynamic(kind: str, key: str) -> MpptBinaryDescription:
        return MpptBinaryDescription(
            key=f"{kind}_{key}",
            name=f"{kind.capitalize()} {key.replace('_', ' ').title()}",
            path=("data", kind, key),
            device_class=BinarySensorDeviceClass.PROBLEM,
        )

    def _add_new_keys(payload: dict | None = None) -> None:
        new_entities = []
        payload_data = payload or {}
        
        # Penanganan fleksibel baik payload berupa list ataupun dict keys
        alarm_keys = payload_data.get("alarm", [])
        if isinstance(alarm_keys, dict):
            alarm_keys = list(alarm_keys.keys())
            
        fault_keys = payload_data.get("fault", [])
        if isinstance(fault_keys, dict):
            fault_keys = list(fault_keys.keys())

        for key in alarm_keys:
            uid = f"alarm_{key}"
            if uid not in added_keys:
                added_keys.add(uid)
                new_entities.append(MpptBinarySensor(hub, module_id, _make_dynamic("alarm", key)))
        for key in fault_keys:
            uid = f"fault_{key}"
            if uid not in added_keys:
                added_keys.add(uid)
                new_entities.append(MpptBinarySensor(hub, module_id, _make_dynamic("fault", key)))
        if new_entities:
            async_add_entities(new_entities)

    # PERBAIKAN: Mengambil data existing dengan aman untuk menghindari AttributeError .keys()
    raw_alarm = hub.get("data", "alarm")
    existing_alarm = list(raw_alarm.keys()) if isinstance(raw_alarm, dict) else (raw_alarm if isinstance(raw_alarm, list) else [])
    
    raw_fault = hub.get("data", "fault")
    existing_fault = list(raw_fault.keys()) if isinstance(raw_fault, dict) else (raw_fault if isinstance(raw_fault, list) else [])

    if existing_alarm or existing_fault:
        _add_new_keys({"alarm": existing_alarm, "fault": existing_fault})

    entry.async_on_unload(
        async_dispatcher_connect(hass, hub.signal_new_keys, _add_new_keys)
    )

    async_add_entities(entities)


class MpptBinarySensor(BinarySensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hub: ModulSaktiMpptHub, module_id: str, description: MpptBinaryDescription) -> None:
        self._hub = hub
        self._description = description
        self._attr_unique_id = f"{module_id}_{description.key}"
        self._attr_name = description.name
        self._attr_device_class = description.device_class
        self._attr_icon = description.icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, module_id)},
            name=f"MPPT {module_id}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return self._hub.available

    @property
    def is_on(self) -> bool | None:
        value = self._hub.get(*self._description.path)
        if value is None:
            return None
        return bool(value)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._hub.signal_update, self.async_write_ha_state)
        )