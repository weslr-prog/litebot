# LiteBotX Unified Trading System

## Quick Start

**Single Command Launch:**
```bash
python3 litebotx_launcher.py
```

## What's Fixed & New

### 🚨 CRITICAL BUGS FIXED:
1. **D+1 Exit Bug Fixed**: System now submits REAL sell orders to Alpaca when positions reach their exit date
2. **Hard-coded Portfolio Values**: All portfolio calculations now use real $963K+ value from Alpaca
3. **Paper Trading Disabled**: System operates in live trading mode only - no paper trading restrictions

### 🎯 New Unified Launcher Features:
- **3 Trading Profiles**: Conservative (10%), Balanced (30%), Aggressive (80% portfolio allocation)
- **Real-time Portfolio Data**: Live $963K+ portfolio value from Alpaca
- **Safety Verification**: Dynamic loss limits based on actual portfolio size
- **Position Tracking**: View current positions with P&L calculations
- **Connection Testing**: Verify Alpaca connection before trading

## Trading Profiles

### 1. Conservative (10% Portfolio)
- Daily Pool: ~$96K (10% of portfolio)
- Max Risk Per Trade: $50
- Max Positions: 3 per day
- Daily Loss Limit: $1.9K (0.2%)
- Confidence Threshold: 30% (high quality signals only)

### 2. Balanced (30% Portfolio) 
- Daily Pool: ~$289K (30% of portfolio)  
- Max Risk Per Trade: $100
- Max Positions: 5 per day
- Daily Loss Limit: $4.8K (0.5%)
- Confidence Threshold: 20% (moderate signals)

### 3. Aggressive (80% Portfolio)
- Daily Pool: ~$770K (80% of portfolio)
- Max Risk Per Trade: $200  
- Max Positions: 8 per day
- Daily Loss Limit: $9.6K (1.0%)
- Confidence Threshold: 10% (accepts lower confidence signals)

## Menu Options

1. **Start Trading**: Choose your risk profile and begin live trading
2. **Portfolio Status**: View current account value and cash
3. **Current Positions**: See active trades with unrealized P&L
4. **Test Connection**: Verify Alpaca API connectivity
5. **View Logs**: Check recent trading activity
6. **Exit**: Stop the system safely

## Key Improvements

✅ **Real Money Trading**: All orders submitted to Alpaca with Order IDs  
✅ **D+1 Exit Strategy**: Automatic next-day exits with real sell orders  
✅ **Dynamic Portfolio**: Uses actual $963K+ account value  
✅ **No Hard-coded Values**: All calculations based on live data  
✅ **Simplified Interface**: One launcher replaces 6+ old files  
✅ **Safety Monitoring**: Dynamic loss limits and kill switches  

## Safety Features

- **Dynamic Loss Limits**: Based on real portfolio percentage
- **Position Size Limits**: Max 2-5% per position depending on profile  
- **Daily Trade Limits**: Max 3-8 positions per day
- **Real-time Monitoring**: Continuous portfolio value updates
- **Exit Confirmations**: Manual approval required for live trading

## Files Cleaned Up

Old launcher files moved to `archive/old_launchers/`:
- `ultra_fixed_launcher.py` (replaced)
- `simple_aggressive_launcher.py` (replaced)
- `extreme_aggressive_launcher.py` (replaced)
- `super_aggressive_launcher.py` (replaced)
- `fixed_aggressive_launcher.py` (replaced)

## Important Notes

⚠️ **LIVE TRADING SYSTEM**: This system trades with real money on Alpaca  
⚠️ **D+1 EXITS**: Positions automatically sell after one trading day  
⚠️ **NO PAPER TRADING**: All modes use live money - no simulation  
⚠️ **RISK MANAGEMENT**: Safety limits active but not guaranteed  

## Support

For issues or questions:
1. Check `unified_trading.log` for detailed logs
2. Use menu option 6 to test Alpaca connection
3. Verify portfolio status with menu option 4

---
**LiteBotX v2.0 - Unified Trading System**  
*Real Money • Real Results • Real Simple*