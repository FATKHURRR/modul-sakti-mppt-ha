"""The Modul Sakti MPPT integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CONF_SERVER, CONF_MODULE_ID
from .hub import ModulSaktiMpptHub

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    hub = ModulSaktiMpptHub(
        hass,
        entry.entry_id,
        entry.data[CONF_SERVER],
        entry.data[CONF_MODULE_ID],
    )
    await hub.async_connect()

    hass.data[DOMAIN][entry.entry_id] = hub

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub: ModulSaktiMpptHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.async_disconnect()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
