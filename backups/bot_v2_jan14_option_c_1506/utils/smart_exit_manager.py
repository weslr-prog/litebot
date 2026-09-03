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
        
        # Smart exit thresholds (optimized for 24h turnaround)
        self.QUICK_PROFIT_TARGET = 0.015  # 1.5% - exit after 4h
        self.STANDARD_PROFIT_TARGET = 0.02  # 2% - standard exit
        self.RSI_NORMALIZATION = 50  # Exit when RSI returns to neutral
        self.RSI_QUICK_EXIT = 55  # Quick exit if RSI > 55 after 4h
        self.TRAILING_STOP_TRIGGER = 0.02  # Activate trailing stop at +2%
        self.TRAILING_STOP_DISTANCE = 0.01  # Trail by 1%
        self.MIN_HOLD_HOURS = 4  # Minimum hold before considering exits
        self.MAX_HOLD_HOURS = 24  # Maximum hold for D+1 overnight strategy
        
        # Emergency exit thresholds (Jan 13, 2026 - more conservative)
        # Only use emergency exits for TRUE emergencies, not small losses
        # A $50 position can easily swing $3-$5 on Friday - don't exit over $0.50
        self.EMERGENCY_DOLLAR_THRESHOLD = 10.0  # $10 loss minimum for emergency
        self.EMERGENCY_PCT_THRESHOLD = -0.05  # 5% loss for hard stop (was 3%)
        self.EMERGENCY_TIME_PCT = -0.04  # 4% loss after 4h for time-based exit (was 2%)
        
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
        
    def should_exit(self, position, current_price: float, rsi: float, 
                   volume_ratio: float, hours_held: float) -> Tuple[bool, str, float]:
        """
        Determine if position should exit based on smart criteria
        
        IMPORTANT: Monday-Thursday reserves same-day exits for TRUE EMERGENCIES ONLY
        - Small profits (1-2%) should wait for D+1 overnight hold
        - Only stop loss and major losses (>1.5%) trigger same-day exit
        - Friday: All exit strategies allowed (intraday trading day)
        
        Returns:
            (should_exit, reason, suggested_exit_price)
        """
        from datetime import date, datetime
        import pytz
        
        profit_pct = (current_price - position.entry_price) / position.entry_price
        
        # Issue 4.3: Calculate dollar P&L for smarter emergency decisions
        position_size = getattr(position, 'position_size_shares', 1)
        profit_dollars = (current_price - position.entry_price) * position_size
        
        # Check if this is a same-day position (entry today)
        today = date.today()
        is_same_day = (position.entry_date == today)
        current_time = datetime.now(pytz.UTC)
        is_friday = current_time.weekday() == 4
        is_mon_thu = current_time.weekday() in [0, 1, 2, 3]  # Mon-Thu
        
        # EMERGENCY EXITS ONLY (Mon-Thu same-day)
        # Issue 4.3: Reserve emergency exits for TRUE emergencies
        # Small losses on small positions should wait for D+1 recovery
        if is_same_day and is_mon_thu:
            
            # CONSERVATIVE APPROACH: Don't waste PDT slots on small losses
            # A $50 position could make $3-$5 on Friday - don't exit over $0.50-$2 loss
            
            # Only consider emergency if loss is significant
            if profit_dollars > -self.EMERGENCY_DOLLAR_THRESHOLD:
                # Loss is small (< $10), hold for D+1 recovery
                return (False, f"✋ Loss ${abs(profit_dollars):.2f} < ${self.EMERGENCY_DOLLAR_THRESHOLD} - hold for D+1", current_price)
            
            # EMERGENCY 1: Absolute Dollar Threshold ($10+ loss)
            # Only trigger if position has been losing for a while (time confirmation)
            if profit_dollars <= -self.EMERGENCY_DOLLAR_THRESHOLD and hours_held >= self.MIN_HOLD_HOURS:
                return (True, f"EMERGENCY: ${abs(profit_dollars):.2f} loss after {hours_held:.1f}h", current_price)
            
            # EMERGENCY 2: Hard Stop (4% - absolute maximum)
            if profit_pct <= self.EMERGENCY_PCT_THRESHOLD:
                return (True, f"EMERGENCY: Hard stop {profit_pct*100:.1f}%", current_price)
            
            # EMERGENCY 3: Time-based major loss (3%+ after 4+ hours = not recovering)
            if hours_held >= self.MIN_HOLD_HOURS and profit_pct <= self.EMERGENCY_TIME_PCT:
                return (True, f"EMERGENCY: {profit_pct*100:.1f}% loss after {hours_held:.1f}h (not recovering)", current_price)
            
            # BLOCK all other exits on same-day Mon-Thu (hold for D+1)
            # Small profits, RSI exits, volume exits should wait for overnight
            return (False, f"✋ Same-day Mon-Thu HOLD for D+1 (P&L: ${profit_dollars:+.2f} / {profit_pct*100:+.1f}%)", current_price)
        
        # FRIDAY or D+1+ positions: ALL EXIT STRATEGIES ALLOWED
        # - Friday same-day: All exits allowed (intraday trading)
        # - D+1 positions: All exits allowed (overnight hold complete)
        # - Weekend prevention: Separate Friday 3:45 PM force exit handles this
        
        # HIGH VOLATILITY STOCK CHECK (Jan 14, 2026)
        # For stocks like NTLA, PL, OSCR - disable RSI-based exits, use trailing only
        symbol = getattr(position, 'symbol', '').upper()
        is_high_vol = symbol in self.HIGH_VOL_STOCKS
        
        if is_high_vol and self.DISABLE_SMART_EXIT_HIGH_VOL:
            # HIGH-VOL MODE: Only trailing stop and emergency exits
            # No RSI exits, no quick profit taking - let these stocks run
            
            # EMERGENCY: Hard stop still applies
            if profit_pct <= self.EMERGENCY_PCT_THRESHOLD:
                return (True, f"HIGH-VOL EMERGENCY: Hard stop {profit_pct*100:.1f}%", current_price)
            
            # TRAILING STOP: The only profit-taking mechanism for high-vol
            if hasattr(position, 'highest_price') and position.highest_price:
                drawdown_from_high = (current_price - position.highest_price) / position.highest_price
                if profit_pct >= self.TRAILING_STOP_TRIGGER:
                    if drawdown_from_high <= -self.TRAILING_STOP_DISTANCE:
                        return (True, f"HIGH-VOL trailing stop from ${position.highest_price:.2f} (drew down {drawdown_from_high*100:.1f}%)", current_price)
            
            # Otherwise HOLD - high-vol needs time to run
            return (False, f"🚀 HIGH-VOL {symbol}: Holding for momentum (P&L: {profit_pct*100:+.1f}%)", current_price)
        
        # LET WINNERS RUN CHECK (Jan 14, 2026)
        # For positions with +3% or more, switch to trailing stop ONLY mode
        if profit_pct >= self.LET_WINNERS_RUN_THRESHOLD:
            # This is a runner - only exit via trailing stop
            if hasattr(position, 'highest_price') and position.highest_price:
                drawdown_from_high = (current_price - position.highest_price) / position.highest_price
                # Use tighter trail for runners
                if drawdown_from_high <= -self.LET_WINNERS_RUN_TRAIL:
                    return (True, f"RUNNER trailing stop from ${position.highest_price:.2f} (locked in {profit_pct*100:.1f}% gain)", current_price)
            # Let it run - no other exits
            return (False, f"🏃 RUNNER {symbol}: Letting it run (P&L: {profit_pct*100:+.1f}%)", current_price)
        
        # STRATEGY 1: Quick Profit Taking (4+ hours, 1.5%+ gain)
        if hours_held >= self.MIN_HOLD_HOURS and profit_pct >= self.QUICK_PROFIT_TARGET:
            return (True, f"Quick profit {profit_pct*100:.1f}% after {hours_held:.1f}h", current_price)
        
        # STRATEGY 2: RSI Normalization Exit (mean reversion complete)
        if hours_held >= self.MIN_HOLD_HOURS and rsi >= self.RSI_NORMALIZATION:
            if profit_pct > 0:
                return (True, f"RSI normalized to {rsi:.0f} with {profit_pct*100:.1f}% profit", current_price)
        
        # STRATEGY 3: RSI Quick Exit (strong bounce after 4h)
        if hours_held >= self.MIN_HOLD_HOURS and rsi >= self.RSI_QUICK_EXIT:
            return (True, f"Strong bounce RSI {rsi:.0f} after {hours_held:.1f}h", current_price)
        
        # STRATEGY 4: Standard Profit Target (2%+ gain)
        if profit_pct >= self.STANDARD_PROFIT_TARGET:
            return (True, f"Profit target {profit_pct*100:.1f}% hit", current_price)
        
        # STRATEGY 5: Volume Exhaustion Exit (low volume + RSI > 45)
        if hours_held >= self.MIN_HOLD_HOURS:
            if volume_ratio < 0.5 and rsi > 45 and profit_pct > 0.005:  # 0.5%+ gain
                return (True, f"Volume exhaustion (0.{volume_ratio:.1f}x) at RSI {rsi:.0f}", current_price)
        
        # STRATEGY 6: Time-Based Safety Exit (24h max hold)
        if hours_held >= self.MAX_HOLD_HOURS:
            if profit_pct > 0:
                return (True, f"24h max hold reached with {profit_pct*100:.1f}% profit", current_price)
            elif profit_pct > -0.01:  # Less than 1% loss
                return (True, f"24h max hold - breakeven exit", current_price)
            # If deep loss, don't force exit yet (allow recovery)
        
        # STRATEGY 7: Stop Loss (4% - wider than before)
        stop_loss_pct = -0.04  # 4% stop
        if profit_pct <= stop_loss_pct:
            return (True, f"Stop loss {profit_pct*100:.1f}%", current_price)
        
        # STRATEGY 8: Trailing Stop (after 2% profit)
        if hasattr(position, 'highest_price') and position.highest_price:
            drawdown_from_high = (current_price - position.highest_price) / position.highest_price
            if profit_pct >= self.TRAILING_STOP_TRIGGER:
                if drawdown_from_high <= -self.TRAILING_STOP_DISTANCE:
                    return (True, f"Trailing stop from ${position.highest_price:.2f} (drew down {drawdown_from_high*100:.1f}%)", current_price)
        
        # STRATEGY 9: Morning Gap Down Protection (D+1 opening gap > 2%)
        if hours_held >= 20 and hours_held <= 25:  # Around D+1 open
            if profit_pct <= -0.02:  # -2% or worse
                # Check if this is a gap down scenario
                return (True, f"D+1 morning gap protection {profit_pct*100:.1f}%", current_price)
        
        # Hold position
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
