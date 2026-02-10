"""
Network Discovery Tool - Main Entry Point
ISP Device Management System

A professional network discovery tool for ISP networks.
Supports Ubiquiti, Mikrotik, and Mimosa device detection.

Usage:
    python main.py

Requirements:
    - Run as Administrator (for packet capture)
    - Scapy >= 2.5.0
    - CustomTkinter >= 5.2.0
    - Pillow >= 10.0.0
    - Npcap installed on Windows
"""

import sys
import os
import ctypes

# Project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def is_admin() -> bool:
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def main():
    """Main application entry point."""
    print("=" * 60)
    print("  Network Discovery Tool - ISP Device Management System")
    print("=" * 60)
    print()
    
    # Admin check
    if not is_admin():
        print("[WARNING] Not running as Administrator!")
        print("[WARNING] Packet capture may not work correctly.")
        print("[INFO] For full functionality, run as Administrator.")
        print()
    
    # Import modules
    from i18n import I18n
    from scanner import ScannerManager, UbiquitiScanner, MNDPScanner
    from ui import DashboardApp
    
    # Initialize i18n
    print("[Main] Initializing localization...")
    i18n = I18n()
    print(f"[Main] Language: {i18n.current_language}")
    
    # Initialize scanner manager (but don't start yet)
    print("[Main] Initializing scanner manager...")
    scanner_manager = ScannerManager()
    
    # Register scanners
    print("[Main] Registering scanners...")
    scanner_manager.register_scanner(UbiquitiScanner())
    scanner_manager.register_scanner(MNDPScanner())
    print(f"[Main] Registered: {scanner_manager.registered_scanners}")
    print()
    
    # Create and run UI (scanning starts when user clicks button)
    print("[Main] Starting UI in idle mode...")
    print("[Main] Click 'Start Scanning' to begin device discovery.")
    print()
    
    app = DashboardApp(scanner_manager, i18n)
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user")
    finally:
        scanner_manager.stop()
        print("[Main] Shutdown complete")


if __name__ == "__main__":
    main()
