"""
Configuration module for bot_v2
Extracted from traders/short_cycle_trader.py
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ShortCycleConfig:
    """Configuration for short-cycle trading system"""
    # Portfolio parameters (OPTION 3: Triple Frequency + 60% Win Rate - $1K Portfolio)
    # Jan 13: Reverted to $50 for better diversification (4×$20 stocks > 1×$80 stock for risk)
    portfolio_value: float = None  # Will be fetched from Alpaca account (default: 1000.0 if fetch fails)
    daily_pool_percent: float = 0.30  # 30% Mon-Wed (90% by Wed), 100% Thu-Fri (aggressive finish)
    max_risk_per_trade_dollars: float = 20.0  # Risk per trade for position sizing (2% of $1K)
    max_position_dollars: float = 50.0  # Reverted: $50 for diversification (more smaller positions)
    max_loss_per_trade_dollars: float = 20.0  # Hard stop at $20 per trade (2% of portfolio)
    
    # Market cap filter (mid-cap only)
    min_market_cap: float = 2_000_000_000  # $2B minimum (mid-cap floor)
    max_market_cap: float = 10_000_000_000  # $10B maximum (mid-cap ceiling)
    
    # Position parameters - fewer, higher quality trades (Jan 14, 2026: Efficiency optimization)
    max_positions_per_day: int = 6  # 6 positions × $50 = $300 max daily exposure (quality over quantity)
    max_daily_entries: int = 6  # Cap new entries at 6/day for efficiency (was unlimited)
    min_position_size_dollars: float = 10.0  # Minimum viable position for $1K account
    max_position_size_percent: float = 0.20  # 20% max position size (hard cap at $200 enforced)
    max_universe_size: int = 500  # Maximum number of symbols in trading universe (scaled for 3-strategy stack)
    
    # Diversification parameters
    max_positions_per_symbol_small: int = 2  # Max positions per symbol for portfolios < $100K
    max_positions_per_symbol_large: int = 3  # Max positions per symbol for portfolios > $100K
    max_concentration_percent_small: float = 0.35  # Max 35% of positions in one symbol (small portfolios)
    max_concentration_percent_large: float = 0.40  # Max 40% of positions in one symbol (large portfolios)
    portfolio_threshold_large: float = 100000.0  # Threshold for "large" portfolio diversification rules
    
    # Time parameters (Efficiency-First Strategy - Jan 14, 2026)
    # Analysis showed: D+1 = 50% win rate (+0.37%), D+3+ = 84% win rate (+1.89%)
    max_hold_days: int = 5  # Allow up to 5 days hold (for weekend holds)
    default_hold_days: int = 2  # Default to D+2 hold (was D+1) - 67% win rate vs 50%
    high_vol_hold_days: int = 3  # High-volatility stocks get D+3 minimum hold
    trading_days: List[str] = None  # All trading days (Mon-Fri)
    exit_time: str = "15:45"  # 15 minutes before close - HARD EXIT for all positions
    d_plus_one_force_exit_time: str = "12:00"  # Smart D+1: Exit by noon (9:30-12:00 window for optimal exit)
    d_plus_one_smart_exit_enabled: bool = True  # Enable smart D+1 exits (exit on profit or >1% loss, else wait till noon)
    friday_force_exit_time: str = "15:45"  # Force exit all Friday positions (no weekend holds)
    
    # PDT (Pattern Day Trader) management
    max_emergency_exits_per_week: int = 3  # 3 same-day exits allowed per week
    allow_friday_entries_with_unused_slots: bool = True  # Use unused emergency slots on Friday
    
    # Profit targets (Dual-Strategy System optimized for D+1 overnight holds - Jan 2026)
    profit_target_pct: float = 0.02  # 2% profit target (lowered from 3% for quick exits)
    
    # Risk parameters (Dual-Strategy System: Gap & Go + Fade/Short)
    max_daily_loss_percent: float = 0.08  # 8% daily loss limit
    max_weekly_loss_percent: float = 0.15   # 15% weekly loss limit
    confidence_threshold: float = 0.25  # 25% minimum confidence (Jan 6: lowered from 50% to match RSI<35 filter intent)
    
    # Triple-Strategy Configuration (Jan 13, 2026: Gap & Go + Fade + Momentum)
    # Gap & Go: 830% return / 748 trades = 1.11% per trade
    # Fade/Short: 174% return / 914 trades = 0.19% per trade
    # Momentum: Trend continuation plays for mid-day entries
    # Gap & Go is 5.8x more profitable per trade → allocate most capital
    enable_gap_and_go: bool = True  # Primary strategy: Morning gap entries (70% capital)
    enable_fade_short: bool = True  # Secondary strategy: Overbought reversals (15% capital)
    enable_momentum: bool = True  # Tertiary strategy: Trend continuation (15% capital)
    gap_and_go_allocation: float = 0.70  # 70% to Gap & Go (primary)
    fade_short_allocation: float = 0.15  # 15% to Fade/Short (secondary)
    momentum_allocation: float = 0.15  # 15% to Momentum (tertiary)
    gap_and_go_priority: bool = True  # Gap & Go wins conflicts (same stock, same day)
    
    # Strategy-specific profit/stop targets (Jan 8, 2026: Gap & Go + Fade/Short)
    gap_and_go_profit_target_pct: float = 0.03  # 3% profit target for gap & go (backtest validated)
    gap_and_go_stop_loss_pct: float = 0.02  # 2% stop loss for gap & go
    fade_short_profit_target_pct: float = 0.02  # 2% profit target for fade/short (quick reversals)
    fade_short_stop_loss_pct: float = 0.015  # 1.5% stop loss for fade/short (tight stops)
    momentum_profit_target_pct: float = 0.025  # 2.5% profit target for momentum (ride the trend)
    momentum_stop_loss_pct: float = 0.015  # 1.5% stop loss for momentum
    
    # High-Volatility Stocks - Special Handling (Jan 14, 2026)
    # These stocks have high intraday volatility and benefit from longer holds
    # Disable Smart Exit RSI-based sells, use D+3 minimum, trailing stops only
    high_volatility_stocks: tuple = (
        'NTLA',   # Intellia - CRISPR biotech, 7.73% win observed
        'PL',     # Planet Labs - Space tech, 6.31% win observed  
        'OSCR',   # Oscar Health - Health insurance, high beta
        'MRNA',   # Moderna - Biotech, news-driven
        'PLUG',   # Plug Power - Clean energy, volatile
        'LCID',   # Lucid Motors - EV, high beta
        'RIVN',   # Rivian - EV, volatile
        'NIO',    # NIO - China EV, news-sensitive
        'MARA',   # Marathon Digital - Crypto proxy
        'RIOT',   # Riot Platforms - Crypto proxy
        'AMC',    # AMC - Meme stock, high vol
        'GME',    # GameStop - Meme stock, high vol
    )
    
    # Let Winners Run Configuration (Jan 14, 2026)
    # For positions with +3% or more, switch to trailing stop only
    let_winners_run_threshold: float = 0.03  # 3% profit triggers "let it run" mode
    let_winners_run_trail_pct: float = 0.015  # 1.5% trailing stop for runners
    disable_smart_exit_for_high_vol: bool = True  # No RSI-based exits for high-vol stocks
    
    # Dynamic Trailing Stops (Jan 23, 2026)
    # Bigger gains = wider trail (but still protective)
    # This prevents selling winners too early while locking in gains
    enable_dynamic_trailing: bool = True
    dynamic_trailing_tiers: tuple = (
        # (min_gain%, trail%)
        (0.015, 0.010),  # +1.5% gain → 1.0% trail (default)
        (0.05, 0.020),   # +5% gain → 2.0% trail
        (0.10, 0.030),   # +10% gain → 3.0% trail
        (0.15, 0.035),   # +15% gain → 3.5% trail
        (0.20, 0.040),   # +20% gain → 4.0% trail (MRNA scenario)
        (0.30, 0.050),   # +30% gain → 5.0% trail (big winner protection)
    )
    
    # Weekend Hold Protection (Jan 23, 2026 - UPDATED)
    # Thu/Fri entries hold through Monday - 84% win rate observed
    # Remove force exit for winners, only exit losers
    weekend_hold_enabled: bool = True  # Allow weekend holds
    friday_force_exit_enabled: bool = False  # DISABLED - let trailing stops do the work
    friday_exit_losers_only: bool = True  # Only force exit positions that are losing
    friday_loser_threshold: float = -0.02  # Exit if down more than 2% on Friday EOD
    weekend_early_exit_threshold: float = 0.05  # Only exit early if +5% profit
    
    # Gap & Go parameters
    gap_min_pct: float = 0.02  # Minimum 2% gap
    gap_max_pct: float = 0.08  # Maximum 8% gap (avoid gap-and-crash)
    gap_rsi_max: float = 75.0  # RSI must be < 75 at gap (not too overbought)
    gap_scan_time: str = "09:35"  # Scan for gaps 5 mins after open
    
    # Fade/Short parameters
    fade_rsi_min: float = 70.0  # RSI must be > 70 (overbought)
    fade_extension_min_pct: float = 0.10  # Must be 10%+ above 20-SMA
    fade_scan_start: str = "10:00"  # Start scanning after morning volatility
    fade_scan_end: str = "14:00"  # Stop scanning before close
    
    # Momentum Strategy parameters (Jan 13, 2026 - Trend Continuation)
    # Entry: Price above SMA20, RSI 45-65 (healthy trend, not overbought), ADR > 2%
    # Best for: Stocks with established uptrend, looking for continuation
    momentum_sma_period: int = 20  # SMA for trend confirmation
    momentum_rsi_min: float = 45.0  # RSI floor (not oversold)
    momentum_rsi_max: float = 65.0  # RSI ceiling (not overbought)
    momentum_min_adr_pct: float = 0.02  # Minimum 2% ADR for volatility
    momentum_min_5d_return: float = 0.03  # Must be up 3%+ in last 5 days
    momentum_max_5d_return: float = 0.15  # Not more than 15% (avoid chasing)
    momentum_scan_start: str = "10:30"  # Start after initial volatility settles
    momentum_scan_end: str = "14:30"  # End before close
    
    # Default targets (Nov 28: Updated for 2:1 R:R ratio)
    profit_target_pct: float = 0.04  # 4% default profit target (raised from 3%)
    stop_loss_pct: float = 0.02  # 2% default stop loss (tightened from 3%)
    
    # Trailing Stop Parameters (Optimized Jan 13, 2026 - earlier activation)
    enable_trailing_stops: bool = True  # Enable trailing stop system
    trailing_trigger_pct: float = 0.015  # Activate after +1.5% gain (lowered from 2% to capture more gains)
    trailing_distance_pct: float = 0.01  # Trail by 1.0% (tightened from 1.5%)
    trailing_min_profit_pct: float = 0.005  # Lock in minimum +0.5% profit once activated
    trailing_update_interval_sec: int = 60  # Update trailing stops every 60 seconds
    
    # Late Entry Parameters (Jan 13, 2026: Afternoon scan for additional opportunities)
    enable_late_entry: bool = True  # Enable afternoon entry scans
    late_entry_start_time: str = "13:00"  # Start late entry scan at 1:00 PM
    late_entry_end_time: str = "14:30"  # End late entry scan at 2:30 PM
    late_entry_confidence_multiplier: float = 1.2  # Require 20% higher confidence for late entries
    late_entry_position_size_pct: float = 0.75  # Use 75% of normal position size (reduced risk)
    late_entry_scan_interval_minutes: int = 15  # Scan every 15 minutes during late window
    late_entry_min_adr_pct: float = 0.025  # Require 2.5% ADR for late entries (more volatility needed)
    
    # Backtesting parameters
    enable_forced_d1_exit: bool = True  # ENABLED - D+1 forced exits at 3:45 PM
    model_transaction_costs: bool = True
    commission_per_trade: float = 0.0  # Assume commission-free
    spread_bp: float = 5.0  # 5 basis points spread cost
    
    def __post_init__(self):
        if self.trading_days is None:
            self.trading_days = ["monday", "tuesday", "wednesday", "thursday"]
        
        # Fetch real account equity if not set
        if self.portfolio_value is None:
            self.portfolio_value = self._fetch_account_equity()
        
        # Calculate derived values
        self.daily_pool_dollars = self.portfolio_value * self.daily_pool_percent
        self.max_daily_loss_dollars = self.portfolio_value * self.max_daily_loss_percent
        self.max_weekly_loss_dollars = self.portfolio_value * self.max_weekly_loss_percent
    
    def _fetch_account_equity(self) -> float:
        """Fetch actual account equity from Alpaca"""
        try:
            import os
            from alpaca.trading.client import TradingClient
            
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if not api_key or not api_secret:
                print("⚠️  Alpaca credentials not found, using default $1000")
                return 1000.0
            
            client = TradingClient(api_key, api_secret, paper=True)
            account = client.get_account()
            equity = float(account.equity)
            
            print(f"✅ Fetched account equity: ${equity:,.2f}")
            return equity
            
        except Exception as e:
            print(f"⚠️  Failed to fetch account equity: {e}")
            print("   Using default $1000")
            return 1000.0
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        errors = []
        
        # Portfolio validation
        if self.portfolio_value <= 0:
            errors.append("portfolio_value must be positive")
        if not 0 < self.daily_pool_percent <= 1.0:
            errors.append("daily_pool_percent must be between 0 and 1")
        if self.max_position_dollars > self.portfolio_value:
            errors.append("max_position_dollars cannot exceed portfolio_value")
        
        # Risk validation
        if not 0 < self.confidence_threshold <= 1.0:
            errors.append("confidence_threshold must be between 0 and 1")
        if self.max_daily_loss_percent < 0:
            errors.append("max_daily_loss_percent must be non-negative")
        
        # Position validation
        if self.max_positions_per_day < 1:
            errors.append("max_positions_per_day must be at least 1")
        if self.min_position_size_dollars > self.max_position_dollars:
            errors.append("min_position_size_dollars cannot exceed max_position_dollars")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        return True
    
    def get_dynamic_confidence_threshold(self, active_position_count: int) -> float:
        """
        Issue 3.1: Dynamic confidence threshold based on position count.
        
        When portfolio has few positions, accept lower confidence signals.
        When portfolio is filling up, require higher quality signals.
        This naturally filters to better trades as positions accumulate.
        
        Args:
            active_position_count: Number of currently active positions
            
        Returns:
            Adjusted confidence threshold (0.25 to 0.55)
        """
        fill_ratio = active_position_count / self.max_positions_per_day
        
        if fill_ratio < 0.25:
            # Few positions: Accept base threshold (need trades)
            return self.confidence_threshold  # 0.25
        elif fill_ratio < 0.50:
            # Half full: Standard threshold
            return max(0.35, self.confidence_threshold)
        elif fill_ratio < 0.75:
            # Mostly full: Higher threshold
            return max(0.45, self.confidence_threshold)
        else:
            # Nearly full: Only best signals
            return max(0.55, self.confidence_threshold)
    
    def get_market_condition_allocation(self, vix_level: float = 20.0, 
                                         spy_momentum: float = 0.0) -> tuple:
        """
        Issue 5.3: Adjust Gap & Go / Fade allocation based on market conditions.
        
        In bullish, low-volatility markets: Favor Gap & Go (momentum continuation)
        In bearish, high-volatility markets: Favor Fade/Short (mean reversion)
        
        Args:
            vix_level: Current VIX level (default 20 = neutral)
            spy_momentum: SPY % change over last 5 days (positive = bullish)
            
        Returns:
            Tuple of (gap_and_go_allocation, fade_short_allocation)
        """
        base_gap = self.gap_and_go_allocation  # 0.80
        base_fade = self.fade_short_allocation  # 0.20
        
        # VIX adjustment
        # Low VIX (<15): Favor Gap & Go (calm market, momentum works)
        # High VIX (>30): Favor Fade/Short (volatile market, reversals work)
        vix_adjustment = 0.0
        if vix_level < 15:
            vix_adjustment = 0.10  # Boost Gap & Go by 10%
        elif vix_level > 30:
            vix_adjustment = -0.15  # Reduce Gap & Go by 15% (favor Fade)
        elif vix_level > 25:
            vix_adjustment = -0.10  # Moderate reduction
        
        # SPY momentum adjustment
        # Strong bullish momentum: Favor Gap & Go
        # Strong bearish momentum: Favor Fade/Short
        momentum_adjustment = 0.0
        if spy_momentum > 0.02:  # SPY up >2% in 5 days
            momentum_adjustment = 0.05  # Slight boost to Gap & Go
        elif spy_momentum < -0.02:  # SPY down >2% in 5 days
            momentum_adjustment = -0.10  # Reduce Gap & Go, favor Fade
        elif spy_momentum < -0.05:  # SPY down >5% in 5 days (correction)
            momentum_adjustment = -0.20  # Strong shift to Fade
        
        # Apply adjustments with bounds
        gap_allocation = min(max(base_gap + vix_adjustment + momentum_adjustment, 0.50), 0.90)
        fade_allocation = 1.0 - gap_allocation
        
        return (gap_allocation, fade_allocation)
    
    def fetch_vix_level(self) -> float:
        """
        Fetch current VIX level from Yahoo Finance.
        Returns cached value if fetched within last 6 hours.
        
        Returns:
            Current VIX level (default 20.0 if fetch fails)
        """
        now = __import__('datetime').datetime.now()
        
        # Return cached value if fresh (< 6 hours old)
        if hasattr(self, '_vix_cache') and self._vix_cache is not None:
            cache_time, cached_vix = self._vix_cache
            if (now - cache_time).total_seconds() < 6 * 3600:
                return cached_vix
        
        try:
            import yfinance as yf
            vix_data = yf.Ticker("^VIX").history(period='1d')
            if not vix_data.empty:
                vix = float(vix_data['Close'].iloc[-1])
                self._vix_cache = (now, vix)
                print(f"📊 VIX fetched: {vix:.1f}")
                return vix
        except Exception as e:
            print(f"⚠️ VIX fetch failed: {e}")
        
        # Default if fetch fails
        return 20.0
    
    def fetch_spy_momentum(self, days: int = 5) -> float:
        """
        Fetch SPY momentum (% change over N days).
        
        Args:
            days: Number of days to calculate momentum
            
        Returns:
            SPY % change (e.g., 0.02 = +2%)
        """
        now = __import__('datetime').datetime.now()
        
        # Return cached value if fresh (< 6 hours old)
        if hasattr(self, '_spy_cache') and self._spy_cache is not None:
            cache_time, cached_momentum = self._spy_cache
            if (now - cache_time).total_seconds() < 6 * 3600:
                return cached_momentum
        
        try:
            import yfinance as yf
            spy = yf.Ticker("SPY").history(period=f'{days + 5}d')
            if len(spy) >= days:
                momentum = (spy['Close'].iloc[-1] / spy['Close'].iloc[-days] - 1)
                self._spy_cache = (now, momentum)
                print(f"📊 SPY momentum ({days}d): {momentum:+.1%}")
                return momentum
        except Exception as e:
            print(f"⚠️ SPY momentum fetch failed: {e}")
        
        return 0.0  # Neutral if fetch fails
    
    def get_live_market_allocation(self) -> tuple:
        """
        Fetch live VIX and SPY data to determine optimal strategy allocation.
        
        This is the main method to call for real-time strategy allocation.
        
        Returns:
            Tuple of (gap_and_go_allocation, fade_short_allocation)
        """
        vix = self.fetch_vix_level()
        spy_momentum = self.fetch_spy_momentum()
        
        gap_alloc, fade_alloc = self.get_market_condition_allocation(vix, spy_momentum)
        
        # Log the allocation
        print(f"📊 Market Allocation: Gap&Go {gap_alloc:.0%} | Fade {fade_alloc:.0%}")
        print(f"   Based on: VIX={vix:.1f} | SPY momentum={spy_momentum:+.1%}")
        
        return (gap_alloc, fade_alloc)

