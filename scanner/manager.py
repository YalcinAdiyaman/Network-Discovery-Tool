"""
Scanner Manager
Orchestrates multiple vendor scanners and manages discovered devices.
"""

import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime

from scapy.all import sniff, conf

from .base import BaseScanner, Device


class ScannerManager:
    """
    Manages multiple network device scanners and aggregates discovered devices.
    
    Features:
    - Register multiple scanner modules
    - Combined packet sniffing for all registered ports
    - Device deduplication using MAC address
    - Thread-safe device storage
    - Callback mechanism for UI updates
    """
    
    def __init__(self):
        self._scanners: List[BaseScanner] = []
        self._devices: Dict[str, Device] = {}  # MAC -> Device
        self._lock = threading.RLock()
        self._sniff_thread: Optional[threading.Thread] = None
        self._running = False
        self._on_device_callback: Optional[Callable[[Device], None]] = None
        self._on_device_update_callback: Optional[Callable[[Device], None]] = None
        
        # Configure Scapy for Windows
        conf.use_pcap = True
    
    def register_scanner(self, scanner: BaseScanner):
        """
        Register a scanner module.
        
        Args:
            scanner: Scanner instance extending BaseScanner
        """
        scanner.set_callback(self._on_device_discovered)
        self._scanners.append(scanner)
        print(f"[Manager] Registered: {scanner}")
    
    def set_on_device_discovered(self, callback: Callable[[Device], None]):
        """
        Set callback for when a NEW device is discovered.
        
        Args:
            callback: Function taking a Device object
        """
        self._on_device_callback = callback
    
    def set_on_device_updated(self, callback: Callable[[Device], None]):
        """
        Set callback for when an existing device is updated (seen again).
        
        Args:
            callback: Function taking a Device object
        """
        self._on_device_update_callback = callback
    
    def _on_device_discovered(self, device: Device):
        """
        Internal callback when any scanner finds a device.
        Handles deduplication and triggers appropriate callbacks.
        """
        with self._lock:
            unique_id = device.unique_id
            
            if unique_id in self._devices:
                # Update existing device's last seen time
                existing = self._devices[unique_id]
                existing.update_last_seen()
                
                # Update IP if changed
                if existing.ip != device.ip:
                    existing.ip = device.ip
                
                if self._on_device_update_callback:
                    self._on_device_update_callback(existing)
            else:
                # New device
                self._devices[unique_id] = device
                print(f"[Manager] New device: {device.brand} - {device.name} ({device.ip})")
                
                if self._on_device_callback:
                    self._on_device_callback(device)
    
    def _build_filter(self) -> str:
        """Build combined BPF filter for all registered scanners."""
        ports = [str(s.port) for s in self._scanners]
        if not ports:
            return "udp"
        return f"udp and (port {' or port '.join(ports)})"
    
    def _packet_handler(self, packet):
        """
        Route captured packets to appropriate scanner.
        
        Each scanner will check if the packet is relevant and parse it.
        """
        for scanner in self._scanners:
            scanner.handle_packet(packet)
    
    def _sniff_loop(self, iface: Optional[str] = None):
        """
        Main sniffing loop running in background thread.
        
        Args:
            iface: Network interface to sniff on (None = all interfaces)
        """
        filter_expr = self._build_filter()
        print(f"[Manager] Starting sniff with filter: {filter_expr}")
        
        try:
            sniff(
                filter=filter_expr,
                prn=self._packet_handler,
                store=False,
                stop_filter=lambda _: not self._running,
                iface=iface
            )
        except PermissionError:
            print("[Manager] ERROR: Administrator privileges required for packet capture!")
        except Exception as e:
            print(f"[Manager] Sniff error: {e}")
        finally:
            print("[Manager] Sniff loop ended")
    
    def start(self, iface: Optional[str] = None):
        """
        Start the scanner manager in a background thread.
        
        Args:
            iface: Network interface to sniff on (None = all interfaces)
        """
        if self._running:
            print("[Manager] Already running")
            return
        
        if not self._scanners:
            print("[Manager] Warning: No scanners registered!")
        
        self._running = True
        self._sniff_thread = threading.Thread(
            target=self._sniff_loop,
            args=(iface,),
            daemon=True,
            name="ScannerThread"
        )
        self._sniff_thread.start()
        print("[Manager] Scanner started")
    
    def stop(self):
        """Stop the scanner manager."""
        self._running = False
        if self._sniff_thread and self._sniff_thread.is_alive():
            self._sniff_thread.join(timeout=2.0)
        print("[Manager] Scanner stopped")
    
    def get_devices(self) -> List[Device]:
        """
        Get list of all discovered devices.
        
        Returns:
            List of Device objects
        """
        with self._lock:
            return list(self._devices.values())
    
    def get_device_count(self) -> int:
        """Get number of discovered devices."""
        with self._lock:
            return len(self._devices)
    
    def clear_devices(self):
        """Clear all discovered devices."""
        with self._lock:
            self._devices.clear()
        print("[Manager] Device list cleared")
    
    def is_running(self) -> bool:
        """Check if scanner is currently running."""
        return self._running
    
    @property
    def registered_scanners(self) -> List[str]:
        """Get list of registered scanner names."""
        return [s.brand for s in self._scanners]
    
    def __repr__(self) -> str:
        return f"<ScannerManager scanners={len(self._scanners)} devices={self.get_device_count()}>"


# Convenience function to create a pre-configured manager
def create_default_manager() -> ScannerManager:
    """
    Create a ScannerManager with all default scanners registered.
    
    Returns:
        Configured ScannerManager instance
    """
    from .ubnt import UbiquitiScanner
    from .mimosa import MNDPScanner
    
    manager = ScannerManager()
    manager.register_scanner(UbiquitiScanner())
    manager.register_scanner(MNDPScanner())
    
    return manager
