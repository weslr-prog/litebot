# 📈 **STOCK TRADING DASHBOARD - DETAILED CREATION PROMPT**

## 🎯 **OVERVIEW**
Create a professional stock trading dashboard with dark mode styling, similar to the crypto dashboard but optimized for stock market trading. The dashboard should be built using Python Dash/Plotly with real-time monitoring capabilities.

---

## 🎨 **DESIGN REQUIREMENTS**

### **Dark Theme Color Palette:**
```python
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
```

### **Layout Structure:**
1. **Header**: "📈 Stock Trading Dashboard" with green primary color
2. **Portfolio Management Section**: Account value, strategy selection
3. **Tabbed Interface**: 5 main tabs (see below)
4. **Responsive Cards**: 3-column grid layout
5. **Real-time Charts**: Plotly graphs with dark theme

---

## 📊 **TAB STRUCTURE**

### **Tab 1: 📊 Portfolio Overview**
**Content:**
- **3 Main Cards:**
  1. **Stock Portfolio Card**: Account balance, daily P&L, account type (Cash/Margin)
  2. **Trading Stats Card**: Total trades, win rate, average gain/loss, commission paid
  3. **Risk Metrics Card**: Portfolio beta, max drawdown, current exposure, margin usage

- **Performance Chart**: Line chart showing portfolio value over time
- **Sector Allocation**: Pie chart showing positions by sector
- **Top Holdings**: Table of largest positions

### **Tab 2: 📈 Live Trading**
**Content:**
- **Active Positions Table**: Symbol, shares, entry price, current price, P&L, % gain/loss
- **Recent Orders**: Order type (market/limit), fill status, execution time
- **Trading Controls**: Start/pause/stop buttons
- **Market Hours**: Display market status (open/closed/pre-market/after-hours)
- **Watchlist**: Symbols being monitored for signals

### **Tab 3: 📊 Performance Analytics**
**Content:**
- **2x2 Chart Grid:**
  1. **Daily Returns Distribution**: Histogram of daily returns
  2. **Cumulative Returns vs S&P 500**: Comparison line chart
  3. **Monthly Performance**: Bar chart by month
  4. **Rolling Sharpe Ratio**: Time series of risk-adjusted returns

### **Tab 4: ⚠️ Risk Management**
**Content:**
- **Risk Metrics Cards:**
  1. **Position Risk**: Individual stock exposure limits
  2. **Portfolio Risk**: Overall portfolio risk (beta, correlation)
  3. **Margin Risk**: Margin usage, buying power, maintenance requirements

- **Risk Charts:**
  - Portfolio heat map by sector exposure
  - Risk vs. return scatter plot
  - Drawdown analysis

### **Tab 5: ⚙️ Settings**
**Content:**
- **Account Settings**: Account type, trading permissions
- **Risk Settings**: Stop loss %, position size limits, max portfolio exposure
- **Data Settings**: Refresh interval, data sources
- **Notification Settings**: Alert preferences

---

## 🔧 **TECHNICAL SPECIFICATIONS**

### **Required Libraries:**
```python
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf  # For stock data
import alpaca_trade_api as tradeapi  # For Alpaca integration
```

### **Data Integration:**
- **Live Data**: Connect to Alpaca API for real-time portfolio data
- **Market Data**: Use yfinance or Alpha Vantage for market data
- **Historical Data**: Load from Alpaca or CSV files
- **Benchmark Data**: S&P 500 data for comparison

### **Key Functions to Implement:**
```python
def load_portfolio_metrics()     # Get account balance, positions, P&L
def load_trading_history()       # Get recent trades and orders
def create_performance_chart()   # Portfolio value over time
def create_sector_allocation()   # Pie chart of sector exposure
def create_positions_table()     # Active positions display
def create_risk_metrics()        # Risk calculations and display
```

---

## 📈 **STOCK-SPECIFIC FEATURES**

### **Portfolio Metrics:**
- Account equity (total value)
- Buying power (available cash + margin)
- Day trading buying power
- Portfolio beta (vs market)
- Sector diversification
- Commission costs

### **Trading Features:**
- **Order Types**: Market, limit, stop-loss, stop-limit
- **Time in Force**: Day, GTC (Good Till Canceled)
- **Position Sizing**: Based on portfolio percentage or dollar amount
- **Paper Trading**: Toggle between live and paper trading

### **Risk Management:**
- **Position Limits**: Max % of portfolio per stock
- **Sector Limits**: Max % per sector
- **Stop Losses**: Automatic or manual stop-loss orders
- **Pattern Day Trader**: PDT rule compliance monitoring

### **Market Integration:**
- **Market Hours**: Display current market status
- **Pre/After Market**: Extended hours trading capability
- **Market Data**: Real-time quotes and fundamentals
- **News Integration**: Recent news for holdings

---

## 🎯 **SPECIFIC STYLING REQUIREMENTS**

### **Cards:**
```python
card_style = {
    'backgroundColor': DARK_THEME['surface'],
    'padding': '20px',
    'margin': '10px',
    'borderRadius': '10px',
    'border': f'2px solid {DARK_THEME["primary"]}',
    'color': DARK_THEME['text']
}
```

### **Tables:**
```python
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
```

### **Charts:**
```python
chart_layout = {
    'paper_bgcolor': DARK_THEME['background'],
    'plot_bgcolor': DARK_THEME['surface'],
    'font': {'color': DARK_THEME['text']},
    'colorway': [DARK_THEME['primary'], DARK_THEME['secondary'], DARK_THEME['accent']]
}
```

---

## 📊 **SAMPLE DATA STRUCTURE**

### **Portfolio Data:**
```python
portfolio_data = {
    'account_value': 50000.00,
    'buying_power': 25000.00,
    'daily_pnl': 250.00,
    'total_pnl': 2500.00,
    'positions': [
        {'symbol': 'AAPL', 'shares': 10, 'avg_cost': 175.50, 'current_price': 178.25},
        {'symbol': 'MSFT', 'shares': 15, 'avg_cost': 420.00, 'current_price': 425.75},
        # ... more positions
    ],
    'orders': [
        {'symbol': 'GOOGL', 'side': 'buy', 'qty': 5, 'price': 141.75, 'status': 'filled'},
        # ... more orders
    ]
}
```

### **Performance Metrics:**
```python
performance_metrics = {
    'total_return': 0.125,      # 12.5% total return
    'daily_return': 0.005,      # 0.5% daily return
    'weekly_return': 0.018,     # 1.8% weekly return
    'monthly_return': 0.042,    # 4.2% monthly return
    'sharpe_ratio': 1.4,
    'max_drawdown': -0.08,      # -8% max drawdown
    'win_rate': 0.72,           # 72% win rate
    'avg_win': 0.032,           # 3.2% average win
    'avg_loss': -0.018,         # -1.8% average loss
    'beta': 1.1                 # Portfolio beta vs S&P 500
}
```

---

## 🚀 **IMPLEMENTATION STEPS**

### **Phase 1: Basic Structure**
1. Set up Dash app with dark theme
2. Create 5-tab layout structure
3. Implement basic portfolio overview
4. Add sample data and charts

### **Phase 2: Data Integration**
1. Connect to Alpaca API
2. Load real portfolio data
3. Implement real-time updates
4. Add market data feeds

### **Phase 3: Advanced Features**
1. Add interactive trading controls
2. Implement risk management
3. Add performance analytics
4. Create notification system

### **Phase 4: Testing & Optimization**
1. Test all features
2. Optimize performance
3. Add error handling
4. Implement logging

---

## 🎯 **DELIVERABLES**

**Main File**: `stock_dashboard.py`
**Additional Files**:
- `stock_api.py` (Alpaca API integration)
- `stock_metrics.py` (Performance calculations)
- `stock_config.py` (Configuration settings)

**Features**:
- ✅ Dark mode interface
- ✅ Real-time portfolio monitoring
- ✅ Performance analytics
- ✅ Risk management
- ✅ Trading controls
- ✅ Market integration
- ✅ Responsive design

---

## 💡 **CUSTOMIZATION NOTES**

- **Colors**: Adjust the DARK_THEME colors to match your preferences
- **Metrics**: Add/remove metrics based on your trading strategy
- **Charts**: Customize chart types and layouts as needed
- **Data Sources**: Can integrate with other brokers (TD Ameritrade, Interactive Brokers, etc.)
- **Features**: Add features like options tracking, dividend monitoring, tax lot management

**This dashboard will provide a professional, dark-themed interface for monitoring your stock trading bot with all the essential metrics and controls needed for effective portfolio management.**
