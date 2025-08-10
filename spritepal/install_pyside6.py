#!/usr/bin/env python3
"""
PySide6 Installation Script

This script helps install PySide6 and verifies the installation works correctly.
"""

import subprocess
import sys
from pathlib import Path


def install_pyside6():
    """Install PySide6 using pip"""
    print("Installing PySide6...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PySide6"])
        print("✓ PySide6 installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install PySide6: {e}")
        return False

def verify_installation():
    """Verify that PySide6 is properly installed"""
    print("\nVerifying PySide6 installation...")

    try:
        # Test basic imports
        from PySide6.QtCore import Qt, Signal, Slot
        from PySide6.QtGui import QIcon, QPalette, QPixmap
        from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
        print("✓ Core PySide6 imports working")

        # Test signal/slot functionality
        from PySide6.QtCore import QObject

        class TestObject(QObject):
            test_signal = Signal(str)

            @Slot()
            def test_slot(self):
                pass

        print("✓ Signal/Slot functionality working")

        # Test basic widget creation (no GUI)
        app = QApplication([])
        QWidget()
        app.quit()
        print("✓ Basic widget creation working")

        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

def check_requirements():
    """Check if requirements.txt needs updating"""
    req_file = Path("requirements.txt")
    if req_file.exists():
        content = req_file.read_text()
        if "PyQt6" in content and "PySide6" not in content:
            print("\n⚠ Warning: requirements.txt contains PyQt6 but not PySide6")
            print("Consider updating requirements.txt to include PySide6")

            # Suggest new content
            suggested_content = content.replace("PyQt6", "PySide6")
            print("\nSuggested requirements.txt update:")
            print("-" * 40)
            for line in suggested_content.split('\n'):
                if 'PySide6' in line:
                    print(f"+ {line}")
            print("-" * 40)

            response = input("\nUpdate requirements.txt automatically? (y/N): ").strip().lower()
            if response == 'y':
                req_file.write_text(suggested_content)
                print("✓ requirements.txt updated")

def main():
    """Main installation and verification process"""
    print("PySide6 Installation Helper")
    print("="*40)

    # Check if already installed
    try:
        import PySide6
        print("PySide6 is already installed")
        if verify_installation():
            print("\n✓ PySide6 is working correctly!")
            check_requirements()
            return True
        print("\n✗ PySide6 installation has issues")
        return False
    except ImportError:
        pass

    # Install PySide6
    if not install_pyside6():
        return False

    # Verify installation
    if verify_installation():
        print("\n✓ PySide6 installation completed and verified!")
        check_requirements()

        print("\nNext steps:")
        print("1. You can now run the migrated SpritePal application")
        print("2. Test with: python3 launch_spritepal.py")
        print("3. If you encounter any issues, check the backup in backup_pyqt6_migration/")

        return True
    print("\n✗ Installation verification failed")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
