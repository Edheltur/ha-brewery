"""Configuration flow for Brewery."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from . import DOMAIN


class BreweryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure Brewery."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup."""
        if user_input is not None:
            return self.async_create_entry(title="Brewery", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
