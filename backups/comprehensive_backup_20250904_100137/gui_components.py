#!/usr/bin/env python3
"""
GUI Components for Enhanced Trading Dashboard
Reusable styling and component classes
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

class ColorTheme:
    """Modern color theme for the trading dashboard"""
    
    def __init__(self):
        self.colors = {
            'bg_dark': '#1e1e1e',
            'bg_light': '#2d2d2d', 
            'accent': '#00d4aa',  # Teal accent
            'success': '#00ff88',  # Bright green
            'danger': '#ff4757',   # Red
            'warning': '#ffa502',  # Orange
            'info': '#3742fa',     # Blue
            'text': '#ffffff',     # White text
            'text_muted': '#a0a0a0'  # Gray text
        }
    
    def get_color(self, name):
        """Get color by name"""
        return self.colors.get(name, '#ffffff')

class StyledFrame:
    """Styled frame component with modern design"""
    
    def __init__(self, parent, theme, title="", emoji="", padx=20, pady=20):
        self.theme = theme
        
        # Main section container
        self.main_frame = tk.Frame(parent, bg=theme.get_color('bg_dark'))
        self.main_frame.pack(fill='x', pady=(0, 25))
        
        if title:
            # Section header with emoji and styling
            header_frame = tk.Frame(self.main_frame, bg=theme.get_color('bg_light'), height=50)
            header_frame.pack(fill='x', pady=(0, 10))
            header_frame.pack_propagate(False)
            
            title_text = f"{emoji} {title}" if emoji else title
            title_label = tk.Label(
                header_frame,
                text=title_text,
                font=('Arial', 16, 'bold'),
                fg=theme.get_color('accent'),
                bg=theme.get_color('bg_light')
            )
            title_label.pack(pady=12)
        
        # Content frame
        self.content_frame = tk.Frame(self.main_frame, bg=theme.get_color('bg_light'), padx=padx, pady=pady)
        self.content_frame.pack(fill='x')
    
    def get_content_frame(self):
        """Get the content frame for adding widgets"""
        return self.content_frame

class MetricRow:
    """Styled metric row with label and value"""
    
    def __init__(self, parent, theme, label, value, color=None, large=False):
        self.theme = theme
        
        row_frame = tk.Frame(parent, bg=theme.get_color('bg_light'))
        row_frame.pack(fill='x', pady=5)
        
        font_size = 12 if large else 11
        font_weight = 'bold' if large else 'normal'
        value_color = color if color else theme.get_color('text')
        
        tk.Label(row_frame, text=label, font=('Arial', font_size), 
                fg=theme.get_color('text_muted'), bg=theme.get_color('bg_light')).pack(side='left')
        tk.Label(row_frame, text=value, font=('Arial', font_size, font_weight), 
                fg=value_color, bg=theme.get_color('bg_light')).pack(side='right')

class PositionTable:
    """Styled table for displaying trading positions"""
    
    def __init__(self, parent, theme, positions_data):
        self.theme = theme
        
        # Create table header
        header_frame = tk.Frame(parent, bg=theme.get_color('bg_dark'), height=40)
        header_frame.pack(fill='x', pady=(0, 10))
        header_frame.pack_propagate(False)
        
        headers = ["Ticker", "Qty", "Entry Price", "Current Price", "P&L", "Sector"]
        header_widths = [100, 80, 120, 120, 100, 120]
        
        for i, (header, width) in enumerate(zip(headers, header_widths)):
            tk.Label(header_frame, text=header, font=('Arial', 11, 'bold'), 
                    fg=theme.get_color('accent'), bg=theme.get_color('bg_dark'), 
                    width=width//8).pack(side='left', padx=5)
        
        # Create position rows
        for pos in positions_data:
            self._create_position_row(parent, pos, header_widths)
    
    def _create_position_row(self, parent, pos, header_widths):
        """Create a single position row"""
        row_frame = tk.Frame(parent, bg=self.theme.get_color('bg_light'), height=35)
        row_frame.pack(fill='x', pady=2)
        row_frame.pack_propagate(False)
        
        pnl = (pos['current'] - pos['entry']) * pos['qty']
        pnl_color = self.theme.get_color('success') if pnl > 0 else self.theme.get_color('danger')
        
        values = [
            pos['ticker'],
            str(pos['qty']),
            f"${pos['entry']:.2f}",
            f"${pos['current']:.2f}",
            f"${pnl:.2f}",
            pos['sector']
        ]
        
        for i, (value, width) in enumerate(zip(values, header_widths)):
            color = pnl_color if i == 4 else self.theme.get_color('text')  # Color P&L column
            tk.Label(row_frame, text=value, font=('Arial', 10), 
                    fg=color, bg=self.theme.get_color('bg_light'), 
                    width=width//8).pack(side='left', padx=5)

class StatusIndicator:
    """Colored status indicator with icon"""
    
    def __init__(self, parent, theme, status_type, text):
        self.theme = theme
        
        # Status mapping
        status_config = {
            'success': {'color': theme.get_color('success'), 'icon': '✅'},
            'warning': {'color': theme.get_color('warning'), 'icon': '⚠️'},
            'danger': {'color': theme.get_color('danger'), 'icon': '❌'},
            'info': {'color': theme.get_color('info'), 'icon': 'ℹ️'}
        }
        
        config = status_config.get(status_type, status_config['info'])
        
        status_frame = tk.Frame(parent, bg=theme.get_color('bg_light'))
        status_frame.pack(fill='x', pady=5)
        
        # Icon
        tk.Label(status_frame, text=config['icon'], font=('Arial', 12), 
                fg=config['color'], bg=theme.get_color('bg_light')).pack(side='left', padx=(0, 10))
        
        # Text
        tk.Label(status_frame, text=text, font=('Arial', 11), 
                fg=config['color'], bg=theme.get_color('bg_light')).pack(side='left')

class LiveClock:
    """Live updating clock widget"""
    
    def __init__(self, parent, theme):
        self.theme = theme
        self.parent = parent
        
        self.clock_label = tk.Label(parent, font=('Arial', 12), 
                                   fg=theme.get_color('text_muted'), 
                                   bg=theme.get_color('bg_dark'))
        self.clock_label.pack(side='right', padx=10)
        
        self.update_clock()
    
    def update_clock(self):
        """Update the clock display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=f"🕐 {current_time}")
        
        # Schedule next update
        self.parent.after(1000, self.update_clock)

class BulletList:
    """Styled bullet list component"""
    
    def __init__(self, parent, theme, items, bullet_color=None):
        self.theme = theme
        bullet_color = bullet_color or theme.get_color('warning')
        
        for item in items:
            bullet_frame = tk.Frame(parent, bg=theme.get_color('bg_light'))
            bullet_frame.pack(fill='x', pady=3)
            
            tk.Label(bullet_frame, text="•", font=('Arial', 14), 
                    fg=bullet_color, bg=theme.get_color('bg_light')).pack(side='left')
            tk.Label(bullet_frame, text=item, font=('Arial', 11), 
                    fg=theme.get_color('text'), bg=theme.get_color('bg_light'), 
                    wraplength=700).pack(side='left', padx=(10, 0))

class ProgressBar:
    """Custom styled progress bar"""
    
    def __init__(self, parent, theme, value, max_value=100, color=None, label=""):
        self.theme = theme
        
        # Container frame
        container = tk.Frame(parent, bg=theme.get_color('bg_light'))
        container.pack(fill='x', pady=5)
        
        # Label
        if label:
            tk.Label(container, text=label, font=('Arial', 10), 
                    fg=theme.get_color('text_muted'), 
                    bg=theme.get_color('bg_light')).pack(anchor='w')
        
        # Progress bar background
        bar_bg = tk.Frame(container, bg=theme.get_color('bg_dark'), height=20)
        bar_bg.pack(fill='x', pady=2)
        
        # Progress bar fill
        fill_width = int((value / max_value) * 300)  # 300px max width
        fill_color = color or theme.get_color('accent')
        
        bar_fill = tk.Frame(bar_bg, bg=fill_color, height=20, width=fill_width)
        bar_fill.pack(side='left')
        
        # Percentage text
        percentage = (value / max_value) * 100
        tk.Label(container, text=f"{percentage:.1f}%", font=('Arial', 10), 
                fg=theme.get_color('text'), bg=theme.get_color('bg_light')).pack(anchor='e')

def format_currency(amount):
    """Format currency with proper commas and signs"""
    if amount >= 0:
        return f"+${amount:,.2f}"
    else:
        return f"-${abs(amount):,.2f}"

def format_percentage(value, show_sign=True):
    """Format percentage with proper sign"""
    if show_sign and value >= 0:
        return f"+{value:.1f}%"
    else:
        return f"{value:.1f}%"

def get_performance_color(theme, value, threshold_good=0, threshold_bad=None):
    """Get color based on performance value"""
    if threshold_bad is not None and value <= threshold_bad:
        return theme.get_color('danger')
    elif value >= threshold_good:
        return theme.get_color('success')
    else:
        return theme.get_color('warning')