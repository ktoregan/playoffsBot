import os
from datetime import datetime, timezone
import asyncio
import time  # For sleep

async def run_script(script_name):
    print(f"Attempting to run the script: {script_name}...")
    command = f"python {script_name}"
    proc = await asyncio.create_subprocess_shell(command)
    await proc.wait()
    print(f"Script {script_name} has completed execution.")

def is_within_time_window():
    # Get the current time in UTC
    now = datetime.now(timezone.utc)
    print(f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if it's Tuesday and between 8:00 AM and 8:03 AM UTC
    if now.weekday() == 1 and now.hour == 8 and 0 <= now.minute < 3:
        print("Within the time window (Tuesday 8:00 AM - 8:03 AM UTC).")
        return True
    else:
        print("Outside the time window.")
        return False

async def main():
    if is_within_time_window():
        print("Conditions met. Running the script.")
        await run_script('results.py')

        # Wait for 6 minutes to ensure the script doesn't run again within the window
        print("Waiting for 5 minutes to ensure the time window has passed.")
        time.sleep(300)  # Wait for 6 minutes
        print("5 minutes passed, resuming.")
    else:
        print("Outside the time window. Script will not run.")

    print("Exiting bot.")

# Run the main function using asyncio
asyncio.run(main())