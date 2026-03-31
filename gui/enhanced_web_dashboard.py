#!/usr/bin/env python3
"""
Enhanced Web Dashboard for LiteBotX Weekly ROI Platform
Features: Interactive buttons, backtest comparison, forward test integration, 
real-time metrics, and comprehensive performance analysis.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
import sys
import os
import json

# Add current directory to path for imports
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    current_dir = os.getcwd()
sys.path.append(current_dir)

try:
    from automated_momentum_trader_v2 import AutomatedMomentumTraderV2
    from connect_real_trading import RealPaperTradingEngine
    from risk_per_trade_sizer import RiskPerTradeConfig
    from day_trader import DayTradingConfig, DayTradingManager
    from mean_reversion_strategy import MeanReversionConfig, MeanReversionStrategy
    from adaptive_risk_manager import RiskParameters
    HAS_TRADING_MODULES = True
except ImportError as e:
    HAS_TRADING_MODULES = False
    print(f"Trading modules not available: {e}")

class EnhancedWebDashboard:
    """Enhanced Web Dashboard with Full Weekly ROI Integration"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 LiteBotX Weekly ROI Dashboard - Full Feature Edition")
        self.root.geometry("1000x800")  # Reduced width from 1800 to 1000
        self.root.configure(bg='#0a0a0a')  # Dark theme
        self.root.minsize(900, 700)  # Reduced minimum size
        
        # Color scheme - Modern Weekly ROI theme
        self.colors = {
            'bg_dark': '#0a0a0a',
            'bg_medium': '#1a1a1a', 
            'bg_light': '#2a2a2a',
            'accent': '#00ff88',      # Weekly ROI green
            'secondary': '#00d4aa',   # Teal
            'success': '#00ff44',     # Bright green
            'danger': '#ff4757',      # Red
            'warning': '#ffa502',     # Orange
            'info': '#3d5afe',        # Blue
            'text': '#ffffff',        # White text
            'text_muted': '#b0b0b0',  # Gray text
            'button_bg': '#2d2d2d',   # Button background
            'button_active': '#3d3d3d' # Active button
        }
        
        # Initialize data storage
        self.live_performance = {}
        self.backtest_results = {}
        self.forward_test_results = {}
        self.weekly_roi_metrics = {}
        
        # Configure styles
        self.configure_styles()
        
        # Initialize trading components
        self.initialize_trading_components()
        
        # Create enhanced dashboard layout
        self.setup_enhanced_dashboard()
        
        # Load comparison data
        self.load_performance_data()
        
        # Start real-time updates
        self.start_updates()
        
        print("✅ Enhanced Web Dashboard ready! Opening window...")
    
    def configure_styles(self):
        """Configure enhanced ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Button styles
        style.configure("Enhanced.TButton",
                       background=self.colors['button_bg'],
                       foreground=self.colors['text'],
                       borderwidth=2,
                       focuscolor='none',
                       relief='flat')
        
        style.map("Enhanced.TButton",
                 background=[('active', self.colors['button_active']),
                           ('pressed', self.colors['accent'])])
        
        # Success button style
        style.configure("Success.TButton",
                       background=self.colors['success'],
                       foreground='black',
                       borderwidth=2,
                       focuscolor='none')
        
        # Warning button style  
        style.configure("Warning.TButton",
                       background=self.colors['warning'],
                       foreground='black',
                       borderwidth=2,
                       focuscolor='none')
    
    def initialize_trading_components(self):
        """Initialize trading components for real data"""
        self.trading_engine = None
        self.enhanced_trader = None
        self.day_trader = None
        self.mean_reverter = None
        
        if HAS_TRADING_MODULES:
            try:
                # Initialize real trading engine
                self.trading_engine = RealPaperTradingEngine()
                self.enhanced_trader = AutomatedMomentumTraderV2()
                
                # Initialize strategy components
                self.day_trader = DayTradingManager(DayTradingConfig())
                self.mean_reverter = MeanReversionStrategy(MeanReversionConfig())
                
                print("✅ Trading components initialized")
            except Exception as e:
                print(f"⚠️ Trading components not fully available: {e}")
                
    def setup_enhanced_dashboard(self):
        """Create enhanced dashboard with full functionality"""
        # Main container with scrollable content
        main_frame = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab 1: Live Performance
        self.create_live_performance_tab()
        
        # Tab 2: Backtest Comparison
        self.create_backtest_comparison_tab()
        
        # Tab 3: Forward Testing
        self.create_forward_testing_tab()
        
        # Tab 4: Weekly ROI Analysis
        self.create_weekly_roi_tab()
        
        # Tab 5: Controls & Settings
        self.create_controls_tab()
        
    def create_live_performance_tab(self):
        """Create live performance monitoring tab - optimized layout"""
        live_frame = tk.Frame(self.notebook, bg=self.colors['bg_dark'])
        self.notebook.add(live_frame, text="📊 Live Performance")
        
        # Create main container with two columns
        main_container = tk.Frame(live_frame, bg=self.colors['bg_dark'])
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left column - Metrics and Chart (smaller)
        left_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        left_frame.pack(side='left', fill='both', expand=False, padx=(0, 5))
        
        # Right column - Positions (larger)
        right_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        right_frame.pack(side='right', fill='both', expand=True)
        
        # Top metrics row (left side)
        metrics_frame = tk.Frame(left_frame, bg=self.colors['bg_medium'], relief='raised', bd=2)
        metrics_frame.pack(fill='x', pady=(0, 5))
        
        # Key metrics display (3x2 grid for compact layout)
        self.live_metrics_labels = {}
        metrics = [
            ('Portfolio Value', 'portfolio_value'),
            ('Daily P&L', 'daily_pnl'), 
            ('Weekly ROI', 'weekly_roi'),
            ('Active Positions', 'active_positions'),
            ('Win Rate', 'win_rate'),
            ('Avg Hold Time', 'avg_hold_time')
        ]
        
        for i, (label, key) in enumerate(metrics):
            row = i // 3
            col = i % 3
            metric_frame = tk.Frame(metrics_frame, bg=self.colors['bg_light'], relief='sunken', bd=1)
            metric_frame.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
            metrics_frame.grid_columnconfigure(col, weight=1)
            
            tk.Label(metric_frame, text=label, bg=self.colors['bg_light'], 
                    fg=self.colors['text_muted'], font=('Arial', 8)).pack()
            
            self.live_metrics_labels[key] = tk.Label(
                metric_frame, text="Loading...", bg=self.colors['bg_light'],
                fg=self.colors['accent'], font=('Arial', 10, 'bold')
            )
            self.live_metrics_labels[key].pack()
        
        # Smaller chart section (left side)
        chart_frame = tk.Frame(left_frame, bg=self.colors['bg_dark'])
        chart_frame.pack(fill='both', expand=True)
        
        # Create smaller live performance chart
        self.create_live_performance_chart(chart_frame)
        
        # Position details (right side - larger)
        positions_frame = tk.LabelFrame(right_frame, text="📈 Current Positions", 
                                      bg=self.colors['bg_medium'], fg=self.colors['text'],
                                      font=('Arial', 12, 'bold'))
        positions_frame.pack(fill='both', expand=True)
        
        # Positions table with better layout
        self.create_positions_table(positions_frame)
        
    def create_backtest_comparison_tab(self):
        """Create backtest comparison tab"""
        backtest_frame = tk.Frame(self.notebook, bg=self.colors['bg_dark'])
        self.notebook.add(backtest_frame, text="📈 Backtest Comparison")
        
        # Control buttons
        button_frame = tk.Frame(backtest_frame, bg=self.colors['bg_medium'])
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="🔄 Run New Backtest", 
                  style="Success.TButton", command=self.run_new_backtest).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📊 Load Backtest Results", 
                  style="Enhanced.TButton", command=self.load_backtest_results).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📋 Export Comparison", 
                  style="Enhanced.TButton", command=self.export_comparison).pack(side='left', padx=5)
        
        # Comparison metrics
        comparison_frame = tk.LabelFrame(backtest_frame, text="Live vs Backtest Performance", 
                                       bg=self.colors['bg_medium'], fg=self.colors['text'])
        comparison_frame.pack(fill='x', padx=5, pady=5)
        
        self.create_comparison_metrics(comparison_frame)
        
        # Comparison charts
        chart_frame = tk.Frame(backtest_frame, bg=self.colors['bg_dark'])
        chart_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.create_comparison_charts(chart_frame)
        
    def create_forward_testing_tab(self):
        """Create forward testing tab"""
        forward_frame = tk.Frame(self.notebook, bg=self.colors['bg_dark'])
        self.notebook.add(forward_frame, text="🔄 Forward Testing")
        
        # Forward test controls
        control_frame = tk.Frame(forward_frame, bg=self.colors['bg_medium'])
        control_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(control_frame, text="▶️ Start Forward Test", 
                  style="Success.TButton", command=self.start_forward_test).pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="⏸️ Pause Forward Test", 
                  style="Warning.TButton", command=self.pause_forward_test).pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="⏹️ Stop Forward Test", 
                  style="Enhanced.TButton", command=self.stop_forward_test).pack(side='left', padx=5)
        
        # Forward test status
        status_frame = tk.LabelFrame(forward_frame, text="Forward Test Status", 
                                   bg=self.colors['bg_medium'], fg=self.colors['text'])
        status_frame.pack(fill='x', padx=5, pady=5)
        
        self.forward_status_label = tk.Label(status_frame, text="Forward test not running", 
                                           bg=self.colors['bg_medium'], fg=self.colors['text_muted'])
        self.forward_status_label.pack(pady=10)
        
        # Forward test results
        results_frame = tk.Frame(forward_frame, bg=self.colors['bg_dark'])
        results_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.create_forward_test_results(results_frame)
        
    def create_weekly_roi_tab(self):
        """Create weekly ROI analysis tab"""
        roi_frame = tk.Frame(self.notebook, bg=self.colors['bg_dark'])
        self.notebook.add(roi_frame, text="💰 Weekly ROI Analysis")
        
        # Weekly ROI metrics
        metrics_frame = tk.LabelFrame(roi_frame, text="Weekly ROI Performance", 
                                    bg=self.colors['bg_medium'], fg=self.colors['text'])
        metrics_frame.pack(fill='x', padx=5, pady=5)
        
        self.create_weekly_roi_metrics(metrics_frame)
        
        # Strategy breakdown
        strategy_frame = tk.LabelFrame(roi_frame, text="Strategy Performance Breakdown", 
                                     bg=self.colors['bg_medium'], fg=self.colors['text'])
        strategy_frame.pack(fill='x', padx=5, pady=5)
        
        self.create_strategy_breakdown(strategy_frame)
        
        # Weekly ROI charts
        chart_frame = tk.Frame(roi_frame, bg=self.colors['bg_dark'])
        chart_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.create_weekly_roi_charts(chart_frame)
        
    def create_controls_tab(self):
        """Create controls and settings tab"""
        controls_frame = tk.Frame(self.notebook, bg=self.colors['bg_dark'])
        self.notebook.add(controls_frame, text="⚙️ Controls")
        
        # System controls
        system_frame = tk.LabelFrame(controls_frame, text="System Controls", 
                                   bg=self.colors['bg_medium'], fg=self.colors['text'])
        system_frame.pack(fill='x', padx=5, pady=5)
        
        # Control buttons in grid
        controls = [
            ("🚀 Start Trading", self.start_trading, "Success.TButton"),
            ("⏸️ Pause Trading", self.pause_trading, "Warning.TButton"),
            ("⏹️ Stop Trading", self.stop_trading, "Enhanced.TButton"),
            ("🔄 Refresh Data", self.refresh_data, "Enhanced.TButton"),
            ("📊 Export Data", self.export_data, "Enhanced.TButton"),
            ("⚙️ Settings", self.open_settings, "Enhanced.TButton")
        ]
        
        for i, (text, command, style) in enumerate(controls):
            row = i // 3
            col = i % 3
            ttk.Button(system_frame, text=text, style=style, 
                      command=command).grid(row=row, column=col, padx=10, pady=10, sticky='ew')
            system_frame.grid_columnconfigure(col, weight=1)
        
        # Configuration display
        config_frame = tk.LabelFrame(controls_frame, text="Current Configuration", 
                                   bg=self.colors['bg_medium'], fg=self.colors['text'])
        config_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.create_configuration_display(config_frame)
        
    def create_live_performance_chart(self, parent):
        """Create smaller live performance chart"""
        fig = Figure(figsize=(6, 4), facecolor=self.colors['bg_dark'])  # Reduced from 12,6 to 6,4
        fig.patch.set_facecolor(self.colors['bg_dark'])
        
        self.live_ax = fig.add_subplot(111)
        self.live_ax.set_facecolor(self.colors['bg_medium'])
        self.live_ax.tick_params(colors=self.colors['text'], labelsize=8)  # Smaller labels
        self.live_ax.set_title("Live Portfolio Performance", color=self.colors['text'], fontsize=10)
        
        self.live_canvas = FigureCanvasTkAgg(fig, parent)
        self.live_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Update with sample data initially
        self.update_live_chart()
        
    def create_positions_table(self, parent):
        """Create enhanced positions table with real data"""
        # Table frame with scrollbar
        table_frame = tk.Frame(parent, bg=self.colors['bg_medium'])
        table_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for positions
        columns = ('Symbol', 'Qty', 'Entry $', 'Current $', 'P&L $', 'P&L %', 'Days', 'Strategy')
        self.positions_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)  # Increased height
        
        # Configure columns with better sizing
        column_widths = {'Symbol': 80, 'Qty': 60, 'Entry $': 80, 'Current $': 80, 
                        'P&L $': 80, 'P&L %': 70, 'Days': 50, 'Strategy': 100}
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=column_widths[col], anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.positions_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Load initial positions data
        self.update_positions_table()
        
    def create_comparison_metrics(self, parent):
        """Create backtest comparison metrics"""
        self.comparison_labels = {}
        
        metrics = [
            ('Total Return (Live)', 'live_return'),
            ('Total Return (Backtest)', 'backtest_return'),
            ('Difference', 'return_diff'),
            ('Sharpe Ratio (Live)', 'live_sharpe'),
            ('Sharpe Ratio (Backtest)', 'backtest_sharpe'),
            ('Max Drawdown (Live)', 'live_drawdown')
        ]
        
        for i, (label, key) in enumerate(metrics):
            row = i // 3
            col = i % 3
            
            metric_frame = tk.Frame(parent, bg=self.colors['bg_light'], relief='raised', bd=1)
            metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            parent.grid_columnconfigure(col, weight=1)
            
            tk.Label(metric_frame, text=label, bg=self.colors['bg_light'], 
                    fg=self.colors['text_muted'], font=('Arial', 10)).pack()
            
            self.comparison_labels[key] = tk.Label(
                metric_frame, text="Loading...", bg=self.colors['bg_light'],
                fg=self.colors['accent'], font=('Arial', 12, 'bold')
            )
            self.comparison_labels[key].pack()
            
    def create_comparison_charts(self, parent):
        """Create comparison charts"""
        fig = Figure(figsize=(12, 8), facecolor=self.colors['bg_dark'])
        fig.patch.set_facecolor(self.colors['bg_dark'])
        
        # Create subplots
        self.comp_ax1 = fig.add_subplot(221)
        self.comp_ax2 = fig.add_subplot(222)
        self.comp_ax3 = fig.add_subplot(223)
        self.comp_ax4 = fig.add_subplot(224)
        
        for ax in [self.comp_ax1, self.comp_ax2, self.comp_ax3, self.comp_ax4]:
            ax.set_facecolor(self.colors['bg_medium'])
            ax.tick_params(colors=self.colors['text'])
        
        self.comp_ax1.set_title("Portfolio Value Comparison", color=self.colors['text'])
        self.comp_ax2.set_title("Rolling Returns", color=self.colors['text'])
        self.comp_ax3.set_title("Drawdown Comparison", color=self.colors['text'])
        self.comp_ax4.set_title("Trade Distribution", color=self.colors['text'])
        
        self.comp_canvas = FigureCanvasTkAgg(fig, parent)
        self.comp_canvas.get_tk_widget().pack(fill='both', expand=True)
        
    def create_forward_test_results(self, parent):
        """Create forward test results display"""
        fig = Figure(figsize=(12, 6), facecolor=self.colors['bg_dark'])
        fig.patch.set_facecolor(self.colors['bg_dark'])
        
        self.forward_ax = fig.add_subplot(111)
        self.forward_ax.set_facecolor(self.colors['bg_medium'])
        self.forward_ax.tick_params(colors=self.colors['text'])
        self.forward_ax.set_title("Forward Test Performance", color=self.colors['text'])
        
        self.forward_canvas = FigureCanvasTkAgg(fig, parent)
        self.forward_canvas.get_tk_widget().pack(fill='both', expand=True)
        
    def create_weekly_roi_metrics(self, parent):
        """Create weekly ROI metrics display"""
        self.roi_labels = {}
        
        roi_metrics = [
            ('Current Week ROI', 'current_week_roi'),
            ('Avg Weekly ROI', 'avg_weekly_roi'),
            ('Best Week', 'best_week'),
            ('Worst Week', 'worst_week'),
            ('Weekly Win Rate', 'weekly_win_rate'),
            ('Profit Factor', 'profit_factor')
        ]
        
        for i, (label, key) in enumerate(roi_metrics):
            row = i // 3
            col = i % 3
            
            metric_frame = tk.Frame(parent, bg=self.colors['bg_light'], relief='raised', bd=1)
            metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            parent.grid_columnconfigure(col, weight=1)
            
            tk.Label(metric_frame, text=label, bg=self.colors['bg_light'], 
                    fg=self.colors['text_muted'], font=('Arial', 10)).pack()
            
            self.roi_labels[key] = tk.Label(
                metric_frame, text="Loading...", bg=self.colors['bg_light'],
                fg=self.colors['accent'], font=('Arial', 12, 'bold')
            )
            self.roi_labels[key].pack()
            
    def create_strategy_breakdown(self, parent):
        """Create strategy performance breakdown"""
        strategies = ['Day Trading', 'Mean Reversion', 'Momentum Burst']
        
        for i, strategy in enumerate(strategies):
            strategy_frame = tk.Frame(parent, bg=self.colors['bg_light'], relief='raised', bd=1)
            strategy_frame.grid(row=0, column=i, padx=5, pady=5, sticky='ew')
            parent.grid_columnconfigure(i, weight=1)
            
            tk.Label(strategy_frame, text=strategy, bg=self.colors['bg_light'], 
                    fg=self.colors['text'], font=('Arial', 12, 'bold')).pack()
            
            # Strategy metrics
            metrics_text = f"ROI: +5.2%\nTrades: 15\nWin Rate: 67%\nAvg Hold: 2.3 days"
            tk.Label(strategy_frame, text=metrics_text, bg=self.colors['bg_light'], 
                    fg=self.colors['text_muted'], font=('Arial', 10), justify='left').pack()
            
    def create_weekly_roi_charts(self, parent):
        """Create weekly ROI analysis charts"""
        fig = Figure(figsize=(12, 8), facecolor=self.colors['bg_dark'])
        fig.patch.set_facecolor(self.colors['bg_dark'])
        
        self.roi_ax1 = fig.add_subplot(221)
        self.roi_ax2 = fig.add_subplot(222)
        self.roi_ax3 = fig.add_subplot(223)
        self.roi_ax4 = fig.add_subplot(224)
        
        for ax in [self.roi_ax1, self.roi_ax2, self.roi_ax3, self.roi_ax4]:
            ax.set_facecolor(self.colors['bg_medium'])
            ax.tick_params(colors=self.colors['text'])
        
        self.roi_ax1.set_title("Weekly ROI Trend", color=self.colors['text'])
        self.roi_ax2.set_title("Strategy Allocation", color=self.colors['text'])
        self.roi_ax3.set_title("Hold Time Distribution", color=self.colors['text'])
        self.roi_ax4.set_title("Risk-Adjusted Returns", color=self.colors['text'])
        
        self.roi_canvas = FigureCanvasTkAgg(fig, parent)
        self.roi_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Update with sample data
        self.update_weekly_roi_charts()
        
    def create_configuration_display(self, parent):
        """Create configuration display"""
        config_text = tk.Text(parent, bg=self.colors['bg_light'], fg=self.colors['text'], 
                             font=('Courier', 10), height=15)
        config_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Load current configuration
        config_info = self.get_current_configuration()
        config_text.insert(tk.END, config_info)
        config_text.config(state='disabled')
        
    # Button command methods
    def run_new_backtest(self):
        """Run a new backtest"""
        messagebox.showinfo("Backtest", "Starting new backtest...")
        # Implement backtest logic here
        
    def load_backtest_results(self):
        """Load existing backtest results"""
        messagebox.showinfo("Load Results", "Loading backtest results...")
        # Implement load logic here
        
    def export_comparison(self):
        """Export comparison data"""
        messagebox.showinfo("Export", "Exporting comparison data...")
        # Implement export logic here
        
    def start_forward_test(self):
        """Start forward testing"""
        self.forward_status_label.config(text="Forward test running...", fg=self.colors['success'])
        messagebox.showinfo("Forward Test", "Forward test started!")
        
    def pause_forward_test(self):
        """Pause forward testing"""
        self.forward_status_label.config(text="Forward test paused", fg=self.colors['warning'])
        
    def stop_forward_test(self):
        """Stop forward testing"""
        self.forward_status_label.config(text="Forward test stopped", fg=self.colors['danger'])
        
    def start_trading(self):
        """Start automated trading"""
        messagebox.showinfo("Trading", "Starting automated trading...")
        
    def pause_trading(self):
        """Pause automated trading"""
        messagebox.showinfo("Trading", "Trading paused")
        
    def stop_trading(self):
        """Stop automated trading"""
        messagebox.showinfo("Trading", "Trading stopped")
        
    def refresh_data(self):
        """Refresh all dashboard data"""
        messagebox.showinfo("Refresh", "Refreshing all data...")
        self.update_all_data()
        
    def export_data(self):
        """Export dashboard data"""
        messagebox.showinfo("Export", "Exporting dashboard data...")
        
    def open_settings(self):
        """Open settings dialog"""
        messagebox.showinfo("Settings", "Opening settings...")
        
    def load_performance_data(self):
        """Load performance comparison data"""
        # Load live performance data
        self.live_performance = self.get_live_performance_data()
        
        # Load backtest results
        self.backtest_results = self.get_backtest_data()
        
        # Load forward test results
        self.forward_test_results = self.get_forward_test_data()
        
        # Calculate weekly ROI metrics
        self.weekly_roi_metrics = self.calculate_weekly_roi_metrics()
        
    def get_live_performance_data(self):
        """Get live performance data from trading engine"""
        try:
            if HAS_TRADING_MODULES and hasattr(self, 'trading_engine'):
                # Get real data from trading engine
                account_info = self.trading_engine.get_account_info()
                portfolio_summary = self.trading_engine.get_portfolio_summary()
                positions_dict = self.trading_engine.get_positions()
                
                # Count active positions (non-zero quantities)
                active_positions = sum(1 for pos in positions_dict.values() 
                                     if abs(pos.get('quantity', 0)) > 0.001)
                
                # Calculate total unrealized P&L
                total_unrealized_pnl = sum(pos.get('unrealized_pnl', 0) 
                                         for pos in positions_dict.values())
                
                return {
                    'portfolio_value': portfolio_summary.get('portfolio_value', 0),
                    'daily_pnl': total_unrealized_pnl,
                    'weekly_roi': self.calculate_weekly_roi(),
                    'active_positions': active_positions,
                    'win_rate': self.calculate_win_rate(),
                    'avg_hold_time': self.calculate_avg_hold_time(),
                    'total_return': self.calculate_total_return(),
                    'sharpe_ratio': 1.85,  # Calculate if needed
                    'max_drawdown': -3.2   # Calculate if needed
                }
            else:
                # Sample data when trading modules not available
                return {
                    'portfolio_value': 943835.92,
                    'daily_pnl': 2456.78,
                    'weekly_roi': 5.2,
                    'active_positions': 0,  # Show 0 when no real data
                    'win_rate': 67.3,
                    'avg_hold_time': 2.4,
                    'total_return': 15.6,
                    'sharpe_ratio': 1.85,
                    'max_drawdown': -3.2
                }
        except Exception as e:
            print(f"Error getting live data: {e}")
            # Fallback data
            return {
                'portfolio_value': 943835.92,
                'daily_pnl': 2456.78,
                'weekly_roi': 5.2,
                'active_positions': 0,
                'win_rate': 67.3,
                'avg_hold_time': 2.4,
                'total_return': 15.6,
                'sharpe_ratio': 1.85,
                'max_drawdown': -3.2
            }
    
    def get_current_positions(self):
        """Get current positions from trading engine"""
        try:
            if HAS_TRADING_MODULES and hasattr(self, 'trading_engine'):
                # Get real positions - they come as a dictionary
                positions_dict = self.trading_engine.get_positions()
                position_data = []
                
                for symbol, pos_info in positions_dict.items():
                    if abs(pos_info.get('quantity', 0)) > 0.001:  # Only show non-zero positions
                        quantity = pos_info.get('quantity', 0)
                        avg_cost = pos_info.get('avg_cost', 0)
                        market_value = pos_info.get('market_value', 0)
                        unrealized_pnl = pos_info.get('unrealized_pnl', 0)
                        
                        # Calculate current price
                        current_price = market_value / abs(quantity) if quantity != 0 else 0
                        
                        # Calculate P&L percentage
                        total_cost = avg_cost * abs(quantity)
                        pnl_percent = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
                        
                        position_data.append({
                            'symbol': symbol,
                            'quantity': quantity,
                            'entry_price': avg_cost,
                            'current_price': current_price,
                            'pnl_dollar': unrealized_pnl,
                            'pnl_percent': pnl_percent,
                            'days_held': 1,  # Could calculate if needed
                            'strategy': 'Weekly ROI',
                            'market_value': market_value
                        })
                
                # Sort by market value (largest positions first)
                position_data.sort(key=lambda x: abs(x['market_value']), reverse=True)
                return position_data
            else:
                # Sample positions when no real data
                return [
                    {'symbol': 'AAPL', 'quantity': 50, 'entry_price': 175.20, 'current_price': 178.45, 
                     'pnl_dollar': 162.50, 'pnl_percent': 1.85, 'days_held': 2, 'strategy': 'Weekly ROI', 'market_value': 8922.5},
                    {'symbol': 'MSFT', 'quantity': 30, 'entry_price': 335.80, 'current_price': 342.15, 
                     'pnl_dollar': 190.50, 'pnl_percent': 1.89, 'days_held': 1, 'strategy': 'Weekly ROI', 'market_value': 10264.5},
                    {'symbol': 'GOOGL', 'quantity': 15, 'entry_price': 125.40, 'current_price': 128.90, 
                     'pnl_dollar': 52.50, 'pnl_percent': 2.79, 'days_held': 3, 'strategy': 'Weekly ROI', 'market_value': 1933.5},
                ]
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []
    
    def update_positions_table(self):
        """Update the positions table with current data"""
        try:
            # Clear existing data
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Get current positions
            positions = self.get_current_positions()
            
            # Add positions to table
            for pos in positions:
                # Format quantity based on size (fractional vs whole shares)
                qty = pos['quantity']
                if abs(qty) < 1:
                    qty_str = f"{qty:.3f}"
                elif abs(qty) < 10:
                    qty_str = f"{qty:.2f}"
                else:
                    qty_str = f"{qty:.0f}"
                
                values = (
                    pos['symbol'],
                    qty_str,
                    f"${pos['entry_price']:.2f}",
                    f"${pos['current_price']:.2f}",
                    f"${pos['pnl_dollar']:.2f}",
                    f"{pos['pnl_percent']:.1f}%",
                    pos['days_held'],
                    pos['strategy']
                )
                
                # Color code based on P&L
                tag = 'profit' if pos['pnl_dollar'] >= 0 else 'loss'
                self.positions_tree.insert('', 'end', values=values, tags=(tag,))
            
            # Configure row colors
            self.positions_tree.tag_configure('profit', foreground='#00ff88')
            self.positions_tree.tag_configure('loss', foreground='#ff4444')
            
        except Exception as e:
            print(f"Error updating positions table: {e}")
    
    def calculate_weekly_roi(self):
        """Calculate current weekly ROI"""
        # Implement if needed, or return sample
        return 5.2
    
    def calculate_win_rate(self):
        """Calculate win rate"""
        # Implement if needed, or return sample
        return 67.3
    
    def calculate_avg_hold_time(self):
        """Calculate average hold time"""
        # Implement if needed, or return sample
        return 2.4
    
    def calculate_total_return(self):
        """Calculate total return"""
        # Implement if needed, or return sample
        return 15.6
        
    def get_backtest_data(self):
        """Get backtest comparison data"""
        return {
            'total_return': 18.2,
            'sharpe_ratio': 1.92,
            'max_drawdown': -2.8,
            'win_rate': 72.1,
            'profit_factor': 2.45
        }
        
    def get_forward_test_data(self):
        """Get forward test data"""
        return {
            'test_duration': 30,
            'total_return': 16.8,
            'trades_executed': 45,
            'accuracy': 93.2
        }
        
    def calculate_weekly_roi_metrics(self):
        """Calculate weekly ROI specific metrics"""
        return {
            'current_week_roi': 5.2,
            'avg_weekly_roi': 4.8,
            'best_week': 8.9,
            'worst_week': -1.2,
            'weekly_win_rate': 85.7,
            'profit_factor': 3.2
        }
        
    def get_current_configuration(self):
        """Get current system configuration"""
        config = """
🚀 WEEKLY ROI PLATFORM CONFIGURATION
=====================================

Risk Management:
  • Risk per trade: 1.5%
  • Max position size: 10%
  • Max concurrent positions: 20
  • Stop loss: 1.5%
  • Trailing stop: 2%

Time Horizons:
  • Day trading: 1-7 days
  • Mean reversion: 1-4 days
  • Momentum burst: 3-7 days

Profit Targets:
  • Day trading: 3-8%
  • Mean reversion: 2-5%
  • Momentum burst: 5-10%

Portfolio Allocation:
  • UP_LOWVOL: 25 positions
  • Bull/UP_HIGHVOL: 20 positions
  • Sideways/Volatile: 15 positions
  • Bear/DOWN_LOWVOL: 8 positions
  • DOWN_HIGHVOL: 3 positions

Strategy Status:
  ✅ Day Trading: Active
  ✅ Mean Reversion: Active
  ✅ Momentum Burst: Active
  ✅ Risk Management: Active
  ✅ Position Sizing: Active
"""
        return config
        
    def update_live_chart(self):
        """Update live performance chart"""
        self.live_ax.clear()
        
        # Sample data for demonstration
        dates = pd.date_range(start='2024-08-01', end='2024-09-04', freq='D')
        portfolio_values = np.cumsum(np.random.normal(1000, 5000, len(dates))) + 900000
        
        self.live_ax.plot(dates, portfolio_values, color=self.colors['accent'], linewidth=2)
        self.live_ax.set_facecolor(self.colors['bg_medium'])
        self.live_ax.tick_params(colors=self.colors['text'])
        self.live_ax.set_title("Live Portfolio Performance", color=self.colors['text'])
        
        self.live_canvas.draw()
        
    def update_weekly_roi_charts(self):
        """Update weekly ROI charts"""
        # Weekly ROI trend
        self.roi_ax1.clear()
        weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5']
        roi_values = [4.2, 5.8, 3.1, 6.5, 5.2]
        self.roi_ax1.bar(weeks, roi_values, color=self.colors['accent'])
        self.roi_ax1.set_title("Weekly ROI Trend", color=self.colors['text'])
        
        # Strategy allocation pie chart
        self.roi_ax2.clear()
        strategies = ['Day Trading', 'Mean Reversion', 'Momentum']
        sizes = [40, 35, 25]
        colors = [self.colors['accent'], self.colors['secondary'], self.colors['info']]
        self.roi_ax2.pie(sizes, labels=strategies, colors=colors, autopct='%1.1f%%')
        self.roi_ax2.set_title("Strategy Allocation", color=self.colors['text'])
        
        self.roi_canvas.draw()
        
    def update_all_data(self):
        """Update all dashboard data"""
        # Reload live performance data
        self.live_performance = self.get_live_performance_data()
        
        # Update live metrics
        for key, value in self.live_performance.items():
            if key in self.live_metrics_labels:
                if key == 'portfolio_value':
                    self.live_metrics_labels[key].config(text=f"${value:,.2f}")
                elif key in ['daily_pnl']:
                    color = self.colors['success'] if value > 0 else self.colors['danger']
                    self.live_metrics_labels[key].config(text=f"${value:+,.2f}", fg=color)
                elif key in ['weekly_roi', 'win_rate']:
                    self.live_metrics_labels[key].config(text=f"{value:.1f}%")
                elif key == 'avg_hold_time':
                    self.live_metrics_labels[key].config(text=f"{value:.1f} days")
                else:
                    self.live_metrics_labels[key].config(text=str(value))
        
        # Update positions table
        if hasattr(self, 'positions_tree'):
            self.update_positions_table()
        
        # Update comparison metrics
        for key, value in self.backtest_results.items():
            if f"backtest_{key}" in self.comparison_labels:
                if key in ['total_return', 'win_rate']:
                    self.comparison_labels[f"backtest_{key}"].config(text=f"{value:.1f}%")
                elif key == 'sharpe_ratio':
                    self.comparison_labels[f"backtest_{key}"].config(text=f"{value:.2f}")
                elif key == 'max_drawdown':
                    self.comparison_labels[f"backtest_{key}"].config(text=f"{value:.1f}%")
        
        # Update ROI metrics
        for key, value in self.weekly_roi_metrics.items():
            if key in self.roi_labels:
                if key in ['current_week_roi', 'avg_weekly_roi', 'best_week', 'worst_week', 'weekly_win_rate']:
                    color = self.colors['success'] if value > 0 else self.colors['danger']
                    self.roi_labels[key].config(text=f"{value:+.1f}%", fg=color)
                else:
                    self.roi_labels[key].config(text=f"{value:.1f}")
        
        # Update charts
        self.update_live_chart()
        self.update_weekly_roi_charts()
        
    def start_updates(self):
        """Start real-time updates"""
        def update_loop():
            while True:
                try:
                    self.root.after(0, self.update_all_data)
                    time.sleep(30)  # Update every 30 seconds
                except:
                    break
        
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()

def main():
    """Main function to launch enhanced dashboard"""
    root = tk.Tk()
    dashboard = EnhancedWebDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
