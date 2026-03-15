"""
Kill stuck Windows Camera Frame Server service and restart it
"""
import subprocess
import ctypes
import time
import sys

def run(cmd):
    """Run PowerShell command."""
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', cmd],
        capture_output=True, text=True
    )
    return result

def run_cmd(args):
    """Run system command."""
    result = subprocess.run(args, capture_output=True, text=True)
    return result

# Check admin
if not ctypes.windll.shell32.IsUserAnAdmin():
    print("Need admin! Right-click and Run as Administrator")
    input()
    sys.exit(1)

print("Killing stuck Windows Camera Frame Server...")
print()

# Step 1: Try to get the PID and kill it
print("Step 1: Finding and killing service process...")

# Get service PID
r = run("(Get-WmiObject Win32_Service -Filter \"Name='Windows Camera Frame Server'\").ProcessId")
if r.stdout.strip() and r.stdout.strip() != '0':
    pid = r.stdout.strip()
    print(f"  Found service PID: {pid}")
    print(f"  Killing process {pid}...")
    run_cmd(['taskkill', '/F', '/PID', pid])
    time.sleep(1)
else:
    print("  No PID found or service not running")

# Step 2: Kill any FrameServer related processes
print("\nStep 2: Killing any FrameServer processes...")
run("Get-Process | Where-Object {$_.ProcessName -match 'FrameServer|CameraFrame'} | Stop-Process -Force")

# Step 3: Force service stop via sc
print("\nStep 3: Force stopping via sc.exe...")
run_cmd(['sc.exe', 'stop', 'Windows Camera Frame Server'])
time.sleep(2)

# Step 4: Reset service
print("\nStep 4: Resetting service configuration...")
run_cmd(['sc.exe', 'config', 'Windows Camera Frame Server', 'start=', 'demand'])
run_cmd(['sc.exe', 'failure', 'Windows Camera Frame Server', 'reset=', '0'])

# Step 5: Start service
print("\nStep 5: Starting service...")
run_cmd(['sc.exe', 'start', 'Windows Camera Frame Server'])
time.sleep(3)

# Check status
print("\nStep 6: Checking final status...")
r = run("(Get-Service 'Windows Camera Frame Server').Status")
status = r.stdout.strip()
print(f"Service status: {status}")

if status == "Running":
    print("\n*** SUCCESS! Service is running! ***")
    print("Try your camera now.")
else:
    print(f"\n*** Service still not running (Status: {status}) ***")
    print("You need to restart your PC.")

print("\nPress Enter to exit...")
input()
