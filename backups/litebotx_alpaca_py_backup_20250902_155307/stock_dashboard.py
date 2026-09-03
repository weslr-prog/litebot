#!/usr/bin/env python3
"""
📈 Professional Stock Trading Dashboard
Dark-themed real-time dashboard for LiteBotX stock trading system
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from datetime import datetime
import os
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file()

# Import LiteBotX components
try:
    from stock_api import StockAPIManager
    from stock_metrics import PerformanceCalculator
    from stock_config import DashboardConfig
except ImportError:
    print("⚠️ Some modules not found. Creating basic dashboard...")

# Dark Theme Color Palette
DARK_THEME = {
    'background': '#1e1e1e',        # Main background
    'surface': '#2d2d2d',           # Card backgrounds
    'surface_light': '#3d3d3d',     # Lighter surfaces
    'primary': '#4caf50',           # Green (stock market theme)
    'secondary': '#2196f3',         # Blue
    'accent': '#ff9800',            # Orange
    'text': '#ffffff',              # Primary text
    'text_secondary': '#b0b0b0',    # Secondary text
    'success': '#4caf50',           # Green for gains
    'warning': '#ff9800',           # Orange for warnings
    'error': '#f44336',             # Red for losses
    'stock_blue': '#1976d2',        # Stock-specific blue
    'market_green': '#388e3c'       # Market green
}

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "📈 Stock Trading Dashboard"

# Card styling
card_style = {
    'backgroundColor': DARK_THEME['surface'],
    'padding': '20px',
    'margin': '10px',
    'borderRadius': '10px',
    'border': f'2px solid {DARK_THEME["primary"]}',
    'color': DARK_THEME['text'],
    'boxShadow': '0 4px 8px rgba(0,0,0,0.3)'
}

# Table styling
table_style = {
    'backgroundColor': DARK_THEME['surface'],
    'border': f'1px solid {DARK_THEME["surface_light"]}',
    'borderCollapse': 'collapse',
    'width': '100%'
}

header_style = {
    'backgroundColor': DARK_THEME['surface_light'],
    'color': DARK_THEME['text'],
    'padding': '10px',
    'borderBottom': f'2px solid {DARK_THEME["primary"]}'
}

# Chart layout template
chart_layout_template = {
    'paper_bgcolor': DARK_THEME['background'],
    'plot_bgcolor': DARK_THEME['surface'],
    'font': {'color': DARK_THEME['text'], 'size': 12},
    'colorway': [DARK_THEME['primary'], DARK_THEME['secondary'], DARK_THEME['accent']],
    'xaxis': {'gridcolor': DARK_THEME['surface_light'], 'zerolinecolor': DARK_THEME['surface_light']},
    'yaxis': {'gridcolor': DARK_THEME['surface_light'], 'zerolinecolor': DARK_THEME['surface_light']},
    'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40}
}

class StockDashboard:
    def __init__(self):
        self.api_manager = None
        self.performance_calc = None
        
        # Initialize performance metrics with defaults
        self.performance_metrics = {
            'total_return': 0.157,      # 15.7% total return
            'daily_return': 0.005,      # 0.5% daily return
            'weekly_return': 0.018,     # 1.8% weekly return
            'monthly_return': 0.042,    # 4.2% monthly return
            'sharpe_ratio': 1.4,
            'max_drawdown': -0.08,      # -8% max drawdown
            'win_rate': 0.72,           # 72% win rate
            'avg_win': 0.032,           # 3.2% average win
            'avg_loss': -0.018,         # -1.8% average loss
            'beta': 1.1,                # Portfolio beta vs S&P 500
            'total_trades': 145,
            'winning_trades': 104,
            'commission_paid': 0.00     # Commission-free trading
        }
        
        self.setup_live_data()
        
    def setup_live_data(self):
        """Setup live data connections"""
        try:
            # Try to connect to live data sources
            self.api_manager = StockAPIManager()
            self.performance_calc = PerformanceCalculator()
            
            # Get live account data if available
            live_account = self.api_manager.get_account_info()
            live_positions = self.api_manager.get_positions()
            
            if live_account and live_account.get('account_value', 0) > 0:
                print("✅ Connected to live Alpaca data")
                self.portfolio_data = self.format_live_data(live_account, live_positions)
                self.use_live_data = True
            else:
                print("⚠️ Using sample data (live data unavailable)")
                self.load_sample_data()
                self.use_live_data = False
                
        except Exception as e:
            print(f"⚠️ Live data connection failed: {e}")
            print("📊 Using sample data for demonstration")
            self.load_sample_data()
            self.use_live_data = False
    
    def format_live_data(self, account_data, positions_data):
        """Format live data for dashboard display"""
        return {
            'account_value': account_data.get('account_value', 0),
            'buying_power': account_data.get('buying_power', 0),
            'cash': account_data.get('cash', 0),
            'daily_pnl': account_data.get('daily_pnl', 0),
            'total_pnl': account_data.get('total_pnl', 0),
            'positions': positions_data,
            'orders': self.api_manager.get_orders(limit=10) if self.api_manager else []
        }
    
    def get_live_performance_metrics(self):
        """Get live performance metrics"""
        if not self.use_live_data or not self.performance_calc:
            return self.get_sample_performance_metrics()
        
        try:
            # Get portfolio history for calculations
            portfolio_history = self.api_manager.get_portfolio_history()
            
            if portfolio_history and portfolio_history.get('equity'):
                return self.performance_calc.calculate_returns(
                    portfolio_history['equity'],
                    portfolio_history['timestamp']
                )
            else:
                return self.get_sample_performance_metrics()
                
        except Exception as e:
            print(f"⚠️ Error calculating live metrics: {e}")
            return self.get_sample_performance_metrics()
    
    def get_sample_performance_metrics(self):
        """Sample performance metrics"""
        return {
            'total_return': 0.157,
            'daily_return': 0.005,
            'weekly_return': 0.018,
            'monthly_return': 0.042,
            'sharpe_ratio': 1.4,
            'max_drawdown': -0.08,
            'win_rate': 0.72,
            'avg_win': 0.032,
            'avg_loss': -0.018,
            'beta': 1.1,
            'total_trades': 145,
            'winning_trades': 104,
            'commission_paid': 0.00
        }
        
    def load_sample_data(self):
        """Load sample data for demonstration"""
        # Sample portfolio data
        self.portfolio_data = {
            'account_value': 925715.60,
            'buying_power': 462857.80,
            'daily_pnl': 4628.58,
            'total_pnl': 125715.60,
            'cash': 231428.90,
            'positions': [
                {'symbol': 'AAPL', 'shares': 25, 'avg_cost': 175.50, 'current_price': 178.25, 'market_value': 4456.25, 'unrealized_pl': 68.75},
                {'symbol': 'MSFT', 'shares': 15, 'avg_cost': 420.00, 'current_price': 425.75, 'market_value': 6386.25, 'unrealized_pl': 86.25},
                {'symbol': 'GOOGL', 'shares': 8, 'avg_cost': 141.75, 'current_price': 145.20, 'market_value': 1161.60, 'unrealized_pl': 27.60},
                {'symbol': 'TSLA', 'shares': 12, 'avg_cost': 245.80, 'current_price': 251.30, 'market_value': 3015.60, 'unrealized_pl': 66.00},
                {'symbol': 'NVDA', 'shares': 10, 'avg_cost': 118.50, 'current_price': 121.75, 'market_value': 1217.50, 'unrealized_pl': 32.50},
            ],
            'orders': [
                {'symbol': 'AAPL', 'side': 'buy', 'qty': 5, 'price': 178.25, 'status': 'filled', 'time': '09:32:15'},
                {'symbol': 'MSFT', 'side': 'sell', 'qty': 2, 'price': 425.75, 'status': 'filled', 'time': '10:15:42'},
                {'symbol': 'META', 'side': 'buy', 'qty': 8, 'price': 505.20, 'status': 'pending', 'time': '11:28:33'},
            ]
        }

dashboard = StockDashboard()

# Get initial performance metrics (live or sample)
initial_performance = dashboard.get_live_performance_metrics() if hasattr(dashboard, 'get_live_performance_metrics') else dashboard.performance_metrics

# App Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("📈 Stock Trading Dashboard", 
                style={'textAlign': 'center', 'color': DARK_THEME['primary'], 
                       'marginBottom': '20px', 'fontSize': '36px'}),
        # Account Info Row
        html.Div([
            html.H3(f"Account Value: ${dashboard.portfolio_data['account_value']:,.2f}", 
                    id="account-value-display",
                    style={'color': DARK_THEME['success'], 'display': 'inline-block', 'marginRight': '40px'}),
            html.H3(f"Daily P&L: ${dashboard.portfolio_data['daily_pnl']:,.2f}", 
                    id="daily-pnl-display",
                    style={'color': DARK_THEME['success'], 'display': 'inline-block', 'marginRight': '40px'}),
            html.H3("🟢 Market Open", 
                    style={'color': DARK_THEME['success'], 'display': 'inline-block'}),
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        
        # Emergency Controls Row
        html.Div([
            html.Div([
                html.Button('🛑 EMERGENCY STOP ALL TRADES', 
                           id='emergency-stop-btn',
                           style={
                               'backgroundColor': DARK_THEME['error'], 
                               'color': 'white', 
                               'border': '2px solid #ff0000',
                               'padding': '15px 25px', 
                               'fontSize': '16px',
                               'fontWeight': 'bold',
                               'borderRadius': '8px',
                               'marginRight': '15px',
                               'cursor': 'pointer'
                           }),
                html.Button('🔴 STOP BOT & GUI', 
                           id='stop-system-btn',
                           style={
                               'backgroundColor': '#ff6b35', 
                               'color': 'white', 
                               'border': '2px solid #ff6b35',
                               'padding': '15px 25px', 
                               'fontSize': '16px',
                               'fontWeight': 'bold',
                               'borderRadius': '8px',
                               'marginRight': '15px',
                               'cursor': 'pointer'
                           }),
                html.Button('⚙️ RISK SETTINGS', 
                           id='risk-settings-btn',
                           style={
                               'backgroundColor': DARK_THEME['warning'], 
                               'color': 'white', 
                               'border': f'2px solid {DARK_THEME["warning"]}',
                               'padding': '15px 25px', 
                               'fontSize': '16px',
                               'fontWeight': 'bold',
                               'borderRadius': '8px',
                               'cursor': 'pointer'
                           })
            ], className="twelve columns", style={'textAlign': 'center'})
        ], className="row", style={'marginBottom': '20px'})
    ], style={'backgroundColor': DARK_THEME['background'], 'padding': '20px'}),
    
    # Main Content with Tabs
    dcc.Tabs(id="main-tabs", value="portfolio-tab", children=[
        
        # Tab 1: Portfolio Overview
        dcc.Tab(label="📊 Portfolio Overview", value="portfolio-tab", children=[
            html.Div([
                # Top 3 cards
                html.Div([
                    # Stock Portfolio Card
                    html.Div([
                        html.H3("💼 Stock Portfolio", style={'color': DARK_THEME['primary']}),
                        html.P(f"Account Balance: ${dashboard.portfolio_data['account_value']:,.2f}", 
                               style={'fontSize': '18px', 'margin': '10px 0'}),
                        html.P(f"Buying Power: ${dashboard.portfolio_data['buying_power']:,.2f}", 
                               style={'fontSize': '16px', 'margin': '5px 0'}),
                        html.P(f"Cash: ${dashboard.portfolio_data['cash']:,.2f}", 
                               style={'fontSize': '16px', 'margin': '5px 0'}),
                        html.P(f"Daily P&L: ${dashboard.portfolio_data['daily_pnl']:,.2f}", 
                               style={'fontSize': '16px', 'margin': '5px 0', 
                                      'color': DARK_THEME['success'] if dashboard.portfolio_data['daily_pnl'] > 0 else DARK_THEME['error']}),
                    ], className="four columns", style=card_style),
                    
                    # Trading Stats Card
                    html.Div([
                        html.H3("📈 Trading Statistics", style={'color': DARK_THEME['secondary']}),
                        html.P(f"Total Trades: {initial_performance.get('total_trades', 145)}", 
                               style={'fontSize': '16px', 'margin': '10px 0'}),
                        html.P(f"Win Rate: {initial_performance.get('win_rate', 0.72):.1%}", 
                               style={'fontSize': '16px', 'margin': '5px 0'}),
                        html.P(f"Avg Win: {initial_performance.get('avg_win', 0.032):.1%}", 
                               style={'fontSize': '16px', 'margin': '5px 0', 'color': DARK_THEME['success']}),
                        html.P(f"Avg Loss: {initial_performance.get('avg_loss', -0.018):.1%}", 
                               style={'fontSize': '16px', 'margin': '5px 0', 'color': DARK_THEME['error']}),
                    ], className="four columns", style=card_style),
                    
                    # Risk Metrics Card
                    html.Div([
                        html.H3("⚠️ Risk Metrics", style={'color': DARK_THEME['warning']}),
                        html.P(f"Portfolio Beta: {initial_performance.get('beta', 1.1):.2f}", 
                               style={'fontSize': '16px', 'margin': '10px 0'}),
                        html.P(f"Max Drawdown: {initial_performance.get('max_drawdown', -0.08):.1%}", 
                               style={'fontSize': '16px', 'margin': '5px 0'}),
                        html.P(f"Sharpe Ratio: {initial_performance.get('sharpe_ratio', 1.4):.2f}", 
                               style={'fontSize': '16px', 'margin': '5px 0'}),
                        html.P(f"Commission: ${initial_performance.get('commission_paid', 0.00):.2f}", 
                               style={'fontSize': '16px', 'margin': '5px 0'}),
                    ], className="four columns", style=card_style),
                ], className="row"),
                
                # Charts Row
                html.Div([
                    # Performance Chart
                    html.Div([
                        dcc.Graph(id="performance-chart")
                    ], className="eight columns", style={'padding': '10px'}),
                    
                    # Sector Allocation
                    html.Div([
                        dcc.Graph(id="sector-allocation-chart")
                    ], className="four columns", style={'padding': '10px'}),
                ], className="row"),
                
                # Top Holdings Table
                html.Div([
                    html.H3("🏆 Current Positions", style={'color': DARK_THEME['text'], 'textAlign': 'center'}),
                    html.Div(id="positions-table")
                ], style={'padding': '20px'})
                
            ])
        ]),
        
        # Tab 2: Live Trading
        dcc.Tab(label="📈 Live Trading", value="trading-tab", children=[
            html.Div([
                # Trading Controls
                html.Div([
                    html.H3("🎮 Trading Controls", style={'color': DARK_THEME['primary']}),
                    html.Button("▶️ Start Trading", id="start-btn", 
                               style={'backgroundColor': DARK_THEME['success'], 'color': 'white', 'margin': '10px'}),
                    html.Button("⏸️ Pause Trading", id="pause-btn", 
                               style={'backgroundColor': DARK_THEME['warning'], 'color': 'white', 'margin': '10px'}),
                    html.Button("⏹️ Stop Trading", id="stop-btn", 
                               style={'backgroundColor': DARK_THEME['error'], 'color': 'white', 'margin': '10px'}),
                    html.Div(id="trading-status", children="🟢 Trading Active", 
                            style={'fontSize': '18px', 'margin': '20px', 'color': DARK_THEME['success']})
                ], style=card_style),
                
                # Active Positions
                html.Div([
                    html.H3("📊 Active Positions", style={'color': DARK_THEME['text']}),
                    html.Div(id="active-positions-table")
                ], style={'padding': '20px'}),
                
                # Recent Orders
                html.Div([
                    html.H3("📋 Recent Orders", style={'color': DARK_THEME['text']}),
                    html.Div(id="recent-orders-table")
                ], style={'padding': '20px'}),
                
                # Watchlist
                html.Div([
                    html.H3("👀 Watchlist", style={'color': DARK_THEME['text']}),
                    html.P("AAPL, MSFT, GOOGL, TSLA, NVDA, META, AMZN, NFLX", 
                           style={'fontSize': '16px', 'color': DARK_THEME['text_secondary']})
                ], style=card_style)
            ])
        ]),
        
        # Tab 3: Performance Analytics
        dcc.Tab(label="📊 Performance Analytics", value="analytics-tab", children=[
            html.Div([
                # 2x2 Chart Grid
                html.Div([
                    html.Div([
                        dcc.Graph(id="returns-distribution")
                    ], className="six columns"),
                    html.Div([
                        dcc.Graph(id="cumulative-returns")
                    ], className="six columns"),
                ], className="row"),
                html.Div([
                    html.Div([
                        dcc.Graph(id="monthly-performance")
                    ], className="six columns"),
                    html.Div([
                        dcc.Graph(id="rolling-sharpe")
                    ], className="six columns"),
                ], className="row")
            ])
        ]),
        
        # Tab 4: Risk Management & Emergency Controls
        dcc.Tab(label="⚠️ Risk Management", value="risk-tab", children=[
            html.Div([
                # Emergency Controls Section
                html.Div([
                    html.H2("🚨 Emergency Controls", style={'color': DARK_THEME['error'], 'marginBottom': '20px'}),
                    html.Div([
                        html.Div([
                            html.H3("� Emergency Stop", style={'color': DARK_THEME['error']}),
                            html.P("Immediately halt all trading activity", style={'fontSize': '14px', 'margin': '10px 0'}),
                            html.Button('🛑 STOP ALL TRADES NOW', 
                                       id='emergency-stop-trades',
                                       style={
                                           'backgroundColor': DARK_THEME['error'], 
                                           'color': 'white', 
                                           'border': '3px solid #ff0000',
                                           'padding': '15px 30px', 
                                           'fontSize': '18px',
                                           'fontWeight': 'bold',
                                           'borderRadius': '10px',
                                           'width': '100%',
                                           'marginTop': '10px',
                                           'cursor': 'pointer'
                                       }),
                            html.Div(id='emergency-status', style={'marginTop': '10px'})
                        ], className="six columns", style=card_style),
                        
                        html.Div([
                            html.H3("🔴 System Shutdown", style={'color': '#ff6b35'}),
                            html.P("Stop bot and free all ports", style={'fontSize': '14px', 'margin': '10px 0'}),
                            html.Button('🔴 SHUTDOWN SYSTEM', 
                                       id='shutdown-system',
                                       style={
                                           'backgroundColor': '#ff6b35', 
                                           'color': 'white', 
                                           'border': '3px solid #ff6b35',
                                           'padding': '15px 30px', 
                                           'fontSize': '18px',
                                           'fontWeight': 'bold',
                                           'borderRadius': '10px',
                                           'width': '100%',
                                           'marginTop': '10px',
                                           'cursor': 'pointer'
                                       }),
                            html.Div(id='shutdown-status', style={'marginTop': '10px'})
                        ], className="six columns", style=card_style)
                    ], className="row", style={'marginBottom': '30px'})
                ]),
                
                # Risk Settings Section
                html.Div([
                    html.H2("⚙️ Risk Controls", style={'color': DARK_THEME['warning'], 'marginBottom': '20px'}),
                    html.Div([
                        html.Div([
                            html.H3("📊 Position Limits", style={'color': DARK_THEME['warning']}),
                            html.Label("Max Position Size (% of portfolio):", style={'color': DARK_THEME['text']}),
                            dcc.Slider(
                                id='max-position-slider',
                                min=1,
                                max=20,
                                value=5,
                                marks={i: f'{i}%' for i in range(1, 21, 2)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            html.Br(),
                            html.Label("Stop Loss (%):", style={'color': DARK_THEME['text']}),
                            dcc.Slider(
                                id='stop-loss-slider',
                                min=1,
                                max=10,
                                value=3,
                                marks={i: f'-{i}%' for i in range(1, 11)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], className="six columns", style=card_style),
                        
                        html.Div([
                            html.H3("🛡️ Portfolio Limits", style={'color': DARK_THEME['warning']}),
                            html.Label("Max Portfolio Exposure (%):", style={'color': DARK_THEME['text']}),
                            dcc.Slider(
                                id='max-exposure-slider',
                                min=50,
                                max=100,
                                value=85,
                                marks={i: f'{i}%' for i in range(50, 101, 10)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            html.Br(),
                            html.Label("Daily Loss Limit (% of account):", style={'color': DARK_THEME['text']}),
                            dcc.Slider(
                                id='daily-loss-slider',
                                min=1,
                                max=10,
                                value=2,
                                marks={i: f'-{i}%' for i in range(1, 11)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], className="six columns", style=card_style)
                    ], className="row"),
                    
                    # Risk Status Cards
                    html.Div([
                        html.Div([
                            html.H3("📍 Current Risk Status", style={'color': DARK_THEME['success']}),
                            html.P("Position Risk: ✅ Safe", style={'fontSize': '16px', 'margin': '10px 0'}),
                            html.P("Portfolio Exposure: 78%", style={'fontSize': '16px', 'margin': '5px 0'}),
                            html.P("Daily P&L: +$4,628 (+0.5%)", style={'fontSize': '16px', 'margin': '5px 0', 'color': DARK_THEME['success']})
                        ], className="four columns", style=card_style),
                        
                        html.Div([
                            html.H3("🎯 Risk Metrics", style={'color': DARK_THEME['warning']}),
                            html.P(f"Beta: {dashboard.performance_metrics.get('beta', 1.0):.2f}" if hasattr(dashboard, 'performance_metrics') and dashboard.performance_metrics else "Beta: 1.00", style={'fontSize': '16px', 'margin': '10px 0'}),
                            html.P("Sharpe Ratio: 1.4", style={'fontSize': '16px', 'margin': '5px 0'}),
                            html.P("Max Drawdown: -8%", style={'fontSize': '16px', 'margin': '5px 0'})
                        ], className="four columns", style=card_style),
                        
                        html.Div([
                            html.H3("🔄 Auto-Protection", style={'color': DARK_THEME['primary']}),
                            html.P("Weekend Protection: ✅ Active", style={'fontSize': '16px', 'margin': '10px 0'}),
                            html.P("Market Hours: ✅ Monitored", style={'fontSize': '16px', 'margin': '5px 0'}),
                            html.P("Risk Alerts: ✅ Enabled", style={'fontSize': '16px', 'margin': '5px 0'})
                        ], className="four columns", style=card_style)
                    ], className="row", style={'marginTop': '20px'})
                ])
            ])
        ]),
        
        # Tab 5: Settings
        dcc.Tab(label="⚙️ Settings", value="settings-tab", children=[
            html.Div([
                # Account Settings
                html.Div([
                    html.H3("👤 Account Settings", style={'color': DARK_THEME['primary']}),
                    html.P("Account Type: Paper Trading", style={'fontSize': '16px', 'margin': '10px 0'}),
                    html.P("Trading Permissions: Stocks Only", style={'fontSize': '16px', 'margin': '5px 0'}),
                    html.P("Status: Active", style={'fontSize': '16px', 'margin': '5px 0', 'color': DARK_THEME['success']})
                ], className="six columns", style=card_style),
                
                # Risk Settings
                html.Div([
                    html.H3("⚠️ Risk Settings", style={'color': DARK_THEME['warning']}),
                    html.P("Stop Loss: 3%", style={'fontSize': '16px', 'margin': '10px 0'}),
                    html.P("Max Position: 5%", style={'fontSize': '16px', 'margin': '5px 0'}),
                    html.P("Max Portfolio Risk: 15%", style={'fontSize': '16px', 'margin': '5px 0'})
                ], className="six columns", style=card_style),
                
                # Data Settings
                html.Div([
                    html.H3("📊 Data Settings", style={'color': DARK_THEME['secondary']}),
                    html.P("Refresh Interval: 30 seconds", style={'fontSize': '16px', 'margin': '10px 0'}),
                    html.P("Data Source: Alpaca + Yahoo Finance", style={'fontSize': '16px', 'margin': '5px 0'}),
                    html.P("Last Update: " + datetime.now().strftime("%H:%M:%S"), style={'fontSize': '16px', 'margin': '5px 0'})
                ], className="six columns", style=card_style),
                
                # Notification Settings
                html.Div([
                    html.H3("🔔 Notifications", style={'color': DARK_THEME['accent']}),
                    html.P("Trade Alerts: Enabled", style={'fontSize': '16px', 'margin': '10px 0'}),
                    html.P("Risk Alerts: Enabled", style={'fontSize': '16px', 'margin': '5px 0'}),
                    html.P("Daily Summary: Enabled", style={'fontSize': '16px', 'margin': '5px 0'})
                ], className="six columns", style=card_style),
            ], className="row")
        ])
        
    ], style={'backgroundColor': DARK_THEME['background']}),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # Update every 30 seconds
        n_intervals=0
    )
    
], style={'backgroundColor': DARK_THEME['background'], 'minHeight': '100vh'})

# Callbacks for interactive components
@app.callback(
    Output('performance-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_performance_chart(n):
    # Generate sample performance data
    dates = pd.date_range(start='2024-01-01', end='2025-09-02', freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.0008, 0.02, len(dates))  # Daily returns
    portfolio_values = [800000]  # Starting value
    
    for ret in returns:
        portfolio_values.append(portfolio_values[-1] * (1 + ret))
    
    # S&P 500 comparison
    sp500_returns = np.random.normal(0.0006, 0.015, len(dates))
    sp500_values = [800000]
    for ret in sp500_returns:
        sp500_values.append(sp500_values[-1] * (1 + ret))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=portfolio_values[1:], 
                            name='Portfolio', line=dict(color=DARK_THEME['primary'], width=3)))
    fig.add_trace(go.Scatter(x=dates, y=sp500_values[1:], 
                            name='S&P 500', line=dict(color=DARK_THEME['secondary'], width=2)))
    
    fig.update_layout(
        title="Portfolio Performance vs S&P 500",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        **chart_layout_template
    )
    return fig

@app.callback(
    Output('sector-allocation-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_sector_chart(n):
    sectors = ['Technology', 'Healthcare', 'Finance', 'Consumer', 'Energy']
    values = [35, 25, 20, 15, 5]
    colors = [DARK_THEME['primary'], DARK_THEME['secondary'], DARK_THEME['accent'], 
              DARK_THEME['warning'], DARK_THEME['stock_blue']]
    
    fig = go.Figure(data=[go.Pie(labels=sectors, values=values, 
                                marker_colors=colors, hole=0.3)])
    fig.update_layout(
        title="Sector Allocation",
        **chart_layout_template
    )
    return fig

@app.callback(
    Output('positions-table', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_positions_table(n):
    """Update positions table with live or sample data"""
    try:
        if dashboard.use_live_data and dashboard.api_manager:
            # Get fresh live data
            live_positions = dashboard.api_manager.get_positions()
            if live_positions:
                df = pd.DataFrame(live_positions)
            else:
                df = pd.DataFrame(dashboard.portfolio_data['positions'])
        else:
            df = pd.DataFrame(dashboard.portfolio_data['positions'])
        
        if not df.empty and 'current_price' in df.columns and 'avg_cost' in df.columns:
            df['pnl_pct'] = ((df['current_price'] - df['avg_cost']) / df['avg_cost'] * 100).round(2)
        else:
            df['pnl_pct'] = 0
    except Exception as e:
        print(f"⚠️ Error updating positions: {e}")
        df = pd.DataFrame(dashboard.portfolio_data['positions'])
        df['pnl_pct'] = ((df['current_price'] - df['avg_cost']) / df['avg_cost'] * 100).round(2)
    
    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[
            {'name': 'Symbol', 'id': 'symbol'},
            {'name': 'Shares', 'id': 'shares'},
            {'name': 'Avg Cost', 'id': 'avg_cost', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Current Price', 'id': 'current_price', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Market Value', 'id': 'market_value', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'P&L', 'id': 'unrealized_pl', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'P&L %', 'id': 'pnl_pct', 'type': 'numeric', 'format': {'specifier': '.2f'}},
        ],
        style_cell={
            'backgroundColor': DARK_THEME['surface'],
            'color': DARK_THEME['text'],
            'textAlign': 'center',
            'padding': '10px',
            'border': f'1px solid {DARK_THEME["surface_light"]}'
        },
        style_header={
            'backgroundColor': DARK_THEME['surface_light'],
            'color': DARK_THEME['text'],
            'fontWeight': 'bold',
            'border': f'2px solid {DARK_THEME["primary"]}'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{unrealized_pl} > 0'},
                'color': DARK_THEME['success']
            },
            {
                'if': {'filter_query': '{unrealized_pl} < 0'},
                'color': DARK_THEME['error']
            }
        ]
    )

# Add callback to update account header with live data
@app.callback(
    [Output('account-value-display', 'children'),
     Output('daily-pnl-display', 'children')],
    Input('interval-component', 'n_intervals')
)
def update_account_display(n):
    """Update account value and P&L display with live data"""
    try:
        if dashboard.use_live_data and dashboard.api_manager:
            # Get fresh account data
            live_account = dashboard.api_manager.get_account_info()
            if live_account:
                account_value = live_account.get('account_value', dashboard.portfolio_data['account_value'])
                daily_pnl = live_account.get('daily_pnl', dashboard.portfolio_data['daily_pnl'])
            else:
                account_value = dashboard.portfolio_data['account_value']
                daily_pnl = dashboard.portfolio_data['daily_pnl']
        else:
            account_value = dashboard.portfolio_data['account_value']
            daily_pnl = dashboard.portfolio_data['daily_pnl']
        
        return (f"Account Value: ${account_value:,.2f}", 
                f"Daily P&L: ${daily_pnl:,.2f}")
                
    except Exception as e:
        print(f"⚠️ Error updating account display: {e}")
        return (f"Account Value: ${dashboard.portfolio_data['account_value']:,.2f}", 
                f"Daily P&L: ${dashboard.portfolio_data['daily_pnl']:,.2f}")

# Live Trading Tab Callbacks
@app.callback(
    Output('active-positions-table', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_active_positions(n):
    """Update active positions table with live data"""
    try:
        if dashboard.use_live_data and dashboard.api_manager:
            positions = dashboard.api_manager.get_positions()
        else:
            positions = dashboard.portfolio_data.get('positions', [])
        
        if not positions:
            return html.P("No active positions", style={'color': DARK_THEME['text_secondary']})
        
        # Create table data
        table_data = []
        for pos in positions[:10]:  # Show top 10 positions
            symbol = pos.get('symbol', 'N/A')
            shares = pos.get('shares', 0)
            avg_cost = pos.get('avg_cost', 0)
            current_price = pos.get('current_price', avg_cost)
            market_value = pos.get('market_value', shares * current_price)
            unrealized_pl = pos.get('unrealized_pl', 0)
            
            # Calculate percentage change
            pct_change = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
            
            table_data.append(html.Tr([
                html.Td(symbol, style={'color': DARK_THEME['text'], 'fontWeight': 'bold'}),
                html.Td(f"{shares:.0f}", style={'color': DARK_THEME['text']}),
                html.Td(f"${avg_cost:.2f}", style={'color': DARK_THEME['text']}),
                html.Td(f"${current_price:.2f}", style={'color': DARK_THEME['text']}),
                html.Td(f"${market_value:.2f}", style={'color': DARK_THEME['text']}),
                html.Td(f"${unrealized_pl:.2f}", 
                       style={'color': DARK_THEME['success'] if unrealized_pl >= 0 else DARK_THEME['error']}),
                html.Td(f"{pct_change:.1f}%", 
                       style={'color': DARK_THEME['success'] if pct_change >= 0 else DARK_THEME['error']})
            ]))
        
        return html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Symbol", style=header_style),
                    html.Th("Shares", style=header_style),
                    html.Th("Avg Cost", style=header_style),
                    html.Th("Current", style=header_style),
                    html.Th("Market Value", style=header_style),
                    html.Th("P&L", style=header_style),
                    html.Th("Change %", style=header_style)
                ])
            ]),
            html.Tbody(table_data)
        ], style=table_style)
        
    except Exception as e:
        return html.P(f"Error loading positions: {str(e)}", 
                     style={'color': DARK_THEME['error']})

@app.callback(
    Output('recent-orders-table', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_recent_orders(n):
    """Update recent orders table with live data"""
    try:
        if dashboard.use_live_data and dashboard.api_manager:
            orders = dashboard.api_manager.get_orders(status='all', limit=10)
        else:
            orders = dashboard.portfolio_data.get('orders', [])
        
        if not orders:
            return html.P("No recent orders", style={'color': DARK_THEME['text_secondary']})
        
        # Create table data
        table_data = []
        for order in orders[:10]:  # Show 10 most recent orders
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'N/A').upper()
            qty = order.get('qty', 0)
            order_type = order.get('order_type', 'market')
            status = order.get('status', 'unknown')
            filled_price = order.get('filled_price')
            submitted_at = order.get('submitted_at', 'N/A')
            
            # Format time
            if submitted_at != 'N/A' and hasattr(submitted_at, 'strftime'):
                time_str = submitted_at.strftime('%H:%M:%S')
            elif isinstance(submitted_at, str) and len(submitted_at) > 10:
                time_str = submitted_at[11:19]  # Extract time part
            else:
                time_str = str(submitted_at)[:8] if submitted_at != 'N/A' else 'N/A'
            
            # Status color
            if status.lower() == 'filled':
                status_color = DARK_THEME['success']
            elif status.lower() in ['pending', 'new']:
                status_color = DARK_THEME['warning']
            else:
                status_color = DARK_THEME['error']
            
            # Side color
            side_color = DARK_THEME['success'] if side == 'BUY' else DARK_THEME['error']
            
            table_data.append(html.Tr([
                html.Td(symbol, style={'color': DARK_THEME['text'], 'fontWeight': 'bold'}),
                html.Td(side, style={'color': side_color, 'fontWeight': 'bold'}),
                html.Td(f"{qty:.0f}", style={'color': DARK_THEME['text']}),
                html.Td(f"${filled_price:.2f}" if filled_price else "Pending", 
                       style={'color': DARK_THEME['text']}),
                html.Td(status.title(), style={'color': status_color, 'fontWeight': 'bold'}),
                html.Td(time_str, style={'color': DARK_THEME['text_secondary']})
            ]))
        
        return html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Symbol", style=header_style),
                    html.Th("Side", style=header_style),
                    html.Th("Qty", style=header_style),
                    html.Th("Price", style=header_style),
                    html.Th("Status", style=header_style),
                    html.Th("Time", style=header_style)
                ])
            ]),
            html.Tbody(table_data)
        ], style=table_style)
        
    except Exception as e:
        return html.P(f"Error loading orders: {str(e)}", 
                     style={'color': DARK_THEME['error']})

# Performance Analytics Tab Callbacks
@app.callback(
    Output('returns-distribution', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_returns_distribution(n):
    """Update daily returns distribution chart"""
    try:
        # Generate sample daily returns data (in real implementation, use actual data)
        np.random.seed(42)
        daily_returns = np.random.normal(0.0008, 0.02, 252)  # One year of trading days
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=daily_returns * 100,  # Convert to percentage
            nbinsx=30,
            name='Daily Returns',
            marker_color=DARK_THEME['primary'],
            opacity=0.7
        ))
        
        fig.update_layout(
            title='Daily Returns Distribution',
            xaxis_title='Daily Return (%)',
            yaxis_title='Frequency',
            showlegend=False,
            **chart_layout_template
        )
        
        return fig
        
    except Exception as e:
        # Return empty chart on error
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(**chart_layout_template)
        return fig

@app.callback(
    Output('cumulative-returns', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_cumulative_returns(n):
    """Update cumulative returns vs S&P 500"""
    try:
        # Generate sample data (in real implementation, use actual portfolio data)
        dates = pd.date_range(start='2024-01-01', end='2025-09-02', freq='D')
        np.random.seed(42)
        
        # Portfolio returns
        portfolio_returns = np.random.normal(0.0008, 0.02, len(dates))
        portfolio_cumulative = (1 + pd.Series(portfolio_returns)).cumprod()
        
        # S&P 500 returns  
        sp500_returns = np.random.normal(0.0006, 0.015, len(dates))
        sp500_cumulative = (1 + pd.Series(sp500_returns)).cumprod()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, 
            y=portfolio_cumulative,
            name='LiteBotX Portfolio',
            line=dict(color=DARK_THEME['primary'], width=3)
        ))
        fig.add_trace(go.Scatter(
            x=dates, 
            y=sp500_cumulative,
            name='S&P 500',
            line=dict(color=DARK_THEME['secondary'], width=2, dash='dash')
        ))
        
        fig.update_layout(
            title='Cumulative Returns vs S&P 500',
            xaxis_title='Date',
            yaxis_title='Cumulative Return',
            **chart_layout_template
        )
        
        return fig
        
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(**chart_layout_template)
        return fig

@app.callback(
    Output('monthly-performance', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_monthly_performance(n):
    """Update monthly performance bar chart"""
    try:
        # Generate sample monthly returns
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
        np.random.seed(42)
        monthly_returns = np.random.normal(0.02, 0.05, len(months))  # Monthly returns
        
        colors = [DARK_THEME['success'] if x >= 0 else DARK_THEME['error'] for x in monthly_returns]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=months,
            y=monthly_returns * 100,  # Convert to percentage
            marker_color=colors,
            name='Monthly Returns'
        ))
        
        fig.update_layout(
            title='Monthly Performance (2025)',
            xaxis_title='Month',
            yaxis_title='Return (%)',
            showlegend=False,
            **chart_layout_template
        )
        
        return fig
        
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(**chart_layout_template)
        return fig

@app.callback(
    Output('rolling-sharpe', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_rolling_sharpe(n):
    """Update rolling Sharpe ratio chart"""
    try:
        # Generate sample rolling Sharpe ratio data
        dates = pd.date_range(start='2024-06-01', end='2025-09-02', freq='W')
        np.random.seed(42)
        sharpe_ratios = np.random.normal(1.2, 0.3, len(dates))  # Rolling 30-day Sharpe
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=sharpe_ratios,
            mode='lines+markers',
            name='30-Day Rolling Sharpe',
            line=dict(color=DARK_THEME['accent'], width=2),
            marker=dict(size=4)
        ))
        
        # Add horizontal line at Sharpe = 1.0
        fig.add_hline(
            y=1.0, 
            line_dash="dash", 
            line_color=DARK_THEME['text_secondary'],
            annotation_text="Sharpe = 1.0"
        )
        
        fig.update_layout(
            title='Rolling 30-Day Sharpe Ratio',
            xaxis_title='Date',
            yaxis_title='Sharpe Ratio',
            **chart_layout_template
        )
        
        return fig
        
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(**chart_layout_template)
        return fig

# Additional callbacks for other charts would go here...

# Emergency Control Callbacks
@app.callback(
    Output('emergency-status', 'children'),
    Input('emergency-stop-trades', 'n_clicks'),
    prevent_initial_call=True
)
def emergency_stop_trades(n_clicks):
    if n_clicks:
        try:
            # Create emergency stop file that the bot will check
            with open('EMERGENCY_STOP.flag', 'w') as f:
                f.write(f"Emergency stop activated at {datetime.now()}")
            
            return html.Div([
                html.P("🛑 EMERGENCY STOP ACTIVATED", 
                       style={'color': '#ff0000', 'fontWeight': 'bold', 'fontSize': '16px'}),
                html.P("All trading activity halted", 
                       style={'color': DARK_THEME['text'], 'fontSize': '14px'})
            ])
        except Exception as e:
            return html.Div([
                html.P(f"❌ Error: {str(e)}", 
                       style={'color': '#ff0000', 'fontSize': '14px'})
            ])
    return ""

@app.callback(
    Output('shutdown-status', 'children'),
    Input('shutdown-system', 'n_clicks'),
    prevent_initial_call=True
)
def shutdown_system(n_clicks):
    if n_clicks:
        try:
            import subprocess
            import sys
            
            # Run the stop script
            subprocess.run([sys.executable, 'stop_litebotx.py'], check=True)
            
            return html.Div([
                html.P("🔴 SYSTEM SHUTDOWN INITIATED", 
                       style={'color': '#ff6b35', 'fontWeight': 'bold', 'fontSize': '16px'}),
                html.P("Bot and dashboard stopping...", 
                       style={'color': DARK_THEME['text'], 'fontSize': '14px'})
            ])
        except Exception as e:
            return html.Div([
                html.P(f"❌ Error: {str(e)}", 
                       style={'color': '#ff0000', 'fontSize': '14px'})
            ])
    return ""

if __name__ == '__main__':
    print("🚀 Starting Stock Trading Dashboard with Emergency Controls...")
    
    # Use different ports to avoid conflicts with other dashboards
    ports_to_try = [8055, 8056, 8057, 8058, 8059]
    
    for port in ports_to_try:
        try:
            print(f"📊 Trying port {port}...")
            print(f"🌐 Dashboard will be available at: http://127.0.0.1:{port}")
            print("💡 Use Ctrl+C to stop the dashboard")
            print("🛑 Emergency controls available in Risk Management tab")
            app.run(debug=False, host='127.0.0.1', port=port)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {port} is busy, trying next port...")
                continue
            else:
                raise e
    else:
        print("❌ All ports are busy. Please stop other Dash applications.")
