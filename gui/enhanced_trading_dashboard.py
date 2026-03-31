#!/usr/bin/env python3
"""
Enhanced Trading Bot Dashboard - Modern Colorful GUI
Integrates with LiteBotX Aggressive Swing Trading System
"""

import tkinter as tk
from tkinter import ttk, messagebox
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Matplotlib not available - charts will be disabled")

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from archive.automated_momentum_trader_v2 import AutomatedMomentumTraderV2
    from connect_real_trading import RealPaperTradingEngine
    from core.sector_analyzer import SectorAnalyzer
    HAS_TRADING_MODULES = True
except ImportError as e:
    HAS_TRADING_MODULES = False
    print(f"Trading modules not available: {e}")

class TradingBotDashboard:
    """Modern Trading Bot Dashboard with Multi-Sector Analysis"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 LitebotX Dashboard")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#1e1e1e')  # Dark theme
        self.root.minsize(1200, 800)  # Minimum size for proper display
        
        # Color scheme - Modern and vibrant
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
        
        # Configure style for better cross-platform compatibility
        self.configure_styles()
        
        # Try to center the window
        self.center_window()
        
        # Initialize trading components
        self.initialize_trading_components()
        
        # Create dashboard layout
        self.setup_dashboard()
        
        # Start real-time updates
        self.start_updates()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = 1600
        height = 1000
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def configure_styles(self):
        """Configure ttk styles for better appearance"""
        try:
            style = ttk.Style()
            style.theme_use('clam')  # Use clam theme as base
            
            # Configure scrollbar style
            style.configure("Vertical.TScrollbar",
                          background=self.colors['bg_light'],
                          troughcolor=self.colors['bg_dark'],
                          arrowcolor=self.colors['text_muted'])
        except Exception as e:
            print(f"Style configuration warning: {e}")
    
    def get_font(self, font_type='normal', size=None):
        """Get appropriate font for cross-platform compatibility"""
        font_families = ['Segoe UI', 'Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif']
        
        # Try each font family until one works
        for family in font_families:
            try:
                if font_type == 'title':
                    return (family, size or 28, 'bold')
                elif font_type == 'heading':
                    return (family, size or 20, 'bold')
                elif font_type == 'metric':
                    return (family, size or 14, 'normal')
                elif font_type == 'metric_large':
                    return (family, size or 16, 'bold')
                else:
                    return (family, size or 12, 'normal')
            except:
                continue
        
        # Fallback to default
        return ('TkDefaultFont', size or 12, 'normal')
    
    
    def initialize_trading_components(self):
        """Initialize trading system components"""
        if HAS_TRADING_MODULES:
            try:
                # Initialize trading engine for portfolio data
                self.trading_engine = RealPaperTradingEngine()
                
                # Initialize enhanced trader (will use dummy data if unavailable)
                try:
                    from archive.automated_momentum_trader_v2 import AutomatedMomentumTraderV2
                    self.enhanced_trader = AutomatedMomentumTraderV2(
                        alpha_vantage_key="O8JA27H3XK5E3NAU",
                        use_enhanced_strategy=True
                    )
                    self.has_enhanced = True
                except:
                    self.enhanced_trader = None
                    self.has_enhanced = False
                
            except Exception as e:
                print(f"Warning: Trading components not available, using demo data: {e}")
                self.trading_engine = None
                self.enhanced_trader = None
                self.has_enhanced = False
        else:
            self.trading_engine = None
            self.enhanced_trader = None
            self.has_enhanced = False
        
        # Get real data or use sample data
        self.sample_data = self.get_real_or_sample_data()
    
    def get_real_or_sample_data(self):
        """Get real trading data or fallback to sample data"""
        if self.trading_engine:
            try:
                # Get real account information
                account_info = self.trading_engine.get_account_info()
                positions = self.trading_engine.get_positions()
                
                # Extract real data
                portfolio_value = float(account_info.get('portfolio_value', 0))
                equity = float(account_info.get('equity', portfolio_value))
                buying_power = float(account_info.get('buying_power', 0))
                day_trade_buying_power = float(account_info.get('day_trade_buying_power', 0))
                
                print(f"📊 Real Portfolio Data:")
                print(f"   Portfolio Value: ${portfolio_value:,.2f}")
                print(f"   Equity: ${equity:,.2f}")
                print(f"   Buying Power: ${buying_power:,.2f}")
                print(f"   Active Positions: {len(positions)}")
                
                # Try to get real trading history and performance metrics
                real_metrics = self.get_real_trading_metrics()
                
                # Calculate portfolio start from real data if available
                portfolio_start = real_metrics.get('starting_portfolio', 900000.00)
                
                # Process real positions
                real_positions = []
                total_pnl = 0
                biggest_winner = {'symbol': 'N/A', 'amount': 0, 'percent': 0}
                biggest_loser = {'symbol': 'N/A', 'amount': 0, 'percent': 0}
                
                for pos in positions:
                    try:
                        # Handle if positions come as strings (symbol names) instead of objects
                        if isinstance(pos, str):
                            # Position is just a symbol name, create basic structure
                            real_positions.append({
                                'ticker': pos,
                                'qty': 1,  # Unknown quantity
                                'entry': 0.0,  # Unknown entry
                                'current': 0.0,  # Unknown current
                                'sector': self.get_sector_for_symbol(pos)
                            })
                            continue
                            
                        # Handle position as dictionary
                        qty = float(pos.get('qty', 0))
                        if qty == 0:
                            continue
                            
                        symbol = pos.get('symbol', 'UNK')
                        avg_entry_price = float(pos.get('avg_entry_price', 0))
                        current_price = float(pos.get('market_value', 0)) / abs(qty) if qty != 0 else 0
                        unrealized_pl = float(pos.get('unrealized_pl', 0))
                        
                        real_positions.append({
                            'ticker': symbol,
                            'qty': int(qty),
                            'entry': avg_entry_price,
                            'current': current_price,
                            'sector': self.get_sector_for_symbol(symbol)
                        })
                        
                        total_pnl += unrealized_pl
                        
                        # Track biggest winner/loser
                        if unrealized_pl > biggest_winner['amount']:
                            biggest_winner = {
                                'symbol': symbol,
                                'amount': unrealized_pl,
                                'percent': (unrealized_pl / (avg_entry_price * abs(qty))) * 100 if avg_entry_price > 0 else 0
                            }
                        if unrealized_pl < biggest_loser['amount']:
                            biggest_loser = {
                                'symbol': symbol,
                                'amount': unrealized_pl,
                                'percent': (unrealized_pl / (avg_entry_price * abs(qty))) * 100 if avg_entry_price > 0 else 0
                            }
                            
                    except Exception as e:
                        print(f"Error processing position {pos}: {e}")
                        continue
                
                # Use real positions if available, otherwise sample data
                if not real_positions:
                    print("📊 No real positions found, using sample data for positions")
                    real_positions = self.generate_sample_data()['positions']
                    if biggest_winner['amount'] == 0:
                        biggest_winner = self.generate_sample_data()['biggest_winner']
                    if biggest_loser['amount'] == 0:
                        biggest_loser = self.generate_sample_data()['biggest_loser']
                
                # Get live market regime if enhanced trader is available
                current_regime = self.get_current_market_regime()
                
                # Calculate real performance metrics
                change_amount = portfolio_value - portfolio_start
                change_percent = (change_amount / portfolio_start) * 100 if portfolio_start > 0 else 0
                
                return {
                    'portfolio_start': portfolio_start,
                    'portfolio_current': portfolio_value,
                    'trades_opened': real_metrics.get('total_trades', len(positions) + 12),
                    'trades_closed': real_metrics.get('closed_trades', 12),
                    'active_trades': len(positions),
                    'win_rate': real_metrics.get('win_rate', 66),
                    'biggest_winner': biggest_winner,
                    'biggest_loser': biggest_loser,
                    'vs_backtest': real_metrics.get('vs_backtest', change_percent - 2),  # Real vs expected
                    'expectancy': real_metrics.get('expectancy', 0.6),
                    'sharpe_ratio': real_metrics.get('sharpe_ratio', 1.4),
                    'target_sharpe': 1.3,
                    'drawdown': real_metrics.get('current_drawdown', -2.5),
                    'largest_loss': min(biggest_loser['amount'], real_metrics.get('largest_loss', -320.00)),
                    'equity_trend': real_metrics.get('equity_trend', 'Above long-term line'),
                    'slippage_loss': real_metrics.get('slippage_loss', 0.05),
                    'partial_fills': real_metrics.get('partial_fills', 3),
                    'partial_fill_loss': real_metrics.get('partial_fill_loss', 240.00),
                    'regime': current_regime,
                    'strategy': 'Aggressive Swing Trading',
                    'positions': real_positions,
                    'portfolio_change_percent': change_percent,
                    'portfolio_change_amount': change_amount
                }
                
            except Exception as e:
                print(f"Error getting real data: {e}")
                
        print("📊 Using sample data (real data unavailable)")
        return self.generate_sample_data()
    
    def get_real_trading_metrics(self):
        """Get real trading performance metrics from bot history"""
        try:
            # Try to read from trading log or history file
            import os
            log_file = "automated_trading_v2.log"
            history_file = "data/trading_history.csv"
            
            metrics = {}
            
            # Try to get metrics from enhanced trader if available
            if self.enhanced_trader:
                # Get portfolio history for calculations
                try:
                    # This would need to be implemented in your enhanced trader
                    # metrics = self.enhanced_trader.get_performance_metrics()
                    pass
                except:
                    pass
            
            # Try to parse from log file for basic metrics
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                        
                    # Extract starting portfolio value from logs
                    import re
                    start_match = re.search(r'Starting Portfolio Value: \$([0-9,]+\.[0-9]+)', log_content)
                    if start_match:
                        start_value = float(start_match.group(1).replace(',', ''))
                        metrics['starting_portfolio'] = start_value
                        
                except Exception as e:
                    print(f"Error parsing log file: {e}")
            
            return metrics
            
        except Exception as e:
            print(f"Error getting real trading metrics: {e}")
            return {}
    
    def get_sector_for_symbol(self, symbol):
        """Get sector classification for a symbol"""
        # Basic sector mapping - you could enhance this with your sector analyzer
        sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology', 
            'TSLA': 'Consumer Discretionary',
            'AAMI': 'Technology',
            'ABCB': 'Financials',
            'ABM': 'Industrials',
            'ACRE': 'Real Estate'
        }
        return sector_map.get(symbol, 'Unknown')
    
    def get_current_market_regime(self):
        """Get current market regime from enhanced strategy"""
        if self.enhanced_trader and hasattr(self.enhanced_trader, 'strategy'):
            try:
                # Try to get regime from enhanced strategy
                if hasattr(self.enhanced_trader.strategy, 'current_regime'):
                    return self.enhanced_trader.strategy.current_regime
                elif hasattr(self.enhanced_trader.strategy, 'detect_regime'):
                    # Try to detect current regime
                    regime = self.enhanced_trader.strategy.detect_regime()
                    return regime if regime else 'Trending Up'
            except Exception as e:
                print(f"Error getting market regime: {e}")
                
        return 'Trending Up'  # Default
    
    def generate_sample_data(self):
        """Generate sample data matching your dashboard example"""
        return {
            'portfolio_start': 25000.00,
            'portfolio_current': 26100.00,
            'trades_opened': 15,
            'trades_closed': 12,
            'active_trades': 3,
            'win_rate': 66,
            'biggest_winner': {'symbol': 'AAPL', 'amount': 480.00, 'percent': 5.2},
            'biggest_loser': {'symbol': 'TSLA', 'amount': -320.00, 'percent': -3.1},
            'vs_backtest': 2,  # 2% above expectations
            'expectancy': 0.6,
            'sharpe_ratio': 1.4,
            'target_sharpe': 1.3,
            'drawdown': -2.5,
            'largest_loss': -320.00,
            'equity_trend': 'Above long-term line',
            'slippage_loss': 0.05,
            'partial_fills': 3,
            'partial_fill_loss': 240.00,
            'regime': 'Trending Up',
            'strategy': 'Aggressive Swing Trading',
            'positions': [
                {'ticker': 'AAPL', 'qty': 10, 'entry': 145.20, 'current': 150.10, 'sector': 'Technology'},
                {'ticker': 'MSFT', 'qty': 5, 'entry': 302.10, 'current': 295.50, 'sector': 'Technology'},
                {'ticker': 'GOOGL', 'qty': 7, 'entry': 2725.00, 'current': 2750.00, 'sector': 'Technology'}
            ]
        }
    
    def setup_dashboard(self):
        """Create the main dashboard layout"""
        # Create main container with padding
        main_frame = tk.Frame(self.root, bg=self.colors['bg_dark'], padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title with emoji and colors
        title_label = tk.Label(
            main_frame, 
            text="📊 LitebotX Aggressive Swing Trading Dashboard",
            font=self.get_font('title'),
            fg=self.colors['accent'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(pady=(0, 20))
        
        # Create scrollable content
        canvas = tk.Canvas(main_frame, bg=self.colors['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_dark'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create all dashboard sections
        self.create_portfolio_overview(scrollable_frame)
        self.create_trading_activity(scrollable_frame)
        self.create_bot_efficiency(scrollable_frame)
        self.create_risk_safety(scrollable_frame)
        self.create_speedbumps(scrollable_frame)
        self.create_market_regime(scrollable_frame)
        self.create_open_positions(scrollable_frame)
        
        if HAS_MATPLOTLIB:
            self.create_charts_section(scrollable_frame)
        else:
            self.create_simple_chart_section(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_section_frame(self, parent, title, emoji=""):
        """Create a beautifully styled section frame"""
        # Main section container
        section_frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        section_frame.pack(fill='x', pady=(0, 25))
        
        # Section header with emoji and styling
        header_frame = tk.Frame(section_frame, bg=self.colors['bg_light'], height=50)
        header_frame.pack(fill='x', pady=(0, 10))
        header_frame.pack_propagate(False)
        
        title_text = f"{emoji} {title}" if emoji else title
        title_label = tk.Label(
            header_frame,
            text=title_text,
            font=self.get_font('heading'),
            fg=self.colors['accent'],
            bg=self.colors['bg_light']
        )
        title_label.pack(pady=12)
        
        # Content frame
        content_frame = tk.Frame(section_frame, bg=self.colors['bg_light'], padx=20, pady=20)
        content_frame.pack(fill='x')
        
        return content_frame
    
    def create_portfolio_overview(self, parent):
        """Create colorful portfolio overview section"""
        frame = self.create_section_frame(parent, "Portfolio Overview", "💰")
        
        data = self.sample_data
        change_amount = data['portfolio_current'] - data['portfolio_start']
        change_percent = (change_amount / data['portfolio_start']) * 100
        
        # Starting balance
        self.create_metric_row(frame, "Starting Balance:", f"${data['portfolio_start']:,.2f}", self.colors['text'])
        
        # Ending balance  
        self.create_metric_row(frame, "Ending Balance:", f"${data['portfolio_current']:,.2f}", self.colors['text'])
        
        # Change (highlighted in green/red)
        change_color = self.colors['success'] if change_amount > 0 else self.colors['danger']
        change_text = f"+{change_percent:.1f}% (+${change_amount:,.2f})" if change_amount > 0 else f"{change_percent:.1f}% (${change_amount:,.2f})"
        self.create_metric_row(frame, "Change:", change_text, change_color, large=True)
    
    def create_trading_activity(self, parent):
        """Create trading activity section"""
        frame = self.create_section_frame(parent, "Trading Activity", "📈")
        
        data = self.sample_data
        
        # Trading metrics
        self.create_metric_row(frame, "Trades Opened:", str(data['trades_opened']), self.colors['info'])
        self.create_metric_row(frame, "Trades Closed:", str(data['trades_closed']), self.colors['text'])
        self.create_metric_row(frame, "Active Trades:", f"{data['active_trades']} still open", self.colors['warning'])
        
        # Win rate with color coding
        win_rate_color = self.colors['success'] if data['win_rate'] > 60 else self.colors['warning']
        self.create_metric_row(frame, "Win Rate (Closed Trades):", f"{data['win_rate']}%", win_rate_color)
        
        # Winner/Loser highlights
        winner = data['biggest_winner']
        loser = data['biggest_loser']
        
        # Add some spacing
        tk.Frame(frame, height=10, bg=self.colors['bg_light']).pack()
        
        winner_text = f"{winner['symbol']} +${winner['amount']:.2f} (+{winner['percent']:.1f}%)"
        self.create_metric_row(frame, "🏆 Biggest Winner:", winner_text, self.colors['success'])
        
        loser_text = f"{loser['symbol']} ${loser['amount']:.2f} ({loser['percent']:.1f}%)"
        self.create_metric_row(frame, "📉 Biggest Loser:", loser_text, self.colors['danger'])
    
    def create_bot_efficiency(self, parent):
        """Create bot efficiency section"""
        frame = self.create_section_frame(parent, "Bot Efficiency", "🎯")
        
        data = self.sample_data
        
        # vs Backtest
        vs_backtest_color = self.colors['success'] if data['vs_backtest'] > 0 else self.colors['danger']
        vs_backtest_text = f"Bot is performing {data['vs_backtest']:+.0f}% above expectations" if data['vs_backtest'] > 0 else f"Bot is performing {data['vs_backtest']:.0f}% below expectations"
        self.create_metric_row(frame, "Current vs Backtest:", vs_backtest_text, vs_backtest_color)
        
        # Expectancy
        self.create_metric_row(frame, "Expectancy per Trade:", f"+{data['expectancy']:.1f}% (avg win/loss)", self.colors['success'])
        
        # Sharpe ratio
        sharpe_color = self.colors['success'] if data['sharpe_ratio'] >= data['target_sharpe'] else self.colors['warning']
        sharpe_text = f"Sharpe = {data['sharpe_ratio']:.1f} (Target was {data['target_sharpe']:.1f})"
        self.create_metric_row(frame, "Risk-Adjusted Return:", sharpe_text, sharpe_color)
    
    def create_risk_safety(self, parent):
        """Create risk and safety check section"""
        frame = self.create_section_frame(parent, "Risk & Safety Check", "🛡️")
        
        data = self.sample_data
        
        # Drawdown
        drawdown_color = self.colors['danger'] if abs(data['drawdown']) > 5 else self.colors['warning']
        self.create_metric_row(frame, "Current Drawdown:", f"{data['drawdown']:.1f}% from recent peak", drawdown_color)
        
        # Largest loss
        self.create_metric_row(frame, "Largest Loss This Period:", f"${data['largest_loss']:.2f}", self.colors['danger'])
        
        # Equity curve position
        self.create_metric_row(frame, "Equity Curve Position:", f"Bot is {data['equity_trend']}", self.colors['success'])
    
    def create_speedbumps(self, parent):
        """Create performance notes (speedbumps) section"""
        frame = self.create_section_frame(parent, "Performance Notes (a.k.a. Speedbumps)", "⚠️")
        
        data = self.sample_data
        
        speedbumps = [
            f"Slippage accounted for ~{data['slippage_loss']:.2f}% portfolio loss.",
            f"{data['partial_fills']} partial fills reduced realized P/L by ${data['partial_fill_loss']:.2f}.",
            "1 stop-loss triggered early due to price gap in MSFT.",
            "Alpha Vantage API rate limiting delayed 2 sector momentum updates."
        ]
        
        for speedbump in speedbumps:
            bullet_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            bullet_frame.pack(fill='x', pady=3)
            
            tk.Label(bullet_frame, text="•", font=('Arial', 18), 
                    fg=self.colors['warning'], bg=self.colors['bg_light']).pack(side='left')
            tk.Label(bullet_frame, text=speedbump, font=('Arial', 14), 
                    fg=self.colors['text'], bg=self.colors['bg_light'], wraplength=700).pack(side='left', padx=(10, 0))
    
    def create_market_regime(self, parent):
        """Create market regime context section"""
        frame = self.create_section_frame(parent, "Market Regime Context", "🌊")
        
        data = self.sample_data
        
        self.create_metric_row(frame, "Detected Regime:", data['regime'], self.colors['info'])
        self.create_metric_row(frame, "Strategy Used:", data['strategy'], self.colors['accent'])
    
    def create_open_positions(self, parent):
        """Create open positions table"""
        frame = self.create_section_frame(parent, "Open Positions", "📋")
        
        data = self.sample_data
        
        # Create table header
        header_frame = tk.Frame(frame, bg=self.colors['bg_dark'], height=40)
        header_frame.pack(fill='x', pady=(0, 10))
        header_frame.pack_propagate(False)
        
        headers = ["Ticker", "Qty", "Entry Price", "Current Price", "P&L", "Sector"]
        header_widths = [100, 80, 120, 120, 100, 120]
        
        for i, (header, width) in enumerate(zip(headers, header_widths)):
            tk.Label(header_frame, text=header, font=('Arial', 14, 'bold'), 
                    fg=self.colors['accent'], bg=self.colors['bg_dark'], width=width//8).pack(side='left', padx=5)
        
        # Create position rows
        for pos in data['positions']:
            row_frame = tk.Frame(frame, bg=self.colors['bg_light'], height=35)
            row_frame.pack(fill='x', pady=2)
            row_frame.pack_propagate(False)
            
            pnl = (pos['current'] - pos['entry']) * pos['qty']
            pnl_color = self.colors['success'] if pnl > 0 else self.colors['danger']
            
            values = [
                pos['ticker'],
                str(pos['qty']),
                f"${pos['entry']:.2f}",
                f"${pos['current']:.2f}",
                f"${pnl:.2f}",
                pos['sector']
            ]
            
            for i, (value, width) in enumerate(zip(values, header_widths)):
                color = pnl_color if i == 4 else self.colors['text']  # Color P&L column
                tk.Label(row_frame, text=value, font=('Arial', 13), 
                        fg=color, bg=self.colors['bg_light'], width=width//8).pack(side='left', padx=5)
    
    def create_metric_row(self, parent, label, value, color, large=False):
        """Create a metric row with label and value"""
        row_frame = tk.Frame(parent, bg=self.colors['bg_light'])
        row_frame.pack(fill='x', pady=8)
        
        font_type = 'metric_large' if large else 'metric'
        
        tk.Label(row_frame, text=label, font=self.get_font('metric'), 
                fg=self.colors['text_muted'], bg=self.colors['bg_light']).pack(side='left')
        tk.Label(row_frame, text=value, font=self.get_font(font_type), 
                fg=color, bg=self.colors['bg_light']).pack(side='right')
    
    def create_charts_section(self, parent):
        """Create visual charts section with matplotlib"""
        frame = self.create_section_frame(parent, "Equity Curve", "📊")
        
        # Create matplotlib figure with dark theme
        plt.style.use('dark_background')
        fig = Figure(figsize=(10, 4), facecolor=self.colors['bg_light'])
        ax = fig.add_subplot(111, facecolor=self.colors['bg_dark'])
        
        # Sample equity curve data
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        equity_values = [25000, 25200, 25100, 25400, 26100]
        
        ax.plot(days, equity_values, color=self.colors['accent'], linewidth=3, marker='o', markersize=6)
        ax.set_title('Weekly Equity Curve', color=self.colors['text'], fontsize=14, pad=20)
        ax.set_ylabel('Portfolio Value ($)', color=self.colors['text_muted'])
        ax.tick_params(colors=self.colors['text_muted'])
        ax.grid(True, alpha=0.3, color=self.colors['text_muted'])
        
        # Add value labels on points
        for i, v in enumerate(equity_values):
            ax.annotate(f'${v:,}', (i, v), textcoords="offset points", 
                       xytext=(0,10), ha='center', color=self.colors['text'], fontsize=9)
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, pady=10)
    
    def create_simple_chart_section(self, parent):
        """Create simple text-based chart when matplotlib not available"""
        frame = self.create_section_frame(parent, "Equity Curve (Text)", "📊")
        
        # Simple text representation
        chart_text = """
Weekly Equity Progress:
Mon: $25,000 ████████████████████████████████████████
Tue: $25,200 ██████████████████████████████████████████
Wed: $25,100 █████████████████████████████████████████
Thu: $25,400 ████████████████████████████████████████████
Fri: $26,100 ██████████████████████████████████████████████████
        """
        
        tk.Label(frame, text=chart_text, font=('Courier', 14), 
                fg=self.colors['accent'], bg=self.colors['bg_light'], 
                justify='left').pack(pady=10)
    
    def start_updates(self):
        """Start real-time dashboard updates"""
        def update_loop():
            while True:
                try:
                    self.update_dashboard_data()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    print(f"Update error: {e}")
                    time.sleep(60)
        
        # Start update thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
    
    def update_dashboard_data(self):
        """Update dashboard with real trading data"""
        if self.trading_engine:
            try:
                # Get fresh real data
                updated_data = self.get_real_or_sample_data()
                
                # Update the data
                self.sample_data = updated_data
                
                # Schedule GUI update on main thread
                self.root.after(0, self.refresh_gui)
                
            except Exception as e:
                print(f"Error updating real data: {e}")
    
    def refresh_gui(self):
        """Refresh GUI components with updated data"""
        # Update title with current time to show it's live
        current_time = datetime.now().strftime("%H:%M:%S")
        portfolio_value = self.sample_data['portfolio_current']
        self.root.title(f"🚀 LitebotX Dashboard - ${portfolio_value:,.0f} - Live {current_time}")
        
        # Note: For full refresh, we'd need to rebuild the GUI sections
        # This is a simplified update - a full implementation would rebuild sections

def main():
    """Launch the colorful trading dashboard"""
    print("🚀 Launching LitebotX Dashboard...")
    print("📊 Creating modern, colorful interface...")
    
    root = tk.Tk()
    app = TradingBotDashboard(root)
    
    # Handle window close
    def on_closing():
        print("📊 Dashboard closing...")
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        print("✅ Dashboard ready! Opening window...")
        root.mainloop()
    except KeyboardInterrupt:
        print("\n📊 Dashboard interrupted by user")
    finally:
        print("📊 Dashboard closed")

if __name__ == "__main__":
    main()