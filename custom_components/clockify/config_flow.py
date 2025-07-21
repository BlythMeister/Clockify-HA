"""Config flow for Clockify integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_WORKSPACE_ID

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_WORKSPACE_ID): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    api_key = data[CONF_API_KEY]
    workspace_id = data[CONF_WORKSPACE_ID]
    
    session = async_get_clientsession(hass)
    
    try:
        async with async_timeout.timeout(10):
            # Test API key by getting user info
            url = "https://api.clockify.me/api/v1/user"
            headers = {"X-Api-Key": api_key}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 401:
                    raise InvalidAuth
                elif response.status != 200:
                    raise CannotConnect
                
                user_data = await response.json()
                
            # Test workspace access
            url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}"
            async with session.get(url, headers=headers) as response:
                if response.status == 403:
                    raise InvalidWorkspace
                elif response.status == 404:
                    raise InvalidWorkspace
                elif response.status != 200:
                    raise CannotConnect
                
                workspace_data = await response.json()
                
        return {
            "title": f"Clockify - {workspace_data['name']}",
            "user_name": user_data.get("name", "Unknown User")
        }
        
    except aiohttp.ClientError:
        raise CannotConnect

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Clockify."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidWorkspace:
                errors["base"] = "invalid_workspace"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_API_KEY]}_{user_input[CONF_WORKSPACE_ID]}"
                )
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidWorkspace(HomeAssistantError):
    """Error to indicate the workspace is invalid."""
