"""
Ping/Latency Measurement Utility
Measures network latency to discovered devices.
"""

import subprocess
import threading
import time
import re
import platform
from typing import Optional, Callable, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future


@dataclass
class PingResult:
    """Result of a ping operation."""
    host: str
    latency_ms: Optional[float]  # None if unreachable
    is_reachable: bool
    packet_loss: float  # Percentage
    error: Optional[str] = None
    
    @property
    def latency_display(self) -> str:
        """Get formatted latency string for display."""
        if not self.is_reachable:
            return "Offline"
        if self.latency_ms is None:
            return "N/A"
        if self.latency_ms < 1:
            return "<1 ms"
        return f"{self.latency_ms:.1f} ms"
    
    @property
    def status_color(self) -> str:
        """Get color code based on latency."""
        if not self.is_reachable:
            return "#FF5252"  # Red
        if self.latency_ms is None:
            return "#808080"  # Gray
        if self.latency_ms < 10:
            return "#4CAF50"  # Green - Excellent
        if self.latency_ms < 50:
            return "#8BC34A"  # Light Green - Good
        if self.latency_ms < 100:
            return "#FFC107"  # Yellow - Fair
        if self.latency_ms < 200:
            return "#FF9800"  # Orange - Poor
        return "#FF5252"  # Red - Bad


class PingUtil:
    """
    Asynchronous ping utility for measuring device latency.
    
    Runs ping operations in background threads to avoid blocking the UI.
    """
    
    def __init__(self, max_workers: int = 10, timeout: int = 2, count: int = 2):
        """
        Initialize ping utility.
        
        Args:
            max_workers: Maximum concurrent ping operations
            timeout: Ping timeout in seconds
            count: Number of ping packets to send
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Ping")
        self._timeout = timeout
        self._count = count
        self._is_windows = platform.system().lower() == "windows"
        self._cache: Dict[str, PingResult] = {}
        self._cache_ttl = 30  # Seconds
        self._cache_timestamps: Dict[str, float] = {}
    
    def _build_command(self, host: str) -> list:
        """Build platform-specific ping command."""
        if self._is_windows:
            # Windows: ping -n count -w timeout_ms host
            return ["ping", "-n", str(self._count), "-w", str(self._timeout * 1000), host]
        else:
            # Linux/Mac: ping -c count -W timeout host
            return ["ping", "-c", str(self._count), "-W", str(self._timeout), host]
    
    def _parse_output(self, host: str, output: str, return_code: int) -> PingResult:
        """Parse ping command output to extract latency."""
        latency = None
        packet_loss = 100.0
        is_reachable = return_code == 0
        
        try:
            # Extract average latency
            if self._is_windows:
                # Windows format: "Average = XXms" or "Ortalama = XXms" (Turkish)
                match = re.search(r'(?:Average|Ortalama|Moyenne)\s*=\s*(\d+)ms', output, re.IGNORECASE)
                if match:
                    latency = float(match.group(1))
                
                # Packet loss: "Lost = X (Y% loss)"
                loss_match = re.search(r'\((\d+)%\s*(?:loss|kayıp|perte)', output, re.IGNORECASE)
                if loss_match:
                    packet_loss = float(loss_match.group(1))
            else:
                # Linux/Mac format: "min/avg/max/mdev = X/Y/Z/W ms"
                match = re.search(r'=\s*[\d.]+/([\d.]+)/', output)
                if match:
                    latency = float(match.group(1))
                
                # Packet loss: "X% packet loss"
                loss_match = re.search(r'(\d+)%\s*packet\s*loss', output, re.IGNORECASE)
                if loss_match:
                    packet_loss = float(loss_match.group(1))
            
            # Determine reachability
            is_reachable = packet_loss < 100 and (latency is not None or return_code == 0)
            
        except Exception as e:
            pass
        
        return PingResult(
            host=host,
            latency_ms=latency,
            is_reachable=is_reachable,
            packet_loss=packet_loss
        )
    
    def _ping_sync(self, host: str) -> PingResult:
        """
        Perform synchronous ping operation.
        
        Args:
            host: IP address or hostname
            
        Returns:
            PingResult with latency information
        """
        try:
            cmd = self._build_command(host)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout * self._count + 5,
                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0
            )
            
            return self._parse_output(host, result.stdout + result.stderr, result.returncode)
            
        except subprocess.TimeoutExpired:
            return PingResult(
                host=host,
                latency_ms=None,
                is_reachable=False,
                packet_loss=100.0,
                error="Timeout"
            )
        except Exception as e:
            return PingResult(
                host=host,
                latency_ms=None,
                is_reachable=False,
                packet_loss=100.0,
                error=str(e)
            )
    
    def ping_async(self, host: str, callback: Callable[[PingResult], None]) -> Future:
        """
        Perform asynchronous ping operation.
        
        Args:
            host: IP address or hostname
            callback: Function to call with result
            
        Returns:
            Future object for the operation
        """
        def task():
            result = self._ping_sync(host)
            # Update cache
            self._cache[host] = result
            self._cache_timestamps[host] = time.time()
            callback(result)
            return result
        
        return self._executor.submit(task)
    
    def ping(self, host: str, use_cache: bool = True) -> PingResult:
        """
        Perform ping with optional caching.
        
        Args:
            host: IP address or hostname
            use_cache: Whether to use cached results
            
        Returns:
            PingResult
        """
        # Check cache
        if use_cache and host in self._cache:
            cache_age = time.time() - self._cache_timestamps.get(host, 0)
            if cache_age < self._cache_ttl:
                return self._cache[host]
        
        result = self._ping_sync(host)
        
        # Update cache
        self._cache[host] = result
        self._cache_timestamps[host] = time.time()
        
        return result
    
    def get_cached(self, host: str) -> Optional[PingResult]:
        """Get cached ping result if available."""
        return self._cache.get(host)
    
    def clear_cache(self):
        """Clear the ping result cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)


# Global instance
_global_ping: Optional[PingUtil] = None


def get_ping_util() -> PingUtil:
    """Get global ping utility instance."""
    global _global_ping
    if _global_ping is None:
        _global_ping = PingUtil()
    return _global_ping


def ping_host(host: str) -> PingResult:
    """Convenience function to ping a host."""
    return get_ping_util().ping(host)
