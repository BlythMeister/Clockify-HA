# Development Notes

## Clockify API Endpoints Used

This integration uses the following Clockify API endpoints:

- `GET /api/v1/user` - Get current user information
- `GET /api/v1/workspaces/{workspaceId}/user/{userId}/time-entries?in-progress=true` - Get current timer
- `GET /api/v1/workspaces/{workspaceId}/user/{userId}/time-entries?start={start}&end={end}` - Get time entries for date range
- `GET /api/v1/workspaces/{workspaceId}/projects/{projectId}` - Get project details
- `GET /api/v1/workspaces/{workspaceId}/projects/{projectId}/tasks/{taskId}` - Get task details

## Authentication

The integration uses API key authentication with the `X-Api-Key` header.

## Update Frequency

The sensor updates every 30 seconds to provide near real-time information about your active timer.

## Error Handling

The integration includes proper error handling for:

- Network connectivity issues
- Invalid API keys
- Invalid workspace IDs
- Missing project or task data

## Testing

To test the integration:

1. Set up a development Home Assistant instance
2. Copy the `custom_components/clockify` folder to your config directory
3. Restart Home Assistant
4. Add the integration through the UI
5. Start a timer in Clockify and verify the sensor updates
