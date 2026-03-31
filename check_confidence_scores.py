#!/usr/bin/env python3
"""
Check confidence scores for today's candidates
Shows why stocks with RSI < 35 are still rejected
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.data.data_loader import DataLoader
import pandas as pd

def calculate_confidence(rsi, rsi_threshold=35):
    """Calculate confidence score using bot's formula"""
    if rsi > rsi_threshold:
        return 0.0
    
    rsi_confidence = (rsi_threshold - rsi) / 20.0
    return min(rsi_confidence, 1.0)

# Stocks that passed RSI < 35 filter today
oversold_stocks = [
    ('WEN', 31.9),   # Wendy's
    ('VIPS', 21.8),  # Vipshop (but failed SMA/momentum)
]

print("=" * 80)
print("🔍 CONFIDENCE SCORE ANALYSIS")
print("=" * 80)
print("\nFormula: confidence = (RSI_threshold - current_RSI) / 20.0")
print("Threshold: 50% minimum required")
print("\n" + "=" * 80)

for symbol, rsi in oversold_stocks:
    conf = calculate_confidence(rsi)
    status = "✅ PASS" if conf >= 0.50 else "❌ FAIL"
    
    print(f"\n{symbol}:")
    print(f"  RSI: {rsi:.1f}")
    print(f"  Calculation: (35 - {rsi:.1f}) / 20.0 = {35 - rsi:.1f} / 20.0")
    print(f"  Confidence: {conf:.1%} {status}")

print("\n" + "=" * 80)
print("💡 PROBLEM IDENTIFIED")
print("=" * 80)
print("\nThe confidence formula requires RSI to be MUCH lower than 35:")
print("")
print("  RSI  | Confidence | Status")
print("  -----|------------|-------")
print("  35   | 0%         | ❌ Rejected")
print("  30   | 25%        | ❌ Rejected")
print("  25   | 50%        | ✅ ACCEPTED")
print("  20   | 75%        | ✅ ACCEPTED")
print("  15   | 100%       | ✅ ACCEPTED")
print("")
print("Current filter: RSI < 35")
print("Actual requirement: RSI < 25 (to hit 50% confidence)")
print("")
print("=" * 80)
print("🔧 RECOMMENDATIONS")
print("=" * 80)
print("")
print("Option 1: Lower confidence threshold to 25% (0.25)")
print("  • Allows RSI 30-35 stocks")
print("  • Matches original RSI < 35 filter intent")
print("  • Trades: WEN (31.9) would qualify today")
print("")
print("Option 2: Keep 50% threshold, adjust formula")
print("  • Change divisor from 20 to 10")
print("  • Formula: (35 - RSI) / 10.0")
print("  • RSI 30 = 50% confidence (marginal)")
print("  • RSI 25 = 100% confidence (strong)")
print("")
print("Option 3: Accept mismatch - only trade RSI < 25")
print("  • Keep current settings")
print("  • Wait for deeper selloffs")
print("  • Fewer trades but higher conviction")
print("")
print("=" * 80)
