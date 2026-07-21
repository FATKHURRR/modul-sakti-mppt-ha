"""Config flow for Modul Sakti MPPT."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_SERVER, CONF_MODULE_ID, SERVERS


class ModulSaktiMpptConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow — add one MPPT module at a time."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            module_id = user_input[CONF_MODULE_ID].strip()
            server_key = user_input[CONF_SERVER]

            if not module_id:
                errors["base"] = "invalid_module_id"
            else:
                await self.async_set_unique_id(module_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"MPPT {module_id}",
                    data={CONF_SERVER: server_key, CONF_MODULE_ID: module_id},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SERVER, default="server1"): vol.In(
                    {key: val["label"] for key, val in SERVERS.items()}
                ),
                vol.Required(CONF_MODULE_ID): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ModulSaktiMpptOptionsFlow(config_entry)


class ModulSaktiMpptOptionsFlow(config_entries.OptionsFlow):
    """Allow changing which broker preset a module uses."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_server = self.config_entry.data.get(CONF_SERVER, "server1")
        schema = vol.Schema(
            {
                vol.Required(CONF_SERVER, default=current_server): vol.In(
                    {key: val["label"] for key, val in SERVERS.items()}
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
