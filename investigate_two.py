#!/usr/bin/env python3
"""
Investigate why TWO (Two Harbors) didn't generate a signal despite RSI=17.3
"""
import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

symbol = 'TWO'

print("="*80)
print(f"INVESTIGATING: {symbol} (Two Harbors Investment Corp)")
print("="*80)
print()

# Fetch data
end_date = datetime.now()
start_date = end_date - timedelta(days=60)
ticker = yf.Ticker(symbol)
data = ticker.history(start=start_date, end=end_date)

# Calculate RSI
def calculate_rsi(data, window=7):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

current_price = data['Close'].iloc[-1]
sma_20 = data['Close'].rolling(20).mean().iloc[-1]
price_vs_sma_pct = ((current_price - sma_20) / sma_20) * 100
five_day_ago_price = data['Close'].iloc[-5]
five_day_momentum_pct = ((current_price - five_day_ago_price) / five_day_ago_price) * 100
rsi = calculate_rsi(data, window=7).iloc[-1]

# Volume and liquidity
avg_volume_20d = data['Volume'].tail(20).mean()
current_volume = data['Volume'].iloc[-1]
avg_dollar_volume = avg_volume_20d * current_price

print(f"📊 Technical Indicators:")
print(f"   Price: ${current_price:.2f}")
print(f"   RSI(7): {rsi:.1f} {'✅ PASS' if rsi <= 35 else '❌ FAIL'} (need ≤35)")
print(f"   20-day SMA: {price_vs_sma_pct:+.1f}% {'✅ PASS' if price_vs_sma_pct > -6 else '❌ FAIL'} (need >-6%)")
print(f"   5-day momentum: {five_day_momentum_pct:+.1f}% {'✅ PASS' if five_day_momentum_pct > -5 else '❌ FAIL'} (need >-5%)")
print()

print(f"💧 Liquidity:")
print(f"   Avg Volume (20d): {avg_volume_20d:,.0f} shares")
print(f"   Current Volume: {current_volume:,.0f} shares")
print(f"   Avg Dollar Volume: ${avg_dollar_volume:,.0f}")
print(f"   Liquidity Check: {'✅ PASS' if avg_dollar_volume >= 500_000 else '❌ FAIL'} (need ≥$500K)")
print()

# RSI confidence calculation
rsi_entry_threshold = 35
if rsi <= rsi_entry_threshold:
    rsi_confidence = (rsi_entry_threshold - rsi) / 20.0
    volume_surge = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
    volume_bonus = min(volume_surge / 2.0, 0.2) if volume_surge > 1.0 else 0
    mean_reversion_confidence = min(rsi_confidence + volume_bonus, 1.0)
    
    print(f"📈 Confidence Calculation:")
    print(f"   RSI Confidence: {rsi_confidence:.3f}")
    print(f"   Volume Surge: {volume_surge:.2f}x")
    print(f"   Volume Bonus: {volume_bonus:.3f}")
    print(f"   Base Confidence: {mean_reversion_confidence:.3f}")
    print(f"   Confidence Check: {'✅ PASS' if mean_reversion_confidence >= 0.50 else '❌ FAIL'} (need ≥0.50)")
    print()

# Check ticker info for market cap and other details
try:
    info = ticker.info
    market_cap = info.get('marketCap', 0)
    sector = info.get('sector', 'Unknown')
    industry = info.get('industry', 'Unknown')
    
    print(f"📋 Company Info:")
    print(f"   Sector: {sector}")
    print(f"   Industry: {industry}")
    print(f"   Market Cap: ${market_cap:,.0f}")
    print()
except Exception as e:
    print(f"⚠️ Could not fetch company info: {e}")
    print()

# Check if it's a REIT (REITs often have low RSI but are dividend stocks, not mean reversion plays)
if 'Real Estate' in sector or 'REIT' in industry.upper():
    print(f"⚠️ WARNING: {symbol} is a REIT (Real Estate Investment Trust)")
    print(f"   REITs are dividend-focused, not ideal for D+1 mean reversion")
    print(f"   Low RSI may reflect structural issues, not temporary oversold")
    print()

print("="*80)
print("LIKELY REJECTION REASONS:")
print("="*80)

rejection_reasons = []

if rsi > 35:
    rejection_reasons.append(f"❌ RSI too high: {rsi:.1f} > 35")
elif rsi <= 35:
    rsi_confidence = (35 - rsi) / 20.0
    volume_surge = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
    volume_bonus = min(volume_surge / 2.0, 0.2) if volume_surge > 1.0 else 0
    confidence = min(rsi_confidence + volume_bonus, 1.0)
    
    if avg_dollar_volume < 500_000:
        rejection_reasons.append(f"❌ Insufficient liquidity: ${avg_dollar_volume:,.0f} < $500K")
    
    if confidence < 0.50:
        rejection_reasons.append(f"❌ Low confidence: {confidence:.3f} < 0.50")
    
    if not rejection_reasons:
        rejection_reasons.append(f"❓ Unknown - may be earnings blackout or quality screen")

for reason in rejection_reasons:
    print(reason)

print()
print("="*80)
print("RECOMMENDATION:")
print("="*80)
print("Add detailed rejection logging to signal_generator.py to see:")
print("1. Which stocks pass SMA/momentum but fail RSI")
print("2. Which stocks pass RSI but fail confidence threshold")
print("3. Which stocks fail liquidity or earnings checks")
print("4. Summary: X rejected by SMA, Y by momentum, Z by RSI, etc.")
print("="*80)
