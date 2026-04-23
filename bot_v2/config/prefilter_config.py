"""
Simple PreFilter Configuration for bot_v2
Optimized for Dual-Strategy: Gap & Go (70%) + Fade/Short (30%)

Design Philosophy:
- Optimized for GAPS + OVERBOUGHT reversals (not mean reversion)
- Gap & Go: Need volatile, liquid stocks that gap 2-8%
- Fade/Short: Need extended stocks 10%+ above SMA
- 3-stage filter (price, volume, volatility)
- Focus on quality over quantity

Date: January 8, 2026
"""

# Simple 3-Stage PreFilter Configuration (DUAL-STRATEGY OPTIMIZED)
SIMPLE_PREFILTER_CONFIG = {
    # Stage 1: Price Range (Gap & Go optimized)
    # Apr 23: Recovery widening to $75 to restore candidate throughput
    # Lower bound allows quality $5-10 stocks; upper avoids penny gaps
    'min_price': 5.0,           # $5 minimum (quality mid-caps, avoid penny stock gaps)
    'max_price': 75.0,          # Recovery mode: admit liquid mid-caps above $50
    
    # Stage 2: Volume (conservative expansion for broader candidate flow)
    # Apr 23: Recovery mode - broader but still tradable liquidity floor
    'min_volume': 1_500_000,    # 1.5M shares minimum (still liquid, broader opportunity set)
    'max_volume': 30_000_000,   # 30M shares maximum (allow more liquid names)
    'min_dollar_volume': 10_000_000,  # Recovery mode: $10M floor to avoid starving universe
    
    # Stage 3: Volatility (conservative expansion — Apr 7, 2026)
    # Recovery mode: widen volatility band to increase candidate flow in mixed regimes
    'min_atr_pct': 0.020,       # 2.0% minimum daily range
    'max_atr_pct': 0.100,       # 10.0% maximum daily range
    
    # Data Requirements
    'min_data_rows': 15,        # Minimum 15 days (yfinance limitation)
    
    # ENABLED Features for Gap & Go (Jan 8, 2026)
    'enable_breakout': False,        # Not needed for gaps
    'enable_momentum': True,         # Recovery mode: align prefilter flags with active momentum strategy
    'enable_gap_detection': True,    # ✅ ENABLED for Gap & Go strategy!
    'enable_regime': False,          # Not needed
    
    # Target Candidate Range (dual-strategy optimized)
    'target_min_candidates': 30,     # More candidates for gap scanning
    'target_max_candidates': 100     # Recovery mode: broader pool for no-activity recovery
}


# Dual-Strategy Configuration (Gap & Go + Fade/Short)
# Updated Jan 8, 2026: Optimized for dual-strategy system
GAP_AND_GO_FADE_CONFIG = {
    # Gap & Go (PRIMARY - 70% allocation)
    'gap_min_pct': 0.02,             # 2% minimum gap
    'gap_max_pct': 0.08,             # 8% maximum gap
    'gap_rsi_max': 75.0,             # RSI < 75 at gap
    'gap_scan_time': '09:35',        # Scan at market open
    'gap_profit_target': 0.03,       # 3% profit target
    'gap_stop_loss': 0.02,           # 2% stop loss
    
    # Fade/Short (BACKUP - 30% allocation)
    'fade_rsi_min': 70.0,            # RSI > 70 (overbought)
    'fade_extension_min': 0.10,      # 10%+ above 20-SMA
    'fade_scan_start': '10:00',      # Start scanning
    'fade_scan_end': '14:00',        # Stop scanning
    'fade_profit_target': 0.02,      # 2% profit target
    'fade_stop_loss': 0.015,         # 1.5% stop loss
    
    # Signal Quality
    'confidence_threshold': 0.25,    # 25% minimum confidence
    'min_atr_pct': 0.030,           # 3.0% minimum volatility (gaps need movement)
    'max_atr_pct': 0.080,           # 8.0% maximum volatility
    
    # Expected Performance (30-Day Backtest Validated)
    'gap_expected_win_rate': 0.543,  # 54.3% win rate
    'fade_expected_win_rate': 0.628, # 62.8% win rate
    'combined_monthly_return': 6.33, # +633% monthly target
    'expected_trades_per_month': 1618,  # 748 Gap + 914 Fade - 44 conflicts
    'expected_conflict_rate': 0.059  # 5.9% conflict rate
}


# Universe Configuration
UNIVERSE_CONFIG = {
    'source': 'mid_cap_universe.json',  # Curated 150-stock list
    'size': 150,                        # Total stocks in universe
    'market_cap_min': 2_000_000_000,    # $2B minimum (mid-cap floor)
    'market_cap_max': 10_000_000_000,   # $10B maximum (mid-cap ceiling)
    
    # Sector Allocation
    'sector_weights': {
        'technology': 0.40,             # 40% tech (high volatility)
        'consumer_discretionary': 0.20, # 20% consumer
        'healthcare_biotech': 0.15,     # 15% healthcare
        'financials': 0.10,             # 10% financials
        'energy_clean': 0.08,           # 8% energy
        'industrials': 0.04,            # 4% industrials
        'communication': 0.02,          # 2% communication
        'materials_commodities': 0.01   # 1% materials
    },
    
    # Quality Filters
    'min_avg_volume': 200_000,          # 200K shares/day minimum
    'min_institutional': 0.40,          # 40% minimum institutional ownership
    'max_institutional': 0.70           # 70% maximum (avoid too stable)
}


# Performance Optimization Settings
OPTIMIZATION_CONFIG = {
    # Timing
    'premarket_scan_time': '09:00',     # Gap scan (may skip if focused on mean reversion)
    'entry_window_start': '09:45',     # Primary entry window start
    'entry_window_end': '10:00',       # Primary entry window end
    'exit_monitoring_start': '10:00',  # Start monitoring exits
    'force_exit_time': '14:30',        # D+1 force exit (improved from 15:45)
    'friday_exit_time': '14:30',       # Friday exit (no weekend holds)
    
    # Execution
    'max_api_calls_per_scan': 150,     # Match universe size
    'expected_scan_time_sec': 5,       # Target: <5 seconds per scan
    'max_scan_time_sec': 10,           # Warning if >10 seconds
    
    # Risk Management
    'max_positions': 12,                # Max concurrent positions
    'max_position_size_pct': 0.083,    # 8.3% per position (1/12)
    'max_daily_loss_pct': 0.08,        # 8% daily loss limit
    'pdt_max_trades': 3,               # PDT limit (3 trades / 5 days)
    
    # Quality Control
    'min_signals_per_day': 5,          # Expect at least 5 signals
    'max_signals_per_day': 20,         # Warning if >20 signals
    'expected_candidates': 25          # Target candidate count
}


# Backtest Validation Thresholds
VALIDATION_CONFIG = {
    'min_win_rate': 0.54,              # Minimum acceptable win rate
    'min_weekly_return': 0.020,        # Minimum 2% weekly return
    'max_drawdown': 0.15,              # Maximum 15% drawdown
    'min_sharpe_ratio': 1.5,           # Minimum Sharpe ratio
    'min_trades_per_week': 15          # Minimum trade frequency
}


# Export all configs
__all__ = [
    'SIMPLE_PREFILTER_CONFIG',
    'MEAN_REVERSION_CONFIG',
    'UNIVERSE_CONFIG',
    'OPTIMIZATION_CONFIG',
    'VALIDATION_CONFIG'
]
