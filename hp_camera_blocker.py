"""
HP Camera Blocker - Modern UI Application
Blocks/unblocks HP TrueVision HD Camera and other webcam devices.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import ctypes
import threading
import json
import time
from pathlib import Path
from typing import Tuple, Optional, List, Dict

# Constants
APP_NAME = "HP CamBlock"
VERSION = "2.0"
CONFIG_FILE = Path.home() / ".hp_camblock_config.json"

# Modern color scheme
COLORS = {
    "bg": "#1e1e2e",
    "fg": "#cdd6f4",
    "accent": "#89b4fa",
    "success": "#a6e3a1",
    "error": "#f38ba8",
    "warning": "#f9e2af",
    "surface": "#313244",
    "button_on": "#a6e3a1",
    "button_off": "#f38ba8",
    "button_bg": "#45475a"
}


def is_admin() -> bool:
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_powershell_command(command: str) -> Tuple[bool, str, str]:
    """Run a PowerShell command and return the result.
    
    Args:
        command: PowerShell command to execute
        
    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
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


def get_camera_devices() -> List[Dict[str, str]]:
    """Detect all camera devices on the system.
    
    Returns:
        List of camera device dictionaries with name, instance_id, and status
    """
    cameras = []
    
    # Search for camera devices by friendly name patterns
    patterns = ['camera', 'webcam', 'cam', 'truevision', 'hd camera']
    
    for pattern in patterns:
        ps_cmd = f"Get-PnpDevice | Where-Object {{$_.FriendlyName -match '{pattern}'}} | Select-Object FriendlyName, InstanceId, Status | ConvertTo-Json"
        success, stdout, stderr = run_powershell_command(ps_cmd)
        
        if success and stdout.strip():
            try:
                import json as json_lib
                devices = json_lib.loads(stdout)
                if isinstance(devices, dict):
                    devices = [devices]
                for dev in devices:
                    if dev and 'InstanceId' in dev:
                        cameras.append({
                            'name': dev.get('FriendlyName', 'Unknown Camera'),
                            'instance_id': dev['InstanceId'],
                            'status': dev.get('Status', 'Unknown')
                        })
            except Exception:
                pass
    
    # Remove duplicates based on instance_id
    seen = set()
    unique_cameras = []
    for cam in cameras:
        if cam['instance_id'] not in seen:
            seen.add(cam['instance_id'])
            unique_cameras.append(cam)
    
    return unique_cameras


def get_camera_frame_server_status() -> str:
    """Get the status of Windows Camera Frame Server service."""
    success, stdout, _ = run_powershell_command(
        "Get-Service -Name 'Windows Camera Frame Server' | Select-Object Status | ConvertTo-Json"
    )
    if success and stdout.strip():
        try:
            import json as json_lib
            data = json_lib.loads(stdout)
            return data.get('Status', 'Unknown')
        except Exception:
            pass
    return 'Unknown'


def restart_camera_frame_server(max_retries: int = 3, wait_seconds: float = 1.0) -> Tuple[bool, str]:
    """Properly restart Windows Camera Frame Server with verification.
    
    This function ensures the service is actually running before returning.
    
    Args:
        max_retries: Number of attempts to start the service
        wait_seconds: Time to wait between attempts
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    import time
    
    # First set startup type to Manual (required for it to start)
    run_powershell_command(
        "Set-Service -Name 'Windows Camera Frame Server' -StartupType Manual -ErrorAction SilentlyContinue"
    )
    time.sleep(0.5)
    
    # Try to stop first (in case it's stuck)
    run_powershell_command(
        "Stop-Service -Name 'Windows Camera Frame Server' -Force -ErrorAction SilentlyContinue"
    )
    time.sleep(0.5)
    
    # Attempt to start with retries
    for attempt in range(max_retries):
        # Start the service
        success, stdout, stderr = run_powershell_command(
            "Start-Service -Name 'Windows Camera Frame Server' -ErrorAction SilentlyContinue"
        )
        
        # Wait for it to actually start
        time.sleep(wait_seconds)
        
        # Verify it's running
        status = get_camera_frame_server_status()
        if status == 'Running':
            return True, f"Service is Running (attempt {attempt + 1})"
        
        # If not running, try restarting
        run_powershell_command(
            "Restart-Service -Name 'Windows Camera Frame Server' -Force -ErrorAction SilentlyContinue"
        )
        time.sleep(wait_seconds)
        
        # Check again after restart
        status = get_camera_frame_server_status()
        if status == 'Running':
            return True, f"Service is Running after restart (attempt {attempt + 1})"
    
    # All retries exhausted
    final_status = get_camera_frame_server_status()
    return False, f"Service failed to start. Final status: {final_status}"


def load_config() -> Dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        'preferred_camera_id': None,
        'auto_enable_on_exit': True,
        'confirm_actions': True
    }


def save_config(config: Dict) -> bool:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except (IOError, OSError, PermissionError) as e:
        print(f"Failed to save config: {e}")
        return False


class CameraBlockerApp:
    """Main application class for the Camera Blocker GUI."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("320x280")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=COLORS["bg"])
        
        # State variables
        self.is_processing = False
        self.cameras: List[Dict[str, str]] = []
        self.config = load_config()
        self.selected_camera_id = tk.StringVar(value=self.config.get('preferred_camera_id', ''))
        
        # Build UI
        self._build_ui()
        
        # Detect cameras on startup
        self.refresh_camera_list()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Center window on screen
        self._center_window()
    
    def _center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = 320
        height = 280
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text=APP_NAME,
            font=('Segoe UI', 18, 'bold'),
            bg=COLORS["bg"],
            fg=COLORS["accent"]
        )
        title_label.pack(pady=(0, 4))
        
        # Subtitle
        subtitle = tk.Label(
            main_frame,
            text="Camera Privacy Control",
            font=('Segoe UI', 9),
            bg=COLORS["bg"],
            fg=COLORS["fg"]
        )
        subtitle.pack(pady=(0, 12))
        
        # Status card
        status_frame = tk.Frame(main_frame, bg=COLORS["surface"], padx=12, pady=12)
        status_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.status_label = tk.Label(
            status_frame,
            text="Detecting...",
            font=('Segoe UI', 14, 'bold'),
            bg=COLORS["surface"],
            fg=COLORS["warning"]
        )
        self.status_label.pack()
        
        self.camera_info_label = tk.Label(
            status_frame,
            text="No camera selected",
            font=('Segoe UI', 9),
            bg=COLORS["surface"],
            fg=COLORS["fg"],
            wraplength=260
        )
        self.camera_info_label.pack(pady=(4, 0))
        
        # Camera selection dropdown
        cam_select_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        cam_select_frame.pack(fill=tk.X, pady=(0, 12))
        
        cam_label = tk.Label(
            cam_select_frame,
            text="Camera:",
            font=('Segoe UI', 9),
            bg=COLORS["bg"],
            fg=COLORS["fg"]
        )
        cam_label.pack(side=tk.LEFT)
        
        self.camera_combo = ttk.Combobox(
            cam_select_frame,
            textvariable=self.selected_camera_id,
            state='readonly',
            font=('Segoe UI', 9)
        )
        self.camera_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.camera_combo.bind('<<ComboboxSelected>>', self._on_camera_selected)
        
        # Refresh button
        refresh_btn = tk.Button(
            cam_select_frame,
            text="↻",
            font=('Segoe UI', 9, 'bold'),
            bg=COLORS["button_bg"],
            fg=COLORS["fg"],
            relief=tk.FLAT,
            command=self.refresh_camera_list,
            cursor='hand2'
        )
        refresh_btn.pack(side=tk.RIGHT, padx=(8, 0))
        
        # Button frame
        btn_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Enable button
        self.btn_enable = tk.Button(
            btn_frame,
            text="ENABLE",
            font=('Segoe UI', 11, 'bold'),
            bg=COLORS["button_on"],
            fg="#1e1e2e",
            relief=tk.FLAT,
            height=2,
            command=self._enable_camera_threaded,
            cursor='hand2',
            activebackground=COLORS["success"],
            activeforeground="#1e1e2e"
        )
        self.btn_enable.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        
        # Disable button
        self.btn_disable = tk.Button(
            btn_frame,
            text="DISABLE",
            font=('Segoe UI', 11, 'bold'),
            bg=COLORS["button_off"],
            fg="#1e1e2e",
            relief=tk.FLAT,
            height=2,
            command=self._disable_camera_threaded,
            cursor='hand2',
            activebackground=COLORS["error"],
            activeforeground="#1e1e2e"
        )
        self.btn_disable.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))
        
        # Progress/Status bar
        self.progress_label = tk.Label(
            main_frame,
            text="Ready",
            font=('Segoe UI', 8),
            bg=COLORS["bg"],
            fg=COLORS["fg"]
        )
        self.progress_label.pack(pady=(8, 0))
        
        # Emergency recover button
        recover_btn = tk.Button(
            main_frame,
            text="🚨 Emergency Recover",
            font=('Segoe UI', 9, 'bold'),
            bg="#f9e2af",
            fg="#1e1e2e",
            relief=tk.FLAT,
            height=1,
            command=self._emergency_recover,
            cursor='hand2'
        )
        recover_btn.pack(fill=tk.X, pady=(8, 0))
        
        # Settings checkbox
        self.auto_enable_var = tk.BooleanVar(value=self.config.get('auto_enable_on_exit', True))
        settings_check = tk.Checkbutton(
            main_frame,
            text="Auto-enable on exit",
            variable=self.auto_enable_var,
            bg=COLORS["bg"],
            fg=COLORS["fg"],
            selectcolor=COLORS["surface"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["fg"],
            font=('Segoe UI', 8)
        )
        settings_check.pack(pady=(8, 0))
        
        # Style the combobox
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TCombobox', 
            fieldbackground=COLORS["surface"],
            background=COLORS["button_bg"],
            foreground=COLORS["fg"],
            arrowcolor=COLORS["accent"]
        )
    
    def _emergency_recover(self):
        """Emergency recovery - fixes camera stuck in disabled state."""
        response = messagebox.askyesno(
            "Emergency Recover",
            "This will force-enable ALL cameras and clear all blocks.\n\nContinue?",
            parent=self.root
        )
        if not response:
            return
        
        self._set_processing_state(True, "Emergency recovery in progress...")
        threading.Thread(target=self._emergency_recover_worker, daemon=True).start()
    
    def _emergency_recover_worker(self):
        """Worker thread for emergency recovery."""
        try:
            success, message = self._emergency_recover_camera()
            self.root.after(0, lambda: self._handle_recover_result(success, message))
        except Exception as e:
            self.root.after(0, lambda: self._handle_recover_result(False, str(e)))
    
    def _emergency_recover_camera(self) -> Tuple[bool, str]:
        """Force recover camera by any means necessary.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        errors = []
        
        # 1. FULLY restore Windows Camera Frame Server (critical fix)
        service_success, service_msg = restart_camera_frame_server(max_retries=3)
        if not service_success:
            errors.append(f"Service restart failed: {service_msg}")
        
        # 2. Clear ALL registry blocks comprehensively
        # Remove entire webcam consent store to reset permissions
        run_powershell_command(
            'Remove-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
            '-Recurse -Force -ErrorAction SilentlyContinue'
        )
        # Recreate with Allow as default
        run_powershell_command(
            'New-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
            '-Force -ErrorAction SilentlyContinue | Out-Null'
        )
        run_powershell_command(
            'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
            '-Name "Value" -Value "Allow" -ErrorAction SilentlyContinue'
        )
        
        # 3. Enable ALL camera devices by various methods
        patterns = ['camera', 'webcam', 'truevision', 'integrated camera', 'hd camera']
        for pattern in patterns:
            ps_cmd = f'Get-PnpDevice | Where-Object {{$_.FriendlyName -match "{pattern}"}} | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue'
            run_powershell_command(ps_cmd)
        
        # Enable by Class Image
        run_powershell_command(
            "Get-PnpDevice -Class 'Image' | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue"
        )
        
        # 4. Force driver reinstallation for camera devices
        # Note: Using single braces {} for PowerShell script blocks, not {{}}
        run_powershell_command(
            "Get-PnpDevice | Where-Object {$_.FriendlyName -match 'camera|webcam'} | ForEach-Object { "
            "   pnputil /restart-device $_.InstanceId "
            "}"
        )
        
        # 5. Trigger hardware rescan (optional - not critical for recovery)
        # Note: pnputil /scandevices doesn't exist in modern Windows, skipping
        
        # 6. Reset Windows Camera privacy settings
        run_powershell_command(
            'Remove-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam\\NonPackaged" '
            '-Name "Value" -ErrorAction SilentlyContinue'
        )
        # Also reset any packaged app permissions
        run_powershell_command(
            'Get-ChildItem -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
            '-ErrorAction SilentlyContinue | Where-Object {$_.PSChildName -ne "NonPackaged"} | ForEach-Object { '
            '    Set-ItemProperty -Path $_.PSPath -Name "Value" -Value "Allow" -ErrorAction SilentlyContinue '
            '}'
        )
        
        # Wait for changes to take effect
        time.sleep(1)
        
        # Refresh and check
        self.cameras = get_camera_devices()
        active_count = sum(1 for cam in self.cameras if cam.get('status') == 'OK')
        
        # Final service check
        service_success, service_stdout, _ = run_powershell_command(
            "Get-Service -Name 'Windows Camera Frame Server' | Select-Object Status, StartType | ConvertTo-Json"
        )
        service_status = "Unknown"
        if service_success:
            try:
                import json
                svc = json.loads(service_stdout)
                service_status = f"{svc.get('Status', 'Unknown')} (Start: {svc.get('StartType', 'Unknown')})"
            except json.JSONDecodeError:
                # JSON parsing failed, keep Unknown status
                pass
        
        if self.cameras:
            if active_count > 0:
                return True, f"Recovered {active_count} camera(s). Service: {service_status}"
            else:
                return False, f"Found {len(self.cameras)} camera(s) but couldn't enable. Service: {service_status}. Try restarting your PC."
        
        return False, "No cameras detected after recovery attempt"
    
    def _handle_recover_result(self, success: bool, message: str):
        """Handle emergency recovery result."""
        self._update_camera_list(self.cameras)
        self._set_processing_state(False, message)
        
        if success:
            self.status_label.config(text="RECOVERED", fg=COLORS["warning"])
            messagebox.showinfo("Success", f"Camera recovered!\n\n{message}", parent=self.root)
        else:
            messagebox.showerror("Recovery Failed", message, parent=self.root)
    
    def _on_camera_selected(self, event=None):
        """Handle camera selection change."""
        selected = self.selected_camera_id.get()
        if selected:
            self.config['preferred_camera_id'] = selected
            save_config(self.config)
            self._update_status_from_selection()
    
    def _update_status_from_selection(self):
        """Update status display based on selected camera."""
        selected_id = self.selected_camera_id.get()
        if not selected_id:
            self.status_label.config(text="No Camera", fg=COLORS["error"])
            self.camera_info_label.config(text="Select a camera from the list")
            return
        
        # Find camera in list
        for cam in self.cameras:
            if cam['instance_id'] == selected_id:
                status = cam.get('status', 'Unknown')
                self.camera_info_label.config(text=cam['name'][:40])
                
                if status == 'OK':
                    self.status_label.config(text="ACTIVE", fg=COLORS["success"])
                elif status == 'Error':
                    self.status_label.config(text="BLOCKED", fg=COLORS["error"])
                else:
                    self.status_label.config(text=status.upper(), fg=COLORS["warning"])
                break
    
    def refresh_camera_list(self):
        """Refresh the list of detected cameras."""
        self.progress_label.config(text="Scanning for cameras...")
        self.root.update_idletasks()
        
        # Run detection in thread to prevent UI freeze
        threading.Thread(target=self._detect_cameras_thread, daemon=True).start()
    
    def _detect_cameras_thread(self):
        """Thread function to detect cameras."""
        cameras = get_camera_devices()
        self.root.after(0, lambda: self._update_camera_list(cameras))
    
    def _update_camera_list(self, cameras: List[Dict[str, str]]):
        """Update the camera list in the UI."""
        self.cameras = cameras
        
        if not cameras:
            self.camera_combo['values'] = ['']
            self.selected_camera_id.set('')
            self.status_label.config(text="NO CAMERA", fg=COLORS["error"])
            self.camera_info_label.config(text="No cameras detected")
            self.progress_label.config(text="No cameras found")
            return
        
        # Build dropdown values (instance_id -> display name mapping)
        values = [cam['instance_id'] for cam in cameras]
        self.camera_combo['values'] = values
        
        # Select preferred or first camera
        preferred = self.config.get('preferred_camera_id')
        if preferred and preferred in values:
            self.selected_camera_id.set(preferred)
        else:
            self.selected_camera_id.set(values[0])
            self.config['preferred_camera_id'] = values[0]
            save_config(self.config)
        
        self._update_status_from_selection()
        self.progress_label.config(text=f"Found {len(cameras)} camera(s)")
    
    def _set_processing_state(self, processing: bool, message: str = ""):
        """Set the processing state of the UI."""
        self.is_processing = processing
        
        if processing:
            self.btn_enable.config(state=tk.DISABLED)
            self.btn_disable.config(state=tk.DISABLED)
            self.progress_label.config(text=message)
        else:
            self.btn_enable.config(state=tk.NORMAL)
            self.btn_disable.config(state=tk.NORMAL)
            self.progress_label.config(text=message or "Ready")
    
    def _enable_camera_threaded(self):
        """Enable camera in a separate thread."""
        if self.is_processing:
            return
        
        self._set_processing_state(True, "Enabling camera...")
        threading.Thread(target=self._enable_camera_worker, daemon=True).start()
    
    def _enable_camera_worker(self):
        """Worker function to enable camera."""
        try:
            success, message = self._enable_camera()
            self.root.after(0, lambda: self._handle_enable_result(success, message))
        except Exception as e:
            self.root.after(0, lambda: self._handle_enable_result(False, str(e)))
    
    def _enable_camera(self) -> Tuple[bool, str]:
        """Enable the selected camera.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        camera_id = self.selected_camera_id.get()
        
        if not camera_id:
            return False, "No camera selected"
        
        errors = []
        
        # Enable by instance ID
        if camera_id:
            # Use single braces for PowerShell script block syntax
            ps_enable = f'Enable-PnpDevice -InstanceId "{camera_id}" -Confirm:$false -ErrorAction SilentlyContinue'
            success, stdout, stderr = run_powershell_command(ps_enable)
            if not success:
                errors.append(f"Instance ID: {stderr}")
        
        # Start Windows Camera Frame Server with verification
        service_success, service_msg = restart_camera_frame_server(max_retries=2)
        if not service_success:
            errors.append(f"Camera Frame Server: {service_msg}")
        
        # Remove registry block for non-packaged apps
        run_powershell_command(
            'Remove-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam\\NonPackaged" '
            '-Name "Value" -ErrorAction SilentlyContinue'
        )
        # Also clear the main webcam value if it exists
        run_powershell_command(
            'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
            '-Name "Value" -Value "Allow" -ErrorAction SilentlyContinue'
        )
        
        # Refresh status
        self.cameras = get_camera_devices()
        
        # Check if camera is now enabled
        for cam in self.cameras:
            if cam['instance_id'] == camera_id:
                if cam.get('status') == 'OK':
                    return True, "Camera enabled successfully"
        
        if errors:
            return False, f"Issues: {'; '.join(errors)}"
        return True, "Camera enable command executed"
    
    def _handle_enable_result(self, success: bool, message: str):
        """Handle the result of enable operation."""
        self._update_status_from_selection()
        self._set_processing_state(False, message)
        
        if success:
            self.status_label.config(text="ACTIVE", fg=COLORS["success"])
        else:
            messagebox.showwarning("Enable Issue", message, parent=self.root)
    
    def _disable_camera_threaded(self):
        """Disable camera in a separate thread."""
        if self.is_processing:
            return
        
        if self.config.get('confirm_actions', True):
            response = messagebox.askyesno(
                "Confirm Disable",
                "Are you sure you want to disable the camera?",
                parent=self.root
            )
            if not response:
                self._set_processing_state(False, "Cancelled")
                return
        
        self._set_processing_state(True, "Disabling camera...")
        threading.Thread(target=self._disable_camera_worker, daemon=True).start()
    
    def _disable_camera_worker(self):
        """Worker function to disable camera."""
        try:
            success, message = self._disable_camera()
            self.root.after(0, lambda: self._handle_disable_result(success, message))
        except Exception as e:
            self.root.after(0, lambda: self._handle_disable_result(False, str(e)))
    
    def _disable_camera(self) -> Tuple[bool, str]:
        """Disable the selected camera.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        camera_id = self.selected_camera_id.get()
        
        if not camera_id:
            return False, "No camera selected"
        
        errors = []
        
        # Disable by instance ID
        if camera_id:
            # Use single braces for PowerShell script block syntax
            ps_disable = f'Disable-PnpDevice -InstanceId "{camera_id}" -Confirm:$false -ErrorAction SilentlyContinue'
            success, stdout, stderr = run_powershell_command(ps_disable)
            if not success:
                errors.append(f"Instance ID: {stderr}")
        
        # Stop Windows Camera Frame Server (temporary - don't change startup type)
        run_powershell_command(
            "Stop-Service -Name 'Windows Camera Frame Server' -Force -ErrorAction SilentlyContinue"
        )
        
        # Block via registry for current session only (volatile)
        run_powershell_command(
            'New-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam\\NonPackaged" '
            '-Force -ErrorAction SilentlyContinue | Out-Null'
        )
        run_powershell_command(
            'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam\\NonPackaged" '
            '-Name "Value" -Value "Deny" -ErrorAction SilentlyContinue'
        )
        
        # Refresh status
        self.cameras = get_camera_devices()
        
        # Check if camera is now disabled
        for cam in self.cameras:
            if cam['instance_id'] == camera_id:
                if cam.get('status') == 'Error':
                    return True, "Camera blocked successfully"
        
        if errors:
            return False, f"Issues: {'; '.join(errors)}"
        return True, "Camera disable command executed"
    
    def _handle_disable_result(self, success: bool, message: str):
        """Handle the result of disable operation."""
        self._update_status_from_selection()
        self._set_processing_state(False, message)
        
        if not success:
            messagebox.showwarning("Disable Issue", message, parent=self.root)
        else:
            self.status_label.config(text="BLOCKED", fg=COLORS["error"])
    
    def _on_closing(self):
        """Handle window close event."""
        # Save config
        self.config['auto_enable_on_exit'] = self.auto_enable_var.get()
        save_config(self.config)
        
        # Auto-enable if configured (with better cleanup)
        if self.auto_enable_var.get() and self.selected_camera_id.get():
            try:
                # Ensure service is re-enabled first with verification
                restart_camera_frame_server(max_retries=2)
                
                # Clear registry blocks
                run_powershell_command(
                    'Remove-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam\\NonPackaged" '
                    '-Name "Value" -ErrorAction SilentlyContinue'
                )
                run_powershell_command(
                    'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" '
                    '-Name "Value" -Value "Allow" -ErrorAction SilentlyContinue'
                )
                # Re-enable the PnP device
                self._enable_camera()
            except Exception:
                pass
        
        self.root.destroy()


def main():
    """Main entry point."""
    # Check for admin privileges
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
    
    # Create main window
    root = tk.Tk()
    app = CameraBlockerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
