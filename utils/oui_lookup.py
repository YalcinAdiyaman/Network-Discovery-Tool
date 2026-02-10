"""
OUI (Organizationally Unique Identifier) Vendor Lookup Module
Identifies device manufacturers based on MAC address prefix.

The OUI is the first 3 bytes (6 hex characters) of a MAC address,
assigned by IEEE to identify the manufacturer.
"""

import os
import json
from typing import Optional, Dict


class OUILookup:
    """
    MAC address OUI vendor lookup utility.
    
    Uses a local database of OUI prefixes to identify manufacturers
    when the discovery protocol doesn't provide vendor information.
    """
    
    # Common ISP/Network equipment vendors (built-in database)
    BUILTIN_OUI_DB: Dict[str, str] = {
        # Ubiquiti Networks
        "00:15:6D": "Ubiquiti",
        "00:27:22": "Ubiquiti",
        "04:18:D6": "Ubiquiti",
        "18:E8:29": "Ubiquiti",
        "24:5A:4C": "Ubiquiti",
        "24:A4:3C": "Ubiquiti",
        "44:D9:E7": "Ubiquiti",
        "68:72:51": "Ubiquiti",
        "70:A7:41": "Ubiquiti",
        "74:83:C2": "Ubiquiti",
        "78:8A:20": "Ubiquiti",
        "80:2A:A8": "Ubiquiti",
        "9C:05:D6": "Ubiquiti",
        "AC:8B:A9": "Ubiquiti",
        "B4:FB:E4": "Ubiquiti",
        "D0:21:F9": "Ubiquiti",
        "DC:9F:DB": "Ubiquiti",
        "E0:63:DA": "Ubiquiti",
        "E2:63:DA": "Ubiquiti",
        "F0:9F:C2": "Ubiquiti",
        "FC:EC:DA": "Ubiquiti",
        
        # Mikrotik
        "00:0C:42": "Mikrotik",
        "08:55:31": "Mikrotik",
        "18:FD:74": "Mikrotik",
        "2C:C8:1B": "Mikrotik",
        "48:8F:5A": "Mikrotik",
        "4C:5E:0C": "Mikrotik",
        "64:D1:54": "Mikrotik",
        "6C:3B:6B": "Mikrotik",
        "74:4D:28": "Mikrotik",
        "B8:69:F4": "Mikrotik",
        "C4:AD:34": "Mikrotik",
        "CC:2D:E0": "Mikrotik",
        "D4:01:C3": "Mikrotik",
        "D4:CA:6D": "Mikrotik",
        "DC:2C:6E": "Mikrotik",
        "E4:8D:8C": "Mikrotik",
        
        # Mimosa Networks
        "58:C1:7A": "Mimosa",
        
        # Cambium Networks
        "00:04:56": "Cambium",
        "58:C1:7A": "Cambium",
        
        # TP-Link
        "00:1D:0F": "TP-Link",
        "00:23:CD": "TP-Link",
        "14:CC:20": "TP-Link",
        "30:B5:C2": "TP-Link",
        "50:C7:BF": "TP-Link",
        "54:C8:0F": "TP-Link",
        "60:E3:27": "TP-Link",
        "6C:5A:B0": "TP-Link",
        "90:F6:52": "TP-Link",
        "98:DA:C4": "TP-Link",
        "B0:BE:76": "TP-Link",
        "C0:25:E9": "TP-Link",
        "C4:E9:84": "TP-Link",
        "D8:07:B6": "TP-Link",
        "E8:DE:27": "TP-Link",
        "F4:F2:6D": "TP-Link",
        
        # Cisco
        "00:00:0C": "Cisco",
        "00:01:42": "Cisco",
        "00:01:43": "Cisco",
        "00:01:64": "Cisco",
        "00:02:3D": "Cisco",
        "00:02:4A": "Cisco",
        "00:02:4B": "Cisco",
        "00:02:7D": "Cisco",
        "00:02:7E": "Cisco",
        "00:03:31": "Cisco",
        "00:03:32": "Cisco",
        
        # Huawei
        "00:18:82": "Huawei",
        "00:1E:10": "Huawei",
        "00:25:9E": "Huawei",
        "00:25:68": "Huawei",
        "00:46:4B": "Huawei",
        "04:02:1F": "Huawei",
        "04:25:C5": "Huawei",
        "04:33:89": "Huawei",
        "04:F9:38": "Huawei",
        
        # Netgear
        "00:09:5B": "Netgear",
        "00:0F:B5": "Netgear",
        "00:14:6C": "Netgear",
        "00:18:4D": "Netgear",
        "00:1B:2F": "Netgear",
        "00:1E:2A": "Netgear",
        "00:1F:33": "Netgear",
        "00:22:3F": "Netgear",
        "00:24:B2": "Netgear",
        
        # Aruba Networks
        "00:0B:86": "Aruba",
        "00:1A:1E": "Aruba",
        "00:24:6C": "Aruba",
        "04:BD:88": "Aruba",
        "18:64:72": "Aruba",
        "20:4C:03": "Aruba",
        "24:DE:C6": "Aruba",
        
        # Ruckus Wireless
        "00:1F:41": "Ruckus",
        "00:22:7F": "Ruckus",
        "00:25:C4": "Ruckus",
        "58:B6:33": "Ruckus",
        "74:91:1A": "Ruckus",
        "84:18:3A": "Ruckus",
        
        # Juniper
        "00:05:85": "Juniper",
        "00:10:DB": "Juniper",
        "00:12:1E": "Juniper",
        "00:14:F6": "Juniper",
        "00:17:CB": "Juniper",
        "00:19:E2": "Juniper",
        "00:1D:B5": "Juniper",
        
        # Dell/EMC
        "00:06:5B": "Dell",
        "00:08:74": "Dell",
        "00:0B:DB": "Dell",
        "00:0D:56": "Dell",
        "00:0F:1F": "Dell",
        "00:11:43": "Dell",
        "00:12:3F": "Dell",
        
        # ZTE
        "00:15:EB": "ZTE",
        "00:19:C6": "ZTE",
        "00:1E:73": "ZTE",
        "00:22:93": "ZTE",
        "00:25:12": "ZTE",
        "00:26:ED": "ZTE",
    }
    
    def __init__(self, custom_db_path: Optional[str] = None):
        """
        Initialize OUI lookup with built-in and optional custom database.
        
        Args:
            custom_db_path: Path to custom OUI JSON database file
        """
        self._db: Dict[str, str] = self.BUILTIN_OUI_DB.copy()
        
        # Load custom database if provided
        if custom_db_path and os.path.exists(custom_db_path):
            self._load_custom_db(custom_db_path)
    
    def _load_custom_db(self, path: str):
        """Load additional OUI entries from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                custom_entries = json.load(f)
                self._db.update(custom_entries)
                print(f"[OUI] Loaded {len(custom_entries)} custom entries")
        except Exception as e:
            print(f"[OUI] Failed to load custom database: {e}")
    
    def _normalize_mac(self, mac: str) -> str:
        """
        Normalize MAC address to XX:XX:XX format (first 3 bytes).
        
        Handles formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXXXXXXXXXX
        """
        # Remove common separators and convert to uppercase
        mac_clean = mac.upper().replace(':', '').replace('-', '').replace('.', '')
        
        # Take first 6 characters (3 bytes) and format
        if len(mac_clean) >= 6:
            prefix = mac_clean[:6]
            return f"{prefix[0:2]}:{prefix[2:4]}:{prefix[4:6]}"
        
        return ""
    
    def lookup(self, mac: str) -> Optional[str]:
        """
        Look up vendor/manufacturer by MAC address.
        
        Args:
            mac: MAC address in any common format
            
        Returns:
            Vendor name if found, None otherwise
        """
        oui = self._normalize_mac(mac)
        return self._db.get(oui)
    
    def lookup_or_default(self, mac: str, default: str = "Unknown") -> str:
        """
        Look up vendor with fallback to default value.
        
        Args:
            mac: MAC address
            default: Default value if not found
            
        Returns:
            Vendor name or default
        """
        return self.lookup(mac) or default
    
    def add_entry(self, mac_prefix: str, vendor: str):
        """
        Add or update an OUI entry.
        
        Args:
            mac_prefix: First 3 bytes of MAC (e.g., "00:15:6D")
            vendor: Vendor name
        """
        normalized = self._normalize_mac(mac_prefix + ":00:00:00")
        self._db[normalized] = vendor
    
    @property
    def database_size(self) -> int:
        """Get number of entries in the OUI database."""
        return len(self._db)


# Global instance
_global_oui: Optional[OUILookup] = None


def get_oui_lookup() -> OUILookup:
    """Get global OUI lookup instance."""
    global _global_oui
    if _global_oui is None:
        _global_oui = OUILookup()
    return _global_oui
