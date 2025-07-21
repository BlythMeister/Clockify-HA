"""The Clockify integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_WORKSPACE_ID

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Clockify from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    workspace_id = entry.data[CONF_WORKSPACE_ID]
    
    coordinator = ClockifyDataUpdateCoordinator(hass, api_key, workspace_id)
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

class ClockifyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Clockify API."""
    
    def __init__(self, hass: HomeAssistant, api_key: str, workspace_id: str) -> None:
        """Initialize."""
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.session = async_get_clientsession(hass)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
    
    async def _async_update_data(self):
        """Update data via library."""
        try:
            async with async_timeout.timeout(10):
                # Get current user
                user_data = await self._async_get_user()
                user_id = user_data["id"]
                
                # Get current timer
                current_timer = await self._async_get_current_timer(user_id)
                
                # If there's an active timer, get project and task details
                if current_timer:
                    project_data = None
                    task_data = None
                    
                    if current_timer.get("projectId"):
                        project_data = await self._async_get_project(current_timer["projectId"])
                    
                    if current_timer.get("taskId"):
                        task_data = await self._async_get_task(current_timer["projectId"], current_timer["taskId"])
                    
                    return {
                        "current_timer": current_timer,
                        "project": project_data,
                        "task": task_data,
                        "user": user_data
                    }
                
                return {
                    "current_timer": None,
                    "project": None,
                    "task": None,
                    "user": user_data
                }
                
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
    
    async def _async_get_user(self):
        """Get current user information."""
        url = "https://api.clockify.me/api/v1/user"
        headers = {"X-Api-Key": self.api_key}
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise UpdateFailed(f"Error getting user: {response.status}")
            return await response.json()
    
    async def _async_get_current_timer(self, user_id: str):
        """Get current active timer."""
        url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/user/{user_id}/time-entries"
        headers = {"X-Api-Key": self.api_key}
        params = {"in-progress": "true"}
        
        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise UpdateFailed(f"Error getting timer: {response.status}")
            
            data = await response.json()
            return data[0] if data else None
    
    async def _async_get_project(self, project_id: str):
        """Get project details."""
        url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/projects/{project_id}"
        headers = {"X-Api-Key": self.api_key}
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                _LOGGER.warning(f"Error getting project {project_id}: {response.status}")
                return None
            return await response.json()
    
    async def _async_get_task(self, project_id: str, task_id: str):
        """Get task details."""
        url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/projects/{project_id}/tasks/{task_id}"
        headers = {"X-Api-Key": self.api_key}
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                _LOGGER.warning(f"Error getting task {task_id}: {response.status}")
                return None
            return await response.json()
