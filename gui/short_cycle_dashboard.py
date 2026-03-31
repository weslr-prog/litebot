#!/usr/bin/env python3
"""
ShortCycleTrader GUI Dashboard - Real-time monitoring for high-ROI trading
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, List, Optional
import json
from collections import deque

class ShortCycleMetricsTracker:
    """Real-time metrics tracking for ShortCycleTrader"""
    
    def __init__(self, max_history=1000):
        self.start_time = datetime.now()
        self.max_history = max_history
        
        # Core metrics
        self.signals_generated = 0
        self.trades_executed = 0
        self.successful_trades = 0
        self.total_pnl = 0.0
        self.win_rate = 0.0
        
        # Time series data (using deque for efficiency)
        self.portfolio_history = deque(maxlen=max_history)
        self.signal_history = deque(maxlen=max_history)
        self.trade_history = deque(maxlen=max_history)
        self.cycle_times = deque(maxlen=max_history)
        
        # Current state
        self.current_positions = {}
        self.latest_signals = []
        self.market_phase = "Unknown"
        self.last_update = datetime.now()
        
    def add_signal(self, symbol: str, confidence: float, action: str, timestamp=None):
        """Add new signal"""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.signals_generated += 1
        self.signal_history.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'confidence': confidence,
            'action': action
        })
        
        # Update latest signals (keep last 10)
        self.latest_signals.append(f"{timestamp.strftime('%H:%M')} {symbol} {action} ({confidence:.2f})")
        if len(self.latest_signals) > 10:
            self.latest_signals.pop(0)
    
    def add_trade(self, symbol: str, action: str, quantity: int, price: float, pnl: float = 0):
        """Add completed trade"""
        timestamp = datetime.now()
        self.trades_executed += 1
        
        if pnl > 0:
            self.successful_trades += 1
            
        self.total_pnl += pnl
        self.win_rate = (self.successful_trades / max(self.trades_executed, 1)) * 100
        
        self.trade_history.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'pnl': pnl,
            'total_pnl': self.total_pnl
        })
    
    def update_portfolio(self, total_value: float, buying_power: float = 0):
        """Update portfolio value"""
        timestamp = datetime.now()
        self.portfolio_history.append({
            'timestamp': timestamp,
            'total_value': total_value,
            'buying_power': buying_power
        })
        self.last_update = timestamp
    
    def update_position(self, symbol: str, quantity: int, avg_price: float, current_price: float):
        """Update current position"""
        unrealized_pnl = (current_price - avg_price) * quantity
        self.current_positions[symbol] = {
            'quantity': quantity,
            'avg_price': avg_price,
            'current_price': current_price,
            'unrealized_pnl': unrealized_pnl,
            'timestamp': datetime.now()
        }
    
    def set_market_phase(self, phase: str):
        """Update current market phase"""
        self.market_phase = phase
    
    def get_performance_summary(self) -> Dict:
        """Get current performance summary"""
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        # Calculate daily return
        daily_return = 0.0
        if len(self.portfolio_history) >= 2:
            start_value = self.portfolio_history[0]['total_value']
            current_value = self.portfolio_history[-1]['total_value']
            daily_return = ((current_value - start_value) / start_value) * 100
        
        # Calculate average confidence
        avg_confidence = 0.0
        if self.signal_history:
            confidences = [s['confidence'] for s in self.signal_history]
            avg_confidence = np.mean(confidences)
        
        return {
            'uptime_hours': uptime_hours,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'daily_return_pct': daily_return,
            'avg_confidence': avg_confidence,
            'active_positions': len(self.current_positions),
            'market_phase': self.market_phase,
            'last_update': self.last_update.strftime('%H:%M:%S')
        }

class ShortCycleDashboard:
    """Real-time GUI Dashboard for ShortCycleTrader"""
    
    def __init__(self, trader=None):
        self.trader = trader
        self.metrics = ShortCycleMetricsTracker()
        
        # Data persistence - retain last known state
        self.last_portfolio_value = 0.0
        self.last_positions = {}
        self.last_performance_data = {}
        self.last_update_time = datetime.now()
        
        # GUI setup
        self.root = tk.Tk()
        self.root.title("🚀 ShortCycleTrader - High-ROI Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0a0a0a')  # Dark background
        
        # Connect to trader if provided
        if trader:
            self.connect_trader(trader)
        
        # Set window icon and properties
        self.root.attributes('-topmost', True)
        self.root.after(3000, lambda: self.root.attributes('-topmost', False))
        
        # Colors and style
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#00ff00',
            'warning': '#ffaa00',
            'error': '#ff4444',
            'profit': '#00dd00',
            'loss': '#dd0000'
        }
        
        self.setup_gui()
        self.is_running = False
        self.update_thread = None
        
    def setup_gui(self):
        """Setup the complete GUI layout"""
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top status bar
        self.setup_status_bar(main_frame)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(10, 0))
        
        # Setup tabs
        self.setup_overview_tab()
        self.setup_signals_tab()
        self.setup_positions_tab()
        self.setup_performance_tab()
        
        # Bottom control panel
        self.setup_controls(main_frame)
    
    def setup_status_bar(self, parent):
        """Setup top status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill='x', pady=(0, 10))
        
        # Title
        title_label = ttk.Label(status_frame, text="🚀 ShortCycleTrader Dashboard", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(side='left')
        
        # Status indicators with better persistence
        status_text = "🟢 Running Continuously" if hasattr(self, 'trader') and self.trader else "⭕ Starting..."
        self.status_label = ttk.Label(status_frame, text=status_text, 
                                     font=('Arial', 12, 'bold'))
        self.status_label.pack(side='right')
        
        self.time_label = ttk.Label(status_frame, text="", font=('Arial', 10))
        self.time_label.pack(side='right', padx=(0, 20))
    
    def setup_overview_tab(self):
        """Setup main overview tab"""
        overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="📊 Overview")
        
        # Split into left and right panels
        left_panel = ttk.Frame(overview_frame)
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        
        right_panel = ttk.Frame(overview_frame)
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Left panel - Key metrics
        self.setup_metrics_panel(left_panel)
        
        # Right panel - Portfolio chart
        self.setup_portfolio_chart(right_panel)
    
    def setup_metrics_panel(self, parent):
        """Setup key metrics display"""
        # Performance metrics
        perf_frame = ttk.LabelFrame(parent, text="📈 Performance")
        perf_frame.pack(fill='x', pady=5)
        
        self.perf_text = tk.Text(perf_frame, height=8, width=40, font=('Courier', 10))
        self.perf_text.pack(padx=5, pady=5)
        
        # Trading activity
        activity_frame = ttk.LabelFrame(parent, text="🔄 Trading Activity")
        activity_frame.pack(fill='x', pady=5)
        
        self.activity_text = tk.Text(activity_frame, height=8, width=40, font=('Courier', 10))
        self.activity_text.pack(padx=5, pady=5)
        
        # Current positions
        positions_frame = ttk.LabelFrame(parent, text="💼 Current Positions")
        positions_frame.pack(fill='x', pady=5)
        
        self.positions_text = tk.Text(positions_frame, height=6, width=40, font=('Courier', 10))
        self.positions_text.pack(padx=5, pady=5)
    
    def setup_portfolio_chart(self, parent):
        """Setup real-time portfolio chart"""
        chart_frame = ttk.LabelFrame(parent, text="📊 Portfolio Value")
        chart_frame.pack(fill='both', expand=True)
        
        # Create matplotlib figure
        self.portfolio_fig, self.portfolio_ax = plt.subplots(figsize=(10, 6))
        self.portfolio_ax.set_title('Portfolio Value Over Time')
        self.portfolio_ax.set_xlabel('Time')
        self.portfolio_ax.set_ylabel('Value ($)')
        self.portfolio_ax.grid(True, alpha=0.3)
        
        # Set dark theme
        self.portfolio_fig.patch.set_facecolor('#2e2e2e')
        self.portfolio_ax.set_facecolor('#2e2e2e')
        self.portfolio_ax.tick_params(colors='white')
        self.portfolio_ax.xaxis.label.set_color('white')
        self.portfolio_ax.yaxis.label.set_color('white')
        self.portfolio_ax.title.set_color('white')
        
        # Embed in tkinter
        self.portfolio_canvas = FigureCanvasTkAgg(self.portfolio_fig, chart_frame)
        self.portfolio_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)
    
    def setup_signals_tab(self):
        """Setup signals monitoring tab"""
        signals_frame = ttk.Frame(self.notebook)
        self.notebook.add(signals_frame, text="🎯 Signals")
        
        # Recent signals
        recent_frame = ttk.LabelFrame(signals_frame, text="🔥 Latest Signals")
        recent_frame.pack(fill='x', padx=10, pady=10)
        
        self.signals_text = tk.Text(recent_frame, height=15, font=('Courier', 10))
        signals_scroll = ttk.Scrollbar(recent_frame, orient="vertical", command=self.signals_text.yview)
        self.signals_text.configure(yscrollcommand=signals_scroll.set)
        
        self.signals_text.pack(side="left", fill='both', expand=True, padx=5, pady=5)
        signals_scroll.pack(side="right", fill="y")
        
        # Signal statistics
        stats_frame = ttk.LabelFrame(signals_frame, text="📊 Signal Statistics")
        stats_frame.pack(fill='x', padx=10, pady=10)
        
        self.signal_stats_text = tk.Text(stats_frame, height=8, font=('Courier', 10))
        self.signal_stats_text.pack(fill='x', padx=5, pady=5)
    
    def setup_positions_tab(self):
        """Setup positions monitoring tab"""
        positions_frame = ttk.Frame(self.notebook)
        self.notebook.add(positions_frame, text="💼 Positions")
        
        # Position details
        details_frame = ttk.LabelFrame(positions_frame, text="📈 Position Details")
        details_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.position_details_text = tk.Text(details_frame, font=('Courier', 10))
        pos_scroll = ttk.Scrollbar(details_frame, orient="vertical", command=self.position_details_text.yview)
        self.position_details_text.configure(yscrollcommand=pos_scroll.set)
        
        self.position_details_text.pack(side="left", fill='both', expand=True, padx=5, pady=5)
        pos_scroll.pack(side="right", fill="y")
    
    def setup_performance_tab(self):
        """Setup performance analytics tab"""
        perf_frame = ttk.Frame(self.notebook)
        self.notebook.add(perf_frame, text="📈 Performance")
        
        # Create performance charts
        self.perf_fig, ((self.pnl_ax, self.signals_ax), 
                       (self.trades_ax, self.confidence_ax)) = plt.subplots(2, 2, figsize=(12, 8))
        
        self.perf_fig.suptitle('Performance Analytics', color='white')
        self.perf_fig.patch.set_facecolor('#2e2e2e')
        
        # Configure each subplot
        for ax in [self.pnl_ax, self.signals_ax, self.trades_ax, self.confidence_ax]:
            ax.set_facecolor('#2e2e2e')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
            ax.grid(True, alpha=0.3)
        
        self.pnl_ax.set_title('P&L Over Time')
        self.signals_ax.set_title('Signals Generated')
        self.trades_ax.set_title('Trade Success Rate')
        self.confidence_ax.set_title('Signal Confidence Distribution')
        
        self.perf_canvas = FigureCanvasTkAgg(self.perf_fig, perf_frame)
        self.perf_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def setup_controls(self, parent):
        """Setup control buttons"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill='x', pady=(10, 0))
        
        # Start/Stop button
        self.start_button = ttk.Button(control_frame, text="▶️ Start Monitoring", 
                                      command=self.toggle_monitoring)
        self.start_button.pack(side='left')
        
        # Refresh button
        refresh_button = ttk.Button(control_frame, text="🔄 Refresh", 
                                   command=self.refresh_data)
        refresh_button.pack(side='left', padx=(10, 0))
        
        # Status text
        status_text = ttk.Label(control_frame, text="Ready to monitor")
        status_text.pack(side='right')
    
    def toggle_monitoring(self):
        """Start/stop monitoring"""
        if not self.is_running:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Start continuous monitoring with graceful error handling"""
        self.is_running = True
        
        def update_loop():
            import logging
            logger = logging.getLogger(__name__)
            
            while self.is_running:
                try:
                    if self.root and self.root.winfo_exists():
                        self.refresh_data()
                        # Update every 5 seconds for responsive UI
                        time.sleep(5)
                    else:
                        break
                except Exception as e:
                    try:
                        logger.info(f"Dashboard update warning: {e}")
                    except:
                        print(f"Dashboard update warning: {e}")
                    time.sleep(10)  # Longer sleep on errors
        
        # Start update loop in background thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        
        # Start main GUI loop
        self.root.mainloop()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        self.start_button.config(text="▶️ Start Monitoring")
        self.status_label.config(text="🔴 Stopped")
    
    def _update_loop(self):
        """Background update loop"""
        while self.is_running:
            try:
                self.refresh_data()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Dashboard update error: {e}")
                time.sleep(5)
    
    def refresh_data(self):
        """Refresh all dashboard data"""
        # Sync positions from trader
        self.sync_positions_from_trader()
        
        # Update GUI
        self.root.after(0, self._update_gui)
    
    def _update_gui(self):
        """Update GUI elements (must run in main thread)"""
        try:
            # Check if widgets still exist
            if not self.root.winfo_exists():
                return
                
            # Update time and status
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if hasattr(self, 'time_label') and self.time_label.winfo_exists():
                self.time_label.config(text=current_time)
            
            # Update status to show continuous operation
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                status_text = "🟢 Running Continuously" if hasattr(self, 'trader') and self.trader else "🔄 Monitoring..."
                self.status_label.config(text=status_text)
            
            # Update metrics
            self.update_metrics_display()
            
            # Update charts
            self.update_portfolio_chart()
            self.update_performance_charts()
            
        except tk.TclError as e:
            # Widget has been destroyed, stop updating
            if "invalid command name" in str(e):
                self.is_running = False
        except Exception as e:
            print(f"GUI update error: {e}")
    
    def update_metrics_display(self):
        """Update metrics text displays with data persistence"""
        try:
            summary = self.metrics.get_performance_summary()
            
            # Update last known values if new data is available
            if summary.get('total_pnl') is not None:
                self.last_performance_data = summary.copy()
                self.last_update_time = datetime.now()
            else:
                # Use last known data if new data isn't available
                summary = self.last_performance_data.copy()
                if summary:
                    age_minutes = (datetime.now() - self.last_update_time).seconds // 60
                    summary['last_update'] = f"{summary.get('last_update', '')} ({age_minutes}m ago)"
            
            # Check if widgets exist before updating
            if hasattr(self, 'perf_text') and self.perf_text.winfo_exists():
                # Performance metrics
                perf_text = f"""Performance Summary
{'='*25}
Uptime:        {summary.get('uptime_hours', 0):.1f} hours
Market Phase:  {summary.get('market_phase', 'Unknown')}
Last Update:   {summary.get('last_update', 'No data')}

P&L:           ${summary.get('total_pnl', 0):.2f}
Daily Return:  {summary.get('daily_return_pct', 0):.2f}%
Win Rate:      {summary.get('win_rate', 0):.1f}%
Avg Confidence: {summary.get('avg_confidence', 0):.2f}
"""
                
                self.perf_text.delete(1.0, tk.END)
                self.perf_text.insert(1.0, perf_text)
            
            if hasattr(self, 'activity_text') and self.activity_text.winfo_exists():
                # Trading activity with persistence
                # Update last known positions if available
                if self.metrics.current_positions:
                    self.last_positions = self.metrics.current_positions.copy()
                
                activity_text = f"""Trading Activity
{'='*20}
Signals:       {summary.get('signals_generated', 0)}
Trades:        {summary.get('trades_executed', 0)}
Active Pos:    {summary.get('active_positions', len(self.last_positions))}
Success Rate:  {summary.get('win_rate', 0):.1f}%

Status:        🟢 Monitoring
Bot State:     Continuous Operation
"""
                
                self.activity_text.delete(1.0, tk.END)
                self.activity_text.insert(1.0, activity_text)
            
            if hasattr(self, 'positions_text') and self.positions_text.winfo_exists():
                # Current positions with persistence
                pos_text = "Current Positions\n" + "="*20 + "\n"
                # Use current positions or fall back to last known
                positions_to_show = self.metrics.current_positions or self.last_positions
                if positions_to_show:
                    for symbol, pos in positions_to_show.items():
                        pnl_color = "📈" if pos.get('unrealized_pnl', 0) >= 0 else "📉"
                        pos_text += f"{symbol}: {pos.get('quantity', 0)} @ ${pos.get('avg_price', 0):.2f} {pnl_color}${pos.get('unrealized_pnl', 0):.2f}\n"
                else:
                    pos_text += "No active positions\n(Monitoring for opportunities)"
                    
                self.positions_text.delete(1.0, tk.END)
                self.positions_text.insert(1.0, pos_text)
                
        except tk.TclError:
            # Widget destroyed, stop updating
            pass
        except Exception as e:
            print(f"Metrics display error: {e}")
    
    def update_portfolio_chart(self):
        """Update portfolio value chart"""
        if not self.metrics.portfolio_history:
            return
            
        # Get recent portfolio data
        recent_data = list(self.metrics.portfolio_history)[-100:]  # Last 100 points
        if not recent_data:
            return
            
        times = [d['timestamp'] for d in recent_data]
        values = [d['total_value'] for d in recent_data]
        
        self.portfolio_ax.clear()
        self.portfolio_ax.plot(times, values, color='#00ff00', linewidth=2)
        self.portfolio_ax.set_title('Portfolio Value Over Time', color='white')
        self.portfolio_ax.set_xlabel('Time', color='white')
        self.portfolio_ax.set_ylabel('Value ($)', color='white')
        self.portfolio_ax.grid(True, alpha=0.3)
        self.portfolio_ax.tick_params(colors='white')
        
        # Format x-axis for time
        if len(times) > 1:
            self.portfolio_fig.autofmt_xdate()
        
        self.portfolio_canvas.draw()
    
    def update_performance_charts(self):
        """Update performance analytics charts"""
        # This would be implemented with actual data from the trader
        pass
    
    def connect_trader(self, trader):
        """Connect to a ShortCycleTrader instance"""
        self.trader = trader
        
        # Set up callbacks if the trader supports them
        if hasattr(trader, 'add_signal_callback'):
            trader.add_signal_callback(self.on_signal_generated)
        if hasattr(trader, 'add_trade_callback'):
            trader.add_trade_callback(self.on_trade_executed)
        
        # Initial sync of current positions
        self.sync_positions_from_trader()
    
    def sync_positions_from_trader(self):
        """Sync current positions from the trader"""
        if not self.trader or not hasattr(self.trader, 'positions'):
            return
            
        # Clear existing positions in dashboard
        self.metrics.current_positions.clear()
        
        # Add current trader positions
        for position in self.trader.positions:
            if position.status.value == "entered":  # Only show active positions
                self.metrics.current_positions[position.symbol] = {
                    'quantity': position.position_size_shares,
                    'avg_price': position.entry_price,
                    'current_price': position.current_price or position.entry_price,
                    'unrealized_pnl': position.unrealized_pnl or 0.0,
                    'entry_date': position.entry_date.strftime('%Y-%m-%d') if position.entry_date else 'Unknown',
                    'status': position.status.value
                }
    
    def on_signal_generated(self, symbol: str, signal_data: dict):
        """Callback for when a signal is generated"""
        self.metrics.add_signal(
            symbol=symbol,
            confidence=signal_data.get('confidence', 0),
            action=signal_data.get('action', 'UNKNOWN')
        )
    
    def on_trade_executed(self, symbol: str, trade_data: dict):
        """Callback for when a trade is executed"""
        self.metrics.add_trade(
            symbol=symbol,
            action=trade_data.get('action', 'UNKNOWN'),
            quantity=trade_data.get('quantity', 0),
            price=trade_data.get('price', 0),
            pnl=trade_data.get('pnl', 0)
        )
    
    def run(self):
        """Start the dashboard"""
        print("🚀 Starting ShortCycleTrader Dashboard...")
        self.start_monitoring()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n🛑 Dashboard stopped by user")
        finally:
            self.stop_monitoring()
    
    def close(self):
        """Close the dashboard"""
        self.stop_monitoring()
        self.root.quit()
        self.root.destroy()

def create_short_cycle_dashboard(trader=None):
    """Create and return a ShortCycleTrader dashboard"""
    return ShortCycleDashboard(trader)

if __name__ == "__main__":
    """Run dashboard standalone for testing"""
    try:
        print("🧪 Testing ShortCycleTrader Dashboard...")
        
        # Create test dashboard
        dashboard = ShortCycleDashboard()
        
        # Add some test data
        dashboard.metrics.add_signal("AAPL", 0.85, "BUY")
        dashboard.metrics.add_signal("TSLA", 0.75, "BUY")
        dashboard.metrics.update_portfolio(100000, 50000)
        dashboard.metrics.set_market_phase("Opening")
        
        print("✅ Dashboard created successfully")
        print("📊 Starting GUI...")
        
        # Run dashboard
        dashboard.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard test stopped by user")
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        import traceback
        traceback.print_exc()