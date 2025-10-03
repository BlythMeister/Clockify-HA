"""Test script to fetch and display Clockify member profile settings."""
import asyncio
import aiohttp
import json

# Replace these with your actual values
API_KEY = "your_api_key_here"
WORKSPACE_ID = "your_workspace_id_here"

async def test_member_profile():
    """Fetch and display member profile settings."""
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
            
            # Check user settings
            if "settings" in user_data:
                print(f"\nUser Settings:")
                print(f"  Week Start: {user_data['settings'].get('weekStart', 'Not set')}")
        
        # Now get member profile
        profile_url = f"https://api.clockify.me/api/v1/workspaces/{WORKSPACE_ID}/member-profile/{user_id}"
        
        print("\n" + "=" * 60)
        print("FETCHING MEMBER PROFILE")
        print("=" * 60)
        print(f"URL: {profile_url}")
        print(f"Workspace ID: {WORKSPACE_ID}")
        print(f"User ID: {user_id}")
        print("-" * 60)
        
        async with session.get(profile_url, headers=headers) as response:
            print(f"Response Status: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                print("\n✅ Member Profile Retrieved Successfully!\n")
                print(json.dumps(data, indent=2))
                
                # Parse key settings
                print("\n" + "=" * 60)
                print("KEY SETTINGS:")
                print("=" * 60)
                
                week_start = data.get("weekStart", "Not set")
                work_capacity = data.get("workCapacity", "Not set")
                working_days_str = data.get("workingDays", "[]")
                
                print(f"Week Start: {week_start}")
                print(f"Work Capacity: {work_capacity}")
                print(f"Working Days (raw): {working_days_str}")
                
                # Parse work capacity
                if work_capacity and work_capacity != "Not set":
                    hours = parse_iso_duration(work_capacity)
                    print(f"Work Capacity (parsed): {hours} hours/day")
                
                # Parse working days
                try:
                    working_days = json.loads(working_days_str)
                    print(f"Working Days (parsed): {working_days}")
                    
                    # Calculate weekly hours
                    if work_capacity and work_capacity != "Not set":
                        hours_per_day = parse_iso_duration(work_capacity)
                        total_weekly = len(working_days) * hours_per_day
                        print(f"\nCalculated Weekly Hours: {total_weekly} hours")
                        print(f"  {len(working_days)} working days × {hours_per_day} hours/day")
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Failed to parse working days: {e}")
                
            elif response.status == 401:
                print("\n❌ Authentication Failed!")
                print("Please check your API key.")
            elif response.status == 403:
                print("\n❌ Forbidden!")
                print("You don't have permission to access this resource.")
            elif response.status == 404:
                print("\n❌ Not Found!")
                print("The member profile endpoint might not be available.")
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
    print("CLOCKIFY MEMBER PROFILE TEST")
    print("=" * 60)
    
    if API_KEY == "your_api_key_here" or WORKSPACE_ID == "your_workspace_id_here":
        print("\n⚠️  Please update API_KEY and WORKSPACE_ID in the script first!")
        return
    
    await test_member_profile()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
