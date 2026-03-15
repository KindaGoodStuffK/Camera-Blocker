"""
Build script to create standalone Windows executable for HP Camera Blocker.
Run: python build_app.py
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller():
    """Install PyInstaller."""
    print("Installing PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    print("PyInstaller installed.")


def build_exe():
    """Build the executable using PyInstaller."""
    app_name = "HP CamBlock"
    main_script = "hp_camera_blocker.py"
    
    # Create icon if it doesn't exist (simple camera icon)
    icon_path = create_icon()
    
    # Build command - only add icon if we have a valid one
    icon_args = []
    if icon_path and icon_path != "NONE":
        icon_args = [f"--icon={icon_path}", "--add-data", f"{icon_path};."]
    
    # Build command
    cmd = [
        "pyinstaller",
        "--onefile",           # Single executable file
        "--windowed",          # GUI mode (no console window)
        "--noconfirm",         # Overwrite existing build
        "--clean",             # Clean build
        f"--name={app_name}",
        *icon_args,
        "--uac-admin",         # Request admin privileges
        main_script
    ]
    
    print(f"Building {app_name}...")
    print("This may take a few minutes...")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[OK] Build complete!")
        print(f"  Executable: dist/{app_name}.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] Build failed: {e}")
        return False


def create_icon():
    """Create a simple camera icon or return existing icon path."""
    icon_path = Path("camera_icon.ico")
    
    if icon_path.exists():
        return str(icon_path)
    
    # Try to create a simple icon using PIL if available
    try:
        from PIL import Image, ImageDraw
        
        # Create a simple camera icon
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw camera body (rectangle)
        draw.rectangle([40, 80, 216, 176], fill='#89b4fa', outline='#1e1e2e', width=4)
        # Draw lens (circle)
        draw.ellipse([88, 88, 168, 168], fill='#1e1e2e', outline='#cdd6f4', width=3)
        draw.ellipse([108, 108, 148, 148], fill='#313244')
        # Draw flash (small rectangle)
        draw.rectangle([168, 96, 200, 112], fill='#f9e2af')
        
        # Save as PNG first, then convert to ICO
        png_path = Path("camera_icon.png")
        img.save(png_path)
        
        # Create multi-size ICO
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = []
        for size in sizes:
            icons.append(img.resize(size, Image.Resampling.LANCZOS))
        
        icons[0].save(icon_path, format='ICO', sizes=sizes, append_images=icons[1:])
        
        # Clean up PNG
        png_path.unlink(missing_ok=True)
        
        print("Created camera icon.")
        return str(icon_path)
        
    except ImportError:
        print("PIL not available, using default icon.")
        # Return empty string to use default pyinstaller icon
        return "NONE"


def create_uac_manifest():
    """Create UAC manifest for admin privileges."""
    manifest_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v2">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">permonitorv2</dpiAwareness>
    </windowsSettings>
  </application>
</assembly>'''
    
    with open("uac.manifest", "w") as f:
        f.write(manifest_content)
    
    return "uac.manifest"


def create_version_info():
    """Create version info file."""
    version_info = '''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'HP CamBlock'),
        StringStruct(u'FileDescription', u'HP Camera Privacy Control'),
        StringStruct(u'FileVersion', u'2.0.0.0'),
        StringStruct(u'InternalName', u'HP CamBlock'),
        StringStruct(u'LegalCopyright', u'© 2026'),
        StringStruct(u'OriginalFilename', u'HP CamBlock.exe'),
        StringStruct(u'ProductName', u'HP CamBlock'),
        StringStruct(u'ProductVersion', u'2.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [0x409, 1200])])
  ]
)'''
    
    with open("version.txt", "w") as f:
        f.write(version_info)
    
    return "version.txt"


def main():
    """Main build process."""
    print("=" * 60)
    print("  HP CamBlock - Windows App Builder")
    print("=" * 60)
    print()
    
    # Check/install PyInstaller
    if not check_pyinstaller():
        install_pyinstaller()
        # Re-check after install
        if not check_pyinstaller():
            print("ERROR: PyInstaller installation failed!")
            print("Try running: pip install pyinstaller")
            return
    
    # Create support files
    # (No longer need uac.manifest - using --uac-admin instead)
    create_version_info()
    
    # Clean old builds
    for folder in ["build", "dist"]:
        if Path(folder).exists():
            shutil.rmtree(folder)
    
    # Build
    if build_exe():
        print()
        print("Next steps:")
        print("  1. Run 'python create_installer.py' to create the installer")
        print("  2. Or copy 'dist/HP CamBlock.exe' to your desktop")
        print()
        print("The app will request admin privileges when launched.")
    
    # Cleanup temp files
    for f in ["version.txt", "camera_icon.ico"]:
        Path(f).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
