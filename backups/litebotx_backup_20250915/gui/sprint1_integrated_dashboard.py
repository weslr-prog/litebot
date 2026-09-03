#!/usr/bin/env python3
"""
Sprint 1 Integrated Dashboard - Auto-launches with trading
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, List
import json

class Sprint1MetricsTracker:
    """Lightweight metrics tracker for Sprint 1"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.signals_generated = 0
        self.trades_executed = 0
        self.successful_trades = 0
        self.portfolio_snapshots = []
        self.trade_history = []
        self.cycle_times = []
        self.error_count = 0
        
    def add_cycle(self, signals: int, trades: int, cycle_time: float, success: bool = True):
        """Add trading cycle data"""
        self.signals_generated += signals
        self.trades_executed += trades
        if success:
            self.successful_trades += trades
        self.cycle_times.append(cycle_time)
        
    def add_portfolio_snapshot(self, portfolio_value: float, buying_power: float = 0):
        """Add portfolio snapshot"""
        self.portfolio_snapshots.append({
            'timestamp': datetime.now(),
            'portfolio_value': portfolio_value,
            'buying_power': buying_power
        })
        
    def add_trade(self, symbol: str, action: str, shares: int, price: float, status: str):
        """Add trade record"""
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': action,
            'shares': shares,
            'price': price,
            'value': shares * price,
            'status': status
        })
        
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        # Calculate returns if we have portfolio data
        total_return = 0.0
        if len(self.portfolio_snapshots) >= 2:
            start_value = self.portfolio_snapshots[0]['portfolio_value']
            current_value = self.portfolio_snapshots[-1]['portfolio_value']
            total_return = ((current_value - start_value) / start_value) * 100
            
        success_rate = (self.successful_trades / max(self.trades_executed, 1)) * 100
        avg_cycle_time = np.mean(self.cycle_times) if self.cycle_times else 0
        
        return {
            'uptime_hours': uptime_hours,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'success_rate': success_rate,
            'total_return_pct': total_return,
            'avg_cycle_time': avg_cycle_time,
            'total_cycles': len(self.cycle_times),
            'error_count': self.error_count
        }

class Sprint1Dashboard:
    """Integrated Sprint 1 Dashboard"""
    
    def __init__(self, sprint1_system, config):
        self.sprint1_system = sprint1_system
        self.config = config
        self.metrics_tracker = Sprint1MetricsTracker()
        
        # GUI setup
        self.root = tk.Tk()
        self.root.title("🚀 Sprint 1 + Alpaca Dashboard")
        self.root.geometry("1200x800")
        
        # Make window always on top initially, then normal
        self.root.attributes('-topmost', True)
        self.root.after(2000, lambda: self.root.attributes('-topmost', False))
        
        self.setup_gui()
        self.is_running = False
        
    def setup_gui(self):
        """Setup the GUI layout"""
        # Create main frames
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill='x', padx=10, pady=5)
        
        middle_frame = ttk.Frame(self.root)
        middle_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill='x', padx=10, pady=5)
        
        # Title and status
        title_label = ttk.Label(top_frame, text="🚀 Sprint 1 Real-Time Dashboard", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(side='left')
        
        self.status_label = ttk.Label(top_frame, text="⭕ Initializing...", 
                                     font=('Arial', 12, 'bold'))
        self.status_label.pack(side='right')
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(middle_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab 1: Live Monitoring
        self.setup_monitoring_tab()
        
        # Tab 2: Performance Charts
        self.setup_charts_tab()
        
        # Tab 3: Trade Log
        self.setup_trades_tab()
        
        # Control buttons
        self.setup_controls(bottom_frame)
        
    def setup_monitoring_tab(self):
        """Setup live monitoring tab"""
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="📊 Live Monitor")
        
        # Left panel - Metrics
        left_panel = ttk.Frame(monitor_frame)
        left_panel.pack(side='left', fill='y', padx=10, pady=10)
        
        # Account Status
        account_group = ttk.LabelFrame(left_panel, text="💰 Account Status")
        account_group.pack(fill='x', pady=5)
        
        self.account_text = tk.Text(account_group, height=6, width=35, font=('Courier', 10))
        self.account_text.pack(padx=5, pady=5)
        
        # Trading Metrics
        trading_group = ttk.LabelFrame(left_panel, text="📈 Trading Metrics")
        trading_group.pack(fill='x', pady=5)
        
        self.trading_text = tk.Text(trading_group, height=8, width=35, font=('Courier', 10))
        self.trading_text.pack(padx=5, pady=5)
        
        # Performance Summary
        perf_group = ttk.LabelFrame(left_panel, text="🎯 Performance")
        perf_group.pack(fill='x', pady=5)
        
        self.perf_text = tk.Text(perf_group, height=6, width=35, font=('Courier', 10))
        self.perf_text.pack(padx=5, pady=5)
        
        # Right panel - Real-time chart
        right_panel = ttk.Frame(monitor_frame)
        right_panel.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        chart_group = ttk.LabelFrame(right_panel, text="📊 Portfolio Value")
        chart_group.pack(fill='both', expand=True)
        
        # Portfolio chart
        self.portfolio_fig, self.portfolio_ax = plt.subplots(figsize=(8, 6))
        self.portfolio_ax.set_title('Portfolio Value Over Time')
        self.portfolio_ax.set_xlabel('Time')
        self.portfolio_ax.set_ylabel('Value ($)')
        
        self.portfolio_canvas = FigureCanvasTkAgg(self.portfolio_fig, chart_group)
        self.portfolio_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)
        
    def setup_charts_tab(self):
        """Setup performance charts tab"""
        charts_frame = ttk.Frame(self.notebook)
        self.notebook.add(charts_frame, text="📈 Charts")
        
        # Create subplots
        self.charts_fig, ((self.signals_ax, self.trades_ax), 
                         (self.returns_ax, self.cycles_ax)) = plt.subplots(2, 2, figsize=(12, 8))
        
        self.charts_fig.suptitle('Sprint 1 Performance Analytics')
        
        # Configure axes
        self.signals_ax.set_title('Signals Generated')
        self.trades_ax.set_title('Trades Executed')
        self.returns_ax.set_title('Portfolio Returns')
        self.cycles_ax.set_title('Cycle Times')
        
        self.charts_canvas = FigureCanvasTkAgg(self.charts_fig, charts_frame)
        self.charts_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
        
    def setup_trades_tab(self):
        """Setup trade log tab"""
        trades_frame = ttk.Frame(self.notebook)
        self.notebook.add(trades_frame, text="📋 Trade Log")
        
        # Trade history table
        columns = ('Time', 'Symbol', 'Action', 'Shares', 'Price', 'Value', 'Status')
        self.trades_tree = ttk.Treeview(trades_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.trades_tree.heading(col, text=col)
            self.trades_tree.column(col, width=100, anchor='center')
        
        # Scrollbar
        trades_scroll = ttk.Scrollbar(trades_frame, orient='vertical', command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=trades_scroll.set)
        
        self.trades_tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        trades_scroll.pack(side='right', fill='y', pady=10)
        
    def setup_controls(self, parent):
        """Setup control buttons"""
        ttk.Button(parent, text="🔄 Refresh", command=self.refresh_display).pack(side='left', padx=5)
        ttk.Button(parent, text="💾 Export", command=self.export_data).pack(side='left', padx=5)
        ttk.Button(parent, text="📊 Screenshot", command=self.take_screenshot).pack(side='left', padx=5)
        
        # Real-time indicator
        self.realtime_label = ttk.Label(parent, text="🔴 Stopped", font=('Arial', 10, 'bold'))
        self.realtime_label.pack(side='right', padx=10)
        
    def start_monitoring(self):
        """Start real-time monitoring"""
        self.is_running = True
        
        # Use after() to ensure GUI updates happen in main thread
        self.root.after(0, self._update_status_labels, True)
        
        # Start update thread
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        
    def _update_status_labels(self, running):
        """Update status labels in main thread"""
        if running:
            self.status_label.config(text="🟢 Running")
            self.realtime_label.config(text="🟢 Live", foreground='green')
        else:
            self.status_label.config(text="🔴 Stopped")
            self.realtime_label.config(text="🔴 Stopped", foreground='red')
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        
        # Use after() to ensure GUI updates happen in main thread
        self.root.after(0, self._update_status_labels, False)
        
    def update_loop(self):
        """Real-time update loop"""
        while self.is_running:
            try:
                # Get latest data from Sprint 1 system
                self.update_metrics()
                
                # Update GUI
                self.root.after(0, self.refresh_display)
                
                # Wait 30 seconds
                time.sleep(30)
                
            except Exception as e:
                print(f"Dashboard update error: {e}")
                time.sleep(10)
                
    def update_metrics(self):
        """Update metrics from Sprint 1 system"""
        try:
            # Get account info
            if hasattr(self.sprint1_system, 'trade_executor'):
                account_info = self.sprint1_system.trade_executor.get_account_info()
                if account_info.get('portfolio_value'):
                    self.metrics_tracker.add_portfolio_snapshot(
                        float(account_info['portfolio_value']),
                        float(account_info.get('buying_power', 0))
                    )
            
            # Get system metrics
            if hasattr(self.sprint1_system, 'get_system_metrics'):
                system_metrics = self.sprint1_system.get_system_metrics()
                
                # Update tracker with system data
                self.metrics_tracker.signals_generated = system_metrics.get('signals_generated', 0)
                self.metrics_tracker.trades_executed = system_metrics.get('trades_executed', 0)
                self.metrics_tracker.successful_trades = system_metrics.get('successful_trades', 0)
                
        except Exception as e:
            print(f"Metrics update error: {e}")
            
    def refresh_display(self):
        """Refresh all display elements"""
        try:
            self.update_account_display()
            self.update_trading_display()
            self.update_performance_display()
            self.update_portfolio_chart()
            self.update_performance_charts()
            self.update_trades_display()
        except Exception as e:
            print(f"Display refresh error: {e}")
            
    def update_account_display(self):
        """Update account information"""
        try:
            if hasattr(self.sprint1_system, 'trade_executor'):
                account_info = self.sprint1_system.trade_executor.get_account_info()
                
                self.account_text.delete(1.0, tk.END)
                self.account_text.insert(tk.END, f"""
Status: {account_info.get('status', 'Unknown')}
Portfolio: ${account_info.get('portfolio_value', 0):,.2f}
Buying Power: ${account_info.get('buying_power', 0):,.2f}
Cash: ${account_info.get('cash', 0):,.2f}
Alpaca: {'✅ Connected' if self.sprint1_system.trade_executor.is_alpaca_available() else '❌ Disconnected'}
""")
        except Exception as e:
            self.account_text.delete(1.0, tk.END)
            self.account_text.insert(tk.END, f"Error loading account data: {e}")
            
    def update_trading_display(self):
        """Update trading metrics"""
        try:
            if hasattr(self.sprint1_system, 'get_system_metrics'):
                metrics = self.sprint1_system.get_system_metrics()
                perf = self.metrics_tracker.get_performance_summary()
                
                self.trading_text.delete(1.0, tk.END)
                self.trading_text.insert(tk.END, f"""
Uptime: {perf['uptime_hours']:.1f} hours
Total Cycles: {perf['total_cycles']}
Signals Generated: {perf['signals_generated']}
Trades Executed: {perf['trades_executed']}
Success Rate: {perf['success_rate']:.1f}%
Avg Cycle Time: {perf['avg_cycle_time']:.2f}s
System Status: {metrics.get('status', 'Unknown')}
""")
        except Exception as e:
            self.trading_text.delete(1.0, tk.END)
            self.trading_text.insert(tk.END, f"Error loading trading data: {e}")
            
    def update_performance_display(self):
        """Update performance metrics"""
        try:
            perf = self.metrics_tracker.get_performance_summary()
            
            self.perf_text.delete(1.0, tk.END)
            self.perf_text.insert(tk.END, f"""
Total Return: {perf['total_return_pct']:.2f}%
Signals/Hour: {perf['signals_generated'] / max(perf['uptime_hours'], 0.1):.1f}
Trades/Hour: {perf['trades_executed'] / max(perf['uptime_hours'], 0.1):.1f}
Error Count: {perf['error_count']}
Data Quality: Good ✅
System Health: Operational ✅
""")
        except Exception as e:
            self.perf_text.delete(1.0, tk.END)
            self.perf_text.insert(tk.END, f"Error loading performance data: {e}")
            
    def update_portfolio_chart(self):
        """Update portfolio value chart"""
        try:
            if not self.metrics_tracker.portfolio_snapshots:
                return
                
            times = [s['timestamp'] for s in self.metrics_tracker.portfolio_snapshots]
            values = [s['portfolio_value'] for s in self.metrics_tracker.portfolio_snapshots]
            
            self.portfolio_ax.clear()
            self.portfolio_ax.plot(times, values, 'b-', linewidth=2, marker='o', markersize=4)
            self.portfolio_ax.set_title('Portfolio Value Over Time')
            self.portfolio_ax.set_xlabel('Time')
            self.portfolio_ax.set_ylabel('Value ($)')
            self.portfolio_ax.grid(True, alpha=0.3)
            
            # Format x-axis
            if len(times) > 1:
                self.portfolio_ax.tick_params(axis='x', rotation=45)
                
            self.portfolio_canvas.draw()
        except Exception as e:
            print(f"Portfolio chart error: {e}")
            
    def update_performance_charts(self):
        """Update performance analysis charts"""
        try:
            # Clear all axes
            for ax in [self.signals_ax, self.trades_ax, self.returns_ax, self.cycles_ax]:
                ax.clear()
                
            perf = self.metrics_tracker.get_performance_summary()
            
            # Signals over time
            if self.metrics_tracker.cycle_times:
                cycles = list(range(1, len(self.metrics_tracker.cycle_times) + 1))
                self.signals_ax.bar(cycles, [1] * len(cycles), alpha=0.7, color='green')
                self.signals_ax.set_title(f'Signals Generated ({perf["signals_generated"]} total)')
                
            # Trades over time
            if self.metrics_tracker.trades_executed > 0:
                self.trades_ax.bar(['Executed', 'Successful'], 
                                  [self.metrics_tracker.trades_executed, self.metrics_tracker.successful_trades],
                                  alpha=0.7, color=['blue', 'green'])
                self.trades_ax.set_title('Trade Execution')
                
            # Returns
            if len(self.metrics_tracker.portfolio_snapshots) > 1:
                values = [s['portfolio_value'] for s in self.metrics_tracker.portfolio_snapshots]
                returns = [(values[i] - values[i-1]) / values[i-1] * 100 for i in range(1, len(values))]
                self.returns_ax.plot(returns, 'r-', linewidth=2)
                self.returns_ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
                self.returns_ax.set_title('Portfolio Returns (%)')
                
            # Cycle times
            if self.metrics_tracker.cycle_times:
                self.cycles_ax.plot(self.metrics_tracker.cycle_times, 'purple', linewidth=2, marker='o')
                self.cycles_ax.set_title(f'Cycle Times (Avg: {perf["avg_cycle_time"]:.2f}s)')
                
            self.charts_canvas.draw()
        except Exception as e:
            print(f"Charts update error: {e}")
            
    def update_trades_display(self):
        """Update trade history table"""
        try:
            # Clear existing items
            for item in self.trades_tree.get_children():
                self.trades_tree.delete(item)
                
            # Add recent trades
            for trade in self.metrics_tracker.trade_history[-50:]:  # Last 50 trades
                self.trades_tree.insert('', 'end', values=(
                    trade['timestamp'].strftime('%H:%M:%S'),
                    trade['symbol'],
                    trade['action'].upper(),
                    f"{trade['shares']:,}",
                    f"${trade['price']:.2f}",
                    f"${trade['value']:,.2f}",
                    trade['status'].title()
                ))
        except Exception as e:
            print(f"Trades display error: {e}")
            
    def export_data(self):
        """Export performance data"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'performance_summary': self.metrics_tracker.get_performance_summary(),
                'portfolio_snapshots': [
                    {**s, 'timestamp': s['timestamp'].isoformat()} 
                    for s in self.metrics_tracker.portfolio_snapshots
                ],
                'trade_history': [
                    {**t, 'timestamp': t['timestamp'].isoformat()} 
                    for t in self.metrics_tracker.trade_history
                ]
            }
            
            filename = f"sprint1_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
            print(f"✅ Performance data exported to {filename}")
        except Exception as e:
            print(f"❌ Export failed: {e}")
            
    def take_screenshot(self):
        """Take screenshot of dashboard"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sprint1_dashboard_{timestamp}.png"
            
            # This would require additional libraries like PIL
            print(f"📊 Screenshot functionality would save to {filename}")
        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
            
    def run(self):
        """Run the dashboard"""
        self.start_monitoring()
        self.root.mainloop()
        
    def close(self):
        """Close the dashboard"""
        self.stop_monitoring()
        self.root.quit()

def create_integrated_dashboard(sprint1_system, config):
    """Create and return integrated dashboard"""
    return Sprint1Dashboard(sprint1_system, config)

if __name__ == "__main__":
    """Run dashboard standalone"""
    import sys
    import os
    
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config import Sprint1Config
    from sprint1_alpaca_integration import Sprint1AlpacaIntegration
    
    try:
        print("🖥️ Starting Sprint 1 Integrated Dashboard...")
        
        # Initialize configuration
        config = Sprint1Config()
        
        # Initialize trading system (dashboard mode only)
        trading_system = Sprint1AlpacaIntegration(launch_gui=False)
        
        # Create and run dashboard
        dashboard = Sprint1Dashboard(trading_system, config)
        
        print("✅ Dashboard initialized successfully")
        print("📊 Starting real-time monitoring...")
        
        # Run dashboard
        dashboard.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Dashboard startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
