"""
Base Scanner Module
Abstract base class for all vendor-specific network discovery scanners.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
from scapy.packet import Packet


@dataclass
class Device:
    """
    Represents a discovered network device.
    Uses MAC address as the unique identifier.
    """
    brand: str
    ip: str
    mac: str
    name: str
    model: str = ""
    firmware: str = ""
    uptime: int = 0
    discovered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def unique_id(self) -> str:
        """MAC address serves as the unique identifier."""
        return self.mac.upper()
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert device to dictionary for serialization."""
        return {
            'brand': self.brand,
            'ip': self.ip,
            'mac': self.mac,
            'name': self.name,
            'model': self.model,
            'firmware': self.firmware,
            'uptime': self.uptime,
            'discovered_at': self.discovered_at.isoformat(),
            'last_seen': self.last_seen.isoformat(),
        }


class BaseScanner(ABC):
    """
    Abstract base class for network device scanners.
    
    Each vendor-specific scanner must extend this class and implement:
    - port: The UDP port to listen on
    - brand: The brand name for discovered devices
    - parse_packet: Logic to extract device info from packets
    """
    
    def __init__(self):
        self._callback: Optional[Callable[[Device], None]] = None
    
    @property
    @abstractmethod
    def port(self) -> int:
        """UDP port number to listen for discovery packets."""
        pass
    
    @property
    @abstractmethod
    def brand(self) -> str:
        """Brand name for devices discovered by this scanner."""
        pass
    
    @property
    def filter_expression(self) -> str:
        """BPF filter expression for Scapy sniffing."""
        return f"udp port {self.port}"
    
    @abstractmethod
    def parse_packet(self, packet: Packet) -> Optional[Device]:
        """
        Parse a captured packet and extract device information.
        
        Args:
            packet: Scapy packet captured from the network
            
        Returns:
            Device object if packet contains valid discovery data,
            None otherwise
        """
        pass
    
    def set_callback(self, callback: Callable[[Device], None]):
        """
        Set callback function to be called when a device is discovered.
        
        Args:
            callback: Function that takes a Device object
        """
        self._callback = callback
    
    def handle_packet(self, packet: Packet):
        """
        Process a captured packet and trigger callback if device found.
        
        Args:
            packet: Scapy packet to process
        """
        try:
            device = self.parse_packet(packet)
            if device and self._callback:
                self._callback(device)
        except Exception as e:
            # Log error but don't crash the scanner
            print(f"[{self.brand}] Packet parsing error: {e}")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} port={self.port} brand='{self.brand}'>"
