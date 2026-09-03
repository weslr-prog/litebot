"""
Smart Exit Strategy Manager
Provides intelligent, signal-based exits instead of time-based force exits

Based on analysis of 92 trades showing:
- Winners hold 63.5h on average
- Losers hold 39.5h on average
- Need to exit winners faster, hold losers slightly longer for recovery
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple


class SmartExitManager:
    """Manages intelligent exit decisions based on market conditions"""
    
    def __init__(self, config):
        self.config = config
        
        # Smart exit thresholds (SWING FIX Feb 13, 2026)
        # Analysis of 68 trades showed: 88% of losses exit within 24h due to tight stops
        # and premature RSI exits. Widening stops + removing early RSI exits.
        self.QUICK_PROFIT_TARGET = 0.04  # 4% - raised from 2% (stop cutting winners early)
        self.STANDARD_PROFIT_TARGET = 0.06  # 6% - raised from 4% (let winners develop)
        self.RSI_NORMALIZATION = 80  # Raised from 75 (only exit at true exhaustion)
        self.RSI_QUICK_EXIT = 85  # Raised from 80 (extreme exhaustion only)
        self.TRAILING_STOP_TRIGGER = 0.99  # DISABLED: Backtest proved trailing clips winners at +2.15%
        self.TRAILING_STOP_DISTANCE = 0.99  # DISABLED: Binary model (stop/target/time) R=1.35
        self.MIN_HOLD_HOURS = 48  # CRITICAL FIX: 48h minimum before RSI/signal exits (was 4h)
        self.MAX_HOLD_HOURS = 120  # 5 trading days max hold
        
        # Emergency exit thresholds (Feb 13 SWING FIX)
        # Hard stop widened to 4% to survive normal mid-cap daily swings
        # Mid-caps with ADR > 2% routinely move 2-4% in pullbacks
        self.EMERGENCY_DOLLAR_THRESHOLD = 10.0  # $10 loss minimum for emergency
        self.EMERGENCY_PCT_THRESHOLD = -0.06  # 6% loss for hard stop (was 5%)
        self.EMERGENCY_TIME_PCT = -0.05  # 5% loss time-based exit (was 4%)
        
        # HIGH VOLATILITY STOCK HANDLING (Jan 14, 2026 - Efficiency optimization)
        # These stocks should NOT use RSI-based exits - they need time to run
        # D+3 minimum hold, trailing stops only
        self.HIGH_VOL_STOCKS = getattr(config, 'high_volatility_stocks', (
            'NTLA', 'PL', 'OSCR', 'MRNA', 'PLUG', 'LCID', 'RIVN', 'NIO',
            'MARA', 'RIOT', 'AMC', 'GME'
        ))
        
        # LET WINNERS RUN (Jan 14, 2026)
        # Positions with 3%+ profit switch to trailing stop only mode
        self.LET_WINNERS_RUN_THRESHOLD = getattr(config, 'let_winners_run_threshold', 0.03)
        self.LET_WINNERS_RUN_TRAIL = getattr(config, 'let_winners_run_trail_pct', 0.015)
        self.DISABLE_SMART_EXIT_HIGH_VOL = getattr(config, 'disable_smart_exit_for_high_vol', True)        
        # DYNAMIC TRAILING STOPS (Jan 23, 2026)
        # Bigger gains = wider trails (protects gains while letting winners run)
        self.ENABLE_DYNAMIC_TRAILING = getattr(config, 'enable_dynamic_trailing', True)
        self.DYNAMIC_TRAILING_TIERS = getattr(config, 'dynamic_trailing_tiers', (
            (0.015, 0.010),  # +1.5% gain → 1.0% trail
            (0.05, 0.020),   # +5% gain → 2.0% trail
            (0.10, 0.030),   # +10% gain → 3.0% trail
            (0.15, 0.035),   # +15% gain → 3.5% trail
            (0.20, 0.040),   # +20% gain → 4.0% trail
            (0.30, 0.050),   # +30% gain → 5.0% trail
        ))
        
    def get_dynamic_trail_pct(self, profit_pct: float) -> float:
        """
        Get dynamic trailing stop percentage based on unrealized gain.
        Bigger gains get wider trails to avoid premature exits.
        
        Example: MRNA at +27% would use 4% trail instead of 1%
        """
        if not self.ENABLE_DYNAMIC_TRAILING:
            return self.TRAILING_STOP_DISTANCE  # Default 1%
        
        trail_pct = self.TRAILING_STOP_DISTANCE  # Start with default
        
        for min_gain, trail in self.DYNAMIC_TRAILING_TIERS:
            if profit_pct >= min_gain:
                trail_pct = trail
        
        return trail_pct        
    def should_exit(self, position, current_price: float, rsi: float, 
                   volume_ratio: float, hours_held: float) -> Tuple[bool, str, float]:
        """
        Determine if position should exit based on smart criteria.
        
        WEEKLY SWING STRATEGY (Feb 11, 2026 rewrite):
        - No same-day blocks, no D+1 forced holds
        - Exit based on signals: stop loss, trailing stop, RSI exhaustion, profit target
        - Let winners run 2-5 days, cut losers at -2%
        
        Returns:
            (should_exit, reason, suggested_exit_price)
        """
        from datetime import date, datetime
        import pytz
        
        profit_pct = (current_price - position.entry_price) / position.entry_price
        
        # Calculate dollar P&L
        position_size = getattr(position, 'position_size_shares', 1)
        profit_dollars = (current_price - position.entry_price) * position_size
        
        # === EMERGENCY STOP LOSS (always active) ===
        # SWING FIX Feb 13: Widened from -2% to -4% to survive normal pullbacks
        # Mid-caps routinely pull back 2-3% on Day 2 before continuing
        # Old -2% stop was killing 88% of trades within 24 hours
        if profit_pct <= -0.04:
            return (True, f"STOP LOSS: {profit_pct*100:.1f}% (${profit_dollars:.2f})", current_price)
        
        # === MINIMUM HOLD: Wait 2 hours before any signal-based exit ===
        if hours_held < 2.0 and profit_pct > -0.04:
            return (False, f"Min hold wait ({hours_held:.1f}h)", current_price)
        
        # HIGH VOLATILITY STOCK CHECK
        symbol = getattr(position, 'symbol', '').upper()
        is_high_vol = symbol in self.HIGH_VOL_STOCKS
        
        if is_high_vol and self.DISABLE_SMART_EXIT_HIGH_VOL:
            # HIGH-VOL MODE: Only trailing stop and emergency exits
            if profit_pct <= self.EMERGENCY_PCT_THRESHOLD:
                return (True, f"HIGH-VOL EMERGENCY: Hard stop {profit_pct*100:.1f}%", current_price)
            
            # Dynamic trailing stop for high-vol
            if hasattr(position, 'highest_price') and position.highest_price:
                drawdown_from_high = (current_price - position.highest_price) / position.highest_price
                dynamic_trail = self.get_dynamic_trail_pct(profit_pct)
                if profit_pct >= self.TRAILING_STOP_TRIGGER:
                    if drawdown_from_high <= -dynamic_trail:
                        return (True, f"HIGH-VOL dynamic trailing stop ({dynamic_trail*100:.1f}% trail) from ${position.highest_price:.2f}", current_price)
            
            return (False, f"HIGH-VOL {symbol}: Holding (P&L: {profit_pct*100:+.1f}%)", current_price)
        
        # LET WINNERS RUN CHECK
        if profit_pct >= self.LET_WINNERS_RUN_THRESHOLD:
            if hasattr(position, 'highest_price') and position.highest_price:
                drawdown_from_high = (current_price - position.highest_price) / position.highest_price
                dynamic_trail = self.get_dynamic_trail_pct(profit_pct)
                if drawdown_from_high <= -dynamic_trail:
                    return (True, f"RUNNER dynamic trailing ({dynamic_trail*100:.1f}% trail) locked in {profit_pct*100:.1f}% gain", current_price)
            return (False, f"RUNNER {symbol}: Letting it run (P&L: {profit_pct*100:+.1f}%)", current_price)
        
        # STRATEGY 1: Quick Profit Taking (48+ hours AND 4%+ gain)
        # SWING FIX Feb 13: Raised from 2% to 4%, requires 48h hold minimum
        # Old logic clipped winners at +1.5-2% that would have run to +6-8%
        if hours_held >= self.MIN_HOLD_HOURS and profit_pct >= self.QUICK_PROFIT_TARGET:
            return (True, f"Quick profit {profit_pct*100:.1f}% after {hours_held:.1f}h", current_price)
        
        # STRATEGY 2: RSI Overbought Exit (RSI > 80 with profit, AFTER 48h)
        # SWING FIX Feb 13: Only fires after 48h. RSI exits on Day 1 were #1 loss cause
        # (23 of 42 losses from premature RSI bounce exits)
        if hours_held >= self.MIN_HOLD_HOURS and rsi >= self.RSI_NORMALIZATION:
            if profit_pct > 0.01:  # At least 1% profit (raised from 0.5%)
                return (True, f"RSI overbought {rsi:.0f} with {profit_pct*100:.1f}% profit", current_price)
        
        # STRATEGY 3: RSI Exhaustion Exit (RSI > 85 = extreme exhaustion, AFTER 48h)
        if hours_held >= self.MIN_HOLD_HOURS and rsi >= self.RSI_QUICK_EXIT:
            return (True, f"RSI exhaustion {rsi:.0f} after {hours_held:.1f}h", current_price)
        
        # STRATEGY 4: Standard Profit Target (6%+ gain - immediate)
        # SWING FIX Feb 13: Raised from 4% to 6% to let winners run
        if profit_pct >= self.STANDARD_PROFIT_TARGET:
            return (True, f"Profit target {profit_pct*100:.1f}% hit", current_price)
        
        # STRATEGY 5: Volume Exhaustion Exit (low volume + RSI > 70, AFTER 48h)
        # SWING FIX Feb 13: Raised RSI threshold from 60 to 70, profit from 1% to 2%
        if hours_held >= self.MIN_HOLD_HOURS:
            if volume_ratio < 0.5 and rsi > 70 and profit_pct > 0.02:
                return (True, f"Volume exhaustion ({volume_ratio:.1f}x) at RSI {rsi:.0f}", current_price)
        
        # STRATEGY 6: Time-Based Safety Exit (MAX_HOLD_HOURS = 120h / ~5 days)
        if hours_held >= self.MAX_HOLD_HOURS:
            if profit_pct > 0:
                return (True, f"Max hold {hours_held:.0f}h with {profit_pct*100:.1f}% profit", current_price)
            elif profit_pct > -0.01:
                return (True, f"Max hold {hours_held:.0f}h - breakeven exit", current_price)
            # Deep loss after max hold - force exit to free capital
            return (True, f"Max hold {hours_held:.0f}h - cut loss {profit_pct*100:.1f}%", current_price)
        
        # STRATEGY 7: Stop Loss (4% for swing trades - matches emergency stop)
        # SWING FIX Feb 13: This was -3% but emergency stop at -2% made it unreachable
        # Now both are unified at -4% to survive normal mid-cap pullbacks
        if profit_pct <= -0.04:
            return (True, f"Stop loss {profit_pct*100:.1f}%", current_price)
        
        # STRATEGY 8: Dynamic Trailing Stop (after 3% profit - UNIFIED)
        # SWING FIX Feb 13: Unified trailing activation to 3%, trail 2%
        if hasattr(position, 'highest_price') and position.highest_price:
            drawdown_from_high = (current_price - position.highest_price) / position.highest_price
            if profit_pct >= self.TRAILING_STOP_TRIGGER:  # 3%
                dynamic_trail = self.get_dynamic_trail_pct(profit_pct)
                if drawdown_from_high <= -dynamic_trail:
                    return (True, f"Dynamic trailing stop ({dynamic_trail*100:.1f}% trail) from ${position.highest_price:.2f}", current_price)
        
        # Hold position - no exit signal
        return (False, None, None)
    
    def update_position_high(self, position, current_price: float):
        """Update position's highest price for trailing stop"""
        if not hasattr(position, 'highest_price') or position.highest_price is None:
            position.highest_price = current_price
        elif current_price > position.highest_price:
            position.highest_price = current_price
    
    def get_exit_priority_score(self, position, current_price: float, rsi: float, 
                                hours_held: float) -> float:
        """
        Calculate exit priority score (0-1, higher = more urgent to exit)
        Used for ranking multiple positions when approaching max positions
        """
        score = 0.0
        profit_pct = (current_price - position.entry_price) / position.entry_price
        
        # Profit contribution (0-0.3)
        if profit_pct >= 0.02:
            score += 0.3  # At target
        elif profit_pct >= 0.015:
            score += 0.2  # Near target
        elif profit_pct >= 0.01:
            score += 0.1  # Profitable
        
        # RSI contribution (0-0.3)
        if rsi >= 60:
            score += 0.3  # Strong bounce
        elif rsi >= 55:
            score += 0.2  # Moderate bounce
        elif rsi >= 50:
            score += 0.1  # Normalized
        
        # Time contribution (0-0.2)
        if hours_held >= 24:
            score += 0.2  # Max hold
        elif hours_held >= 20:
            score += 0.15  # Near max
        elif hours_held >= 12:
            score += 0.1  # Mid-hold
        
        # Profit quality (0-0.2)
        if profit_pct > 0 and hours_held < 8:
            score += 0.2  # Quick winner
        elif profit_pct > 0 and hours_held < 16:
            score += 0.1  # Normal winner
        
        return min(score, 1.0)
    
    def get_exit_recommendation(self, position, market_data: pd.DataFrame) -> dict:
        """
        Get comprehensive exit recommendation with reasoning
        
        Returns:
            {
                'should_exit': bool,
                'reason': str,
                'confidence': float,
                'alternative_exits': [...]
            }
        """
        if market_data is None or len(market_data) < 2:
            return {
                'should_exit': False,
                'reason': 'Insufficient data',
                'confidence': 0.0,
                'alternative_exits': []
            }
        
        # Get latest data
        latest = market_data.iloc[-1]
        current_price = latest['close']
        rsi = latest.get('rsi', 50)  # Default to neutral if not available
        volume = latest.get('volume', 0)
        avg_volume = market_data['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calculate hold time
        entry_time = position.entry_timestamp if hasattr(position, 'entry_timestamp') else datetime.now()
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        hours_held = (datetime.now() - entry_time).total_seconds() / 3600
        
        # Get primary exit decision
        should_exit, reason, exit_price = self.should_exit(
            position, current_price, rsi, volume_ratio, hours_held
        )
        
        # Calculate confidence
        profit_pct = (current_price - position.entry_price) / position.entry_price
        confidence = 0.5
        
        if should_exit:
            # Increase confidence based on multiple factors aligning
            if profit_pct >= 0.015:
                confidence += 0.2
            if rsi >= 50:
                confidence += 0.2
            if hours_held >= 20:
                confidence += 0.1
            
            confidence = min(confidence, 1.0)
        
        # Generate alternative exit scenarios
        alternatives = []
        
        # Alternative 1: Wait for higher profit
        if profit_pct > 0 and profit_pct < 0.025 and hours_held < 20:
            alternatives.append({
                'strategy': 'Hold for higher profit',
                'target': 0.025,
                'estimated_time': '4-8h',
                'risk': 'Potential reversal'
            })
        
        # Alternative 2: RSI target exit
        if rsi < 60 and hours_held < 20:
            alternatives.append({
                'strategy': 'Wait for RSI 60+',
                'target': 'RSI normalization',
                'estimated_time': '2-6h',
                'risk': 'May not reach RSI 60'
            })
        
        # Alternative 3: Time-based exit
        if hours_held < 24:
            alternatives.append({
                'strategy': '24h automatic exit',
                'target': 'Max hold time',
                'estimated_time': f'{24-hours_held:.1f}h',
                'risk': 'May miss optimal exit'
            })
        
        return {
            'should_exit': should_exit,
            'reason': reason,
            'exit_price': exit_price,
            'confidence': confidence,
            'current_profit': profit_pct,
            'hours_held': hours_held,
            'rsi': rsi,
            'volume_ratio': volume_ratio,
            'alternative_exits': alternatives,
            'priority_score': self.get_exit_priority_score(position, current_price, rsi, hours_held)
        }
