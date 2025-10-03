"""Test script to fetch and display Clockify user schedule settings."""
import asyncio
import aiohttp
import json

# Replace these with your actual values
API_KEY = "your_api_key_here"
WORKSPACE_ID = "your_workspace_id_here"

async def test_user_schedule():
    """Fetch and display user schedule settings."""
    # First get user ID
    user_url = "https://api.clockify.me/api/v1/user"
    headers = {"X-Api-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("=" * 60)
        print("FETCHING USER INFORMATION")
        print("=" * 60)
        
        async with session.get(user_url, headers=headers) as response:
            if response.status != 200:
                print(f"❌ Failed to get user info: {response.status}")
                return
            
            user_data = await response.json()
            user_id = user_data.get("id")
            print(f"✅ User ID: {user_id}")
            print(f"User Name: {user_data.get('name')}")
            print(f"Email: {user_data.get('email')}")
        
        # Now get user schedule
        schedule_url = f"https://api.clockify.me/api/v1/workspaces/{WORKSPACE_ID}/scheduling/users/{user_id}"
        
        print("\n" + "=" * 60)
        print("FETCHING USER SCHEDULE SETTINGS")
        print("=" * 60)
        print(f"URL: {schedule_url}")
        print(f"Workspace ID: {WORKSPACE_ID}")
        print("-" * 60)
        
        async with session.get(schedule_url, headers=headers) as response:
            print(f"Response Status: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                print("\n✅ User Schedule Retrieved Successfully!\n")
                print(json.dumps(data, indent=2))
                
                # Parse the workWeek like the integration does
                work_week = data.get("workWeek", {})
                
                if work_week:
                    print("\n" + "=" * 60)
                    print("PARSED WORK WEEK:")
                    print("=" * 60)
                    
                    day_mapping = {
                        "monday": "Mon",
                        "tuesday": "Tue",
                        "wednesday": "Wed",
                        "thursday": "Thu",
                        "friday": "Fri",
                        "saturday": "Sat",
                        "sunday": "Sun"
                    }
                    
                    working_days = []
                    daily_hours = {}
                    
                    for api_day, short_day in day_mapping.items():
                        day_data = work_week.get(api_day, {})
                        is_work_day = day_data.get("isWorkDay", False)
                        duration = day_data.get("duration", "PT0H")
                        
                        if is_work_day:
                            working_days.append(short_day)
                            hours = parse_iso_duration(duration)
                            daily_hours[short_day] = hours
                            print(f"{short_day}: {hours} hours ({duration})")
                    
                    print("\n" + "-" * 60)
                    print(f"Working Days: {working_days}")
                    print(f"Total Weekly Hours: {sum(daily_hours.values())}")
                else:
                    print("\n⚠️  No workWeek data found in response")
                
            elif response.status == 401:
                print("\n❌ Authentication Failed!")
                print("Please check your API key.")
            elif response.status == 403:
                print("\n❌ Forbidden!")
                print("You don't have permission to access this resource.")
            elif response.status == 404:
                print("\n❌ Not Found!")
                print("The scheduling endpoint might not be available.")
                print("This might require a specific Clockify plan or feature.")
            else:
                error_text = await response.text()
                print(f"\n❌ Error: {response.status}")
                print(f"Response: {error_text}")

def parse_iso_duration(duration: str) -> float:
    """Parse ISO 8601 duration format (e.g., PT6H, PT6H30M) to hours."""
    try:
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
        print(f"Error parsing duration '{duration}': {err}")
        return 0.0

async def main():
    """Run the test."""
    print("=" * 60)
    print("CLOCKIFY USER SCHEDULE TEST")
    print("=" * 60)
    
    if API_KEY == "your_api_key_here" or WORKSPACE_ID == "your_workspace_id_here":
        print("\n⚠️  Please update API_KEY and WORKSPACE_ID in the script first!")
        return
    
    await test_user_schedule()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
