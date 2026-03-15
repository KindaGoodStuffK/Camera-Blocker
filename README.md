# Camera Blocker for Windows

A simple Windows app to block and unblock your webcam. Useful for privacy when you don't want the camera on.

## What it does

- Disables your camera with one click
- Re-enables it when you need it
- Works with any webcam (built-in laptop cameras, USB webcams, etc.)
- Has an emergency recovery mode if something goes wrong

## How to use

### Option 1: Run from Python
1. Make sure you have Python 3 installed
2. Right-click `hp_camera_blocker.py` and run as Administrator
3. Click "Disable" to turn off camera, "Enable" to turn it back on

### Option 2: Build an executable
1. Run `build_and_update.bat` as Administrator
2. This creates `HP CamBlock.exe` in `C:\Program Files\HP CamBlock\`
3. Shortcut gets added to your desktop

### If the camera gets stuck

Sometimes Windows Camera Frame Server service gets stuck. Run these as Admin:

- `camera_recovery.py` - Fixes most issues automatically
- `kill_and_restart_service.py` - Forcefully kills stuck service if recovery fails

## Requirements

- Windows 10 or 11
- Administrator privileges (required to control camera devices)
- Python 3.x (if running from source)

## Supported cameras

Works with pretty much any camera:
- HP TrueVision HD (what I originally made this for)
- Logitech webcams
- Dell laptops
- Lenovo cameras
- Any USB webcam that shows up in Device Manager

It detects cameras by name patterns like "camera", "webcam", "truevision", etc.

## What it actually does under the hood

- Uses PowerShell to enable/disable PnP devices
- Stops/starts Windows Camera Frame Server service
- Clears registry blocks in Windows camera privacy settings

## Known issues

- Windows Camera Frame Server can get stuck in "Stop Pending" state
- Some camera apps need to be restarted after enabling camera
- If recovery scripts don't work, a PC restart usually fixes it

## Disclaimer

This modifies system services and device states. Use at your own risk. The recovery tools should fix any issues but no guarantees.
