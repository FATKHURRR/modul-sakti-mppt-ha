"""Sensor platform for Modul Sakti MPPT."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MODULE_ID, MANUFACTURER, MODEL
from .hub import ModulSaktiMpptHub


@dataclass(frozen=True)
class MpptSensorDescription:
    key: str
    name: str
    path: tuple
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None


SENSOR_TYPES: tuple[MpptSensorDescription, ...] = (
    MpptSensorDescription("volt_battery", "Battery Voltage", ("data", "volt_battery"), "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("current", "Battery Current", ("data", "current"), "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("power", "Battery Power", ("data", "power"), "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("peak_power", "Peak Power", ("data", "peak_power"), "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("volt_pv", "PV Voltage", ("data", "volt_pv"), "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("today_energy", "Today Energy", ("data", "today_energy"), "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    MpptSensorDescription("total_energy", "Total Energy", ("data", "total_energy"), "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    MpptSensorDescription("load_percent", "Load Percent", ("data", "load_percent"), "%", None, SensorStateClass.MEASUREMENT, "mdi:gauge"),
    MpptSensorDescription("temp_envi", "Environment Temperature", ("data", "temp_envi"), "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("temp_mppt", "Heatsink Temperature", ("data", "temp_mppt"), "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("status_code", "Status Code", ("data", "status_code"), None, None, None, "mdi:information-outline"),
    MpptSensorDescription("wifi_rssi", "WiFi RSSI", ("device", "wifi"), "dBm", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("free_heap", "Free Heap", ("device", "heap"), "B", None, SensorStateClass.MEASUREMENT, "mdi:memory"),
    MpptSensorDescription("uptime", "Uptime", ("device", "uptime"), "s", SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT),
    MpptSensorDescription("ip_address", "IP Address", ("device", "ip"), None, None, None, "mdi:ip-network"),
    MpptSensorDescription("fw_version", "Firmware Version", ("device", "fw version"), None, None, None, "mdi:chip"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: ModulSaktiMpptHub = hass.data[DOMAIN][entry.entry_id]
    module_id = entry.data[CONF_MODULE_ID]

    entities = [MpptSensor(hub, module_id, description) for description in SENSOR_TYPES]
    async_add_entities(entities)


class MpptSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hub: ModulSaktiMpptHub, module_id: str, description: MpptSensorDescription) -> None:
        self._hub = hub
        self._description = description
        self._attr_unique_id = f"{module_id}_{description.key}"
        self._attr_name = description.name
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
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
    def native_value(self):
        return self._hub.get(*self._description.path)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._hub.signal_update, self.async_write_ha_state)
        )
