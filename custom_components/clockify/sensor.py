"""Sensor platform for Clockify integration."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Clockify sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([ClockifyCurrentTimerSensor(coordinator, entry)])

class ClockifyCurrentTimerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Clockify current timer sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current_timer"
        self._attr_name = "Clockify Current Timer"
        self._attr_icon = "mdi:timer"
        self._entry = entry

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        current_timer = self.coordinator.data.get("current_timer")
        
        if not current_timer:
            return "No active timer"
        
        # Get project and task names
        project_name = "Unknown Project"
        task_name = ""
        
        project_data = self.coordinator.data.get("project")
        if project_data:
            project_name = project_data.get("name", "Unknown Project")
        
        task_data = self.coordinator.data.get("task")
        if task_data:
            task_name = f" - {task_data.get('name', 'Unknown Task')}"
        
        return f"{project_name}{task_name}"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None
            
        current_timer = self.coordinator.data.get("current_timer")
        
        if not current_timer:
            return {
                "status": "inactive",
                "description": None,
                "project_id": None,
                "project_name": None,
                "task_id": None,
                "task_name": None,
                "start_time": None,
                "duration": None
            }
        
        # Parse start time
        start_time = None
        duration = None
        if current_timer.get("timeInterval", {}).get("start"):
            start_time_str = current_timer["timeInterval"]["start"]
            try:
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                # Calculate duration
                now = datetime.now(timezone.utc)
                duration_seconds = int((now - start_time).total_seconds())
                hours = duration_seconds // 3600
                minutes = (duration_seconds % 3600) // 60
                duration = f"{hours:02d}:{minutes:02d}:{duration_seconds % 60:02d}"
            except ValueError:
                pass
        
        project_data = self.coordinator.data.get("project")
        task_data = self.coordinator.data.get("task")
        
        return {
            "status": "active",
            "description": current_timer.get("description", ""),
            "project_id": current_timer.get("projectId"),
            "project_name": project_data.get("name") if project_data else None,
            "project_color": project_data.get("color") if project_data else None,
            "task_id": current_timer.get("taskId"),
            "task_name": task_data.get("name") if task_data else None,
            "start_time": start_time.isoformat() if start_time else None,
            "duration": duration,
            "duration_seconds": duration_seconds if start_time else None,
            "billable": current_timer.get("billable", False),
            "tags": [tag.get("name") for tag in current_timer.get("tags", [])],
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
