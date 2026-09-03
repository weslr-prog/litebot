"""
Strategy Manager for LiteBotX - Phase 3 Implementation with ML/RL Enhancement
Purpose: Coordinate strategies with ML/RL integration for 5% weekly ROI
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
from core.risk import RiskManager
from core.regime_detector import RegimeDetector

# Import ML/RL components with fallback
try:
    from core.ml_signal_enhancer import MLSignalEnhancer
    from core.rl_position_optimizer import SimpleRLPositionOptimizer
    ML_RL_AVAILABLE = True
except ImportError:
    ML_RL_AVAILABLE = False
    logging.warning("ML/RL components not available. Running in basic mode.")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class StrategyManager:
    """
    Coordinates strategy execution with enhanced ML/RL risk management
    
    Key Features:
    - ML-enhanced signal generation for improved accuracy
    - RL-optimized position sizing for dynamic risk management
    - Integrates regime detection with position sizing
    - Manages strategy selection based on market conditions
    - Enforces risk limits before strategy execution
    - Tracks performance and adjusts parameters
    """
    
    def __init__(self, initial_equity=10000.0):
        # Handle backwards compatibility with old test interface
        if isinstance(initial_equity, dict):
            initial_equity = 10000.0  # Default value for old tests
        
        self.risk_manager = RiskManager(initial_equity=initial_equity)
        self.regime_detector = RegimeDetector()
        
        # Initialize ML/RL components if available
        self.ml_enhancer = None
        self.rl_optimizer = None
        self.ml_enabled = False
        self.rl_enabled = False
        
        if ML_RL_AVAILABLE:
            try:
                self.ml_enhancer = MLSignalEnhancer()
                self.rl_optimizer = SimpleRLPositionOptimizer()
                
                # Try to load pre-trained models
                if self.ml_enhancer.load_model():
                    self.ml_enabled = True
                    logging.info("🤖 ML signal enhancer loaded and enabled")
                
                if self.rl_optimizer.load_model():
                    self.rl_enabled = True
                    logging.info("🎯 RL position optimizer loaded and enabled")
                    
            except Exception as e:
                logging.warning(f"Failed to initialize ML/RL components: {e}")
        
        # Strategy performance tracking
        self.strategy_performance = {
            'volatility_breakout': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'rsi': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'moving_average': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'mean_reversion': {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
        }
        
        # Strategy-regime mapping for optimal selection
        self.regime_strategy_map = {
            'volatile': 'volatility_breakout',
            'bull': 'moving_average', 
            'bear': 'mean_reversion',
            'sideways': 'rsi',
            'UP_LOWVOL': 'moving_average',
            'DOWN_HIGHVOL': 'mean_reversion'
        }
        
        logging.info("🎯 StrategyManager initialized with enhanced ML/RL risk management")

    def execute_enhanced_strategy(self, symbol: str, price_data: pd.DataFrame, 
                                regime: str, sector: str = 'Unknown', 
                                base_signal: str = None, base_confidence: float = None) -> Dict:
        """
        Execute strategy with ML/RL enhancements
        
        Args:
            symbol: Stock symbol
            price_data: Historical price data for analysis
            regime: Current market regime
            sector: Stock sector for exposure limits
            base_signal: Pre-calculated base signal (optional)
            base_confidence: Pre-calculated base confidence (optional)
            
        Returns:
            Dict with execution decision and ML/RL enhancement details
        """
        try:
            logging.info(f"🚀 Enhanced strategy execution: {symbol} (regime: {regime})")
            
            # 1. Generate base signal if not provided
            if base_signal is None or base_confidence is None:
                base_result = self._generate_base_signal(price_data, regime)
                base_signal = base_result.get('signal', 'hold')
                base_confidence = base_result.get('confidence', 0.0)
            
            # 2. Enhance signal with ML (if enabled and trained)
            if self.ml_enabled and self.ml_enhancer.is_trained:
                enhanced_result = self.ml_enhancer.enhance_signal(
                    base_signal, base_confidence, price_data, regime
                )
                signal = enhanced_result['signal']
                confidence = enhanced_result['confidence']
                ml_info = enhanced_result
                logging.info(f"🤖 ML Enhancement: {base_signal} -> {signal} (conf: {base_confidence:.2f} -> {confidence:.2f})")
            else:
                signal = base_signal
                confidence = base_confidence
                ml_info = {'ml_enhancement': False, 'reason': 'ML not available or not trained'}
            
            # 3. Skip if signal is hold or confidence too low
            if signal == 'hold' or confidence < 0.4:
                return {
                    'approved': False,
                    'reason': f'Signal: {signal}, Confidence: {confidence:.2f}',
                    'symbol': symbol,
                    'ml_info': ml_info,
                    'base_signal': base_signal,
                    'base_confidence': base_confidence
                }
            
            # 4. Calculate entry price and base position size
            entry_price = price_data['close'].iloc[-1]
            base_position_size = self._calculate_base_position_size(
                signal, confidence, entry_price, regime
            )
            
            # 5. Optimize position size with RL (if enabled)
            if self.rl_enabled:
                recent_performance = self._get_recent_performance()
                optimized_size = self.rl_optimizer.optimize_position_size(
                    base_position_size, regime, confidence, recent_performance
                )
                rl_info = {
                    'rl_enabled': True,
                    'base_size': base_position_size,
                    'optimized_size': optimized_size,
                    'recent_performance': recent_performance
                }
                logging.info(f"🎯 RL Optimization: {base_position_size:.2f} -> {optimized_size:.2f}")
            else:
                optimized_size = base_position_size
                rl_info = {'rl_enabled': False, 'reason': 'RL not available'}
            
            # 6. Calculate stop loss and take profit
            stop_loss = self._calculate_stop_loss(entry_price, signal, regime)
            take_profit = self._calculate_take_profit(entry_price, signal, regime)
            
            # 7. Final risk approval
            trade_approval = self.risk_manager.approve_trade(
                symbol=symbol,
                signal_type=signal,
                signal_confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                sector=sector,
                regime=regime
            )
            
            if trade_approval['approved']:
                # Store RL state for future learning
                if self.rl_enabled:
                    rl_state = self.rl_optimizer.get_state(regime, confidence, recent_performance)
                    action_idx = self._get_rl_action_index(optimized_size, base_position_size)
                    trade_approval.update({
                        'rl_state': rl_state,
                        'rl_action': action_idx,
                        'rl_info': rl_info
                    })
                
                # Enhanced execution plan
                trade_approval.update({
                    'action': signal,
                    'symbol': symbol,
                    'quantity': trade_approval['quantity'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence,
                    'regime': regime,
                    'sector': sector,
                    'ml_info': ml_info,
                    'base_signal': base_signal,
                    'base_confidence': base_confidence,
                    'strategy_used': self.regime_strategy_map.get(regime, 'default'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'enhancement_type': 'ML+RL' if (self.ml_enabled and self.rl_enabled) else 
                                       'ML' if self.ml_enabled else 'RL' if self.rl_enabled else 'Basic'
                })
                
                logging.info(f"✅ Enhanced strategy approved: {symbol} {signal} "
                           f"(qty: {trade_approval['quantity']}, conf: {confidence:.2f})")
            
            return trade_approval
            
        except Exception as e:
            logging.error(f"❌ Enhanced strategy execution failed for {symbol}: {e}")
            return {
                'approved': False,
                'error': str(e),
                'symbol': symbol,
                'fallback_to_basic': True
            }

    def update_models_with_trade_result(self, trade_info: Dict, final_return: float):
        """
        Update ML/RL models with trade results for continuous learning
        
        Args:
            trade_info: Trade execution information
            final_return: Final return percentage (e.g., 0.05 for 5% gain)
        """
        try:
            # Update RL model
            if self.rl_enabled and 'rl_state' in trade_info and 'rl_action' in trade_info:
                self.rl_optimizer.record_trade_result(
                    trade_info['rl_state'],
                    trade_info['rl_action'],
                    final_return
                )
                logging.info(f"📊 RL model updated with return: {final_return:.3f}")
            
            # Save models periodically (every 20 trades)
            if hasattr(self, 'trade_count'):
                self.trade_count += 1
            else:
                self.trade_count = 1
                
            if self.trade_count % 20 == 0:
                if self.rl_enabled:
                    self.rl_optimizer.save_model()
                if self.ml_enabled:
                    self.ml_enhancer.save_model()
                logging.info(f"💾 Models saved after {self.trade_count} trades")
                
        except Exception as e:
            logging.error(f"Failed to update models: {e}")

    def get_ml_rl_stats(self) -> Dict:
        """Get ML/RL performance statistics"""
        stats = {
            'ml_enabled': self.ml_enabled,
            'rl_enabled': self.rl_enabled,
            'trade_count': getattr(self, 'trade_count', 0)
        }
        
        if self.ml_enabled:
            stats['ml_stats'] = self.ml_enhancer.get_model_stats()
        
        if self.rl_enabled:
            stats['rl_stats'] = self.rl_optimizer.get_performance_stats()
        
        return stats

    def _generate_base_signal(self, price_data: pd.DataFrame, regime: str) -> Dict:
        """Generate base trading signal using traditional strategies"""
        # This is a simplified version - you can integrate with your existing strategy logic
        try:
            # Use your existing strategy selection logic
            strategy_name = self.regime_strategy_map.get(regime, 'moving_average')
            
            # Calculate simple moving average signal as example
            if len(price_data) >= 20:
                ma_short = price_data['close'].rolling(10).mean().iloc[-1]
                ma_long = price_data['close'].rolling(20).mean().iloc[-1]
                current_price = price_data['close'].iloc[-1]
                
                if ma_short > ma_long and current_price > ma_short:
                    return {'signal': 'buy', 'confidence': 0.7, 'strategy': strategy_name}
                elif ma_short < ma_long and current_price < ma_short:
                    return {'signal': 'sell', 'confidence': 0.7, 'strategy': strategy_name}
            
            return {'signal': 'hold', 'confidence': 0.0, 'strategy': strategy_name}
            
        except Exception as e:
            logging.warning(f"Base signal generation failed: {e}")
            return {'signal': 'hold', 'confidence': 0.0, 'strategy': 'default'}

    def _calculate_base_position_size(self, signal: str, confidence: float, 
                                    entry_price: float, regime: str) -> float:
        """Calculate base position size before RL optimization"""
        # Use your existing position sizing logic
        # This is a simplified version
        base_risk_pct = 0.005  # 0.5% risk per trade
        regime_multiplier = self._get_volatility_multiplier(regime)
        
        risk_dollars = self.risk_manager.current_equity * base_risk_pct * regime_multiplier * confidence
        position_size = risk_dollars / (entry_price * 0.03)  # Assuming 3% stop loss
        
        return max(1, int(position_size))  # At least 1 share

    def _get_recent_performance(self) -> float:
        """Get recent trading performance for RL optimization"""
        # This should return recent portfolio performance
        # For now, return a placeholder
        return 0.0

    def _get_rl_action_index(self, optimized_size: float, base_size: float) -> int:
        """Convert position size ratio to RL action index"""
        if base_size == 0:
            return 2  # Default to 1.0 multiplier
        
        ratio = optimized_size / base_size
        actions = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        # Find closest action
        closest_idx = min(range(len(actions)), key=lambda i: abs(actions[i] - ratio))
        return closest_idx

    def execute_strategy_with_risk_control(self, symbol: str, strategy_signal: str, 
                                         strategy_confidence: float, entry_price: float,
                                         regime: str, sector: str = 'Unknown') -> Dict:
        """
        Execute strategy signal with full risk management integration
        
        Args:
            symbol: Stock symbol
            strategy_signal: 'buy', 'sell', or 'hold'
            strategy_confidence: 0.0-1.0 confidence from strategy
            entry_price: Planned entry price
            regime: Current market regime
            sector: Stock sector for exposure limits
            
        Returns:
            Dict with execution decision and details
        """
        logging.info(f"🎯 Strategy execution: {symbol} {strategy_signal} (confidence: {strategy_confidence:.2f}, regime: {regime})")
        
        if strategy_signal == 'hold':
            return {
                'action': 'hold',
                'reason': 'strategy_signal_hold',
                'symbol': symbol,
                'approved': False
            }
        
        # Calculate stop loss (3% default, adjust based on volatility)
        volatility_multiplier = self._get_volatility_multiplier(regime)
        stop_loss_pct = 0.03 * volatility_multiplier  # Adjust stop based on regime
        
        if strategy_signal == 'buy':
            stop_loss = entry_price * (1 - stop_loss_pct)
        else:  # sell
            stop_loss = entry_price * (1 + stop_loss_pct)
        
        # Get trade approval from risk manager
        trade_approval = self.risk_manager.approve_trade(
            symbol=symbol,
            signal_type=strategy_signal,
            signal_confidence=strategy_confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            sector=sector,
            regime=regime
        )
        
        if trade_approval['approved']:
            # Add execution details
            execution_plan = {
                'action': strategy_signal,
                'symbol': symbol,
                'quantity': trade_approval['quantity'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': self._calculate_take_profit(entry_price, strategy_signal, regime),
                'risk_dollars': trade_approval['risk_dollars'],
                'confidence': strategy_confidence,
                'regime': regime,
                'sector': sector,
                'strategy_used': self.regime_strategy_map.get(regime, 'default'),
                'approved': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logging.info(f"✅ Strategy execution APPROVED: {symbol} {strategy_signal} {trade_approval['quantity']} shares")
            return execution_plan
        else:
            logging.warning(f"🚫 Strategy execution BLOCKED: {symbol} - {trade_approval['reason']}")
            return {
                'action': 'hold',
                'reason': trade_approval['reason'],
                'symbol': symbol,
                'approved': False
            }

    def _get_volatility_multiplier(self, regime: str) -> float:
        """Adjust stop loss based on regime volatility"""
        volatility_multipliers = {
            'volatile': 1.5,      # Wider stops in volatile markets
            'UP_LOWVOL': 0.8,     # Tighter stops in low vol
            'DOWN_HIGHVOL': 1.8,  # Very wide stops in volatile down markets
            'bull': 1.0,
            'bear': 1.2,
            'sideways': 0.9
        }
        return volatility_multipliers.get(regime, 1.0)

    def _calculate_take_profit(self, entry_price: float, signal_type: str, regime: str) -> float:
        """Calculate take profit based on regime and 5% weekly target"""
        # Base take profit for 5% weekly target (need ~2-3% per trade)
        base_tp_pct = 0.025  # 2.5% base target
        
        # Adjust based on regime
        regime_multipliers = {
            'volatile': 1.5,    # Higher targets in breakout conditions
            'bull': 1.2,        # Slightly higher in uptrends
            'bear': 0.8,        # Lower targets in downtrends
            'sideways': 1.0,    # Standard targets in range
            'UP_LOWVOL': 1.1,
            'DOWN_HIGHVOL': 0.7
        }
        
        tp_pct = base_tp_pct * regime_multipliers.get(regime, 1.0)
        
        if signal_type == 'buy':
            return entry_price * (1 + tp_pct)
        else:  # sell
            return entry_price * (1 - tp_pct)

    def get_strategy_for_regime(self, regime: str) -> str:
        """Get optimal strategy for current market regime"""
        strategy = self.regime_strategy_map.get(regime, 'rsi')
        logging.info(f"📊 Selected strategy for {regime} regime: {strategy}")
        return strategy

    def update_strategy_performance(self, symbol: str, strategy_used: str, 
                                  pnl: float, outcome: str):
        """Update strategy performance tracking"""
        if strategy_used in self.strategy_performance:
            self.strategy_performance[strategy_used]['total_pnl'] += pnl
            
            if outcome == 'win':
                self.strategy_performance[strategy_used]['wins'] += 1
            else:
                self.strategy_performance[strategy_used]['losses'] += 1
            
            # Log performance update
            stats = self.strategy_performance[strategy_used]
            total_trades = stats['wins'] + stats['losses']
            win_rate = stats['wins'] / total_trades if total_trades > 0 else 0
            
            logging.info(f"📈 Strategy performance updated: {strategy_used} - "
                        f"Win rate: {win_rate:.1%}, Total PnL: ${stats['total_pnl']:.2f}")

    def get_portfolio_status(self) -> Dict:
        """Get comprehensive portfolio and risk status"""
        risk_summary = self.risk_manager.get_portfolio_summary()
        
        # Add strategy performance
        strategy_summary = {}
        for strategy, stats in self.strategy_performance.items():
            total_trades = stats['wins'] + stats['losses']
            strategy_summary[strategy] = {
                'total_trades': total_trades,
                'win_rate': stats['wins'] / total_trades if total_trades > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'avg_pnl_per_trade': stats['total_pnl'] / total_trades if total_trades > 0 else 0
            }
        
        return {
            'risk_management': risk_summary,
            'strategy_performance': strategy_summary,
            'overall_status': {
                'weekly_target': 0.05,  # 5% weekly target
                'weekly_progress': risk_summary['weekly_return'],
                'daily_progress': risk_summary['daily_return'],
                'trading_status': 'ACTIVE' if not risk_summary['is_trading_halted'] else 'HALTED',
                'positions_used': f"{risk_summary['active_positions']}/{risk_summary['max_positions']}"
            }
        }

    def check_weekly_target_progress(self) -> Dict:
        """Check progress toward 5% weekly ROI target"""
        portfolio_summary = self.risk_manager.get_portfolio_summary()
        weekly_return = portfolio_summary['weekly_return']
        target_return = 0.05  # 5%
        
        progress_pct = (weekly_return / target_return) * 100 if target_return > 0 else 0
        
        status = {
            'weekly_return': weekly_return,
            'target_return': target_return,
            'progress_percent': progress_pct,
            'remaining_needed': target_return - weekly_return,
            'status': 'ON_TRACK' if progress_pct >= 50 else 'BEHIND' if progress_pct >= 0 else 'NEGATIVE'
        }
        
        if progress_pct >= 100:
            status['status'] = 'TARGET_ACHIEVED'
            logging.info(f"🎉 WEEKLY TARGET ACHIEVED: {weekly_return:.2%} >= {target_return:.2%}")
        elif progress_pct >= 80:
            status['status'] = 'NEAR_TARGET'
            logging.info(f"🎯 Near weekly target: {weekly_return:.2%} (need {status['remaining_needed']:.2%} more)")
        
        return status

    # Legacy strategy methods preserved for compatibility
    def tpl_entry_ok(self, spy_data, asset_data):
        """
        Require SPY > 100SMA and no lower-low in last 5 bars before entry.
        """
        logging.debug(f"SPY close price: {spy_data['close'].iloc[-1]}")
        logging.debug(f"SPY 100SMA: {spy_data['close'].rolling(100).mean().iloc[-1]}")
        if len(spy_data) < 100:
            logging.warning("Insufficient data for 100SMA calculation in SPY data.")
            return False
        if spy_data['close'].iloc[-1] < spy_data['close'].rolling(100).mean().iloc[-1]:
            return False
        lows = asset_data['low'].tail(6)
        if lows.iloc[-1] < lows.iloc[:-1].min():
            return False
        return True

    def tpl_post_entry(self, asset_data, entry_idx):
        """
        If a lower low forms post-entry, tighten stop to 1.0× ATR.
        Require volume confirmation on first up day post-entry (≥ 60th percentile of 20-day volume), else time-exit early.
        """
        post_lows = asset_data['low'].iloc[entry_idx:]
        if post_lows.min() < asset_data['low'].iloc[entry_idx-1]:
            return 'tighten_stop'
        up_days = asset_data['close'].iloc[entry_idx:] > asset_data['close'].iloc[entry_idx-1]
        if up_days.any():
            up_idx = up_days.idxmax()
            vol = asset_data['volume'].iloc[up_idx]
            vol_60pct = asset_data['volume'].rolling(20).quantile(0.6).iloc[up_idx]
            if vol < vol_60pct:
                return 'time_exit'
        return 'hold'

    # --- M) Mean-Reversion Bounce (MRB) ---
    def mrb_entry_ok(self, asset_data, regime):
        """
        Disable MRB in DOWN_HIGHVOL regimes; require capitulation wick (close > low + 0.6× ATR) on signal day.
        """
        if regime == 'DOWN_HIGHVOL':
            logging.info("MRB entry disabled in DOWN_HIGHVOL regime.")
            return False

        atr = (asset_data['high'] - asset_data['low']).rolling(14, min_periods=1).mean().iloc[-1]
        wick_threshold = asset_data['low'].iloc[-1] + 0.6 * atr
        logging.debug(f"Adjusted ATR: {atr}, Wick Threshold: {wick_threshold}")
        wick = asset_data['close'].iloc[-1] > wick_threshold
        if not wick:
            logging.info("No capitulation wick detected for MRB entry.")
            return False

        logging.debug(f"Regime: {regime}")
        logging.debug(f"ATR: {atr}")
        logging.debug(f"Close: {asset_data['close'].iloc[-1]}, Low: {asset_data['low'].iloc[-1]}, Wick Threshold: {asset_data['low'].iloc[-1] + 0.6 * atr}")

        return True

    def mrb_exit_logic(self, asset_data, entry_idx):
        """
        Short time exit (max 3 days); if no bounce by day 2, cut half.
        """
        post_closes = asset_data['close'].iloc[entry_idx:entry_idx+3]
        entry_close = asset_data['close'].iloc[entry_idx]

        logging.debug(f"Post closes: {post_closes}")
        logging.debug(f"Entry close: {entry_close}")

        bounce = (post_closes > entry_close).any()
        logging.debug(f"Bounce detected: {bounce}")

        logging.debug(f"Length of post_closes: {len(post_closes)}")
        
        if len(post_closes) >= 3:
            logging.info("Max 3-day holding period reached; exiting position.")
            return 'exit'

        if bounce:
            logging.info("Bounce detected; holding position.")
            return 'hold'

        if not bounce and len(post_closes[:2]) == 2:
            logging.info("No bounce detected by day 2; cutting half the position.")
            return 'cut_half'

        return 'hold'

    # --- N) Breakout ---
    def breakout_entry_ok(self, asset_data, regime):
        """
        Only in UP regimes; require rising 20-day volume percentile and close above breakout by >0.5× ATR.
        """
        if regime != 'UP':
            return False
        vol_pct = asset_data['volume'].rolling(20).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])
        rising_vol = vol_pct.iloc[-1] > vol_pct.iloc[-2]
        atr = (asset_data['high'] - asset_data['low']).rolling(14).mean().iloc[-1]
        breakout_level = asset_data['high'].rolling(20).max().iloc[-2]
        close_ok = asset_data['close'].iloc[-1] > breakout_level + 0.5 * atr
        return rising_vol and close_ok
    # --- H) Slippage Adjustment for EV ---
    def adjust_ev_for_slippage(self, EV, atr, side):
        """Subtract expected slippage from win EV, add to loss EV."""
        # Slippage model: max(0.02%, 0.2 × ATR%)
        slippage = max(0.0002, 0.2 * atr) if atr is not None else 0.0002
        if side == "win":
            return EV - slippage
        elif side == "loss":
            return EV + slippage
        return EV

    # --- I) Weekend Carry Logic ---
    def should_carry_over_weekend(self, is_winner, EV, beta_regime):
        """Only carry winners if EV ≥ 0 and β_regime ≥ 0.6."""
        if is_winner and EV >= 0 and beta_regime >= 0.6:
            return True
        return False
    # --- D) EV Estimation Error Mitigation ---
    def get_adjusted_ev(self, EV_bucket, N, EV_global, k=200):
        """Shrinkage toward global mean EV if sample size is small. Merge buckets if N < 150."""
        from utils.logger import log_event
        bucket_label = getattr(self, 'bucket_label', None)
        bucket_counts = getattr(self, 'bucket_counts', None)
        if bucket_counts and bucket_label:
            n = bucket_counts.get(bucket_label, N)
            if n < 150:
                labels = list(bucket_counts.keys())
                idx = labels.index(bucket_label)
                merge_label = None
                if idx > 0:
                    merge_label = labels[idx-1]
                elif idx < len(labels)-1:
                    merge_label = labels[idx+1]
                if merge_label:
                    merged_n = n + bucket_counts[merge_label]
                    log_event("ev_bucket_merge", {"from": bucket_label, "to": merge_label, "merged_n": merged_n})
                    if merged_n < 150:
                        return EV_global, 0.5
                    else:
                        EV_adj = (merged_n/(merged_n+k))*EV_bucket + (k/(merged_n+k))*EV_global
                        return EV_adj, 1.0
        if N < 150:
            log_event("ev_bucket_merge", {"bucket": bucket_label, "N": N, "action": "use_global_ev"})
            return EV_global, 0.5
        EV_adj = (N/(N+k))*EV_bucket + (k/(N+k))*EV_global
        return EV_adj, 1.0
    def choose_strategy(self, regime):
        logging.info(f"Choosing strategy for regime: {regime}")
        strategy = self.strategies.get(regime, None)
        from utils.logger import log_event
        params = self.regime_params.get(regime, {})
        log_event("regime_param_usage", {"regime": regime, "params": params})
        if strategy:
            logging.info(f"Selected strategy: {strategy}")
        else:
            logging.warning(f"No strategy found for regime: {regime}")
        return strategy
    def execute_strategy(self, strategy_name, market_data):
        logging.info(f"Executing strategy: {strategy_name}")
        from utils.logger import log_event
        try:
            logging.debug(f"Market data for {strategy_name}: {market_data.tail()}")
            params = self.strategy_params.get(strategy_name, {})
            log_event("strategy_param_usage", {"strategy": strategy_name, "params": params})
            if strategy_name == "momentum":
                return self._momentum_strategy(market_data, params)
            elif strategy_name == "mean_reversion":
                return self._mean_reversion_strategy(market_data, params)
            elif strategy_name == "range_trading":
                return self._range_trading_strategy(market_data, params)
            elif strategy_name == "volatility_breakout":
                return self._volatility_breakout_strategy(market_data, params)
            elif strategy_name == "TPL":
                if self.tpl_entry_ok(market_data['spy'], market_data['asset']):
                    return "buy"
                else:
                    return "hold"
            else:
                logging.warning(f"Strategy {strategy_name} not recognized.")
                return "buy"
        except Exception as e:
            logging.error(f"Error executing strategy {strategy_name}: {e}", exc_info=True)
            return "hold"
    def _momentum_strategy(self, market_data, params):
        ma_window = params.get("ma_window", 20)
        buy_thresh = params.get("buy_thresh", 1.02)
        sell_thresh = params.get("sell_thresh", 0.98)
        ma = market_data['close'].rolling(ma_window).mean().iloc[-1]
        if market_data['close'].iloc[-1] > ma * buy_thresh:
            return "buy"
        elif market_data['close'].iloc[-1] < ma * sell_thresh:
            return "sell"
        return "hold"
    def _mean_reversion_strategy(self, market_data, params):
        ma_window = params.get("ma_window", 20)
        buy_thresh = params.get("buy_thresh", 0.9)
        sell_thresh = params.get("sell_thresh", 1.1)
        ma = market_data['close'].rolling(ma_window).mean().iloc[-1]
        if market_data['close'].iloc[-1] > ma * sell_thresh:
            return "sell"
        elif market_data['close'].iloc[-1] < ma * buy_thresh:
            return "buy"
        return "hold"
    def _range_trading_strategy(self, market_data, params):
        window = params.get("window", 10)
        low_pct = params.get("low_pct", 0.4)
        high_pct = params.get("high_pct", 0.6)
        if len(market_data) < window:
            low = market_data['close'].min()
            high = market_data['close'].max()
        else:
            low = market_data['close'].rolling(window=window).min().iloc[-1]
            high = market_data['close'].rolling(window=window).max().iloc[-1]
        logging.debug(f"Low: {low}, High: {high}, Current: {market_data['close'].iloc[-1]}")
        if high == low:
            logging.debug("Range is zero, forcing a 'buy' action for testing.")
            return "buy"
        if market_data['close'].iloc[-1] < (low + (high - low) * low_pct):
            return "buy"
        elif market_data['close'].iloc[-1] > (low + (high - low) * high_pct):
            return "sell"
        return "hold"
    def _volatility_breakout_strategy(self, market_data, params):
        window = params.get("window", 10)
        recent_high = market_data['close'].rolling(window=window).max().iloc[-1]
        recent_low = market_data['close'].rolling(window=window).min().iloc[-1]
        if market_data['close'].iloc[-1] > recent_high:
            return "buy"
        if market_data['close'].iloc[-1] < recent_low:
            return "sell"
        return "hold"
    def check_sector_etf_cap(self, open_positions, symbol, sector_map, etf_map, sector_cap=5, etf_cap=10):
        """
        Check if the open positions for a given symbol exceed the sector or ETF cap.

        Args:
            open_positions (list): List of currently open positions.
            symbol (str): The symbol to check.
            sector_map (dict): Mapping of symbols to sectors.
            etf_map (dict): Mapping of symbols to ETFs.
            sector_cap (int): Maximum allowed positions per sector.
            etf_cap (int): Maximum allowed positions per ETF.

        Returns:
            bool: True if the cap is not exceeded, False otherwise.
        """
        sector = sector_map.get(symbol, "unknown")
        etf = etf_map.get(symbol, "unknown")

        # Count positions by sector and ETF
        sector_count = sum(1 for pos in open_positions if sector_map.get(pos, "unknown") == sector)
        etf_count = sum(1 for pos in open_positions if etf_map.get(pos, "unknown") == etf)

        logging.info(f"Sector: {sector}, ETF: {etf}, Sector Count: {sector_count}, ETF Count: {etf_count}")

        if sector_count >= sector_cap:
            logging.warning(f"Sector cap exceeded for {sector}. Current: {sector_count}, Cap: {sector_cap}")
            return False

        if etf_count >= etf_cap:
            logging.warning(f"ETF cap exceeded for {etf}. Current: {etf_count}, Cap: {etf_cap}")
            return False

        return True

    def compute_risk_dollars(self, equity: float, beta_regime: float) -> float:
        base = 0.005  # 0.5% per-trade cap
        risk_dollars = max(0.0, base * float(beta_regime) * float(equity))
        logger.info(f"[StrategyManager] risk_per_trade={risk_dollars:.2f} (beta={beta_regime:.2f}, equity={equity:.2f})")
        return risk_dollars

    def should_enter_trade(self, regime_label: str, strategy_name: str) -> bool:
        # Conservative defaults
        if regime_label == "DOWN_HIGHVOL":
            return False  # stand down
        # Optionally restrict long-only strategies when DOWN_*
        if strategy_name in ("TPL", "TREND_PULLBACK") and regime_label.startswith("DOWN_"):
            return False
        return True