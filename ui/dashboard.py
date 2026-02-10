"""
Dashboard UI Module - Polished Professional Edition
Modern CustomTkinter interface with proper theming, tabs, and help system.
"""

import webbrowser
import customtkinter as ctk
from typing import Optional, Dict
from PIL import Image
import os

# Project imports
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from i18n import I18n, get_i18n
from scanner.base import Device
from scanner.manager import ScannerManager
from utils.ping import PingUtil, PingResult
from utils.oui_lookup import OUILookup, get_oui_lookup
from ui.network_map import NetworkMapView

# Asset paths
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")


class HelpDialog(ctk.CTkToplevel):
    """Help/User Guide popup dialog."""
    
    def __init__(self, parent, i18n: I18n):
        super().__init__(parent)
        self.i18n = i18n
        
        self.title(self.i18n.t("help_title"))
        self.geometry("600x550")
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the help dialog UI."""
        # Main container with padding
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)
        
        # Title
        ctk.CTkLabel(
            container,
            text=self.i18n.t("help_title"),
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 20))
        
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Help sections
        sections = [
            ("help_discovery_title", "help_discovery_desc"),
            ("help_latency_title", "help_latency_desc"),
            ("help_oui_title", "help_oui_desc"),
            ("help_network_map_title", "help_network_map_desc"),
            ("help_manage_title", "help_manage_desc"),
        ]
        
        for title_key, desc_key in sections:
            self._add_section(scroll, title_key, desc_key)
        
        # Warning
        warning_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=8)
        warning_frame.pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            warning_frame,
            text=self.i18n.t("help_admin_warning"),
            font=ctk.CTkFont(size=13),
            text_color=("gray30", "#FFC107"),
            wraplength=500
        ).pack(padx=15, pady=12)
        
        # About section
        about_frame = ctk.CTkFrame(scroll, fg_color=("gray90", "gray17"), corner_radius=8)
        about_frame.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(
            about_frame,
            text=f"{self.i18n.t('about_title')} - {self.i18n.t('about_version')}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=15, pady=(12, 5), anchor="w")
        
        ctk.CTkLabel(
            about_frame,
            text=self.i18n.t("about_desc"),
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            wraplength=500
        ).pack(padx=15, pady=(0, 12), anchor="w")
        
        # Close button
        ctk.CTkButton(
            container,
            text=self.i18n.t("btn_close"),
            width=120,
            height=36,
            command=self.destroy
        ).pack(pady=(15, 0))
    
    def _add_section(self, parent, title_key: str, desc_key: str):
        """Add a help section."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            frame,
            text=self.i18n.t(title_key),
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            frame,
            text=self.i18n.t(desc_key),
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            wraplength=520,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))


class DeviceRow(ctk.CTkFrame):
    """A single device row in the table."""
    
    BRAND_COLORS = {
        "Ubiquiti": ("#0559C9", "#3399FF"),
        "Mikrotik": ("#D32F2F", "#FF5252"),
        "Mimosa": ("#E65100", "#FF9800"),
        "Mikrotik/Mimosa": ("#7B1FA2", "#BA68C8"),
        "Mikrotik/MNDP": ("#455A64", "#78909C"),
    }
    
    def __init__(self, parent, device: Device, i18n: I18n, row_index: int,
                 ping_util: PingUtil, oui_lookup: OUILookup):
        # Theme-aware alternating colors (light_color, dark_color)
        bg_colors = [("gray92", "#1a1a2e"), ("gray88", "#16213e")]
        bg = bg_colors[row_index % 2]
        super().__init__(parent, fg_color=bg, corner_radius=8)
        
        self.device = device
        self.i18n = i18n
        self.ping_util = ping_util
        self.oui_lookup = oui_lookup
        self.latency_label: Optional[ctk.CTkLabel] = None
        
        self._setup_ui()
        self._start_ping()
    
    def _setup_ui(self):
        """Setup row layout."""
        self.grid_columnconfigure(0, weight=1, minsize=130)
        self.grid_columnconfigure(1, weight=2, minsize=130)
        self.grid_columnconfigure(2, weight=2, minsize=155)
        self.grid_columnconfigure(3, weight=2, minsize=160)
        self.grid_columnconfigure(4, weight=1, minsize=90)
        self.grid_columnconfigure(5, weight=1, minsize=90)
        
        # Brand
        brand_text = self.device.brand or self.oui_lookup.lookup_or_default(self.device.mac, "Unknown")
        colors = self.BRAND_COLORS.get(self.device.brand, ("#388E3C", "#4CAF50"))
        
        ctk.CTkLabel(
            self, text=brand_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=colors
        ).grid(row=0, column=0, padx=12, pady=12, sticky="w")
        
        # IP - theme aware cyan
        ctk.CTkLabel(
            self, text=self.device.ip,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=("#0277BD", "#00D9FF")
        ).grid(row=0, column=1, padx=8, pady=12, sticky="w")
        
        # MAC
        ctk.CTkLabel(
            self, text=self.device.mac,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=("gray50", "gray60")
        ).grid(row=0, column=2, padx=8, pady=12, sticky="w")
        
        # Name
        ctk.CTkLabel(
            self, text=self.device.name,
            font=ctk.CTkFont(size=13),
            text_color=("gray20", "#E0E0E0")
        ).grid(row=0, column=3, padx=8, pady=12, sticky="w")
        
        # Latency
        self.latency_label = ctk.CTkLabel(
            self, text=self.i18n.t("latency_checking"),
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        self.latency_label.grid(row=0, column=4, padx=8, pady=12, sticky="w")
        
        # Manage button
        ctk.CTkButton(
            self, text=self.i18n.t("btn_manage"),
            width=75, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#2E7D32", "#0E7A0D"),
            hover_color=("#1B5E20", "#0A5A0A"),
            command=self._on_manage
        ).grid(row=0, column=5, padx=10, pady=8, sticky="e")
    
    def _start_ping(self):
        self.ping_util.ping_async(self.device.ip, self._on_ping_result)
    
    def _on_ping_result(self, result: PingResult):
        if self.latency_label and self.latency_label.winfo_exists():
            self.latency_label.after(0, lambda: self._update_latency(result))
    
    def _update_latency(self, result: PingResult):
        if self.latency_label and self.latency_label.winfo_exists():
            self.latency_label.configure(text=result.latency_display, text_color=result.status_color)
    
    def _on_manage(self):
        webbrowser.open(f"http://{self.device.ip}")
    
    def refresh_ping(self):
        if self.latency_label:
            self.latency_label.configure(text=self.i18n.t("latency_checking"), text_color=("gray50", "gray60"))
        self._start_ping()


class DeviceTable(ctk.CTkScrollableFrame):
    """Scrollable device table with header."""
    
    def __init__(self, parent, i18n: I18n, ping_util: PingUtil, oui_lookup: OUILookup):
        super().__init__(parent, fg_color="transparent", corner_radius=12)
        
        self.i18n = i18n
        self.ping_util = ping_util
        self.oui_lookup = oui_lookup
        self.device_rows: Dict[str, DeviceRow] = {}
        self._row_count = 0
        
        self._setup_header()
    
    def _setup_header(self):
        """Create table header."""
        self.header = ctk.CTkFrame(self, fg_color=("gray85", "#252545"), corner_radius=8)
        self.header.pack(fill="x", pady=(0, 8))
        
        for i in range(6):
            self.header.grid_columnconfigure(i, weight=1 if i in [1,2,3] else 0)
        
        headers = ["header_brand", "header_ip", "header_mac", "header_name", "header_latency", "header_action"]
        self.header_labels = []
        
        for col, key in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.header, text=self.i18n.t(key),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray40", "#9090B0")
            )
            lbl.grid(row=0, column=col, padx=12, pady=10, sticky="w")
            self.header_labels.append((lbl, key))
    
    def update_translations(self):
        for lbl, key in self.header_labels:
            lbl.configure(text=self.i18n.t(key))
    
    def add_device(self, device: Device):
        if device.unique_id in self.device_rows:
            return
        row = DeviceRow(self, device, self.i18n, self._row_count, self.ping_util, self.oui_lookup)
        row.pack(fill="x", pady=2)
        self.device_rows[device.unique_id] = row
        self._row_count += 1
    
    def clear(self):
        for row in self.device_rows.values():
            row.destroy()
        self.device_rows.clear()
        self._row_count = 0
    
    def ping_all(self):
        for row in self.device_rows.values():
            row.refresh_ping()
    
    def get_count(self) -> int:
        return len(self.device_rows)


class DashboardApp(ctk.CTk):
    """Main Dashboard - Polished Professional Edition."""
    
    def __init__(self, scanner_manager: ScannerManager, i18n: Optional[I18n] = None):
        super().__init__()
        
        self.scanner_manager = scanner_manager
        self.i18n = i18n or get_i18n()
        self.ping_util = PingUtil()
        self.oui_lookup = get_oui_lookup()
        self._is_scanning = False
        
        # Window config
        self.title(self.i18n.t("app_title"))
        self.geometry("1200x750")
        self.minsize(1000, 600)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.i18n.on_language_change(self._update_all_text)
        self.scanner_manager.set_on_device_discovered(self._on_device_discovered)
        
        self._setup_header()
        self._setup_tabview()
        self._setup_status_bar()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_header(self):
        """Build header with title and controls."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)
        
        # Left: Title block
        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=0, sticky="w")
        
        self.title_label = ctk.CTkLabel(
            title_block, text=self.i18n.t("app_title"),
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(
            title_block, text=self.i18n.t("app_subtitle"),
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        self.subtitle_label.pack(anchor="w")
        
        # Right: Controls
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=2, sticky="e")
        
        # Appearance dropdown
        app_frame = ctk.CTkFrame(controls, fg_color="transparent")
        app_frame.pack(side="left", padx=(0, 12))
        
        ctk.CTkLabel(app_frame, text=self.i18n.t("appearance"), 
                    font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).pack(side="left", padx=(0,5))
        
        self.appearance_var = ctk.StringVar(value="Dark")
        self.appearance_menu = ctk.CTkOptionMenu(
            app_frame, values=["Dark", "Light", "System"],
            variable=self.appearance_var, width=90, height=30,
            command=self._on_appearance_change
        )
        self.appearance_menu.pack(side="left")
        
        # Language dropdown
        lang_frame = ctk.CTkFrame(controls, fg_color="transparent")
        lang_frame.pack(side="left", padx=(0, 12))
        
        ctk.CTkLabel(lang_frame, text=self.i18n.t("language"),
                    font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).pack(side="left", padx=(0,5))
        
        self.lang_var = ctk.StringVar(value="TR" if self.i18n.current_language == "tr" else "EN")
        self.lang_menu = ctk.CTkOptionMenu(
            lang_frame, values=["TR", "EN"],
            variable=self.lang_var, width=70, height=30,
            command=self._on_language_select
        )
        self.lang_menu.pack(side="left")
        
        # Separator
        ctk.CTkFrame(controls, width=2, height=30, fg_color=("gray70", "gray30")).pack(side="left", padx=12)
        
        # Action buttons
        self.help_btn = ctk.CTkButton(
            controls, text="?", width=36, height=36,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=("gray75", "#3A3A5A"), hover_color=("gray65", "#4A4A6A"),
            command=self._show_help
        )
        self.help_btn.pack(side="left", padx=4)
        
        self.ping_btn = ctk.CTkButton(
            controls, text=self.i18n.t("btn_ping_all"),
            width=100, height=36,
            fg_color=("#1565C0", "#1565C0"), hover_color=("#0D47A1", "#0D47A1"),
            command=self._ping_all
        )
        self.ping_btn.pack(side="left", padx=4)
        
        self.clear_btn = ctk.CTkButton(
            controls, text=self.i18n.t("btn_clear"),
            width=90, height=36,
            fg_color=("gray70", "#4A4A6A"), hover_color=("gray60", "#5A5A7A"),
            command=self._on_clear
        )
        self.clear_btn.pack(side="left", padx=4)
        
        self.scan_btn = ctk.CTkButton(
            controls, text=self.i18n.t("btn_start"),
            width=150, height=36,
            fg_color=("#2E7D32", "#2E7D32"), hover_color=("#1B5E20", "#1B5E20"),
            command=self._toggle_scan
        )
        self.scan_btn.pack(side="left", padx=4)
    
    def _setup_tabview(self):
        """Setup modern tabview."""
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=25, pady=5)
        
        # Discovery tab
        self.tab_discovery = self.tabview.add(self.i18n.t("tab_discovery"))
        
        # Container for table and empty state
        self.discovery_container = ctk.CTkFrame(self.tab_discovery, fg_color="transparent")
        self.discovery_container.pack(fill="both", expand=True)
        
        self.device_table = DeviceTable(self.discovery_container, self.i18n, self.ping_util, self.oui_lookup)
        self.device_table.pack(fill="both", expand=True)
        
        # Empty state overlay
        self.empty_frame = ctk.CTkFrame(self.discovery_container, fg_color="transparent")
        self.empty_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        self.empty_label = ctk.CTkLabel(
            self.empty_frame, text=self.i18n.t("no_devices"),
            font=ctk.CTkFont(size=16),
            text_color=("gray50", "#505070"),
            justify="center"
        )
        self.empty_label.pack()
        
        # Network Map tab
        self.tab_map = self.tabview.add(self.i18n.t("tab_network_map"))
        self.network_map = NetworkMapView(self.tab_map, self.i18n)
        self.network_map.pack(fill="both", expand=True)
    
    def _setup_status_bar(self):
        """Setup bottom status bar."""
        status = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=("gray90", "#151525"))
        status.grid(row=2, column=0, sticky="ew")
        status.grid_columnconfigure(1, weight=1)
        
        self.status_dot = ctk.CTkLabel(
            status, text="●", font=ctk.CTkFont(size=14),
            text_color=("#B0B0B0", "#808080")
        )
        self.status_dot.grid(row=0, column=0, padx=(25, 5), pady=10)
        
        self.status_label = ctk.CTkLabel(
            status, text=self.i18n.t("status_idle"),
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "#909090")
        )
        self.status_label.grid(row=0, column=1, sticky="w", pady=10)
        
        self.ports_label = ctk.CTkLabel(
            status, text=self.i18n.t("scanning_ports"),
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "#606060")
        )
        self.ports_label.grid(row=0, column=2, padx=15, pady=10)
        
        self.count_label = ctk.CTkLabel(
            status, text=self.i18n.t("status_devices_found", count=0),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#0277BD", "#00D9FF")
        )
        self.count_label.grid(row=0, column=3, padx=25, pady=10)
    
    def _on_appearance_change(self, value: str):
        ctk.set_appearance_mode(value.lower())
    
    def _on_language_select(self, value: str):
        self.i18n.load(value.lower())
    
    def _update_all_text(self):
        """Update all UI text on language change."""
        self.title(self.i18n.t("app_title"))
        self.title_label.configure(text=self.i18n.t("app_title"))
        self.subtitle_label.configure(text=self.i18n.t("app_subtitle"))
        self.ping_btn.configure(text=self.i18n.t("btn_ping_all"))
        self.clear_btn.configure(text=self.i18n.t("btn_clear"))
        self.scan_btn.configure(text=self.i18n.t("btn_stop") if self._is_scanning else self.i18n.t("btn_start"))
        self.empty_label.configure(text=self.i18n.t("no_devices"))
        self.ports_label.configure(text=self.i18n.t("scanning_ports"))
        self.device_table.update_translations()
        self.network_map.update_translations()
        self._update_status()
        self._update_count()
    
    def _update_status(self):
        if self._is_scanning:
            self.status_label.configure(text=self.i18n.t("status_scanning"))
            self.status_dot.configure(text_color=("#4CAF50", "#4CAF50"))
        else:
            self.status_label.configure(text=self.i18n.t("status_idle"))
            self.status_dot.configure(text_color=("#B0B0B0", "#808080"))
    
    def _update_count(self):
        count = self.device_table.get_count()
        self.count_label.configure(text=self.i18n.t("status_devices_found", count=count))
    
    def _show_help(self):
        HelpDialog(self, self.i18n)
    
    def _on_device_discovered(self, device: Device):
        self.after(0, lambda: self._add_device(device))
    
    def _add_device(self, device: Device):
        if self.device_table.get_count() == 0:
            self.empty_frame.place_forget()
        self.device_table.add_device(device)
        self.network_map.add_device(device)
        self._update_count()
    
    def _ping_all(self):
        self.device_table.ping_all()
    
    def _on_clear(self):
        self.device_table.clear()
        self.network_map.clear()
        self.scanner_manager.clear_devices()
        self._update_count()
        self.empty_frame.place(relx=0.5, rely=0.5, anchor="center")
    
    def _start_scanning(self):
        self.scanner_manager.start()
        self._is_scanning = True
        self.scan_btn.configure(
            text=self.i18n.t("btn_stop"),
            fg_color=("#C62828", "#D32F2F"),
            hover_color=("#B71C1C", "#B71C1C")
        )
        self._update_status()
    
    def _stop_scanning(self):
        self.scanner_manager.stop()
        self._is_scanning = False
        self.scan_btn.configure(
            text=self.i18n.t("btn_start"),
            fg_color=("#2E7D32", "#2E7D32"),
            hover_color=("#1B5E20", "#1B5E20")
        )
        self._update_status()
    
    def _toggle_scan(self):
        if self._is_scanning:
            self._stop_scanning()
        else:
            self._start_scanning()
    
    def _on_close(self):
        self.scanner_manager.stop()
        self.ping_util.shutdown()
        self.destroy()
    
    def run(self):
        self.mainloop()
