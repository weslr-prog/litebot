#!/usr/bin/env python3
# Quick reset for daily loss kill switch
import sys
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleConfig, ShortCycleTrader

config = ShortCycleConfig()
trader = ShortCycleTrader(config)
trader.kill_switches["daily_loss_exceeded"] = False
print("✅ Daily loss kill switch reset")
