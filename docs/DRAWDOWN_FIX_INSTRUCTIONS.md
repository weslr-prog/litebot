
DRAWDOWN FIX INTEGRATION INSTRUCTIONS
=======================================

The investigation revealed:
- Win rate: 32.3% (should be >50%)
- Largest loss: $739.88 (should be <$100)
- 16/21 losses via FAST_EXIT (stops not working effectively)

FILES CREATED:
1. risk_override.json - New risk parameter configuration
2. risk_manager_v2.py - Enhanced risk management module

MANUAL INTEGRATION REQUIRED:
-----------------------------

1. Update traders/short_cycle_trader.py:

   In ShortCycleConfig, change:
   
   max_position_size: int = 400  # Down from ~1200
   stop_loss_pct: float = 0.02   # Down from 0.03
   fast_exit_threshold: float = 0.008  # Down from 0.015
   confidence_threshold: float = 0.08  # Up from 0.055
   
2. Add max loss check in _check_exits():

   # After calculating current_pnl
   if abs(current_pnl) > 100:  # $100 max loss
       logger.warning(f"Max loss limit hit: ${current_pnl:.2f}")
       return True, "MAX_LOSS_LIMIT"

3. Implement progressive sizing in _calculate_position_size():

   base_size = min(base_calculation, 400)
   
   # Progressive sizing based on confidence
   if confidence < 0.10:
       return int(base_size * 0.5)
   elif confidence < 0.15:
       return int(base_size * 0.7)
   return base_size

TESTING STEPS:
--------------
1. Run: python test_todays_optimizations.py
2. Review positions: Check that max size is now $400
3. Monitor: Watch for improved win rate over next 10 trades
4. Validate: Ensure no single loss exceeds $100

EXPECTED IMPROVEMENTS:
---------------------
- Max single loss: $100 (was $739)
- Win rate: >45% (was 32.3%)
- Drawdown: <10% (was 24.3%)
- Sharpe ratio: maintained at ~2.4

ROLLBACK IF NEEDED:
-------------------
cd backups/drawdown_fix_[timestamp]
cp * ../../
