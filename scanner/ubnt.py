"""
Ubiquiti Discovery Scanner
Listens for Ubiquiti Discovery Protocol packets on UDP port 10001.

Protocol Reference:
- Ubiquiti devices broadcast discovery packets on UDP 10001
- Packet format: Type-Length-Value (TLV) structure
- Common TLV types:
    0x01: Hardware Address (MAC)
    0x02: IP Info (MAC + IP)
    0x03: Firmware Version
    0x0B: Device Name (Hostname)
    0x0C: Model (Short)
    0x0D: ESSID
    0x0E: Uptime
    0x14: Model (Full)
"""

import struct
from typing import Optional
from scapy.packet import Packet
from scapy.layers.inet import IP, UDP

from .base import BaseScanner, Device


class UbiquitiScanner(BaseScanner):
    """
    Scanner for Ubiquiti devices using the Ubiquiti Discovery Protocol.
    Captures and parses UDP broadcast packets on port 10001.
    """
    
    # Ubiquiti TLV Type Constants
    TLV_MAC_ADDRESS = 0x01
    TLV_IP_INFO = 0x02
    TLV_FIRMWARE = 0x03
    TLV_HOSTNAME = 0x0B
    TLV_MODEL_SHORT = 0x0C
    TLV_ESSID = 0x0D
    TLV_UPTIME = 0x0E
    TLV_MODEL_FULL = 0x14
    
    @property
    def port(self) -> int:
        return 10001
    
    @property
    def brand(self) -> str:
        return "Ubiquiti"
    
    def parse_packet(self, packet: Packet) -> Optional[Device]:
        """
        Parse Ubiquiti Discovery Protocol packet.
        
        The packet payload starts with a header:
        - Bytes 0-1: Version (0x01 0x00)
        - Bytes 2-3: Command (0x00 0x00 for discovery response)
        - Bytes 4-5: Payload length
        
        Followed by TLV entries.
        """
        # Ensure packet has IP and UDP layers
        if not packet.haslayer(IP) or not packet.haslayer(UDP):
            return None
        
        udp_layer = packet[UDP]
        
        # Check if this is on our port (source or destination)
        if udp_layer.sport != self.port and udp_layer.dport != self.port:
            return None
        
        # Get raw payload
        if not hasattr(udp_layer, 'load') or udp_layer.load is None:
            return None
        
        payload = bytes(udp_layer.load)
        
        # Minimum header size check
        if len(payload) < 6:
            return None
        
        # Verify Ubiquiti discovery signature (version 1)
        if payload[0:2] != b'\x01\x00' and payload[0:2] != b'\x02\x00':
            return None
        
        # Parse TLV entries
        tlv_data = self._parse_tlv(payload[4:])
        
        # Extract required fields
        mac = tlv_data.get('mac', '')
        ip = tlv_data.get('ip', packet[IP].src)
        name = tlv_data.get('hostname', 'Unknown')
        model = tlv_data.get('model', '')
        firmware = tlv_data.get('firmware', '')
        uptime = tlv_data.get('uptime', 0)
        
        # MAC is required
        if not mac:
            return None
        
        return Device(
            brand=self.brand,
            ip=ip,
            mac=mac,
            name=name,
            model=model,
            firmware=firmware,
            uptime=uptime
        )
    
    def _parse_tlv(self, data: bytes) -> dict:
        """
        Parse Type-Length-Value encoded data from Ubiquiti packet.
        
        Each TLV entry:
        - 1 byte: Type
        - 2 bytes: Length (big-endian)
        - N bytes: Value
        """
        result = {}
        offset = 0
        
        while offset + 3 <= len(data):
            try:
                tlv_type = data[offset]
                tlv_len = struct.unpack('>H', data[offset+1:offset+3])[0]
                
                if offset + 3 + tlv_len > len(data):
                    break
                
                value = data[offset+3:offset+3+tlv_len]
                
                # Parse based on type
                if tlv_type == self.TLV_MAC_ADDRESS:
                    if len(value) >= 6:
                        result['mac'] = ':'.join(f'{b:02X}' for b in value[:6])
                
                elif tlv_type == self.TLV_IP_INFO:
                    # Format: 6 bytes MAC + 4 bytes IP
                    if len(value) >= 10:
                        result['mac'] = ':'.join(f'{b:02X}' for b in value[:6])
                        result['ip'] = '.'.join(str(b) for b in value[6:10])
                
                elif tlv_type == self.TLV_FIRMWARE:
                    result['firmware'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_HOSTNAME:
                    result['hostname'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_MODEL_SHORT:
                    if 'model' not in result:  # Prefer full model
                        result['model'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_MODEL_FULL:
                    result['model'] = value.decode('utf-8', errors='ignore').strip('\x00')
                
                elif tlv_type == self.TLV_UPTIME:
                    if len(value) >= 4:
                        result['uptime'] = struct.unpack('>I', value[:4])[0]
                
                offset += 3 + tlv_len
                
            except Exception:
                break
        
        return result
