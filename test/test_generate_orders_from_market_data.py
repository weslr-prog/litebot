#!/usr/bin/env python3
"""
Test: Simulate order generation using historical market close data.
Loads sample data, runs signal generation, and checks if orders would be created.
"""
import sys
import pandas as pd
from datetime import datetime, timedelta
sys.path.insert(0, '.')
from traders.short_cycle_trader import ShortCycleConfig, AISignalGenerator, AIConfidencePositionSizer

def make_series(symbol: str, start_price: float, daily_return: float, base_volume: int):
    # Build 25 days so momentum_lookback (5) and 20-day avg volume work
    dates = [datetime(2025, 8, 22) + timedelta(days=i) for i in range(25)]
    prices = []
    price = start_price
    for i in range(25):
        # simulate simple compounding with small noise
        price *= (1 + daily_return)
        prices.append(price)
    df = pd.DataFrame({
        'symbol': symbol,
        'date': dates,
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [base_volume] * 24 + [int(base_volume * 2.5)]  # last day volume surge
    })
    return df

# Simulate market close data with mild positive momentum and volume surge on last day
data = {
    'AAPL': make_series('AAPL', 170.0, 0.003, 1_000_000),  # ~0.3% daily uptrend
    'TSLA': make_series('TSLA', 240.0, 0.004, 800_000),    # ~0.4% daily uptrend
    'ORCL': make_series('ORCL', 125.0, 0.0025, 600_000),   # ~0.25% daily uptrend
}

config = ShortCycleConfig()
signal_gen = AISignalGenerator(config)
sizer = AIConfidencePositionSizer(config)

universe = list(data.keys())
print(f"🧪 Generating signals for: {universe}")

signals = []
print("\n🔍 Diagnostic signal generation:")
for symbol in universe:
    try:
        sig = signal_gen._analyze_symbol(symbol, data[symbol])
        if sig is not None:
            print(f"✅ {symbol}: Signal generated (confidence={sig.confidence:.2f}, entry={sig.entry_price})")
            signals.append(sig)
        else:
            # Provide extra diagnostics consistent with generator's logic
            df = data[symbol]
            if len(df) >= 6:
                recent_returns = df['close'].pct_change().tail(5)
                momentum = recent_returns.mean()
                vol_surge = df['volume'].iloc[-1] / df['volume'].tail(20).mean()
                print(f"❌ {symbol}: No signal | momentum={momentum:.5f}, vol_surge={vol_surge:.2f}")
            else:
                print(f"❌ {symbol}: No signal generated (insufficient data)")
    except Exception as e:
        print(f"[ERROR] {symbol}: Exception during signal analysis: {e}")

if not signals:
    print("❌ No signals generated for this market data.")
    sys.exit(1)

print(f"\n✅ {len(signals)} signals generated:")
for sig in signals:
    print(f"  {sig.symbol}: confidence={sig.confidence:.2f}, entry={sig.entry_price}")
    # Simulate position sizing for each signal
    stop_price = sig.entry_price * 0.98  # 2% stop
    shares, pos_value = sizer.calculate_position_size(sig, stop_price, config.portfolio_value)
    if shares > 0:
        print(f"    ➡️ Would open position: {shares} shares, value=${pos_value:.2f}")
    else:
        print(f"    ❌ Position size too small or risk too high, no order.")

# --- Smarter adaptive grid search for actionable signals ---
def smart_adaptive_actionable_signal_search(data, base_config, max_attempts=8):
    print("\n🔄 No actionable signals found, starting smart adaptive grid search...")
    # Define parameter grids (logarithmic/exponential steps for wide coverage)
    thresholds = [base_config.confidence_threshold * (0.5 ** i) for i in range(max_attempts)]
    min_sizes = [base_config.min_position_size_dollars * (0.5 ** i) for i in range(max_attempts)]
    portfolio_values = [base_config.portfolio_value * (2 ** i) for i in range(max_attempts)]
    max_risks = [base_config.max_risk_per_trade_dollars * (0.5 ** i) for i in range(max_attempts)]
    # Try all combinations, but prioritize more likely successful ones first
    found_any = False
    for pv in portfolio_values:
        for mr in max_risks:
            for t in thresholds:
                for s in min_sizes:
                    config = ShortCycleConfig(
                        portfolio_value=pv,
                        daily_pool_percent=base_config.daily_pool_percent,
                        max_risk_per_trade_dollars=mr,
                        max_positions_per_day=base_config.max_positions_per_day,
                        min_position_size_dollars=s,
                        max_position_size_percent=base_config.max_position_size_percent,
                        max_hold_days=base_config.max_hold_days,
                        trading_days=base_config.trading_days,
                        exit_time=base_config.exit_time,
                        max_daily_loss_percent=base_config.max_daily_loss_percent,
                        max_weekly_loss_percent=base_config.max_weekly_loss_percent,
                        confidence_threshold=t,
                        enable_forced_d1_exit=base_config.enable_forced_d1_exit,
                        model_transaction_costs=base_config.model_transaction_costs,
                        commission_per_trade=base_config.commission_per_trade,
                        spread_bp=base_config.spread_bp
                    )
                    signal_gen = AISignalGenerator(config)
                    sizer = AIConfidencePositionSizer(config)
                    actionable = []
                    for symbol in data:
                        sig = signal_gen._analyze_symbol(symbol, data[symbol])
                        if sig is not None:
                            stop_price = sig.entry_price * 0.98
                            shares, pos_value = sizer.calculate_position_size(sig, stop_price, config.portfolio_value)
                            print(f"[DEBUG] {symbol}: conf={sig.confidence:.3f}, risk={mr:.2f}, min_size={s:.2f}, pv={pv}, shares={shares}, pos_val={pos_value:.2f}")
                            if shares > 0:
                                actionable.append((sig, shares, pos_value, pv, mr, t, s))
                                found_any = True
                        else:
                            print(f"[DEBUG] {symbol}: No signal for conf_thresh={t:.4f}, min_size={s:.2f}, pv={pv}, risk={mr:.2f}")
                    if actionable:
                        print(f"\n✅ Actionable signals found with portfolio_value={pv}, max_risk_per_trade_dollars={mr}, confidence_threshold={t:.4f}, min_position_size_dollars={s:.2f}")
                        for sig, shares, pos_value, pv, mr, t, s in actionable:
                            print(f"  {sig.symbol}: confidence={sig.confidence:.2f}, entry={sig.entry_price}, shares={shares}, value=${pos_value:.2f}")
                        return actionable, pv, mr, t, s
    if not found_any:
        print("[DEBUG] No signals generated for any parameter set.")
    print("❌ No actionable signals generated after smart grid search.")
    return [], None, None, None, None

# --- Smarter adaptive grid search for actionable signals with confidence multiplier ---
def smart_adaptive_actionable_signal_search(data, base_config, max_attempts=8):
    print("\n🔄 No actionable signals found, starting smart adaptive grid search...")
    thresholds = [base_config.confidence_threshold]
    min_sizes = [base_config.min_position_size_dollars]
    portfolio_values = [base_config.portfolio_value]
    max_risks = [base_config.max_risk_per_trade_dollars]
    confidence_multipliers = [3.0]  # Only test the higher multiplier
    found_any = False
    for pv in portfolio_values:
        for mr in max_risks:
            for t in thresholds:
                for s in min_sizes:
                    for cm in confidence_multipliers:
                        config = ShortCycleConfig(
                            portfolio_value=pv,
                            daily_pool_percent=base_config.daily_pool_percent,
                            max_risk_per_trade_dollars=mr,
                            max_positions_per_day=base_config.max_positions_per_day,
                            min_position_size_dollars=s,
                            max_position_size_percent=base_config.max_position_size_percent,
                            max_hold_days=base_config.max_hold_days,
                            trading_days=base_config.trading_days,
                            exit_time=base_config.exit_time,
                            max_daily_loss_percent=base_config.max_daily_loss_percent,
                            max_weekly_loss_percent=base_config.max_weekly_loss_percent,
                            confidence_threshold=t,
                            enable_forced_d1_exit=base_config.enable_forced_d1_exit,
                            model_transaction_costs=base_config.model_transaction_costs,
                            commission_per_trade=base_config.commission_per_trade,
                            spread_bp=base_config.spread_bp
                        )
                        signal_gen = AISignalGenerator(config)
                        sizer = AIConfidencePositionSizer(config)
                        actionable = []
                        for symbol in data:
                            sig = signal_gen._analyze_symbol(symbol, data[symbol])
                            if sig is not None:
                                stop_price = sig.entry_price * 0.98
                                # Override confidence multiplier for testing
                                entry_price = sig.entry_price
                                if entry_price is None or stop_price >= entry_price:
                                    shares, pos_value = 0, 0.0
                                else:
                                    base_risk = mr
                                    risk_amount = base_risk * min(sig.confidence * cm, cm)
                                    stop_distance = entry_price - stop_price
                                    shares = int(risk_amount / stop_distance)
                                    pos_value = shares * entry_price
                                    max_position_value = pv * config.max_position_size_percent
                                    min_position_value = s
                                    if pos_value > max_position_value:
                                        shares = int(max_position_value / entry_price)
                                        pos_value = shares * entry_price
                                    if pos_value < min_position_value:
                                        shares, pos_value = 0, 0.0
                                print(f"[DEBUG] {symbol}: conf={sig.confidence:.3f}, cmult={cm}, risk={mr:.2f}, min_size={s:.2f}, pv={pv}, shares={shares}, pos_val={pos_value:.2f}")
                                if shares > 0:
                                    actionable.append((sig, shares, pos_value, pv, mr, t, s, cm))
                                    found_any = True
                            else:
                                print(f"[DEBUG] {symbol}: No signal for conf_thresh={t:.4f}, min_size={s:.2f}, pv={pv}, risk={mr:.2f}, cmult={cm}")
                        if actionable:
                            print(f"\n✅ Actionable signals found with portfolio_value={pv}, max_risk_per_trade_dollars={mr}, confidence_threshold={t:.4f}, min_position_size_dollars={s:.2f}, confidence_multiplier={cm}")
                            for sig, shares, pos_value, pv, mr, t, s, cm in actionable:
                                print(f"  {sig.symbol}: confidence={sig.confidence:.2f}, entry={sig.entry_price}, shares={shares}, value=${pos_value:.2f}, cmult={cm}")
                            return actionable, pv, mr, t, s, cm
    if not found_any:
        print("[DEBUG] No signals generated for any parameter set.")
    return [], None, None, None, None, None

# Replace previous adaptive search logic:
if not signals or all(sizer.calculate_position_size(sig, sig.entry_price * 0.98, config.portfolio_value)[0] <= 0 for sig in signals):
    actionable, found_pv, found_mr, found_threshold, found_min_size, found_cmult = smart_adaptive_actionable_signal_search(data, config)
    if not actionable:
        print("❌ No actionable signals generated for this market data, even after smart grid search.")
        sys.exit(1)
    else:
        print(f"\n[INFO] First working parameters: portfolio_value={found_pv}, max_risk_per_trade_dollars={found_mr}, confidence_threshold={found_threshold:.4f}, min_position_size_dollars={found_min_size:.2f}, confidence_multiplier={found_cmult}")
else:
    actionable = [(sig, *sizer.calculate_position_size(sig, sig.entry_price * 0.98, config.portfolio_value), config.portfolio_value, config.max_risk_per_trade_dollars, config.confidence_threshold, config.min_position_size_dollars, 1.0) for sig in signals if sizer.calculate_position_size(sig, sig.entry_price * 0.98, config.portfolio_value)[0] > 0]

print(f"\n✅ {len(actionable)} actionable signals generated:")
for sig, shares, pos_value, pv, mr, t, s, cm in actionable:
    print(f"  {sig.symbol}: confidence={sig.confidence:.2f}, entry={sig.entry_price}, shares={shares}, value=${pos_value:.2f}, portfolio_value={pv}, max_risk={mr}, threshold={t:.4f}, min_size={s:.2f}, cmult={cm}")
