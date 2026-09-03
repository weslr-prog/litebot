#!/usr/bin/env python3
"""
Demo: Adaptive Risk Management System
Shows how the bot adapts its risk parameters based on performance
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from adaptive_risk_manager import AdaptiveRiskManager
import random

def demo_adaptive_system():
    print("🧠 ADAPTIVE RISK MANAGEMENT DEMONSTRATION")
    print("=" * 60)
    
    # Initialize adaptive risk manager
    arm = AdaptiveRiskManager()
    
    def show_params(title):
        params = arm.get_current_parameters()
        perf = arm.get_performance_summary()
        print(f"\n{title}")
        print(f"Stop Loss: {params.stop_loss_pct:.1%} | Profit Target: {params.profit_target_pct:.1%} | Time Stop: {params.time_stop_days}d")
        if perf['total_trades'] > 0:
            print(f"Performance: {perf['total_trades']} trades, {perf['win_rate']:.1%} win rate, ${perf['avg_trade_pnl']:.2f} avg P&L")
    
    show_params("📊 INITIAL PARAMETERS:")
    
    # Scenario 1: High win rate with small gains
    print("\n" + "="*60)
    print("📈 SCENARIO 1: High win rate but small average gains")
    print("Simulating 15 small wins...")
    
    for i in range(15):
        entry = 100 + random.uniform(-3, 3)
        exit = entry * (1 + random.uniform(0.01, 0.03))  # 1-3% wins
        arm.record_trade(f'SMALL_WIN_{i}', entry, exit, 100, '2025-09-01', '2025-09-02', 'profit-target')
    
    show_params("AFTER SMALL WINS - System should increase profit targets:")
    
    # Scenario 2: Add some losses to reduce win rate
    print("\n" + "="*60)
    print("📉 SCENARIO 2: Adding losses to reduce win rate")
    print("Simulating 8 losses...")
    
    for i in range(8):
        entry = 100 + random.uniform(-3, 3)
        exit = entry * (1 + random.uniform(-0.05, -0.02))  # 2-5% losses
        arm.record_trade(f'LOSS_{i}', entry, exit, 100, '2025-09-01', '2025-09-03', 'stop-loss')
    
    show_params("AFTER LOSSES - System should tighten stops:")
    
    # Scenario 3: High volatility trades
    print("\n" + "="*60)
    print("⚡ SCENARIO 3: High volatility period")
    print("Simulating 10 volatile trades...")
    
    for i in range(10):
        entry = 100 + random.uniform(-5, 5)
        # High volatility - big wins or big losses
        if random.random() > 0.5:
            exit = entry * (1 + random.uniform(0.08, 0.15))  # 8-15% wins
            reason = 'profit-target'
        else:
            exit = entry * (1 + random.uniform(-0.08, -0.04))  # 4-8% losses
            reason = 'stop-loss'
        arm.record_trade(f'VOLATILE_{i}', entry, exit, 100, '2025-09-01', '2025-09-04', reason)
    
    show_params("AFTER VOLATILITY - System should adjust for market conditions:")
    
    print("\n" + "="*60)
    print("🎯 FINAL ADAPTIVE SYSTEM STATE:")
    perf = arm.get_performance_summary()
    params = arm.get_current_parameters()
    
    print(f"Total Trades: {perf['total_trades']}")
    print(f"Win Rate: {perf['win_rate']:.1%}")
    print(f"Total P&L: ${perf['total_pnl']:.2f}")
    print(f"Average P&L per Trade: ${perf['avg_trade_pnl']:.2f}")
    print(f"Average Win: ${perf['avg_win']:.2f}")
    print(f"Average Loss: ${perf['avg_loss']:.2f}")
    print()
    print("🎛️ ADAPTED PARAMETERS:")
    print(f"Stop Loss: {params.stop_loss_pct:.1%} (was 3.0%)")
    print(f"Profit Target: {params.profit_target_pct:.1%} (was 6.0%)")
    print(f"Time Stop: {params.time_stop_days} days (was 10 days)")
    
    print("\n✅ The system has learned from", perf['total_trades'], "trades and optimized its parameters!")
    print("   This will improve future profitability by:")
    print("   - Reducing losses through optimized stop-losses")
    print("   - Maximizing gains through adaptive profit targets")
    print("   - Preventing dead capital through smart time stops")

if __name__ == "__main__":
    demo_adaptive_system()
