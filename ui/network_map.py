"""
Network Map View Module - Theme-aware Edition
Visualizes discovered devices as nodes in a network topology map.
"""

import math
import tkinter as tk
import customtkinter as ctk
from typing import Dict, Optional
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.base import Device


@dataclass
class NodePosition:
    """Position of a node in the network map."""
    x: float
    y: float


class NetworkMapView(ctk.CTkFrame):
    """Network topology map with proper light/dark theme support."""
    
    BRAND_COLORS = {
        "Ubiquiti": "#0559C9",
        "Mikrotik": "#D32F2F",
        "Mimosa": "#FF9800",
        "Mikrotik/Mimosa": "#9C27B0",
        "Mikrotik/MNDP": "#607D8B",
        "Unknown": "#757575"
    }
    
    def __init__(self, parent, i18n, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.i18n = i18n
        self.devices: Dict[str, Device] = {}
        self.node_positions: Dict[str, NodePosition] = {}
        self.selected_node: Optional[str] = None
        
        self._setup_ui()
        
        # Listen for appearance changes
        self.bind("<Map>", lambda e: self.after(100, self._draw_map))
    
    def _get_colors(self):
        """Get theme-appropriate colors."""
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return {
                "bg": "#0f0f1a",
                "hub_fill": "#252545",
                "hub_outline": "#4a4a6a",
                "line": "#2a2a4a",
                "node_fill": "#1a1a2e",
                "text": "#A0A0A0",
                "ip_text": "#606080",
                "empty_text": "#404060"
            }
        else:
            return {
                "bg": "#f5f5f5",
                "hub_fill": "#e0e0e0",
                "hub_outline": "#9e9e9e",
                "line": "#bdbdbd",
                "node_fill": "#ffffff",
                "text": "#424242",
                "ip_text": "#757575",
                "empty_text": "#9e9e9e"
            }
    
    def _setup_ui(self):
        """Setup the network map UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        self.title_label = ctk.CTkLabel(
            header,
            text=self.i18n.t("network_map"),
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(side="left")
        
        # Legend
        legend = ctk.CTkFrame(header, fg_color=("gray90", "#151525"), corner_radius=8)
        legend.pack(side="right", padx=10)
        
        for brand, color in [("Ubiquiti", "#0559C9"), ("Mikrotik", "#D32F2F"), ("Mimosa", "#FF9800")]:
            item = ctk.CTkFrame(legend, fg_color="transparent")
            item.pack(side="left", padx=8, pady=5)
            ctk.CTkLabel(item, text="●", font=ctk.CTkFont(size=14), text_color=color).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(item, text=brand, font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).pack(side="left")
        
        # Canvas frame
        self.canvas_frame = ctk.CTkFrame(self, fg_color=("gray95", "#0f0f1a"), corner_radius=12)
        self.canvas_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        
        # Info panel
        self.info_panel = ctk.CTkFrame(self, fg_color=("gray90", "#1a1a2e"), corner_radius=10)
        self.info_panel.place_forget()
        
        self.info_title = ctk.CTkLabel(self.info_panel, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.info_title.pack(padx=15, pady=(10, 5), anchor="w")
        
        self.info_content = ctk.CTkLabel(self.info_panel, text="", font=ctk.CTkFont(size=12),
                                          text_color=("gray50", "gray60"), justify="left")
        self.info_content.pack(padx=15, pady=(0, 10), anchor="w")
        
        self._draw_empty_state()
    
    def _draw_empty_state(self):
        colors = self._get_colors()
        self.canvas.configure(bg=colors["bg"])
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 500
        self.canvas.create_text(w // 2, h // 2, text=self.i18n.t("no_devices"),
                                font=("Segoe UI", 16), fill=colors["empty_text"], justify="center")
    
    def _calculate_layout(self):
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 500
        center_x, center_y = w // 2, h // 2
        
        device_list = list(self.devices.values())
        n = len(device_list)
        if n == 0:
            return
        
        radius = max(100, min(min(w, h) * 0.38, 80 + n * 15))
        
        for i, device in enumerate(device_list):
            angle = (2 * math.pi * i / n) - (math.pi / 2)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self.node_positions[device.unique_id] = NodePosition(x, y)
    
    def _draw_map(self):
        colors = self._get_colors()
        self.canvas.configure(bg=colors["bg"])
        self.canvas.delete("all")
        
        if not self.devices:
            self._draw_empty_state()
            return
        
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 500
        cx, cy = w // 2, h // 2
        
        # Hub
        r = 35
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=colors["hub_fill"], 
                                outline=colors["hub_outline"], width=2)
        self.canvas.create_text(cx, cy, text="🌐", font=("Segoe UI Emoji", 20), fill="#00D9FF")
        
        # Nodes
        for did, pos in self.node_positions.items():
            device = self.devices.get(did)
            if not device:
                continue
            
            self.canvas.create_line(cx, cy, pos.x, pos.y, fill=colors["line"], width=2, dash=(4, 4))
            self._draw_node(device, pos, colors)
    
    def _draw_node(self, device: Device, pos: NodePosition, colors: dict):
        r = 28
        brand_color = self.BRAND_COLORS.get(device.brand, self.BRAND_COLORS["Unknown"])
        is_selected = device.unique_id == self.selected_node
        outline = "#FFFFFF" if is_selected else brand_color
        width = 3 if is_selected else 2
        
        self.canvas.create_oval(pos.x-r, pos.y-r, pos.x+r, pos.y+r,
                                fill=colors["node_fill"], outline=outline, width=width,
                                tags=f"node_{device.unique_id}")
        
        self.canvas.create_text(pos.x, pos.y, text=device.brand[0] if device.brand else "?",
                                font=("Segoe UI", 14, "bold"), fill=brand_color,
                                tags=f"node_{device.unique_id}")
        
        name = device.name[:15] + "..." if len(device.name) > 15 else device.name
        self.canvas.create_text(pos.x, pos.y + r + 15, text=name,
                                font=("Segoe UI", 10), fill=colors["text"])
        self.canvas.create_text(pos.x, pos.y + r + 30, text=device.ip,
                                font=("Consolas", 9), fill=colors["ip_text"])
    
    def _on_resize(self, event):
        self._calculate_layout()
        self._draw_map()
    
    def _on_click(self, event):
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            for tag in self.canvas.gettags(item):
                if tag.startswith("node_"):
                    self._select_node(tag[5:])
                    return
        self._deselect_node()
    
    def _select_node(self, device_id: str):
        self.selected_node = device_id
        self._draw_map()
        device = self.devices.get(device_id)
        if device:
            self.info_title.configure(text=device.name)
            info = f"Brand: {device.brand}\nIP: {device.ip}\nMAC: {device.mac}"
            if device.model:
                info += f"\nModel: {device.model}"
            self.info_content.configure(text=info)
            self.info_panel.place(relx=1.0, rely=0.0, anchor="ne", x=-30, y=60)
    
    def _deselect_node(self):
        self.selected_node = None
        self._draw_map()
        self.info_panel.place_forget()
    
    def add_device(self, device: Device):
        self.devices[device.unique_id] = device
        self._calculate_layout()
        self._draw_map()
    
    def clear(self):
        self.devices.clear()
        self.node_positions.clear()
        self.selected_node = None
        self.info_panel.place_forget()
        self._draw_empty_state()
    
    def refresh(self):
        self._calculate_layout()
        self._draw_map()
    
    def update_translations(self):
        self.title_label.configure(text=self.i18n.t("network_map"))
        if not self.devices:
            self._draw_empty_state()
