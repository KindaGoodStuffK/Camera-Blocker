"""
Camera Recovery Tool - Fixes broken camera after using HP CamBlock
Run this as Administrator to restore camera functionality.
"""

import subprocess
import sys
import ctypes
import json
import time
from typing import Tuple


def is_admin() -> bool:
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_powershell_command(command: str) -> Tuple[bool, str, str]:
    """Run a PowerShell command and return the result."""
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_service_status() -> str:
    """Get Windows Camera Frame Server status."""
    success, stdout, _ = run_powershell_command(
        "Get-Service -Name 'Windows Camera Frame Server' | Select-Object Status | ConvertTo-Json"
    )
    if success and stdout.strip():
        try:
            data = json.loads(stdout)
            return data.get('Status', 'Unknown')
        except Exception:
            pass
    return 'Unknown'


def restart_camera_service() -> Tuple[bool, str]:
    """Restart camera service with verification."""
    print("Step 1: Setting service startup type...")
    run_powershell_command(
        "Set-Service -Name 'Windows Camera Frame Server' -StartupType Manual -ErrorAction SilentlyContinue"
    )
    time.sleep(0.5)
    
    print("Step 2: Stopping service (if stuck)...")
    run_powershell_command(
        "Stop-Service -Name 'Windows Camera Frame Server' -Force -ErrorAction SilentlyContinue"
    )
    time.sleep(0.5)
    
    print("Step 3: Starting service...")
    for attempt in range(3):
        run_powershell_command(
            "Start-Service -Name 'Windows Camera Frame Server' -ErrorAction SilentlyContinue"
        )
        time.sleep(1)
        
        status = get_service_status()
        if status == 'Running':
            return True, f"Service is Running (attempt {attempt + 1})"
        
        print(f"  Attempt {attempt + 1}: Service status is {status}, retrying...")
        run_powershell_command(
            "Restart-Service -Name 'Windows Camera Frame Server' -Force -ErrorAction SilentlyContinue"
        )
        time.sleep(1)
    
    final_status = get_service_status()
    return False, f"Service failed to start. Final status: {final_status}"


def enable_all_cameras():
    """Enable all camera devices."""
    print("Step 4: Enabling camera devices...")
    
    patterns = ['camera', 'webcam', 'truevision', 'integrated camera', 'hd camera']
    for pattern in patterns:
        ps_cmd = f"Get-PnpDevice | Where-Object {{$_.FriendlyName -match '{pattern}'}} | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue"
        run_powershell_command(ps_cmd)
    
    run_powershell_command(
        "Get-PnpDevice -Class 'Image' | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue"
    )
    
    # Rescan for hardware (optional - using devcon is more reliable but requires installation)
    print("Step 5: Hardware scan skipped (pnputil /scandevices deprecated)")


def clear_registry_blocks():
    """Clear registry blocks on camera."""
    print("Step 6: Clearing registry blocks...")
    
    # Remove and recreate webcam consent store
    run_powershell_command(
        'Remove-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
        '-Recurse -Force -ErrorAction SilentlyContinue'
    )
    run_powershell_command(
        'New-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
        '-Force -ErrorAction SilentlyContinue | Out-Null'
    )
    run_powershell_command(
        'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
        '-Name "Value" -Value "Allow" -ErrorAction SilentlyContinue'
    )
    
    # Reset packaged app permissions
    print("Step 7: Resetting packaged app camera permissions...")
    run_powershell_command(
        'Get-ChildItem -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
        '-ErrorAction SilentlyContinue | Where-Object {$_.PSChildName -ne "NonPackaged"} | ForEach-Object { '
        '    Set-ItemProperty -Path $_.PSPath -Name "Value" -Value "Allow" -ErrorAction SilentlyContinue '
        '}'
    )


def check_cameras() -> int:
    """Check how many cameras are now active."""
    print("\nChecking camera status...")
    
    cameras = []
    patterns = ['camera', 'webcam', 'cam', 'truevision', 'hd camera']
    
    for pattern in patterns:
        ps_cmd = f"Get-PnpDevice | Where-Object {{$_.FriendlyName -match '{pattern}'}} | Select-Object FriendlyName, InstanceId, Status | ConvertTo-Json"
        success, stdout, stderr = run_powershell_command(ps_cmd)
        
        if success and stdout.strip():
            try:
                devices = json.loads(stdout)
                if isinstance(devices, dict):
                    devices = [devices]
                for dev in devices:
                    if dev and 'InstanceId' in dev:
                        cameras.append({
                            'name': dev.get('FriendlyName', 'Unknown'),
                            'status': dev.get('Status', 'Unknown')
                        })
            except Exception:
                pass
    
    # Remove duplicates
    seen = set()
    unique = []
    for cam in cameras:
        key = cam['name']
        if key not in seen:
            seen.add(key)
            unique.append(cam)
    
    active = sum(1 for c in unique if c['status'] == 'OK')
    
    print(f"\n  Found {len(unique)} camera(s):")
    for cam in unique:
        status_icon = "OK" if cam['status'] == 'OK' else "ERR"
        print(f"    [{status_icon}] {cam['name']}")
    
    return active


def main():
    print("=" * 60)
    print("  CAMERA RECOVERY TOOL")
    print("  Fixes camera broken by HP CamBlock")
    print("=" * 60)
    print()
    
    # Check admin
    if not is_admin():
        print("Requesting administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
    
    print("Running recovery steps...")
    print()
    
    # Run recovery
    service_ok, service_msg = restart_camera_service()
    print(f"  Service: {service_msg}")
    
    enable_all_cameras()
    clear_registry_blocks()
    
    # Check results
    active_count = check_cameras()
    
    print()
    print("=" * 60)
    if active_count > 0 and service_ok:
        print("  SUCCESS: Camera should now be working!")
        print(f"  Active cameras: {active_count}")
    else:
        print("  PARTIAL SUCCESS: Some steps completed")
        if not service_ok:
            print("  WARNING: Camera Frame Server service may need manual restart")
        print(f"  Active cameras: {active_count}")
        print()
        print("  If camera still doesn't work:")
        print("  1. Restart your computer")
        print("  2. Run Windows Update")
        print("  3. Check camera privacy settings in Windows Settings")
    print("=" * 60)
    print()
    
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
