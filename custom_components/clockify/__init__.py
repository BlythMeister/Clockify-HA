"""The Clockify integration."""
from __future__ import annotations

import logging
from datetime import timedelta, datetime, timezone

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_WORKSPACE_ID,
    SERVICE_START_TIMER,
    SERVICE_STOP_TIMER,
)

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
    
    # Register services
    await _async_register_services(hass, coordinator)
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Unregister services if no more instances
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_START_TIMER)
            hass.services.async_remove(DOMAIN, SERVICE_STOP_TIMER)
    
    return unload_ok


# Service schemas
START_TIMER_SCHEMA = vol.Schema({
    vol.Optional("description"): cv.string,
    vol.Optional("project_id"): cv.string,
    vol.Optional("task_id"): cv.string,
})

STOP_TIMER_SCHEMA = vol.Schema({})


async def _async_register_services(hass: HomeAssistant, coordinator: ClockifyDataUpdateCoordinator) -> None:
    """Register Clockify services."""
    
    async def async_start_timer(call: ServiceCall) -> None:
        """Handle start timer service call."""
        description = call.data.get("description")
        project_id = call.data.get("project_id")
        task_id = call.data.get("task_id")
        
        await coordinator.async_start_timer(description, project_id, task_id)
    
    async def async_stop_timer(call: ServiceCall) -> None:
        """Handle stop timer service call."""
        await coordinator.async_stop_timer()
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_TIMER,
        async_start_timer,
        schema=START_TIMER_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_TIMER,
        async_stop_timer,
        schema=STOP_TIMER_SCHEMA,
    )

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
                
                # Get user's member profile for workspace-specific settings
                member_profile = await self._async_get_member_profile(user_id)
                
                # Get week start day from member profile
                week_start_day = "MONDAY"
                if member_profile:
                    week_start_day = member_profile.get("weekStart", "MONDAY")
                
                # Use member profile for capacity calculations
                user_schedule = member_profile if member_profile else None
                
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
                    weekly_duration, week_start, week_end = await self._async_get_weekly_time(user_id, now, week_start_day)
                except Exception as err:
                    _LOGGER.warning(f"Error getting weekly time: {err}")
                    weekly_duration = 0
                    week_start = now.strftime("%Y-%m-%d")
                    week_end = now.strftime("%Y-%m-%d")
                
                # Calculate totals including current timer
                current_timer_duration = 0
                if current_timer and current_timer.get("timeInterval", {}).get("start"):
                    try:
                        # Check if current timer should be excluded from totals
                        if not await self._should_exclude_time_entry(current_timer, {}):
                            start_time_str = current_timer["timeInterval"]["start"]
                            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                            current_timer_duration = int((now - start_time).total_seconds())
                        else:
                            current_timer_duration = 0
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
                    daily_breakdown, daily_breakdown_total, daily_breakdown_formatted, daily_breakdown_total_formatted = await self._async_get_weekly_daily_breakdown(user_id, now, current_timer, current_timer_duration, week_start_day)
                except Exception as err:
                    _LOGGER.warning(f"Error getting weekly daily breakdown: {err}")
                    daily_breakdown = {}
                    daily_breakdown_total = {}
                    daily_breakdown_formatted = {}
                    daily_breakdown_total_formatted = {}
                
                # Calculate expected hours and progress metrics
                expected_hours = self._calculate_expected_hours(user_schedule, now, week_start_day)
                
                # Daily progress metrics (for completed time)
                daily_progress = self._calculate_progress_metrics(
                    daily_duration,
                    expected_hours["daily_expected_seconds"]
                )
                
                # Daily total progress metrics (including current timer)
                daily_total_progress = self._calculate_progress_metrics(
                    daily_total,
                    expected_hours["daily_expected_seconds"]
                )
                
                # Weekly progress metrics (for completed time) - full week
                weekly_progress = self._calculate_progress_metrics(
                    weekly_duration,
                    expected_hours["weekly_expected_seconds"]
                )
                
                # Weekly total progress metrics (including current timer) - full week
                weekly_total_progress = self._calculate_progress_metrics(
                    weekly_total,
                    expected_hours["weekly_expected_seconds"]
                )
                
                # Weekly to-date progress metrics (for completed time)
                weekly_to_date_progress = self._calculate_progress_metrics(
                    weekly_duration,
                    expected_hours["weekly_to_date_expected_seconds"]
                )
                
                # Weekly to-date total progress metrics (including current timer)
                weekly_to_date_total_progress = self._calculate_progress_metrics(
                    weekly_total,
                    expected_hours["weekly_to_date_expected_seconds"]
                )
                
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
                    # Expected hours
                    "daily_expected_seconds": expected_hours["daily_expected_seconds"],
                    "daily_expected_hours": expected_hours["daily_expected_hours"],
                    "weekly_expected_seconds": expected_hours["weekly_expected_seconds"],
                    "weekly_expected_hours": expected_hours["weekly_expected_hours"],
                    "weekly_to_date_expected_seconds": expected_hours["weekly_to_date_expected_seconds"],
                    "weekly_to_date_expected_hours": expected_hours["weekly_to_date_expected_hours"],
                    "weekly_remaining_expected_seconds": expected_hours["weekly_remaining_expected_seconds"],
                    "weekly_remaining_expected_hours": expected_hours["weekly_remaining_expected_hours"],
                    "working_days": expected_hours["working_days"],
                    # Daily progress (completed only)
                    "daily_progress_percent": daily_progress["progress_percent"],
                    "daily_remaining_seconds": daily_progress["remaining_seconds"],
                    "daily_remaining_hours": daily_progress["remaining_hours"],
                    "daily_remaining_formatted": daily_progress["remaining_formatted"],
                    # Daily total progress (including current timer)
                    "daily_total_progress_percent": daily_total_progress["progress_percent"],
                    "daily_total_remaining_seconds": daily_total_progress["remaining_seconds"],
                    "daily_total_remaining_hours": daily_total_progress["remaining_hours"],
                    "daily_total_remaining_formatted": daily_total_progress["remaining_formatted"],
                    # Weekly progress (completed only) - full week
                    "weekly_progress_percent": weekly_progress["progress_percent"],
                    "weekly_remaining_seconds": weekly_progress["remaining_seconds"],
                    "weekly_remaining_hours": weekly_progress["remaining_hours"],
                    "weekly_remaining_formatted": weekly_progress["remaining_formatted"],
                    # Weekly total progress (including current timer) - full week
                    "weekly_total_progress_percent": weekly_total_progress["progress_percent"],
                    "weekly_total_remaining_seconds": weekly_total_progress["remaining_seconds"],
                    "weekly_total_remaining_hours": weekly_total_progress["remaining_hours"],
                    "weekly_total_remaining_formatted": weekly_total_progress["remaining_formatted"],
                    # Weekly to-date progress (completed only)
                    "weekly_to_date_progress_percent": weekly_to_date_progress["progress_percent"],
                    "weekly_to_date_remaining_seconds": weekly_to_date_progress["remaining_seconds"],
                    "weekly_to_date_remaining_hours": weekly_to_date_progress["remaining_hours"],
                    "weekly_to_date_remaining_formatted": weekly_to_date_progress["remaining_formatted"],
                    # Weekly to-date total progress (including current timer)
                    "weekly_to_date_total_progress_percent": weekly_to_date_total_progress["progress_percent"],
                    "weekly_to_date_total_remaining_seconds": weekly_to_date_total_progress["remaining_seconds"],
                    "weekly_to_date_total_remaining_hours": weekly_to_date_total_progress["remaining_hours"],
                    "weekly_to_date_total_remaining_formatted": weekly_to_date_total_progress["remaining_formatted"],
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
    
    def _get_week_start_offset(self, week_start_day: str) -> int:
        """
        Get the offset for the week start day.
        
        Args:
            week_start_day: One of 'MONDAY', 'SUNDAY', 'SATURDAY'
            
        Returns:
            The weekday number (0=Monday, 6=Sunday) that starts the week
        """
        week_start_map = {
            "MONDAY": 0,
            "SUNDAY": 6,
            "SATURDAY": 5,
        }
        return week_start_map.get(week_start_day, 0)  # Default to Monday
    
    def _get_week_day_order(self, week_start_day: str) -> list[str]:
        """
        Get the ordered list of day names starting from the configured week start.
        
        Args:
            week_start_day: One of 'MONDAY', 'SUNDAY', 'SATURDAY'
            
        Returns:
            List of day names in order starting from week_start_day
        """
        # Standard Python weekday order (0=Mon, 6=Sun)
        standard_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        week_start_offset = self._get_week_start_offset(week_start_day)
        
        # Rotate the list to start from the configured week start
        return standard_order[week_start_offset:] + standard_order[:week_start_offset]
    
    def _calculate_days_since_week_start(self, current_date: datetime, week_start_day: str) -> int:
        """
        Calculate how many days have passed since the start of the week.
        
        Args:
            current_date: The current date
            week_start_day: One of 'MONDAY', 'SUNDAY', 'SATURDAY'
            
        Returns:
            Number of days since the week started (0 = week start day)
        """
        week_start_offset = self._get_week_start_offset(week_start_day)
        current_weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        
        # Calculate days since week start
        if current_weekday >= week_start_offset:
            return current_weekday - week_start_offset
        else:
            # Week wraps around (e.g., Sunday start, current day is Mon-Sat)
            return 7 - week_start_offset + current_weekday
    
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

    async def _async_get_member_profile(self, user_id: str):
        """Get workspace member profile including work week configuration and settings."""
        # Use the member profile API to get workspace-specific user settings
        url = f"https://api.clockify.me/api/v1/workspaces/{self.workspace_id}/member-profile/{user_id}"
        headers = {"X-Api-Key": self.api_key}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    _LOGGER.warning(f"Error getting member profile: {response.status}")
                    return None
                return await response.json()
        except Exception as err:
            _LOGGER.warning(f"Error fetching member profile: {err}")
            return None

    def _calculate_expected_hours(self, user_schedule: dict, current_date: datetime, week_start_day: str = "MONDAY") -> dict:
        """Calculate expected hours based on user schedule settings.
        
        Args:
            user_schedule: User schedule settings from the API
            current_date: The current date/time
            week_start_day: The day the week starts ('MONDAY', 'SUNDAY', or 'SATURDAY')
        """
        result = {
            "daily_expected_seconds": 0,
            "daily_expected_hours": 0.0,
            "weekly_expected_seconds": 0,
            "weekly_expected_hours": 0.0,
            "weekly_to_date_expected_seconds": 0,
            "weekly_to_date_expected_hours": 0.0,
            "weekly_remaining_expected_seconds": 0,
            "weekly_remaining_expected_hours": 0.0,
            "working_days": [],
        }
        
        if not user_schedule:
            # Default to 8 hours/day, Mon-Fri if no settings available
            _LOGGER.info("No user schedule settings available, using defaults")
            day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_date.weekday()]
            if day_name in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
                result["daily_expected_seconds"] = 8 * 3600
                result["daily_expected_hours"] = 8.0
                result["working_days"] = ["Mon", "Tue", "Wed", "Thu", "Fri"]
            result["weekly_expected_seconds"] = 5 * 8 * 3600
            result["weekly_expected_hours"] = 40.0
            
            # Calculate to-date (only count working days up to today)
            days_since_week_start = self._calculate_days_since_week_start(current_date, week_start_day)
            week_day_order = self._get_week_day_order(week_start_day)
            working_days_to_date = min(days_since_week_start + 1, 5)  # Max 5 working days
            result["weekly_to_date_expected_seconds"] = working_days_to_date * 8 * 3600
            result["weekly_to_date_expected_hours"] = working_days_to_date * 8.0
            
            # Calculate remaining (only count working days after today)
            working_days_remaining = 0
            for i in range(days_since_week_start + 1, 7):  # Days after today
                if week_day_order[i] in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
                    working_days_remaining += 1
            result["weekly_remaining_expected_seconds"] = working_days_remaining * 8 * 3600
            result["weekly_remaining_expected_hours"] = working_days_remaining * 8.0
            
            return result
        
        # First, try to parse member profile format (workCapacity + workingDays)
        if "workCapacity" in user_schedule and "workingDays" in user_schedule:
            # Parse work capacity (e.g., "PT7H")
            work_capacity_str = user_schedule.get("workCapacity", "PT8H")
            hours_per_day = self._parse_iso_duration(work_capacity_str)
            
            # Parse working days - can be either a list or a JSON string
            working_days_raw = user_schedule.get("workingDays", [])
            if isinstance(working_days_raw, str):
                # If it's a JSON string, parse it
                import json as json_lib
                try:
                    working_days_api = json_lib.loads(working_days_raw)
                except (json_lib.JSONDecodeError, TypeError):
                    working_days_api = []
            else:
                # If it's already a list, use it directly
                working_days_api = working_days_raw
            
            # Map Clockify day names to our short names
            day_mapping = {
                "MONDAY": "Mon",
                "TUESDAY": "Tue",
                "WEDNESDAY": "Wed",
                "THURSDAY": "Thu",
                "FRIDAY": "Fri",
                "SATURDAY": "Sat",
                "SUNDAY": "Sun"
            }
            
            working_days = [day_mapping.get(day, day[:3]) for day in working_days_api]
            result["working_days"] = working_days
            
            # Get current day name
            current_day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_date.weekday()]
            
            # Calculate daily expected hours
            if current_day_name in working_days:
                result["daily_expected_seconds"] = int(hours_per_day * 3600)
                result["daily_expected_hours"] = float(hours_per_day)
            
            # Calculate weekly expected hours
            result["weekly_expected_seconds"] = len(working_days) * int(hours_per_day * 3600)
            result["weekly_expected_hours"] = len(working_days) * float(hours_per_day)
            
            # Calculate expected hours for week to date
            days_since_week_start = self._calculate_days_since_week_start(current_date, week_start_day)
            week_day_order = self._get_week_day_order(week_start_day)
            working_days_to_date = 0
            
            for i in range(days_since_week_start + 1):
                if week_day_order[i] in working_days:
                    working_days_to_date += 1
            
            result["weekly_to_date_expected_seconds"] = working_days_to_date * int(hours_per_day * 3600)
            result["weekly_to_date_expected_hours"] = working_days_to_date * float(hours_per_day)
            
            # Calculate expected hours for remaining days of the week (after today)
            working_days_remaining = 0
            for i in range(days_since_week_start + 1, 7):  # Days after today until end of week
                if week_day_order[i] in working_days:
                    working_days_remaining += 1
            
            result["weekly_remaining_expected_seconds"] = working_days_remaining * int(hours_per_day * 3600)
            result["weekly_remaining_expected_hours"] = working_days_remaining * float(hours_per_day)
            
            return result
        
        # Parse user schedule settings
        # Clockify scheduling API returns structure like:
        # {
        #   "workWeek": {
        #     "monday": { "duration": "PT6H", "isWorkDay": true },
        #     "tuesday": { "duration": "PT6H", "isWorkDay": true },
        #     ...
        #   }
        # }
        work_week = user_schedule.get("workWeek", {})
        
        if not work_week:
            # Try alternative structure (daysOfWeek/hoursPerDay for workspace defaults)
            days_of_week = user_schedule.get("daysOfWeek", [])
            hours_per_day = user_schedule.get("hoursPerDay", 8)
            
            if days_of_week:
                # Map Clockify day names to our short names
                day_mapping = {
                    "MONDAY": "Mon",
                    "TUESDAY": "Tue",
                    "WEDNESDAY": "Wed",
                    "THURSDAY": "Thu",
                    "FRIDAY": "Fri",
                    "SATURDAY": "Sat",
                    "SUNDAY": "Sun"
                }
                
                working_days = [day_mapping.get(day, day[:3]) for day in days_of_week]
                result["working_days"] = working_days
                
                # Get current day name
                current_day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_date.weekday()]
                
                # Calculate daily expected hours
                if current_day_name in working_days:
                    result["daily_expected_seconds"] = int(hours_per_day * 3600)
                    result["daily_expected_hours"] = float(hours_per_day)
                
                # Calculate weekly expected hours
                result["weekly_expected_seconds"] = len(working_days) * int(hours_per_day * 3600)
                result["weekly_expected_hours"] = len(working_days) * float(hours_per_day)
                
                # Calculate expected hours for week to date
                days_since_week_start = self._calculate_days_since_week_start(current_date, week_start_day)
                week_day_order = self._get_week_day_order(week_start_day)
                working_days_to_date = 0
                
                for i in range(days_since_week_start + 1):
                    if week_day_order[i] in working_days:
                        working_days_to_date += 1
                
                result["weekly_to_date_expected_seconds"] = working_days_to_date * int(hours_per_day * 3600)
                result["weekly_to_date_expected_hours"] = working_days_to_date * float(hours_per_day)
                
                # Calculate expected hours for remaining days of the week (after today)
                working_days_remaining = 0
                for i in range(days_since_week_start + 1, 7):  # Days after today until end of week
                    if week_day_order[i] in working_days:
                        working_days_remaining += 1
                
                result["weekly_remaining_expected_seconds"] = working_days_remaining * int(hours_per_day * 3600)
                result["weekly_remaining_expected_hours"] = working_days_remaining * float(hours_per_day)
                
                return result
        
        # Parse the workWeek structure with per-day durations
        day_mapping = {
            "monday": "Mon",
            "tuesday": "Tue",
            "wednesday": "Wed",
            "thursday": "Thu",
            "friday": "Fri",
            "saturday": "Sat",
            "sunday": "Sun"
        }
        
        # Build working days list and calculate total hours
        working_days = []
        daily_hours = {}
        
        for api_day, short_day in day_mapping.items():
            day_data = work_week.get(api_day, {})
            is_work_day = day_data.get("isWorkDay", False)
            
            if is_work_day:
                working_days.append(short_day)
                
                # Parse duration (format: "PT6H" or "PT6H30M")
                duration_str = day_data.get("duration", "PT0H")
                hours = self._parse_iso_duration(duration_str)
                daily_hours[short_day] = hours
        
        result["working_days"] = working_days
        
        # Get current day name
        current_day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_date.weekday()]
        
        # Calculate daily expected hours for today
        if current_day_name in daily_hours:
            result["daily_expected_seconds"] = int(daily_hours[current_day_name] * 3600)
            result["daily_expected_hours"] = daily_hours[current_day_name]
        
        # Calculate weekly expected hours (sum of all working days)
        total_weekly_hours = sum(daily_hours.values())
        result["weekly_expected_seconds"] = int(total_weekly_hours * 3600)
        result["weekly_expected_hours"] = total_weekly_hours
        
        # Calculate expected hours for week to date
        days_since_week_start = self._calculate_days_since_week_start(current_date, week_start_day)
        week_day_order = self._get_week_day_order(week_start_day)
        week_to_date_hours = 0
        
        for i in range(days_since_week_start + 1):  # Include today
            day_name = week_day_order[i]
            if day_name in daily_hours:
                week_to_date_hours += daily_hours[day_name]
        
        result["weekly_to_date_expected_seconds"] = int(week_to_date_hours * 3600)
        result["weekly_to_date_expected_hours"] = week_to_date_hours
        
        # Calculate expected hours for remaining days of the week (after today)
        week_remaining_hours = 0
        for i in range(days_since_week_start + 1, 7):  # Days after today until end of week
            day_name = week_day_order[i]
            if day_name in daily_hours:
                week_remaining_hours += daily_hours[day_name]
        
        result["weekly_remaining_expected_seconds"] = int(week_remaining_hours * 3600)
        result["weekly_remaining_expected_hours"] = week_remaining_hours
        
        return result
    
    def _parse_iso_duration(self, duration: str) -> float:
        """Parse ISO 8601 duration format (e.g., PT6H, PT6H30M) to hours."""
        try:
            # Remove 'PT' prefix
            if not duration.startswith("PT"):
                return 0.0
            
            duration = duration[2:]
            hours = 0.0
            minutes = 0.0
            
            # Parse hours
            if "H" in duration:
                hours_part = duration.split("H")[0]
                hours = float(hours_part)
                duration = duration.split("H")[1] if "H" in duration else ""
            
            # Parse minutes
            if "M" in duration:
                minutes_part = duration.split("M")[0]
                minutes = float(minutes_part)
            
            return hours + (minutes / 60.0)
        except (ValueError, IndexError) as err:
            _LOGGER.warning(f"Error parsing duration '{duration}': {err}")
            return 0.0

    def _calculate_progress_metrics(self, logged_seconds: int, expected_seconds: int) -> dict:
        """Calculate progress percentage and remaining time."""
        result = {
            "progress_percent": 0.0,
            "remaining_seconds": 0,
            "remaining_hours": 0.0,
            "remaining_formatted": "00:00",
        }
        
        if expected_seconds > 0:
            result["progress_percent"] = round((logged_seconds / expected_seconds) * 100, 1)
            result["remaining_seconds"] = max(0, expected_seconds - logged_seconds)
            result["remaining_hours"] = round(result["remaining_seconds"] / 3600, 2)
            
            # Format remaining time as HH:MM
            hours = result["remaining_seconds"] // 3600
            minutes = (result["remaining_seconds"] % 3600) // 60
            result["remaining_formatted"] = f"{hours:02d}:{minutes:02d}"
        
        return result

    async def _should_exclude_time_entry(self, entry: dict, project_cache: dict = None) -> bool:
        """Check if a time entry should be excluded from totals."""
        try:
            # Check if it's a BREAK type entry
            if entry.get("type") == "BREAK":
                return True
            
            # Check if it's in a "Breaks" project
            project_id = entry.get("projectId")
            if project_id:
                # Use cached project data if available
                if project_cache and project_id in project_cache:
                    project_data = project_cache[project_id]
                else:
                    project_data = await self._async_get_project(project_id)
                    # Cache the result for future use
                    if project_cache is not None:
                        project_cache[project_id] = project_data
                
                if project_data and project_data.get("name", "").lower() == "breaks":
                    return True
            
            return False
        except Exception as err:
            _LOGGER.warning(f"Error checking if entry should be excluded: {err}")
            return False
    
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
                project_cache = {}  # Cache projects for this calculation
                
                for entry in entries:
                    # Skip excluded entries (breaks)
                    if await self._should_exclude_time_entry(entry, project_cache):
                        continue
                        
                    time_interval = entry.get("timeInterval", {})
                    if time_interval.get("start") and time_interval.get("end"):
                        start = datetime.fromisoformat(time_interval["start"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(time_interval["end"].replace("Z", "+00:00"))
                        total_seconds += int((end - start).total_seconds())
                
                return total_seconds
                
        except Exception as err:
            _LOGGER.warning(f"Error calculating daily time: {err}")
            return 0
    
    async def _async_get_weekly_time(self, user_id: str, date: datetime, week_start_day: str = "MONDAY") -> tuple[int, str, str]:
        """Get total time for this week.
        
        Args:
            user_id: The user ID
            date: The current date
            week_start_day: The day the week starts ('MONDAY', 'SUNDAY', or 'SATURDAY')
        """
        # Calculate start of week based on user's week start setting
        days_since_week_start = self._calculate_days_since_week_start(date, week_start_day)
        week_start = date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_week_start)
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
                project_cache = {}  # Cache projects for this calculation
                
                for entry in entries:
                    # Skip excluded entries (breaks)
                    if await self._should_exclude_time_entry(entry, project_cache):
                        continue
                        
                    time_interval = entry.get("timeInterval", {})
                    if time_interval.get("start") and time_interval.get("end"):
                        start = datetime.fromisoformat(time_interval["start"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(time_interval["end"].replace("Z", "+00:00"))
                        total_seconds += int((end - start).total_seconds())
                
                return total_seconds, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")
                
        except Exception as err:
            _LOGGER.warning(f"Error calculating weekly time: {err}")
            return 0, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")

    async def _async_get_weekly_daily_breakdown(self, user_id: str, date: datetime, current_timer: dict, current_timer_duration: int, week_start_day: str = "MONDAY") -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str]]:
        """Get daily breakdown for the current week.
        
        Args:
            user_id: The user ID
            date: The current date
            current_timer: The current active timer
            current_timer_duration: Duration of the current timer in seconds
            week_start_day: The day the week starts ('MONDAY', 'SUNDAY', or 'SATURDAY')
        """
        # Calculate start of week based on user's week start setting
        days_since_week_start = self._calculate_days_since_week_start(date, week_start_day)
        week_start = date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_week_start)
        
        daily_breakdown = {}
        daily_breakdown_total = {}
        daily_breakdown_formatted = {}
        daily_breakdown_total_formatted = {}
        week_day_order = self._get_week_day_order(week_start_day)
        
        try:
            # Create a shared project cache for all days to minimize API calls
            project_cache = {}
            
            for i, day_name in enumerate(week_day_order):
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
                            # Skip excluded entries (breaks) - using shared cache
                            if await self._should_exclude_time_entry(entry, project_cache):
                                continue
                                
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
                
                # For total breakdown, add current timer if it's today and not excluded
                day_total_seconds = day_seconds
                if day_date.date() == date.date():
                    # Only add current timer duration if it's not a break timer
                    if current_timer and not await self._should_exclude_time_entry(current_timer, project_cache):
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
            empty_breakdown = {day: 0.0 for day in week_day_order}
            empty_formatted = {day: "00:00" for day in week_day_order}
            return empty_breakdown, empty_breakdown.copy(), empty_formatted, empty_formatted.copy()

    async def async_start_timer(self, description: str = None, project_id: str = None, task_id: str = None) -> bool:
        """Start a new timer in Clockify."""
        try:
            url = f"https://api.clockify.me/api/v1/workspaces/{self._workspace_id}/time-entries"
            
            # Build the request payload
            payload = {
                "start": datetime.now(timezone.utc).isoformat(),
            }
            
            if description:
                payload["description"] = description
            
            if project_id:
                payload["projectId"] = project_id
            
            if task_id:
                payload["taskId"] = task_id
            
            headers = {
                "X-Api-Key": self._api_key,
                "Content-Type": "application/json"
            }
            
            async with async_timeout.timeout(10):
                async with self._session.post(url, json=payload, headers=headers) as response:
                    if response.status == 201:
                        _LOGGER.info("Timer started successfully")
                        # Trigger immediate data update
                        await self.async_request_refresh()
                        return True
                    else:
                        response_text = await response.text()
                        _LOGGER.error(f"Failed to start timer: {response.status} - {response_text}")
                        return False
                        
        except Exception as err:
            _LOGGER.error(f"Error starting timer: {err}")
            return False

    async def async_stop_timer(self) -> bool:
        """Stop the currently running timer in Clockify."""
        try:
            # Get current user info to get the user ID
            if not self.data or not self.data.get("user"):
                _LOGGER.error("No user data available for stopping timer")
                return False
            
            user_id = self.data["user"]["id"]
            url = f"https://api.clockify.me/api/v1/workspaces/{self._workspace_id}/user/{user_id}/time-entries"
            
            payload = {
                "end": datetime.now(timezone.utc).isoformat(),
            }
            
            headers = {
                "X-Api-Key": self._api_key,
                "Content-Type": "application/json"
            }
            
            async with async_timeout.timeout(10):
                async with self._session.patch(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        _LOGGER.info("Timer stopped successfully")
                        # Trigger immediate data update
                        await self.async_request_refresh()
                        return True
                    else:
                        response_text = await response.text()
                        _LOGGER.error(f"Failed to stop timer: {response.status} - {response_text}")
                        return False
                        
        except Exception as err:
            _LOGGER.error(f"Error stopping timer: {err}")
            return False
