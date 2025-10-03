# Clockify Home Assistant Integration

A custom Home Assistant integration to monitor and control your Clockify time tracking activities directly from Home Assistant.

## Features

- **Current Timer Sensor**: Shows your currently active timer with project and task names
- **Weekly Time Sensor**: Displays total time tracked for the current week (Monday to Sunday)
- **Daily Time Sensor**: Shows total time tracked for today
- **Progress Tracking**: Automatic progress tracking based on your Clockify workspace settings
  - Daily and weekly progress percentages
  - Remaining time calculations
  - Expected hours based on your configured work capacity
  - Week-to-date vs full week progress metrics
- **Timer Actions**: Start and stop timers directly from Home Assistant automations
- **Break Time Exclusion**: Automatically excludes break time from all time calculations
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

### What's New

- **📊 Progress Tracking**: All sensors now include automatic progress tracking based on your Clockify workspace settings - see how you're tracking against your daily/weekly goals with percentage complete and remaining time
- **🎯 Timer Actions**: Start and stop timers directly from Home Assistant using `clockify.start_timer` and `clockify.stop_timer` services
- **☕ Break Time Exclusion**: All time calculations now automatically exclude break time for more accurate work tracking
- **🤖 Enhanced Automations**: Create powerful automations to manage your time tracking based on location, schedule, or other Home Assistant entities

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

Shows the total time tracked for the current week (Monday to Sunday) from completed time entries only.

**State:** Total hours for the week (decimal format, e.g., 40.5)

**Attributes:**

- `duration_seconds`: Total duration in seconds
- `duration_formatted`: Human-readable duration (HH:MM)
- `week_start`: Start date of the week (YYYY-MM-DD)
- `week_end`: End date of the week (YYYY-MM-DD)
- `Mon`: Hours tracked on Monday (decimal format)
- `Tue`: Hours tracked on Tuesday (decimal format)
- `Wed`: Hours tracked on Wednesday (decimal format)
- `Thu`: Hours tracked on Thursday (decimal format)
- `Fri`: Hours tracked on Friday (decimal format)
- `Sat`: Hours tracked on Saturday (decimal format)
- `Sun`: Hours tracked on Sunday (decimal format)
- `Mon_formatted`: Hours tracked on Monday (HH:MM format)
- `Tue_formatted`: Hours tracked on Tuesday (HH:MM format)
- `Wed_formatted`: Hours tracked on Wednesday (HH:MM format)
- `Thu_formatted`: Hours tracked on Thursday (HH:MM format)
- `Fri_formatted`: Hours tracked on Friday (HH:MM format)
- `Sat_formatted`: Hours tracked on Saturday (HH:MM format)
- `Sun_formatted`: Hours tracked on Sunday (HH:MM format)
- **Progress Tracking:**
  - `expected_hours`: Expected work hours for the full week
  - `expected_hours_to_date`: Expected work hours from Monday to today
  - `progress_percent`: Progress percentage against full week's expected hours
  - `progress_percent_to_date`: Progress percentage against week-to-date expected hours
  - `remaining_hours`: Hours remaining to meet full week goal
  - `remaining_hours_to_date`: Hours remaining to meet week-to-date goal
  - `remaining_formatted`: Remaining time for full week (HH:MM format)
  - `remaining_formatted_to_date`: Remaining time for week-to-date (HH:MM format)
  - `working_days`: List of working days from Clockify settings (e.g., ["Mon", "Tue", "Wed", "Thu", "Fri"])

### `sensor.clockify_weekly_total`

Shows the total time tracked for the current week (Monday to Sunday) including any currently active timer.

**State:** Total hours for the week (decimal format, e.g., 40.5)

**Attributes:**

- `duration_seconds`: Total duration in seconds
- `duration_formatted`: Human-readable duration (HH:MM)
- `week_start`: Start date of the week (YYYY-MM-DD)
- `week_end`: End date of the week (YYYY-MM-DD)
- `includes_current_timer`: Whether the current active timer is included
- `completed_time_seconds`: Completed time entries only (excluding current timer)
- `Mon`: Hours tracked on Monday including current timer if today (decimal format)
- `Tue`: Hours tracked on Tuesday including current timer if today (decimal format)
- `Wed`: Hours tracked on Wednesday including current timer if today (decimal format)
- `Thu`: Hours tracked on Thursday including current timer if today (decimal format)
- `Fri`: Hours tracked on Friday including current timer if today (decimal format)
- `Sat`: Hours tracked on Saturday including current timer if today (decimal format)
- `Sun`: Hours tracked on Sunday including current timer if today (decimal format)
- `Mon_formatted`: Hours tracked on Monday including current timer if today (HH:MM format)
- `Tue_formatted`: Hours tracked on Tuesday including current timer if today (HH:MM format)
- `Wed_formatted`: Hours tracked on Wednesday including current timer if today (HH:MM format)
- `Thu_formatted`: Hours tracked on Thursday including current timer if today (HH:MM format)
- `Fri_formatted`: Hours tracked on Friday including current timer if today (HH:MM format)
- `Sat_formatted`: Hours tracked on Saturday including current timer if today (HH:MM format)
- `Sun_formatted`: Hours tracked on Sunday including current timer if today (HH:MM format)
- **Progress Tracking:**
  - `expected_hours`: Expected work hours for the full week
  - `expected_hours_to_date`: Expected work hours from Monday to today
  - `progress_percent`: Progress percentage against full week's expected hours
  - `progress_percent_to_date`: Progress percentage against week-to-date expected hours
  - `remaining_hours`: Hours remaining to meet full week goal
  - `remaining_hours_to_date`: Hours remaining to meet week-to-date goal
  - `remaining_formatted`: Remaining time for full week (HH:MM format)
  - `remaining_formatted_to_date`: Remaining time for week-to-date (HH:MM format)
  - `working_days`: List of working days from Clockify settings (e.g., ["Mon", "Tue", "Wed", "Thu", "Fri"])

### `sensor.clockify_daily_time`

Shows the total time tracked for today from completed time entries only.

**State:** Total hours for today (decimal format, e.g., 8.25)

**Attributes:**

- `duration_seconds`: Total duration in seconds
- `duration_formatted`: Human-readable duration (HH:MM)
- `date`: Current date (YYYY-MM-DD)
- **Progress Tracking:**
  - `expected_hours`: Expected work hours for today (0 if not a working day)
  - `progress_percent`: Progress percentage against expected hours for today
  - `remaining_hours`: Hours remaining to meet daily goal
  - `remaining_formatted`: Remaining time in HH:MM format

### `sensor.clockify_daily_total`

Shows the total time tracked for today including any currently active timer.

**State:** Total hours for today (decimal format, e.g., 8.25)

**Attributes:**

- `duration_seconds`: Total duration in seconds
- `duration_formatted`: Human-readable duration (HH:MM)
- `date`: Current date (YYYY-MM-DD)
- `includes_current_timer`: Whether the current active timer is included
- `completed_time_seconds`: Completed time entries only (excluding current timer)
- **Progress Tracking:**
  - `expected_hours`: Expected work hours for today (0 if not a working day)
  - `progress_percent`: Progress percentage against expected hours for today
  - `remaining_hours`: Hours remaining to meet daily goal
  - `remaining_formatted`: Remaining time in HH:MM format

## Timer Actions

The integration provides services to start and stop timers directly from Home Assistant, enabling automation of your time tracking.

### `clockify.start_timer`

Start a new timer in Clockify with optional parameters.

**Parameters:**

- `description` (optional): Description for the time entry
- `project_id` (optional): Clockify project ID to assign to the timer
- `task_id` (optional): Clockify task ID to assign to the timer

**Examples:**

```yaml
# Start a basic timer
- service: clockify.start_timer

# Start timer with description
- service: clockify.start_timer
  data:
    description: "Working on Home Assistant integration"

# Start timer with project and task
- service: clockify.start_timer
  data:
    description: "Bug fixing"
    project_id: "5f9b3b3b9b3b3b3b3b3b3b3b"
    task_id: "5f9b3b3b9b3b3b3b3b3b3b3c"
```

### `clockify.stop_timer`

Stop the currently running timer in Clockify.

**Parameters:** None

**Example:**

```yaml
# Stop the current timer
- service: clockify.stop_timer
```

## Break Time Exclusion

The integration automatically excludes break time from all time calculations to provide accurate work time tracking:

- **Type-based exclusion**: Time entries with `type: "BREAK"` are excluded from totals
- **Project-based exclusion**: Time entries in projects named "Breaks" are excluded from totals
- **Current timer exclusion**: If the currently running timer is a break timer, it's excluded from current totals

This ensures that all sensors (`clockify_daily_time`, `clockify_daily_total`, `clockify_weekly_time`, `clockify_weekly_total`) show only actual work time, not break periods.

**Note:** Break time entries are still tracked in Clockify normally - they're only excluded from the Home Assistant sensor calculations for more accurate work time reporting.

## Progress Tracking

All time sensors now include automatic progress tracking based on your Clockify workspace settings. The integration fetches your configured working days and daily work capacity directly from Clockify, so there's no additional configuration needed in Home Assistant.

### How It Works

1. **Workspace Settings**: The integration fetches your workweek configuration from Clockify (working days and hours per day)
2. **Automatic Calculations**: Expected hours are calculated based on whether today is a working day and how many working days are in the current week
3. **Progress Metrics**: Each sensor provides progress percentages, remaining time, and expected hours

### Daily Progress

The daily sensors (`clockify_daily_time` and `clockify_daily_total`) include:

- **Expected Hours**: Hours you should work today (based on Clockify settings, 0 if it's not a working day)
- **Progress Percent**: How much of your daily goal is complete (e.g., 75.0%)
- **Remaining Hours**: Hours left to meet your daily goal
- **Remaining Formatted**: Remaining time in HH:MM format

**Example**: If you're configured for 8-hour days and have logged 6 hours:
- `expected_hours`: 8.0
- `progress_percent`: 75.0
- `remaining_hours`: 2.0
- `remaining_formatted`: "02:00"

### Weekly Progress

The weekly sensors (`clockify_weekly_time` and `clockify_weekly_total`) include two types of progress tracking:

#### Full Week Progress
Compares your logged time against the full week's expected hours:
- `expected_hours`: Total expected hours for the week (e.g., 40 hours for 5-day week)
- `progress_percent`: Progress against full week's goal
- `remaining_hours`: Hours remaining to meet full week goal
- `remaining_formatted`: Remaining time in HH:MM format

#### Week-to-Date Progress
Compares your logged time against expected hours from Monday to today:
- `expected_hours_to_date`: Expected hours from Monday to today
- `progress_percent_to_date`: Progress against week-to-date goal
- `remaining_hours_to_date`: Hours remaining to meet week-to-date goal  
- `remaining_formatted_to_date`: Remaining time in HH:MM format

**Example**: On Wednesday of a 5-day work week (8 hours/day):
- Full Week: `expected_hours`: 40.0, comparing against full week
- To-Date: `expected_hours_to_date`: 24.0 (Mon+Tue+Wed), comparing against what you should have done by now

### Default Settings

If workspace settings can't be fetched from Clockify:
- Defaults to 8 hours per day
- Defaults to Monday-Friday as working days
- A warning is logged but the integration continues to function normally

### Use Cases

**Track Daily Progress:**
```yaml
- Create a dashboard gauge showing daily progress percentage
- Set up notifications when you reach 100% of your daily goal
- Monitor if you're on track throughout the day
```

**Monitor Weekly Goals:**
```yaml
- Use week-to-date progress to see if you're keeping pace
- Compare full week progress to plan remaining days
- Create automations based on progress thresholds
```

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

### Automatic work timer schedule

```yaml
automation:
  - alias: "Start Work Timer at 9 AM"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: clockify.start_timer
        data:
          description: "Daily work session"
          project_id: "your-work-project-id"

  - alias: "Stop Work Timer at 5 PM"
    trigger:
      - platform: time
        at: "17:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: clockify.stop_timer
```

### Start timer when arriving at office

```yaml
automation:
  - alias: "Start Timer When Arriving at Office"
    trigger:
      - platform: zone
        entity_id: person.your_name
        zone: zone.office
        event: enter
    condition:
      - condition: time
        after: "08:00:00"
        before: "18:00:00"
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: clockify.start_timer
        data:
          description: "Arrived at office"
          project_id: "your-office-project-id"
```

### Smart break timer

```yaml
automation:
  - alias: "Start Break Timer"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_desk
        to: "off"
        for:
          minutes: 15
    condition:
      - condition: state
        entity_id: sensor.clockify_current_timer
        state: "No active timer"
        attribute: status
        state: "active"
    action:
      - service: clockify.stop_timer
      - service: clockify.start_timer
        data:
          description: "Break time"
          project_id: "your-breaks-project-id"
```

### Daily goal achieved notification

```yaml
automation:
  - alias: "Daily Work Goal Reached"
    trigger:
      - platform: numeric_state
        entity_id: sensor.clockify_daily_total
        attribute: progress_percent
        above: 100
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🎉 Daily Goal Reached!"
          message: "You've completed {{ states('sensor.clockify_daily_total') }} hours today. Great work!"
```

### Weekly progress check

```yaml
automation:
  - alias: "Weekly Progress Report"
    trigger:
      - platform: time
        at: "17:00:00"
    condition:
      - condition: time
        weekday:
          - fri
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📊 Weekly Progress Report"
          message: >
            This week you've logged {{ states('sensor.clockify_weekly_total') }} hours
            ({{ state_attr('sensor.clockify_weekly_total', 'progress_percent') }}% of your goal).
            {% if state_attr('sensor.clockify_weekly_total', 'progress_percent') | float < 100 %}
            You have {{ state_attr('sensor.clockify_weekly_total', 'remaining_formatted') }} remaining.
            {% else %}
            You've exceeded your weekly goal! 🎉
            {% endif %}
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
      • {{ state_attr('sensor.clockify_current_timer', 'duration')[:5] }}
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
  
  ⏱️ **Duration:** {{ state_attr('sensor.clockify_current_timer', 'duration')[:5] if state_attr('sensor.clockify_current_timer', 'duration') else 'Starting...' }}
  
  {% if state_attr('sensor.clockify_current_timer', 'billable') %}
  💰 **Billable** | {% endif %} 🏷️ {{ state_attr('sensor.clockify_current_timer', 'tags') | join(', ') if state_attr('sensor.clockify_current_timer', 'tags') else 'No tags' }}
  
  ---
  ⏰ **Started:** {{ as_timestamp(state_attr('sensor.clockify_current_timer', 'start_time')) | timestamp_custom('%H:%M', true) if state_attr('sensor.clockify_current_timer', 'start_time') else 'Unknown' }}
  {% else %}
  ## ⏸️ No Active Timer
  
  Start a timer in Clockify to begin tracking your work.
  {% endif %}
  
  ## Totals

  📊 **Today:** {{ state_attr('sensor.clockify_daily_total', 'duration_formatted') or '00:00' }} | **Week:** {{ state_attr('sensor.clockify_weekly_total', 'duration_formatted') or '00:00' }}
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
    name: Today's Completed
    icon: mdi:calendar-today
  - entity: sensor.clockify_daily_total
    name: Today's Total
    icon: mdi:calendar-today-outline
  - entity: sensor.clockify_weekly_time
    name: Week's Completed
    icon: mdi:calendar-week
  - entity: sensor.clockify_weekly_total
    name: Week's Total
    icon: mdi:calendar-week-begin
state_color: true
```

### Weekly Daily Breakdown Card

View daily hours for the current week using the new daily breakdown attributes:

```yaml
type: markdown
title: 📅 Weekly Breakdown
content: |
  ## This Week's Daily Hours
  
  **Monday:** {{ state_attr('sensor.clockify_weekly_total', 'Mon_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Mon') or '0.0' }}h)
  **Tuesday:** {{ state_attr('sensor.clockify_weekly_total', 'Tue_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Tue') or '0.0' }}h)
  **Wednesday:** {{ state_attr('sensor.clockify_weekly_total', 'Wed_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Wed') or '0.0' }}h)
  **Thursday:** {{ state_attr('sensor.clockify_weekly_total', 'Thu_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Thu') or '0.0' }}h)
  **Friday:** {{ state_attr('sensor.clockify_weekly_total', 'Fri_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Fri') or '0.0' }}h)
  **Saturday:** {{ state_attr('sensor.clockify_weekly_total', 'Sat_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Sat') or '0.0' }}h)
  **Sunday:** {{ state_attr('sensor.clockify_weekly_total', 'Sun_formatted') or '00:00' }} ({{ state_attr('sensor.clockify_weekly_total', 'Sun') or '0.0' }}h)
  
  ---
  **Total:** {{ state_attr('sensor.clockify_weekly_total', 'duration_formatted') or '00:00' }} ({{ states('sensor.clockify_weekly_total') }}h)
  *({{ state_attr('sensor.clockify_weekly_total', 'week_start') }} to {{ state_attr('sensor.clockify_weekly_total', 'week_end') }})*
```

### Progress Tracking Dashboard

Display your daily and weekly progress with visual indicators:

```yaml
type: markdown
title: 📊 Work Progress Tracker
content: |
  ## Today's Progress
  **Logged:** {{ state_attr('sensor.clockify_daily_total', 'duration_formatted') or '00:00' }}
  **Expected:** {{ state_attr('sensor.clockify_daily_total', 'expected_hours') or '0.0' }}h
  **Progress:** {{ state_attr('sensor.clockify_daily_total', 'progress_percent') or '0.0' }}%
  {% if state_attr('sensor.clockify_daily_total', 'remaining_hours') | float > 0 %}
  **Remaining:** {{ state_attr('sensor.clockify_daily_total', 'remaining_formatted') or '00:00' }}
  {% else %}
  ✅ **Daily goal reached!**
  {% endif %}
  
  ---
  
  ## This Week's Progress
  **Logged:** {{ state_attr('sensor.clockify_weekly_total', 'duration_formatted') or '00:00' }}
  **Expected (Full Week):** {{ state_attr('sensor.clockify_weekly_total', 'expected_hours') or '0.0' }}h
  **Expected (To Date):** {{ state_attr('sensor.clockify_weekly_total', 'expected_hours_to_date') or '0.0' }}h
  
  **Full Week Progress:** {{ state_attr('sensor.clockify_weekly_total', 'progress_percent') or '0.0' }}%
  **Week-to-Date Progress:** {{ state_attr('sensor.clockify_weekly_total', 'progress_percent_to_date') or '0.0' }}%
  
  {% if state_attr('sensor.clockify_weekly_total', 'progress_percent_to_date') | float >= 100 %}
  ✅ **On track for this week!**
  {% elif state_attr('sensor.clockify_weekly_total', 'progress_percent_to_date') | float >= 90 %}
  ⚠️ **Nearly on track** ({{ state_attr('sensor.clockify_weekly_total', 'remaining_formatted_to_date') }} remaining for today)
  {% else %}
  ⏰ **Behind schedule** ({{ state_attr('sensor.clockify_weekly_total', 'remaining_formatted_to_date') }} remaining to catch up)
  {% endif %}
  
  **Working Days:** {{ state_attr('sensor.clockify_weekly_total', 'working_days') | join(', ') }}
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
    name: Today Done
  - entity: sensor.clockify_daily_total
    name: Today Total
  - entity: sensor.clockify_weekly_time
    name: Week Done
  - entity: sensor.clockify_weekly_total
    name: Week Total
columns: 5
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
