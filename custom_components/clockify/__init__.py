"""The Clockify integration."""
from __future__ import annotations

import logging
from datetime import timedelta, datetime, timezone

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
                
                # Get time summaries with error handling
                now = datetime.now(timezone.utc)
                try:
                    daily_duration = await self._async_get_daily_time(user_id, now)
                except Exception as err:
                    _LOGGER.warning(f"Error getting daily time: {err}")
                    daily_duration = 0
                
                try:
                    weekly_duration, week_start, week_end = await self._async_get_weekly_time(user_id, now)
                except Exception as err:
                    _LOGGER.warning(f"Error getting weekly time: {err}")
                    weekly_duration = 0
                    week_start = now.strftime("%Y-%m-%d")
                    week_end = now.strftime("%Y-%m-%d")
                
                # Calculate totals including current timer
                current_timer_duration = 0
                if current_timer and current_timer.get("timeInterval", {}).get("start"):
                    try:
                        start_time_str = current_timer["timeInterval"]["start"]
                        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        current_timer_duration = int((now - start_time).total_seconds())
                    except (ValueError, KeyError):
                        current_timer_duration = 0
                
                daily_total = daily_duration + current_timer_duration
                weekly_total = weekly_duration + current_timer_duration
                
                # If there's an active timer, get project and task details
                project_data = None
                task_data = None
                
                if current_timer:
                    if current_timer.get("projectId"):
                        project_data = await self._async_get_project(current_timer["projectId"])
                    
                    if current_timer.get("taskId"):
                        task_data = await self._async_get_task(current_timer["projectId"], current_timer["taskId"])
                
                # Get daily breakdown for the week
                try:
                    daily_breakdown, daily_breakdown_total, daily_breakdown_formatted, daily_breakdown_total_formatted = await self._async_get_weekly_daily_breakdown(user_id, now, current_timer_duration)
                except Exception as err:
                    _LOGGER.warning(f"Error getting weekly daily breakdown: {err}")
                    daily_breakdown = {}
                    daily_breakdown_total = {}
                    daily_breakdown_formatted = {}
                    daily_breakdown_total_formatted = {}
                
                return {
                    "current_timer": current_timer,
                    "project": project_data,
                    "task": task_data,
                    "user": user_data,
                    "daily_duration": daily_duration,
                    "weekly_duration": weekly_duration,
                    "daily_total": daily_total,
                    "weekly_total": weekly_total,
                    "current_date": now.strftime("%Y-%m-%d"),
                    "week_start": week_start,
                    "week_end": week_end,
                    "daily_breakdown": daily_breakdown,
                    "daily_breakdown_total": daily_breakdown_total,
                    "daily_breakdown_formatted": daily_breakdown_formatted,
                    "daily_breakdown_total_formatted": daily_breakdown_total_formatted,
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
    
    async def _async_get_daily_time(self, user_id: str, date: datetime) -> int:
        """Get total time for today."""
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/user/{user_id}/time-entries"
        headers = {"X-Api-Key": self.api_key}
        params = {
            "start": start_date.isoformat().replace("+00:00", "Z"),
            "end": end_date.isoformat().replace("+00:00", "Z"),
        }
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    _LOGGER.warning(f"Error getting daily time: {response.status}")
                    return 0
                
                entries = await response.json()
                total_seconds = 0
                
                for entry in entries:
                    time_interval = entry.get("timeInterval", {})
                    if time_interval.get("start") and time_interval.get("end"):
                        start = datetime.fromisoformat(time_interval["start"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(time_interval["end"].replace("Z", "+00:00"))
                        total_seconds += int((end - start).total_seconds())
                
                return total_seconds
                
        except Exception as err:
            _LOGGER.warning(f"Error calculating daily time: {err}")
            return 0
    
    async def _async_get_weekly_time(self, user_id: str, date: datetime) -> tuple[int, str, str]:
        """Get total time for this week."""
        # Calculate start of week (Monday)
        days_since_monday = date.weekday()
        week_start = date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        
        url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/user/{user_id}/time-entries"
        headers = {"X-Api-Key": self.api_key}
        params = {
            "start": week_start.isoformat().replace("+00:00", "Z"),
            "end": week_end.isoformat().replace("+00:00", "Z"),
        }
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    _LOGGER.warning(f"Error getting weekly time: {response.status}")
                    return 0, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")
                
                entries = await response.json()
                total_seconds = 0
                
                for entry in entries:
                    time_interval = entry.get("timeInterval", {})
                    if time_interval.get("start") and time_interval.get("end"):
                        start = datetime.fromisoformat(time_interval["start"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(time_interval["end"].replace("Z", "+00:00"))
                        total_seconds += int((end - start).total_seconds())
                
                return total_seconds, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")
                
        except Exception as err:
            _LOGGER.warning(f"Error calculating weekly time: {err}")
            return 0, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")

    async def _async_get_weekly_daily_breakdown(self, user_id: str, date: datetime, current_timer_duration: int) -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str]]:
        """Get daily breakdown for the current week."""
        # Calculate start of week (Monday)
        days_since_monday = date.weekday()
        week_start = date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
        
        daily_breakdown = {}
        daily_breakdown_total = {}
        daily_breakdown_formatted = {}
        daily_breakdown_total_formatted = {}
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        try:
            for i, day_name in enumerate(day_names):
                day_date = week_start + timedelta(days=i)
                day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/user/{user_id}/time-entries"
                headers = {"X-Api-Key": self.api_key}
                params = {
                    "start": day_start.isoformat().replace("+00:00", "Z"),
                    "end": day_end.isoformat().replace("+00:00", "Z"),
                }
                
                day_seconds = 0
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        entries = await response.json()
                        
                        for entry in entries:
                            time_interval = entry.get("timeInterval", {})
                            if time_interval.get("start") and time_interval.get("end"):
                                start = datetime.fromisoformat(time_interval["start"].replace("Z", "+00:00"))
                                end = datetime.fromisoformat(time_interval["end"].replace("Z", "+00:00"))
                                day_seconds += int((end - start).total_seconds())
                
                # Convert to hours for display
                daily_breakdown[day_name] = round(day_seconds / 3600, 2)
                
                # Format as HH:MM for display
                hours = day_seconds // 3600
                minutes = (day_seconds % 3600) // 60
                daily_breakdown_formatted[day_name] = f"{hours:02d}:{minutes:02d}"
                
                # For total breakdown, add current timer if it's today
                day_total_seconds = day_seconds
                if day_date.date() == date.date():
                    day_total_seconds += current_timer_duration
                
                daily_breakdown_total[day_name] = round(day_total_seconds / 3600, 2)
                
                # Format total as HH:MM for display
                total_hours = day_total_seconds // 3600
                total_minutes = (day_total_seconds % 3600) // 60
                daily_breakdown_total_formatted[day_name] = f"{total_hours:02d}:{total_minutes:02d}"
            
            return daily_breakdown, daily_breakdown_total, daily_breakdown_formatted, daily_breakdown_total_formatted
            
        except Exception as err:
            _LOGGER.warning(f"Error calculating daily breakdown: {err}")
            # Return empty breakdown with 0 hours for each day
            empty_breakdown = {day: 0.0 for day in day_names}
            empty_formatted = {day: "00:00" for day in day_names}
            return empty_breakdown, empty_breakdown.copy(), empty_formatted, empty_formatted.copy()
