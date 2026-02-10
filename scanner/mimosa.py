"""
MNDP (Mikrotik Neighbor Discovery Protocol) Scanner
Listens for MNDP packets on UDP port 5678.

This scanner supports:
- Mikrotik RouterOS devices
- Mimosa devices (uses MNDP compatible protocol)
- Other MNDP-compatible vendors

Protocol Reference:
- UDP port 5678
- Packet format: Type-Length-Value (TLV) structure
- Common TLV types:
    0x0001: MAC Address
    0x0005: Identity (Device Name)
    0x0007: Version (Firmware)
    0x0008: Platform (Model)
    0x000A: Uptime
    0x000B: Software ID
    0x000E: Board Name
    0x000F: Unpack (compression info)
    0x0010: IPv6 Address
    0x0011: Interface Name
    0x0014: IPv4 Address
"""

import struct
from typing import Optional
from scapy.packet import Packet
from scapy.layers.inet import IP, UDP

from .base import BaseScanner, Device


class MNDPScanner(BaseScanner):
    """
    Scanner for Mikrotik/Mimosa devices using MNDP protocol.
    Captures and parses UDP broadcast packets on port 5678.
    """
    
    # MNDP TLV Type Constants
    TLV_MAC_ADDRESS = 0x0001
    TLV_IDENTITY = 0x0005
    TLV_VERSION = 0x0007
    TLV_PLATFORM = 0x0008
    TLV_UPTIME = 0x000A
    TLV_SOFTWARE_ID = 0x000B
    TLV_BOARD = 0x000E
    TLV_IPV6 = 0x0010
    TLV_INTERFACE = 0x0011
    TLV_IPV4 = 0x0014
    
    @property
    def port(self) -> int:
        return 5678
    
    @property
    def brand(self) -> str:
        return "Mikrotik/Mimosa"
    
    def parse_packet(self, packet: Packet) -> Optional[Device]:
        """
        Parse MNDP (Mikrotik Neighbor Discovery Protocol) packet.
        
        MNDP packets consist of consecutive TLV entries:
        - 2 bytes: Type (little-endian)
        - 2 bytes: Length (little-endian)
        - N bytes: Value
        """
        # Ensure packet has IP and UDP layers
        if not packet.haslayer(IP) or not packet.haslayer(UDP):
            return None
        
        udp_layer = packet[UDP]
        
        # Check if this is on our port
        if udp_layer.sport != self.port and udp_layer.dport != self.port:
            return None
        
        # Get raw payload
        if not hasattr(udp_layer, 'load') or udp_layer.load is None:
            return None
        
        payload = bytes(udp_layer.load)
        
        # Minimum size check
        if len(payload) < 4:
            return None
        
        # Parse TLV entries
        tlv_data = self._parse_tlv(payload)
        
        # Extract required fields
        mac = tlv_data.get('mac', '')
        ip = tlv_data.get('ip', packet[IP].src)
        identity = tlv_data.get('identity', 'Unknown')
        platform = tlv_data.get('platform', '')
        board = tlv_data.get('board', '')
        version = tlv_data.get('version', '')
        uptime = tlv_data.get('uptime', 0)
        
        # MAC is required
        if not mac:
            return None
        
        # Determine brand based on platform/board info
        brand = self._detect_brand(platform, board)
        
        # Use board as model, or platform if board not available
        model = board if board else platform
        
        return Device(
            brand=brand,
            ip=ip,
            mac=mac,
            name=identity,
            model=model,
            firmware=version,
            uptime=uptime
        )
    
    def _parse_tlv(self, data: bytes) -> dict:
        """
        Parse Type-Length-Value encoded data from MNDP packet.
        
        Each TLV entry:
        - 2 bytes: Type (little-endian)
        - 2 bytes: Length (little-endian)
        - N bytes: Value
        """
        result = {}
        offset = 0
        
        while offset + 4 <= len(data):
            try:
                tlv_type = struct.unpack('<H', data[offset:offset+2])[0]
                tlv_len = struct.unpack('<H', data[offset+2:offset+4])[0]
                
                if offset + 4 + tlv_len > len(data):
                    break
                
                value = data[offset+4:offset+4+tlv_len]
                
                # Parse based on type
                if tlv_type == self.TLV_MAC_ADDRESS:
                    if len(value) >= 6:
                        result['mac'] = ':'.join(f'{b:02X}' for b in value[:6])
                
                elif tlv_type == self.TLV_IDENTITY:
                    result['identity'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_VERSION:
                    result['version'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_PLATFORM:
                    result['platform'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_BOARD:
                    result['board'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_UPTIME:
                    if len(value) >= 4:
                        result['uptime'] = struct.unpack('<I', value[:4])[0]
                
                elif tlv_type == self.TLV_IPV4:
                    if len(value) >= 4:
                        result['ip'] = '.'.join(str(b) for b in value[:4])
                
                offset += 4 + tlv_len
                
            except Exception:
                break
        
        return result
    
    def _detect_brand(self, platform: str, board: str) -> str:
        """
        Detect device brand based on platform and board information.
        
        Args:
            platform: Platform string from MNDP
            board: Board name from MNDP
            
        Returns:
            Detected brand name
        """
        combined = (platform + ' ' + board).lower()
        
        # Mimosa detection
        if 'mimosa' in combined:
            return 'Mimosa'
        
        # Mikrotik specific boards/platforms
        mikrotik_indicators = [
            'routerboard', 'rb', 'ccr', 'crs', 'css', 'hex', 'hap',
            'mikrotik', 'routeros', 'chr', 'ltap', 'wap', 'disc',
            'sxt', 'lhg', 'basebox', 'netbox', 'netmetal', 'powerbox'
        ]
        
        for indicator in mikrotik_indicators:
            if indicator in combined:
                return 'Mikrotik'
        
        # Default to generic MNDP
        return 'Mikrotik/MNDP'
