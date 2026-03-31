#!/usr/bin/env python3
"""
Analyze actual per-trade and weekly return rates from backtest results
"""

# Top 5 strategies out-of-sample (2020-2024)
strategies = [
    {
        "name": "Hybrid: Reversion Entry/Momentum Exit",
        "total_return": 4.00,  # %
        "trades": 235,
        "win_rate": 0.481,
        "avg_win": 8.29,  # %
        "avg_loss": -4.39,  # %
        "years": 5
    },
    {
        "name": "Swing High Breakout",
        "total_return": 3.96,
        "trades": 584,
        "win_rate": 0.414,
        "avg_win": 8.66,
        "avg_loss": -4.97,
        "years": 5
    },
    {
        "name": "Double Bottom Reversion",
        "total_return": 3.17,
        "trades": 289,
        "win_rate": 0.457,
        "avg_win": 7.59,
        "avg_loss": -4.36,
        "years": 5
    },
    {
        "name": "Gap & Go",
        "total_return": 2.78,
        "trades": 445,
        "win_rate": 0.452,
        "avg_win": 6.17,
        "avg_loss": -3.94,
        "years": 5
    },
    {
        "name": "Mean Reversion RSI(30)",
        "total_return": 2.62,
        "trades": 240,
        "win_rate": 0.562,
        "avg_win": 5.97,
        "avg_loss": -5.18,
        "years": 5
    }
]

print("="*80)
print("ACTUAL TRADING FREQUENCY & RETURNS ANALYSIS")
print("="*80)
print()

for s in strategies:
    print(f"\n{s['name']}")
    print("-" * 60)
    
    # Calculate metrics
    trading_weeks = s['years'] * 52  # 260 weeks
    trades_per_week = s['trades'] / trading_weeks
    
    # Average return per trade
    avg_return_per_trade = s['total_return'] / s['trades']
    
    # Weekly return (if trading every week)
    weekly_return = avg_return_per_trade * trades_per_week
    
    # Expected value per trade
    expected_value = (s['win_rate'] * s['avg_win']) + ((1 - s['win_rate']) * s['avg_loss'])
    
    # Annualized return
    annual_return = s['total_return'] / s['years']
    
    print(f"  Total Trades: {s['trades']} over {s['years']} years")
    print(f"  Frequency: {trades_per_week:.2f} trades/week ({s['trades']/s['years']/12:.1f} trades/month)")
    print(f"  Avg Return Per Trade: {avg_return_per_trade:+.3f}%")
    print(f"  Expected Value/Trade: {expected_value:+.2f}%")
    print(f"  Weekly Return Rate: {weekly_return:+.3f}%")
    print(f"  Annual Return: {annual_return:+.2f}%")
    print()
    print(f"  🎯 If trading 1 position/week: {weekly_return:+.3f}% per week")
    print(f"  🎯 If trading 5 positions/week: {weekly_return*5:+.2f}% per week")

print("\n" + "="*80)
print("KEY INSIGHTS")
print("="*80)
print()
print("❌ PROBLEM: All strategies have LOW trade frequency")
print("   - Hybrid: 0.90 trades/week (less than 1 trade per week!)")
print("   - Gap & Go: 1.71 trades/week")
print("   - Swing High: 2.25 trades/week")
print()
print("❌ WEEKLY RETURNS are VERY LOW:")
print("   - Hybrid: +0.015% per week (that's 1.5 basis points!)")
print("   - Best case (5 positions): +0.077% per week")
print()
print("💡 FOR WEEKLY TRADING STRATEGY:")
print("   - Need 5-10+ signals per week minimum")
print("   - Need 0.5-1.0% avg return per trade")
print("   - Current strategies are TOO SLOW for weekly operation")
print()
print("🎯 SOLUTION OPTIONS:")
print("   1. Switch to DAILY trading (higher frequency)")
print("   2. Trade LARGER universe (more mid-caps = more opportunities)")
print("   3. Use MULTIPLE strategies simultaneously")
print("   4. Accept LOWER frequency (monthly instead of weekly)")

