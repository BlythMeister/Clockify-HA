# Clockify Home Assistant Integration

A custom Home Assistant integration to monitor your Clockify time tracking activities.

## Features

- **Current Timer Sensor**: Shows your currently active timer with project and task names
- **Weekly Time Sensor**: Displays total time tracked for the current week (Monday to Sunday)
- **Daily Time Sensor**: Shows total time tracked for today
- **Real-time Updates**: Automatically updates every 30 seconds
- **Rich Attributes**: Provides detailed information about your active timer including:
  - Project name and color
  - Task name (if applicable)
  - Timer description
  - Start time and duration
  - Billable status
  - Tags

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/BlythMeister/Clockify-HA`
5. Select "Integration" as the category
6. Click "Add"
7. Find "Clockify" in the integration list and click "Download"
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/clockify` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Configuration > Integrations
2. Click "Add Integration"
3. Search for "Clockify"
4. Enter your Clockify API key and Workspace ID

### Getting Your API Key

1. Go to [Clockify](https://clockify.me)
2. Sign in to your account
3. Go to your Profile settings (click your avatar in the top-right corner)
4. Scroll down to the "API" section
5. Copy your API key

### Getting Your Workspace ID

1. Go to your Clockify workspace
2. Look at the URL in your browser
3. The workspace ID is the string after `/workspaces/` in the URL
4. Example: `https://app.clockify.me/workspaces/5f4f4f4f4f4f4f4f4f4f4f4f/dashboard`
   - Workspace ID: `5f4f4f4f4f4f4f4f4f4f4f4f`

## Sensors

### `sensor.clockify_current_timer`

Shows the current active timer with project and task names.

**States:**

- `"No active timer"` - When no timer is running
- `"Project Name - Task Name"` - When a timer is active with a task
- `"Project Name"` - When a timer is active without a task

**Attributes:**

- `status`: "active" or "inactive"
- `description`: Timer description
- `project_id`: Project ID
- `project_name`: Project name
- `project_color`: Project color (hex code)
- `task_id`: Task ID (if applicable)
- `task_name`: Task name (if applicable)
- `start_time`: Timer start time (ISO format)
- `duration`: Human-readable duration (HH:MM:SS)
- `duration_seconds`: Duration in seconds
- `billable`: Whether the timer is billable
- `tags`: List of tag names

### `sensor.clockify_weekly_time`

Shows the total time tracked for the current week (Monday to Sunday).

**State:** Total hours for the week (decimal format, e.g., 40.5)

**Attributes:**

- `duration_seconds`: Total duration in seconds
- `duration_formatted`: Human-readable duration (HH:MM)
- `week_start`: Start date of the week (YYYY-MM-DD)
- `week_end`: End date of the week (YYYY-MM-DD)

### `sensor.clockify_daily_time`

Shows the total time tracked for today.

**State:** Total hours for today (decimal format, e.g., 8.25)

**Attributes:**

- `duration_seconds`: Total duration in seconds
- `duration_formatted`: Human-readable duration (HH:MM)
- `date`: Current date (YYYY-MM-DD)

## Example Automations

### Notify when timer starts

```yaml
automation:
  - alias: "Clockify Timer Started"
    trigger:
      - platform: state
        entity_id: sensor.clockify_current_timer
        from: "No active timer"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Timer Started"
          message: "Started tracking time for {{ state_attr('sensor.clockify_current_timer', 'project_name') }}"
```

### Turn on focus lights when working

```yaml
automation:
  - alias: "Focus Mode On"
    trigger:
      - platform: state
        entity_id: sensor.clockify_current_timer
        from: "No active timer"
    action:
      - service: light.turn_on
        target:
          entity_id: light.desk_light
        data:
          color_name: blue
          brightness: 200
```

## Example Lovelace Dashboard

### Current Timer Status Card

Here's a beautiful dashboard card to display your current Clockify timer:

```yaml
type: custom:mushroom-template-card
primary: |
  {% if state_attr('sensor.clockify_current_timer', 'status') == 'active' %}
    🔴 {{ states('sensor.clockify_current_timer') }}
  {% else %}
    ⏸️ No Active Timer
  {% endif %}
secondary: |
  {% if state_attr('sensor.clockify_current_timer', 'status') == 'active' %}
    {{ state_attr('sensor.clockify_current_timer', 'description') or 'No description' }}
    {% if state_attr('sensor.clockify_current_timer', 'duration') %}
      • {{ state_attr('sensor.clockify_current_timer', 'duration') }}
    {% endif %}
  {% else %}
    Start a timer in Clockify to begin tracking
  {% endif %}
icon: |
  {% if state_attr('sensor.clockify_current_timer', 'status') == 'active' %}
    mdi:timer
  {% else %}
    mdi:timer-off
  {% endif %}
icon_color: |
  {% if state_attr('sensor.clockify_current_timer', 'status') == 'active' %}
    red
  {% else %}
    grey
  {% endif %}
badge_icon: |
  {% if state_attr('sensor.clockify_current_timer', 'billable') %}
    mdi:currency-usd
  {% endif %}
badge_color: green
tap_action:
  action: more-info
```

### Current Timer Status (Markdown - No Dependencies)

A simple markdown card that works with standard Home Assistant:

```yaml
type: markdown
title: 🔴 Clockify Timer
content: |
  {% if state_attr('sensor.clockify_current_timer', 'status') == 'active' %}
  ## ⏰ Currently Working On:
  **{{ states('sensor.clockify_current_timer') }}**
  
  {% if state_attr('sensor.clockify_current_timer', 'description') %}
  📝 *{{ state_attr('sensor.clockify_current_timer', 'description') }}*
  {% endif %}
  
  ⏱️ **Duration:** {{ state_attr('sensor.clockify_current_timer', 'duration') or 'Starting...' }}
  
  {% if state_attr('sensor.clockify_current_timer', 'billable') %}
  💰 **Billable** | 
  {% endif %}
  🏷️ {{ state_attr('sensor.clockify_current_timer', 'tags') | join(', ') if state_attr('sensor.clockify_current_timer', 'tags') else 'No tags' }}
  
  ---
  ⏰ **Started:** {{ as_timestamp(state_attr('sensor.clockify_current_timer', 'start_time')) | timestamp_custom('%H:%M', true) if state_attr('sensor.clockify_current_timer', 'start_time') else 'Unknown' }}
  {% else %}
  ## ⏸️ No Active Timer
  
  Start a timer in Clockify to begin tracking your work.
  
  📊 **Today:** {{ states('sensor.clockify_daily_time') }}h | **Week:** {{ states('sensor.clockify_weekly_time') }}h
  {% endif %}
```

### Time Tracking Summary Card

A comprehensive overview card showing all your time tracking data:

```yaml
type: entities
title: 📊 Clockify Time Tracking
entities:
  - entity: sensor.clockify_current_timer
    name: Current Timer
    icon: mdi:timer
  - entity: sensor.clockify_daily_time
    name: Today's Total
    icon: mdi:calendar-today
  - entity: sensor.clockify_weekly_time
    name: This Week's Total
    icon: mdi:calendar-week
state_color: true
```

### Minimal Timer Display

For a clean, minimal display:

```yaml
type: glance
title: Clockify Status
entities:
  - entity: sensor.clockify_current_timer
    name: Current
  - entity: sensor.clockify_daily_time
    name: Today
  - entity: sensor.clockify_weekly_time
    name: Week
columns: 3
```

**Note:** The mushroom card example requires the [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) custom component from HACS.

#### Installing Mushroom Cards

1. Open HACS in your Home Assistant instance
2. Go to "Frontend" section
3. Click "Explore & Download Repositories"
4. Search for "Mushroom"
5. Install "Mushroom Cards" by @piitaya
6. Restart Home Assistant
7. Clear your browser cache or hard refresh (Ctrl+F5)

## Support

If you encounter any issues or have feature requests, please [create an issue](https://github.com/BlythMeister/Clockify-HA/issues) on GitHub.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.