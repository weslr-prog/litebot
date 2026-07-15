"""
AI-powered signal generation with multi-source inputs and confidence scoring
Extracted from traders/short_cycle_trader.py
"""

import logging
import re
import pandas as pd
from typing import Any, List, Dict, Optional, Callable, Tuple
from datetime import datetime, timedelta

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import PositionStatus


# Market cap cache configuration
MARKET_CAP_CACHE_HOURS = 24  # Market caps don't change quickly, 24h is reasonable


class AISignalGenerator:
    """AI-powered signal generation with multi-source inputs and confidence scoring"""
    
    def __init__(self, config: ShortCycleConfig, price_fetcher: Optional[Callable] = None, 
                 adaptive_params: bool = True):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AISignalGenerator")
        self.price_fetcher = price_fetcher  # Function to fetch real-time prices
        
        # TIER 2 (Feb 25, 2026): Real-time Alpaca prices injected before each scan cycle.
        # Replaces stale daily close in EMA/SMA comparisons and momentum calculations.
        self._realtime_prices: Dict[str, float] = {}
        
        # Adaptive parameters
        self.adaptive_params_enabled = adaptive_params
        self.adaptive_manager = None
        if adaptive_params:
            try:
                from bot_v2.adaptive import AdaptiveParameterManager
                self.adaptive_manager = AdaptiveParameterManager(config)
                self.logger.info("✅ Adaptive parameter management ENABLED")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not initialize adaptive params: {e}, using static")
                self.adaptive_params_enabled = False
        
        # Model placeholders (Sprint 1 implementation)
        self.model = None
        self.feature_pipeline = None
        
        # Market cap filtering with time-based cache
        self._market_cap_cache: Dict[str, Tuple[float, datetime]] = {}  # {symbol: (market_cap, timestamp)}
        
        # Enhanced quality scoring
        try:
            from intraday_quality_scorer import IntradayQualityScorer
            self.quality_scorer = IntradayQualityScorer()
            self.logger.info("✅ Enhanced quality scorer initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize quality scorer: {e}")
            self.quality_scorer = None
        
        # News sentiment analyzer (Alpaca News API - free)
        try:
            from bot_v2.data_sources import NewsSentimentAnalyzer
            self.sentiment_analyzer = NewsSentimentAnalyzer()
            self.logger.info("✅ News sentiment analyzer initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize sentiment analyzer: {e}")
            self.sentiment_analyzer = None
        
        # Sentiment veto gate (FIX #3 - hard exclusion rules)
        try:
            from bot_v2.safety.sentiment_veto import SentimentVetoGate
            self.sentiment_veto = SentimentVetoGate()
            self.logger.info("✅ Sentiment veto gate initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize sentiment veto gate: {e}")
            self.sentiment_veto = None
        
        # Dark pool detector (Alpaca IEX - free)
        try:
            from bot_v2.data_sources import DarkPoolDetector
            self.dark_pool_detector = DarkPoolDetector()
            self.logger.info("✅ Dark pool detector initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize dark pool detector: {e}")
            self.dark_pool_detector = None
        
        # Earnings calendar filter (yfinance - free)
        try:
            from bot_v2.data_sources import EarningsCalendar
            self.earnings_calendar = EarningsCalendar(days_before=3, days_after=1)
            self.logger.info("✅ Earnings calendar initialized (skip 3d before, 1d after)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize earnings calendar: {e}")
            self.earnings_calendar = None
        
        # Options flow analyzer (Alpaca Options API - free)
        try:
            from bot_v2.data_sources import OptionsFlowAnalyzer
            self.options_analyzer = OptionsFlowAnalyzer()
            self.logger.info("✅ Options flow analyzer initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize options analyzer: {e}")
            self.options_analyzer = None
        
        # Entry quality screening (observation mode - logs but doesn't block)
        try:
            from entry_quality_screener import EntryQualityScreener
            self.entry_screener = EntryQualityScreener(strict_mode=False)
            self.screening_enabled = True  # Feature flag
            self.logger.info("✅ Entry quality screener initialized (OBSERVATION MODE)")
            self.logger.info("   📊 Screening will log quality but NOT block entries")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize entry screener: {e}")
            self.entry_screener = None
            self.screening_enabled = False
        
        # Symbol blacklist manager (automated underperformer filtering)
        try:
            from bot_v2.utils.symbol_blacklist_manager import SymbolBlacklistManager
            self.blacklist_manager = SymbolBlacklistManager()
            blacklisted = self.blacklist_manager.get_blacklisted_symbols()
            self.logger.info(f"✅ Symbol blacklist loaded ({len(blacklisted)} symbols blocked)")
            if blacklisted:
                self.logger.info(f"   🚫 Blacklisted: {', '.join(sorted(blacklisted))}")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize blacklist manager: {e}")
            self.blacklist_manager = None
        
        # Issue 3.2: Sector momentum tracking (Jan 13, 2026)
        try:
            from bot_v2.sector import SectorSpecificExitManager
            self.sector_manager = SectorSpecificExitManager()
            self.logger.info("✅ Sector momentum tracking initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize sector manager: {e}")
            self.sector_manager = None
        
        # Volume threshold for signal generation
        self.volume_threshold = 1.0  # Minimum volume surge ratio
        
        # Temporary rule-based system for Sprint 0
        self.momentum_lookback = 4

        # Keep latest rejection telemetry for downstream logging/reporting.
        self._last_rejection_stats: Dict[str, int] = {}
        self._last_rejection_details: List[str] = []
    
    def _check_market_cap(self, symbol: str, data_loader) -> bool:
        """Check if symbol meets mid-cap requirements ($2B-$10B)"""
        try:
            # Check cache first (with expiry)
            now = datetime.now()
            cache_entry = self._market_cap_cache.get(symbol)
            
            if cache_entry:
                market_cap, cached_at = cache_entry
                cache_age = now - cached_at
                if cache_age < timedelta(hours=MARKET_CAP_CACHE_HOURS):
                    # Use cached value
                    pass
                else:
                    # Cache expired, refresh
                    info = data_loader.get_stock_info(symbol)
                    market_cap = info.get('marketCap', 0) if info else 0
                    self._market_cap_cache[symbol] = (market_cap, now)
            else:
                # No cache, fetch fresh
                info = data_loader.get_stock_info(symbol)
                market_cap = info.get('marketCap', 0) if info else 0
                self._market_cap_cache[symbol] = (market_cap, now)
            
            # Require verified market cap if configured
            if not market_cap:
                if self.config.require_market_cap_verification:
                    self.logger.debug(f"❌ {symbol}: Market cap unavailable (verification required)")
                    return False

            # Check if within mid-cap range
            if market_cap < self.config.min_market_cap:
                self.logger.debug(f"❌ {symbol}: Market cap ${market_cap/1e9:.2f}B < ${self.config.min_market_cap/1e9:.0f}B (too small)")
                return False
            
            if market_cap > self.config.max_market_cap:
                self.logger.debug(f"❌ {symbol}: Market cap ${market_cap/1e9:.2f}B > ${self.config.max_market_cap/1e9:.0f}B (too large)")
                return False
            
            self.logger.debug(f"✅ {symbol}: Market cap ${market_cap/1e9:.2f}B (mid-cap)")
            return True
            
        except Exception as e:
            if self.config.require_market_cap_verification:
                self.logger.warning(f"⚠️ {symbol}: Market cap verification failed: {e}, rejecting by policy")
                return False
            self.logger.warning(f"⚠️ {symbol}: Could not verify market cap: {e}, allowing by default")
            return True  # Allow if we can't verify (fail open)
        self.volume_threshold = 1.0
        
    def set_realtime_prices(self, prices: Dict[str, float]):
        """Inject batch real-time prices from Alpaca IEX before a scan cycle.

        TIER 2 (Feb 25, 2026): Called by launcher before generate_signals().
        Each price overrides data['close'].iloc[-1] in _analyze_symbol(),
        giving EMA/SMA comparisons and momentum calculations real-time data
        instead of yesterday's daily close.
        """
        self._realtime_prices = prices
        if prices:
            self.logger.info(f"📡 Injected {len(prices)} real-time prices from Alpaca IEX")

    def get_last_rejection_stats(self) -> Dict[str, Any]:
        """Return rejection counts/details from the most recent generate_signals call."""
        return {
            "counts": dict(self._last_rejection_stats),
            "details": list(self._last_rejection_details),
            "total_rejected": sum(self._last_rejection_stats.values()) if self._last_rejection_stats else 0,
        }

    def _set_strategy_gate_rejection(self, strategy: str, gate: str, detail: str):
        """Store first-fail setup gate context for rejection telemetry."""
        self._current_rejection = f"{strategy} gate [{gate}] - {detail}"

    def _parse_hhmm_to_minutes(self, value: str, default: str) -> int:
        """Parse HH:MM strings to minutes since midnight with safe defaults."""
        raw = value or default
        try:
            hour_str, minute_str = raw.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
            hour = max(0, min(hour, 23))
            minute = max(0, min(minute, 59))
            return hour * 60 + minute
        except Exception:
            hour_str, minute_str = default.split(":", 1)
            return int(hour_str) * 60 + int(minute_str)

    def _is_within_scan_window(self, now: datetime, start_hhmm: str, end_hhmm: str) -> bool:
        """Return True when now falls within [start, end] inclusive by minute."""
        current_minutes = now.hour * 60 + now.minute
        start_minutes = self._parse_hhmm_to_minutes(start_hhmm, start_hhmm)
        end_minutes = self._parse_hhmm_to_minutes(end_hhmm, end_hhmm)
        return start_minutes <= current_minutes <= end_minutes

    def generate_signals(self, universe: List[str], market_data: Dict[str, pd.DataFrame], 
                        active_positions: Optional[List] = None) -> List[AISignal]:
        """Generate AI signals for given universe
        
        Args:
            universe: List of candidate symbols
            market_data: Historical price data for each symbol
            active_positions: List of currently active positions (for PDT validation)
        """
        # CRITICAL FIX #1: Validate entry candidates to prevent PDT violations
        validated_universe = self._validate_entry_candidates(universe, active_positions or [])
        
        # Issue 3.1: Calculate dynamic confidence threshold based on position count
        active_count = len([p for p in (active_positions or []) if p.status == PositionStatus.ENTERED])
        dynamic_threshold = self.config.get_dynamic_confidence_threshold(active_count)
        
        if dynamic_threshold != self.config.confidence_threshold:
            self.logger.info(
                f"📊 Dynamic threshold: {self.config.confidence_threshold:.0%} → {dynamic_threshold:.0%} "
                f"(positions: {active_count}/{self.config.max_positions_per_day})"
            )
        
        signals = []
        rejection_stats = {
            'sma_reject': 0,
            'momentum_reject': 0,
            'rsi_high': 0,
            'confidence_low': 0,
            'liquidity_low': 0,
            'earnings_blackout': 0,
            'quality_reject': 0,
            'data_insufficient': 0,
            'momentum_gate_reject': 0,
            'swing_gate_reject': 0,
            'other_reject': 0
        }
        rejection_details = []  # Track detailed rejections with confidence scores
        
        for symbol in validated_universe:
            try:
                signal, reject_reason, confidence = self._analyze_symbol_with_reason(symbol, market_data.get(symbol))
                # Use dynamic threshold instead of static
                if signal and signal.confidence >= dynamic_threshold:
                    signals.append(signal)
                elif reject_reason:
                    # Log rejection with confidence score
                    confidence_label = f"{confidence:.1%}" if confidence > 0 else "n/a"
                    rejection_details.append(f"{symbol}: {confidence_label} confidence - {reject_reason}")
                    # Track rejection reasons
                    reason_lower = reject_reason.lower()
                    gate_match = re.search(r'\[(.*?)\]', reject_reason)
                    if gate_match:
                        gate_key = gate_match.group(1).strip().lower().replace(' ', '_')
                        if gate_key:
                            stat_key = f"gate_{gate_key}"
                            rejection_stats[stat_key] = rejection_stats.get(stat_key, 0) + 1
                    if 'momentum gate [' in reason_lower:
                        rejection_stats['momentum_gate_reject'] += 1
                    elif 'swing_pullback gate [' in reason_lower:
                        rejection_stats['swing_gate_reject'] += 1
                    elif 'below 20 ema' in reason_lower or 'sma' in reason_lower or 'below' in reason_lower:
                        rejection_stats['sma_reject'] += 1
                    elif 'ema slope' in reason_lower or 'downtrend' in reason_lower:
                        rejection_stats['sma_reject'] += 1
                    elif 'momentum' in reason_lower or 'falling' in reason_lower:
                        rejection_stats['momentum_reject'] += 1
                    elif 'rsi' in reason_lower:
                        rejection_stats['rsi_high'] += 1
                    elif 'confidence' in reason_lower:
                        rejection_stats['confidence_low'] += 1
                    elif 'liquid' in reason_lower:
                        rejection_stats['liquidity_low'] += 1
                    elif 'earning' in reason_lower:
                        rejection_stats['earnings_blackout'] += 1
                    elif 'quality' in reason_lower:
                        rejection_stats['quality_reject'] += 1
                    elif 'insufficient data' in reason_lower:
                        rejection_stats['data_insufficient'] += 1
                    else:
                        rejection_stats['other_reject'] += 1
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
                rejection_stats['data_insufficient'] += 1
        
        # Log rejection summary
        total_rejected = sum(rejection_stats.values())
        if total_rejected > 0:
            self.logger.info(f"📊 Rejection Summary ({total_rejected} stocks):")
            # Show ALL rejections with confidence scores
            if rejection_details:
                self.logger.info(f"   Confidence scores for rejected candidates:")
                for detail in rejection_details:
                    self.logger.info(f"      • {detail}")
            if rejection_stats['sma_reject'] > 0:
                self.logger.info(f"   • SMA filter: {rejection_stats['sma_reject']} (>10% below 20-EMA trend - OPTIMIZATION: relaxed from >6%)")
            if rejection_stats['momentum_reject'] > 0:
                self.logger.info(f"   • Momentum filter: {rejection_stats['momentum_reject']} (falling knife <-5%)")
            if rejection_stats['rsi_high'] > 0:
                self.logger.info(f"   • RSI too high: {rejection_stats['rsi_high']} (not oversold, RSI >35)")
            if rejection_stats['momentum_gate_reject'] > 0:
                self.logger.info(f"   • Momentum setup gates: {rejection_stats['momentum_gate_reject']} (volume ratio <0.75x, support >4.5%, or 5d return - OPTIMIZATION: relaxed)")
            if rejection_stats['swing_gate_reject'] > 0:
                self.logger.info(f"   • Swing pullback setup gates: {rejection_stats['swing_gate_reject']} (volume ratio <0.65x, support >4.5%, or RSI/price bands - OPTIMIZATION: relaxed)")
            if rejection_stats['confidence_low'] > 0:
                self.logger.info(f"   • Low confidence: {rejection_stats['confidence_low']} (<{self.config.confidence_threshold:.0%} threshold)")
            if rejection_stats['liquidity_low'] > 0:
                self.logger.info(f"   • Insufficient liquidity: {rejection_stats['liquidity_low']} (<$500K avg)")
            if rejection_stats['earnings_blackout'] > 0:
                self.logger.info(f"   • Earnings blackout: {rejection_stats['earnings_blackout']} (3d before/1d after)")
            if rejection_stats['quality_reject'] > 0:
                self.logger.info(f"   • Quality screen: {rejection_stats['quality_reject']} (failed quality check)")
            if rejection_stats['other_reject'] > 0:
                self.logger.info(f"   • Other strategy/filter rejects: {rejection_stats['other_reject']}")
            if rejection_stats['data_insufficient'] > 0:
                self.logger.info(f"   • Data errors: {rejection_stats['data_insufficient']}")

        # Persist stats so launcher/reporting can include rejection reasons in summaries.
        self._last_rejection_stats = dict(rejection_stats)
        self._last_rejection_details = list(rejection_details)
        
        # Sort by confidence and limit to max positions
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals[:self.config.max_positions_per_day]
    
    def generate_signal(self, symbol: str, market_data: pd.DataFrame, 
                       current_positions: Optional[List] = None) -> Optional[AISignal]:
        """Generate a single AI signal for a symbol (used for late-entry scanning)
        
        Args:
            symbol: Symbol to analyze
            market_data: Historical price data for the symbol
            current_positions: List of currently active positions (for PDT validation)
            
        Returns:
            AISignal if valid signal found, None otherwise
        """
        try:
            # Validate entry candidate (check PDT/D+1 rules)
            active_symbols = {pos.symbol.upper() for pos in (current_positions or [])
                            if pos.status == PositionStatus.ENTERED}
            
            if symbol.upper() in active_symbols:
                self.logger.debug(f"{symbol}: Skipped - active position exists (D+1 rule)")
                return None
            
            # Analyze symbol
            return self._analyze_symbol(symbol, market_data)
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    def _analyze_symbol_with_reason(self, symbol: str, data: Optional[pd.DataFrame]) -> tuple:
        """
        Analyze symbol and return (signal, rejection_reason, confidence_score)
        Used for detailed rejection tracking
        """
        if data is None or len(data) < self.momentum_lookback + 1:
            return (None, "Insufficient data", 0.0)
        
        try:
            # Store rejection reason and confidence in instance variables
            self._current_rejection = None
            self._current_confidence = 0.0
            signal = self._analyze_symbol(symbol, data)
            
            if signal:
                return (signal, None, signal.confidence)
            else:
                # Return the rejection reason and confidence captured during analysis
                return (None, self._current_rejection or "Unknown rejection", self._current_confidence)
        except Exception as e:
            return (None, f"Error: {str(e)}", 0.0)
    
    def _validate_entry_candidates(self, candidates: List[str], active_positions: List) -> List[str]:
        """
        CRITICAL: Remove any symbols that already have active positions (D+1 rule enforcement)
        This prevents PDT violations like the CRM issue on Oct 22.
        Also filters out blacklisted symbols and same-day exits.
        
        Args:
            candidates: List of candidate symbols to validate
            active_positions: List of currently active positions
        """
        active_symbols = {pos.symbol.upper() for pos in active_positions 
                         if pos.status == PositionStatus.ENTERED}
        
        # Remove active positions (D+1 rule)
        valid = [sym for sym in candidates if sym.upper() not in active_symbols]
        
        filtered = set(c.upper() for c in candidates) - set(v.upper() for v in valid)
        if filtered:
            self.logger.warning(
                f"⚠️ D+1 Rule: Filtered {len(filtered)} symbols with active positions: {filtered}"
            )
            self.logger.warning(
                f"   These symbols cannot be re-entered until existing positions are closed"
            )
        
        # SAME-DAY RE-ENTRY BLOCK: Don't buy back stocks we sold today
        # This prevents buying back at worse prices (e.g., NTLA sold $11.43, rebought $11.97)
        today_exits = getattr(self, '_today_exits', set())
        same_day_blocks = [s for s in valid if s.upper() in today_exits]
        if same_day_blocks:
            self.logger.warning(
                f"🚫 Same-Day Block: {same_day_blocks} sold today, blocking re-entry"
            )
            valid = [s for s in valid if s.upper() not in today_exits]
        
        # Remove blacklisted symbols
        if self.blacklist_manager:
            blacklisted_in_candidates = [s for s in valid if self.blacklist_manager.is_blacklisted(s)]
            if blacklisted_in_candidates:
                self.logger.warning(
                    f"⚠️ Blacklist Filter: Removed {len(blacklisted_in_candidates)} chronic losers: {blacklisted_in_candidates}"
                )
                valid = [s for s in valid if not self.blacklist_manager.is_blacklisted(s)]
        
        return valid
    
    def record_exit(self, symbol: str):
        """Record that a symbol was exited today (blocks same-day re-entry)"""
        if not hasattr(self, '_today_exits'):
            self._today_exits = set()
        if not hasattr(self, '_exit_date'):
            self._exit_date = datetime.now().date()
        
        # Reset if new day
        if datetime.now().date() != self._exit_date:
            self._today_exits = set()
            self._exit_date = datetime.now().date()
        
        self._today_exits.add(symbol.upper())
        self.logger.info(f"📝 Recorded exit: {symbol} (blocked for same-day re-entry)")
    
    def _analyze_symbol(self, symbol: str, data: Optional[pd.DataFrame]) -> Optional[AISignal]:
        """Analyze individual symbol with enhanced quality scoring"""
        if data is None or len(data) < self.momentum_lookback + 1:
            return None

        try:
            # Initialize rejection tracking
            rejection_reasons = []
            
            # Normalize column names (handle both upper and lowercase)
            data_normalized = data.copy()
            data_normalized.columns = [col.lower() for col in data_normalized.columns]
            
            # TIER 2 (Feb 25, 2026): Override last close with Alpaca real-time price.
            # Indicators (RSI, EMA, SMA) still use full daily history for accuracy,
            # but comparisons like "price > EMA" and "5-day momentum" use real-time.
            rt_price = self._realtime_prices.get(symbol)
            if rt_price is not None and not data_normalized.empty:
                data_normalized.loc[data_normalized.index[-1], 'close'] = rt_price
                self.logger.debug(f"   📡 {symbol}: Using Alpaca real-time ${rt_price:.2f} (daily close was ${data['close'].iloc[-1]:.2f})")
            
            # ═══════════════════════════════════════════════════════════════
            # SWING CONTINUATION FILTER (Feb 13, 2026 — replaced mean-reversion tolerance)
            # ═══════════════════════════════════════════════════════════════
            # External analysis: The #1 structural gap is allowing longs below the 20 EMA.
            # Old filter let entries up to 6% below SMA (mean-reversion logic).
            # New filter: Price must be ABOVE 20 EMA AND 20 EMA slope must be positive.
            # This single change is expected to move win rate from 42% → 46-48%.
            # ═══════════════════════════════════════════════════════════════
            if len(data_normalized) >= 20:
                # Use EMA (more responsive than SMA for trend detection)
                ema_20 = data_normalized['close'].ewm(span=20, adjust=False).mean()
                current_ema = ema_20.iloc[-1]
                current_price = data_normalized['close'].iloc[-1]
                
                # RULE 1: Price should be above 20 EMA (directional bias), with a small
                # configurable tolerance to avoid rejecting borderline prints around the EMA.
                ema_break_tolerance = getattr(self.config, 'momentum_ema_break_tolerance_pct', 0.0)
                ema_floor = current_ema * (1 - max(ema_break_tolerance, 0.0))
                if current_price < ema_floor:
                    price_below_pct = ((current_ema - current_price) / current_ema) * 100
                    self.logger.info(
                        f"   ❌ {symbol}: Price ${current_price:.2f} below 20 EMA ${current_ema:.2f} "
                        f"({price_below_pct:.1f}% below — outside tolerance {ema_break_tolerance:.2%})"
                    )
                    self._current_rejection = f"Below 20 EMA ({price_below_pct:.1f}% below trend)"
                    return None
                
                # RULE 2: 20 EMA slope must be positive over last 3 bars
                # This confirms the trend is actively rising, not just sideways
                if len(ema_20) >= 4:
                    ema_3_bars_ago = ema_20.iloc[-4]
                    ema_slope = current_ema - ema_3_bars_ago
                    ema_slope_pct = (ema_slope / ema_3_bars_ago) * 100
                    
                    # TIER 1 FIX (Feb 25, 2026): Loosened from <= 0 to < -0.5%
                    # Old filter rejected ALL sideways markets (slope=0). This killed
                    # signal generation — 86% of scans returned zero signals.
                    # Now allows flat/slightly declining trends, only rejects clear downtrends.
                    # Jul 15: Further loosened to -2.0% to reduce sma_reject in choppy tape.
                    if ema_slope_pct < -2.0:
                        self.logger.info(
                            f"   ❌ {symbol}: 20 EMA slope too negative ({ema_slope_pct:+.2f}% over 3 bars — downtrend)"
                        )
                        self._current_rejection = f"20 EMA slope too negative ({ema_slope_pct:+.2f}%)"
                        return None
                    else:
                        self.logger.debug(
                            f"   ✅ {symbol}: 20 EMA trend confirmed — price ${current_price:.2f} > EMA ${current_ema:.2f}, "
                            f"slope {ema_slope_pct:+.2f}% over 3 bars"
                        )
            
            # MOMENTUM CONFIRMATION: 5-day momentum filter (Nov 28 addition)
            # Dec 8: Loosened from -3% to -5% for mean reversion (utilities/staples drop deeper)
            # Prevents catching falling knives - but allows deeper oversold for quality stocks
            if len(data_normalized) >= 5:
                five_day_ago_price = data_normalized['close'].iloc[-5]
                current_price = data_normalized['close'].iloc[-1]
                five_day_momentum = (current_price - five_day_ago_price) / five_day_ago_price
                
                if five_day_momentum < -0.08:  # Loosened to -8% — only reject sharp downtrends
                    self.logger.info(
                        f"   ❌ {symbol}: 5-day momentum {five_day_momentum*100:.1f}% (>-8% = falling knife)"
                    )
                    self._current_rejection = f"Momentum falling knife ({five_day_momentum*100:.1f}%)"
                    return None
            
            # ═══════════════════════════════════════════════════════════════
            # 3-STRATEGY STACK FOR D+1 SWING TRADING (Nov 24, 2025)
            # ═══════════════════════════════════════════════════════════════
            # Based on comprehensive backtest (15 strategies, 2011-2024):
            # 
            # STRATEGY 1: Mean Reversion RSI - +2.62%, 56.2% WR, 0.92 tr/wk
            # STRATEGY 2: Gap & Go - +2.78%, 45.2% WR, 1.71 tr/wk
            # STRATEGY 3: Double Bottom - +3.17%, 46% WR, 1.11 tr/wk
            #
            # Expected on 500 stocks: 40-90 trades/week, 5-8% monthly return
            # ═══════════════════════════════════════════════════════════════
            
            # Import RSI calculation (modular approach)
            try:
                from core.indicators import calculate_rsi
            except ImportError:
                # Fallback for bot_v2 modular structure
                def calculate_rsi(data, window=14):
                    """Simple RSI calculation fallback"""
                    delta = data['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    data_copy = data.copy()
                    data_copy['rsi'] = rsi
                    return data_copy
            
            # Calculate RSI(7) - optimal period from optimization
            df_with_rsi = calculate_rsi(data_normalized, window=7)
            current_rsi = df_with_rsi['rsi'].iloc[-1]
            
            # Get adaptive parameters if enabled
            if self.adaptive_params_enabled and self.adaptive_manager:
                adaptive_params = self.adaptive_manager.get_adaptive_parameters(symbol, data_normalized)
                rsi_entry_threshold = adaptive_params['rsi_entry']
                rsi_exit_threshold = adaptive_params['rsi_exit']
                confidence_threshold = adaptive_params['confidence_threshold']
                stop_loss_pct = adaptive_params['stop_loss_pct']
                profit_target_pct = adaptive_params['profit_target_pct']
                self.logger.debug(f"{symbol} adaptive: RSI entry={rsi_entry_threshold}, "
                                f"exit={rsi_exit_threshold}, conf={confidence_threshold:.2f}")
            else:
                # Static defaults (Nov 27: RSI relaxed 30→35 for more signals)
                rsi_entry_threshold = 35
                rsi_exit_threshold = 70
                confidence_threshold = self.config.confidence_threshold
                stop_loss_pct = self.config.stop_loss_pct
                profit_target_pct = self.config.profit_target_pct
            
            # Volume/Liquidity check (Dec 4: Changed from spike to liquidity)
            # OLD: Required 1.2x volume spike (day trading concept)
            # NEW: Check average dollar volume for liquidity (D+1 swing trading)
            avg_volume_20d = data_normalized['volume'].tail(20).mean()
            current_volume = data_normalized['volume'].iloc[-1]
            volume_surge = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
            volume_ratio = volume_surge / max(self.volume_threshold, 1e-6)
            volume_ratio_capped = min(volume_ratio, 2.5)
            
            # LIQUIDITY CHECK: Average dollar volume >= $500K/day (Dec 4 fix)
            # This ensures we can enter/exit positions without slippage
            avg_dollar_volume = avg_volume_20d * current_price
            is_liquid = avg_dollar_volume >= 500_000  # $500K minimum daily liquidity
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # DUAL-STRATEGY SYSTEM (Jan 8, 2026): GAP & GO + FADE/SHORT
            # ═══════════════════════════════════════════════════════════════════════════════
            # Based on 30-day D+1 backtest (Dec 9, 2025 - Jan 8, 2026):
            # 
            # PRIMARY: Gap & Go - +830%, 54.3% WR, 748 trades/month (70% capital)
            # BACKUP:  Fade/Short - +174%, 62.8% WR, 914 trades/month (30% capital)
            # Combined: +633%/month with only 5.9% conflict rate
            #
            # Gap & Go: Morning gaps 2-8% at open, RSI < 75, hold overnight
            # Fade/Short: RSI > 70 + 10%+ above SMA20, short overbought, cover next day
            # ═══════════════════════════════════════════════════════════════════════════════
            
            # Initialize all strategy signals
            mean_reversion_signal = False
            mean_reversion_confidence = 0.0
            gap_and_go_signal = False
            gap_and_go_confidence = 0.0
            fade_short_signal = False
            fade_short_confidence = 0.0
            momentum_signal = False
            momentum_confidence = 0.0
            swing_pullback_signal = False
            swing_pullback_confidence = 0.0
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY 1: GAP & GO (PRIMARY - 70% allocation)
            # ───────────────────────────────────────────────────────────────
            # Backtest: +830% over 30 days, 54.3% win rate, 748 trades
            # Entry: Morning gap 2-8% at open (9:35 AM)
            # Filter: RSI < 75, gap holding (close > prev_close)
            # Exit: Next day (D+1) at open/intraday/close
            
            if self.config.enable_gap_and_go and len(data_normalized) >= 2:
                gap_signal_result = self._check_gap_and_go(symbol, data_normalized)
                if gap_signal_result:
                    gap_and_go_signal = True
                    gap_and_go_confidence = gap_signal_result['confidence']
                    self.logger.info(
                        f"   ✅ {symbol} GAP & GO: +{gap_signal_result['gap_pct']*100:.1f}% gap, "
                        f"RSI {gap_signal_result['rsi']:.1f}, conf={gap_and_go_confidence:.2f}"
                    )
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY 2: FADE/SHORT (SECONDARY - 15% allocation)
            # ───────────────────────────────────────────────────────────────
            # Backtest: +174% over 30 days, 62.8% win rate, 914 trades
            # Entry: RSI > 70 + 10%+ above SMA20 (overbought extreme)
            # Exit: Next day (D+1) when reverses or hits stop
            
            if self.config.enable_fade_short and len(data_normalized) >= 20:
                fade_signal_result = self._check_fade_short(symbol, data_normalized, current_rsi)
                if fade_signal_result:
                    fade_short_signal = True
                    fade_short_confidence = fade_signal_result['confidence']
                    self.logger.info(
                        f"   ✅ {symbol} FADE/SHORT: RSI {fade_signal_result['rsi']:.1f}, "
                        f"+{fade_signal_result['extension_pct']*100:.1f}% above SMA, "
                        f"conf={fade_short_confidence:.2f}"
                    )
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY 3: MOMENTUM (TERTIARY - 15% allocation)
            # ───────────────────────────────────────────────────────────────
            # Entry: Price above SMA20, RSI 45-65, +3-15% in 5 days
            # Best for: Mid-day trend continuation entries
            # Exit: Next day (D+1) or profit target
            
            if getattr(self.config, 'enable_momentum', True) and len(data_normalized) >= 20:
                momentum_signal_result = self._check_momentum(symbol, data_normalized, current_rsi)
                if momentum_signal_result:
                    momentum_signal = True
                    momentum_confidence = momentum_signal_result['confidence']
                    self.logger.info(
                        f"   ✅ {symbol} MOMENTUM: 5d return +{momentum_signal_result['five_day_return']*100:.1f}%, "
                        f"RSI {momentum_signal_result['rsi']:.1f}, ADR {momentum_signal_result['adr']*100:.1f}%, "
                        f"support {momentum_signal_result['support_name']} ({momentum_signal_result['support_distance']*100:.1f}%), "
                        f"pullback vol {momentum_signal_result['pullback_volume_ratio']:.2f}x, bounce vol {momentum_signal_result['bounce_volume_ratio']:.2f}x, "
                        f"conf={momentum_confidence:.2f}"
                    )

            # ───────────────────────────────────────────────────────────────
            # STRATEGY 4: SWING PULLBACK (CHOPPY/WEAK-TREND FALLBACK)
            # ───────────────────────────────────────────────────────────────
            # Objective: keep opportunity flow in range-bound tape without forcing trend entries.
            # Hold intent: 1-3 days.
            if getattr(self.config, 'enable_swing_pullback', True) and len(data_normalized) >= 20:
                if self._is_choppy_or_weak_trend(data_normalized):
                    pullback_result = self._check_swing_pullback(symbol, data_normalized, current_rsi)
                    if pullback_result:
                        swing_pullback_signal = True
                        swing_pullback_confidence = pullback_result['confidence']
                        self.logger.info(
                            f"   ✅ {symbol} SWING PULLBACK: RSI {pullback_result['rsi']:.1f}, "
                            f"3d return {pullback_result['three_day_return']*100:+.1f}%, "
                            f"support {pullback_result['support_name']} ({pullback_result['support_distance']*100:.1f}%), "
                            f"pullback vol {pullback_result['pullback_volume_ratio']:.2f}x, bounce vol {pullback_result['bounce_volume_ratio']:.2f}x, "
                            f"conf={swing_pullback_confidence:.2f}"
                        )
            
            # Store confidence for rejection tracking
            self._current_confidence = max(
                gap_and_go_confidence,
                fade_short_confidence,
                momentum_confidence,
                swing_pullback_confidence,
                mean_reversion_confidence,
            )
            
            # ───────────────────────────────────────────────────────────────
            # CONFLICT RESOLUTION & STRATEGY SELECTION
            # ───────────────────────────────────────────────────────────────
            # Priority: Gap & Go > Fade/Short > Momentum
            # Gap & Go has best returns, Momentum is for fallback entries
            
            best_strategy = None
            best_signal = False
            base_confidence = 0.0
            
            # Priority 1: Gap & Go (70% allocation, +830% returns)
            if gap_and_go_signal and gap_and_go_confidence >= confidence_threshold:
                if is_liquid:
                    best_strategy = 'GAP_AND_GO'
                    best_signal = True
                    base_confidence = gap_and_go_confidence
                    if fade_short_signal or momentum_signal:
                        self.logger.info(f"   🔄 {symbol}: Gap & Go takes priority (conflict resolution)")
            
            # Priority 2: Fade/Short (15% allocation, +174% returns, 62.8% WR)
            elif fade_short_signal and fade_short_confidence >= confidence_threshold:
                if is_liquid:
                    best_strategy = 'FADE_SHORT'
                    best_signal = True
                    base_confidence = fade_short_confidence
                    if momentum_signal:
                        self.logger.info(f"   🔄 {symbol}: Fade/Short takes priority over Momentum")
            
            # Priority 3: Momentum (15% allocation, trend continuation)
            elif momentum_signal and momentum_confidence >= confidence_threshold:
                if is_liquid:
                    best_strategy = 'MOMENTUM'
                    best_signal = True
                    base_confidence = momentum_confidence

            # Priority 4: Swing Pullback (range-bound fallback for 1-3 day holds)
            elif swing_pullback_signal and swing_pullback_confidence >= confidence_threshold:
                if is_liquid:
                    best_strategy = 'SWING_PULLBACK'
                    best_signal = True
                    base_confidence = swing_pullback_confidence
            
            # No signal if no strategy triggers
            if not best_signal:
                if not is_liquid:
                    self.logger.info(
                        f"   ❌ {symbol}: Insufficient liquidity (${avg_dollar_volume:,.0f} < $500K)"
                    )
                    self._current_rejection = f"Insufficient liquidity (${avg_dollar_volume:,.0f})"
                elif not gap_and_go_signal and not fade_short_signal and not momentum_signal and not swing_pullback_signal:
                    self.logger.info(
                        f"   ❌ {symbol}: No strategy trigger - Gap={gap_and_go_signal}, "
                        f"Fade={fade_short_signal}, Momentum={momentum_signal}, Pullback={swing_pullback_signal}, RSI={current_rsi:.1f}"
                    )
                    if not self._current_rejection:
                        self._current_rejection = f"No strategy trigger (RSI={current_rsi:.1f})"
                else:
                    self.logger.info(
                        f"   ❌ {symbol}: Confidence too low - best={base_confidence:.2f} < {confidence_threshold:.2f}"
                    )
                    self._current_rejection = f"Low confidence ({base_confidence:.2f} < {confidence_threshold:.2f})"
                rejection_reasons.append(f"No valid strategy signal")
                return None

            # Enhance with quality scoring if available
            if best_signal and self.quality_scorer and len(data_normalized) >= 100:
                try:
                    quality_result = self.quality_scorer.score_signal(
                        symbol=symbol,
                        current_data=data_normalized,
                        current_price=data_normalized['close'].iloc[-1]
                    )
                    
                    quality_score = quality_result['total_score']
                    quality_tier = quality_result['quality_tier']
                    
                    # Convert quality score (0-100) to confidence boost
                    # Strong quality (70+) → 2x-3x confidence
                    # Medium quality (40-70) → 1.5x-2x confidence
                    # Weak quality (<40) → 1x confidence (no boost)
                    quality_multiplier = 1.0 + (quality_score / 50.0)  # 0→1x, 50→2x, 100→3x
                    enhanced_confidence = min(base_confidence * quality_multiplier, 1.0)
                    
                    self.logger.info(
                        f"🎯 {symbol} [{best_strategy}]: base_conf={base_confidence:.3f}, "
                        f"quality={quality_score:.1f} ({quality_tier}), "
                        f"multiplier={quality_multiplier:.2f}x → final={enhanced_confidence:.3f}"
                    )
                    confidence = enhanced_confidence
                except Exception as e:
                    self.logger.debug(f"Quality scoring failed for {symbol}: {e}")
                    confidence = base_confidence
            else:
                confidence = base_confidence
            
            # ═══════════════════════════════════════════════════════════════
            # ENHANCED DATA SOURCES (Dec 12, 2025)
            # ═══════════════════════════════════════════════════════════════
            # Check earnings calendar FIRST - skip if earnings too close
            if self.earnings_calendar:
                try:
                    earnings_info = self.earnings_calendar.check_earnings(symbol)
                    if earnings_info['should_skip']:
                        self.logger.warning(f"❌ SKIP {symbol}: {self.earnings_calendar.format_earnings_log(symbol, earnings_info)}")
                        self._current_rejection = "Earnings blackout (3d before/1d after)"
                        return None
                    elif earnings_info['has_earnings_soon']:
                        self.logger.info(f"   {self.earnings_calendar.format_earnings_log(symbol, earnings_info)}")
                except Exception as e:
                    self.logger.debug(f"{symbol}: Earnings check failed: {e}")
            
            # SENTIMENT & DARK POOL ENHANCEMENT (Nov 26, 2025)
            # ═══════════════════════════════════════════════════════════════
            # Check news sentiment and institutional activity (free Alpaca data)
            # Nov 28: Updated to use CONTRARIAN sentiment logic for mean reversion
            # For mean reversion: mildly bearish + dark pool = ideal (smart money buying dip)
            sentiment_boost = 0.0
            dark_pool_boost = 0.0
            options_boost = 0.0
            has_dark_pool_buying = False
            sentiment = None
            
            # Dark Pool Activity Check FIRST (needed for contrarian sentiment logic)
            if self.dark_pool_detector:
                try:
                    dark_pool_activity = self.dark_pool_detector.detect_institutional_activity(
                        symbol, hours_lookback=4
                    )
                    
                    # Log institutional activity
                    if dark_pool_activity['is_active']:
                        self.logger.info(f"   {self.dark_pool_detector.format_dark_pool_log(symbol, dark_pool_activity)}")
                    
                    # Check if dark pool shows buying
                    has_dark_pool_buying = dark_pool_activity['is_active'] and dark_pool_activity.get('confidence_boost', 0) > 0
                    
                    # Apply dark pool boost
                    dark_pool_boost = dark_pool_activity['confidence_boost']
                    
                except Exception as e:
                    self.logger.debug(f"{symbol}: Dark pool check failed: {e}")
            
            # News Sentiment Check (Alpaca News API) - Using CONTRARIAN logic for mean reversion
            if self.sentiment_analyzer:
                try:
                    sentiment = self.sentiment_analyzer.get_sentiment(symbol, hours_lookback=24)
                    
                    # Log sentiment
                    if sentiment['article_count'] > 0:
                        self.logger.info(f"   {self.sentiment_analyzer.format_sentiment_log(symbol, sentiment)}")
                    
                    # NEW FIX #3: Check for hard veto on disaster news
                    if self.sentiment_veto:
                        should_veto, reason, severity = self.sentiment_veto.check_veto(sentiment, symbol)
                        if should_veto:
                            veto_msg = self.sentiment_veto.format_veto_message(symbol, (should_veto, reason, severity))
                            self.logger.warning(veto_msg)
                            return None  # Hard reject - no scoring possible
                        elif severity == 'soft':
                            # Log soft veto as warning but don't block
                            self.logger.warning(f"⚠️  {symbol}: {reason}")
                    
                    # Map strategy name for sentiment scoring
                    sentiment_strategy = 'gap_go' if best_strategy == 'GAP_AND_GO' else \
                                        'fade_short' if best_strategy == 'FADE_SHORT' else \
                                        'mean_reversion'  # Default for MOMENTUM and others
                    
                    # Check if we should skip trade based on strategy
                    if self.sentiment_analyzer.should_skip_trade(sentiment, strategy=sentiment_strategy):
                        self.logger.warning(f"❌ SKIP {symbol}: {sentiment['signal']} sentiment conflicts with {best_strategy}")
                        return None
                    
                    # Use strategy-specific adjustment
                    sentiment_boost = self.sentiment_analyzer.get_sentiment_adjustment(
                        sentiment,
                        strategy=sentiment_strategy,
                        has_dark_pool_buying=has_dark_pool_buying
                    )
                    
                    # Log special conditions
                    if has_dark_pool_buying and sentiment['signal'] == 'BEAR':
                        self.logger.info(f"   🎯 CONTRARIAN SETUP: {symbol} - Bearish news + Dark Pool buying = smart money dip buy")
                    
                except Exception as e:
                    self.logger.debug(f"{symbol}: Sentiment check failed: {e}")
            
            # NEW FIX #2: Apply data quality penalties
            if sentiment:
                if sentiment['data_quality'] == 'missing':
                    # No news in 24h = uncertainty penalty
                    original_conf = confidence
                    confidence *= 0.80  # Multiply confidence by 0.80 (20% reduction)
                    self.logger.debug(f"   ⚠️  {symbol}: No news in 24h - applying -20% confidence penalty ({original_conf:.3f} → {confidence:.3f})")
                
                elif sentiment['data_quality'] == 'low':
                    # Single article = low reliability
                    original_conf = confidence
                    confidence *= 0.85  # 15% reduction
                    self.logger.debug(f"   ⚠️  {symbol}: Low sentiment confidence (1 article) - applying -15% penalty ({original_conf:.3f} → {confidence:.3f})")
                
                elif sentiment['data_quality'] == 'medium':
                    # 2-3 articles = moderate reliability
                    quality_conf = sentiment.get('quality_confidence', 0.5)
                    if quality_conf < 0.6:
                        original_conf = confidence
                        confidence *= 0.95  # 5% reduction
                        self.logger.debug(f"   ⚠️  {symbol}: Medium sentiment confidence - applying -5% penalty ({original_conf:.3f} → {confidence:.3f})")
                
                # Check if confidence dropped below threshold due to data quality
                if confidence < confidence_threshold:
                    self.logger.warning(f"❌ {symbol}: Below confidence threshold ({confidence:.1%}) due to data quality issues")
                    return None
            
            # Options Flow Check (Alpaca Options API)
            if self.options_analyzer:
                try:
                    options_flow = self.options_analyzer.analyze_flow(symbol)
                    
                    # Log options activity
                    if options_flow['institutional_signal'] != 'NEUTRAL':
                        self.logger.info(f"   {self.options_analyzer.format_flow_log(symbol, options_flow)}")
                    
                    # Check if we should skip (strong bearish flow)
                    if self.options_analyzer.should_skip_trade(options_flow):
                        self.logger.warning(f"❌ SKIP {symbol}: Strong bearish options flow (P/C={options_flow['put_call_ratio']:.2f})")
                        return None
                    
                    # Apply options boost
                    options_boost = options_flow['confidence_boost']
                    
                except Exception as e:
                    self.logger.debug(f"{symbol}: Options flow check failed: {e}")
            
            # Apply all confidence adjustments (sentiment + dark pool + options)
            # FIX #4: Use multiplicative gating for negative adjustments (more severe impact)
            if sentiment_boost != 0 or dark_pool_boost != 0 or options_boost != 0:
                original_confidence = confidence
                
                # Apply negative adjustments multiplicatively (they reduce confidence more)
                # Apply positive adjustments additively (they enhance confidence)
                
                # Sentiment adjustment
                if sentiment_boost < 0:
                    # Negative: multiply down (e.g., -0.20 → 0.80x)
                    confidence *= (1.0 + sentiment_boost)
                else:
                    # Positive: add up
                    confidence = min(confidence + sentiment_boost, 1.0)
                
                # Dark pool adjustment
                if dark_pool_boost < 0:
                    confidence *= (1.0 + dark_pool_boost)
                else:
                    confidence = min(confidence + dark_pool_boost, 1.0)
                
                # Options adjustment
                if options_boost < 0:
                    confidence *= (1.0 + options_boost)
                else:
                    confidence = min(confidence + options_boost, 1.0)
                
                # Ensure within bounds [0, 1]
                confidence = max(min(confidence, 1.0), 0.0)
                
                if confidence != original_confidence:
                    adjustment_type = "contrarian" if sentiment and sentiment['signal'] in ['BEAR', 'STRONG_BEAR'] else "standard"
                    self.logger.info(
                        f"   🔄 Confidence adjusted ({adjustment_type}): {original_confidence:.3f} → {confidence:.3f} "
                        f"(sentiment={sentiment_boost:+.3f}, dark_pool={dark_pool_boost:+.3f}, options={options_boost:+.3f})"
                    )
            
            # Issue 1.3: Apply time-weighted scoring (Jan 13, 2026)
            if best_signal:
                original_conf = confidence
                confidence = self._apply_time_weight(best_strategy, confidence)
                if confidence != original_conf:
                    self.logger.debug(f"   ⏰ Time-weighted: {original_conf:.3f} → {confidence:.3f}")
            
            # Issue 3.3: Pre-market volume filter (Jan 13, 2026)
            # Boost confidence if pre-market volume is abnormally high
            premarket_boost = 0.0
            if len(data_normalized) >= 2 and best_signal:
                # Check if current volume is significantly above average (2x+)
                if volume_surge >= 2.0:
                    premarket_boost = 0.10  # 10% boost for high volume
                    self.logger.info(
                        f"   📊 High volume detected: {volume_surge:.1f}x average → +{premarket_boost*100:.0f}% confidence"
                    )
                elif volume_surge >= 1.5:
                    premarket_boost = 0.05  # 5% boost for elevated volume
                
                if premarket_boost > 0:
                    original_conf = confidence
                    confidence = min(confidence + premarket_boost, 1.0)
            
            # Issue 3.2: Sector momentum factor (Jan 13, 2026)
            # Boost confidence for symbols in high-performing sectors
            sector_boost = 0.0
            current_sector = None
            if self.sector_manager and best_signal:
                current_sector = self.sector_manager.symbol_to_sector.get(symbol)
                if current_sector:
                    # Get sector configuration
                    sector_config = self.sector_manager.SECTOR_RULES.get(current_sector, {})
                    
                    # Boost for high win rate sectors (Airlines/Travel: 51.6%)
                    if current_sector in ['Airlines/Travel', 'Cruise']:
                        sector_boost = 0.08  # 8% boost for proven D+1 sectors
                        self.logger.info(
                            f"   ✈️ {current_sector} sector boost: +{sector_boost*100:.0f}% confidence"
                        )
                    # Small penalty for underperforming sectors (Consumer: 39.2%)
                    elif current_sector == 'Consumer':
                        sector_boost = -0.05  # 5% penalty for weak sector
                        self.logger.debug(
                            f"   🍔 {current_sector} sector penalty: {sector_boost*100:.0f}% confidence"
                        )
                    
                    if sector_boost != 0:
                        original_conf = confidence
                        confidence = min(max(confidence + sector_boost, 0.0), 1.0)
            # ═══════════════════════════════════════════════════════════════

            # Strategy diagnostics logging
            if best_signal:
                self.logger.info(
                    f"🎯 {symbol} [{best_strategy}]: RSI={current_rsi:.1f}, "
                    f"vol_surge={volume_surge:.2f}x, confidence={confidence:.3f}"
                )
                
                # Log strategy-specific details
                if best_strategy == 'GAP_AND_GO' and len(data_normalized) >= 2:
                    today_open = data_normalized['open'].iloc[-1]
                    yesterday_close = data_normalized['close'].iloc[-2]
                    gap_pct = (today_open - yesterday_close) / yesterday_close
                    self.logger.info(f"   📈 Gap: {gap_pct*100:+.1f}% (${yesterday_close:.2f} → ${today_open:.2f})")
                elif best_strategy == 'DOUBLE_BOTTOM' and len(data_normalized) >= 20:
                    recent_lows = data_normalized['low'].tail(20)
                    min_low = recent_lows.min()
                    support_tests = (recent_lows <= min_low * 1.02).sum()
                    self.logger.info(f"   🔄 Support tests: {support_tests} at ${min_low:.2f}")
                elif best_strategy == 'MEAN_REVERSION_RSI':
                    self.logger.info(f"   📉 RSI oversold: {current_rsi:.1f} (threshold: 30)")

            # Entry signal generation (if best strategy found)
            if best_signal and confidence >= confidence_threshold:
                # Entry quality screening (observation mode - log but don't block)
                if self.screening_enabled and self.entry_screener:
                    try:
                        # Note: momentum_score not calculated for all strategies
                        # Using RSI as proxy for screening
                        should_enter, quality_level, reason = self.entry_screener.screen_entry(
                            symbol=symbol,
                            momentum=0.0,  # Not used for mean reversion/double bottom
                            volume_surge=volume_surge,
                            sector=None  # TODO: Add sector lookup
                        )
                        
                        # Log screening result with emoji indicators
                        quality_emoji = {
                            'IDEAL': '🟢',
                            'GOOD': '🟡', 
                            'ACCEPTABLE': '🟠',
                            'REJECT': '🔴'
                        }.get(quality_level, '⚪')
                        
                        self.logger.info(
                            f"📊 ENTRY SCREENING: {symbol} [{best_strategy}] → {quality_emoji} {quality_level}: {reason}"
                        )
                        
                        # Observation mode: Log only, don't block trades
                        # Future: Add soft enforcement option (block only REJECT quality)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Entry screening failed for {symbol}: {e}")
                
                # CRITICAL FIX (Nov 19): Get REAL-TIME price from Alpaca, not cached historical data
                # Bug discovered: MSTZ showed $10.59 (cached), actual fill $12.56 (18.6% slippage!)
                # Solution: Always fetch live price before creating signal
                realtime_price = None
                if self.price_fetcher:
                    try:
                        realtime_price = self.price_fetcher(symbol)
                    except Exception as e:
                        self.logger.debug(f"Price fetcher failed for {symbol}: {e}")
                
                if realtime_price is None:
                    # Fallback to historical if real-time fetch fails
                    realtime_price = data_normalized['close'].iloc[-1]
                    self.logger.debug(f"{symbol}: Using cached price ${realtime_price:.2f}")
                else:
                    # Log price source for transparency
                    cached_price = data_normalized['close'].iloc[-1]
                    price_diff_pct = abs(realtime_price - cached_price) / cached_price
                    if price_diff_pct > 0.02:  # >2% difference
                        self.logger.warning(
                            f"⚠️ {symbol}: Price mismatch - cached: ${cached_price:.2f}, "
                            f"real-time: ${realtime_price:.2f} ({price_diff_pct:.1%} diff)"
                        )
                
                # Calculate stop loss and profit target based on strategy
                # (if not already set by adaptive parameters)
                if not self.adaptive_params_enabled:
                    if best_strategy == "GAP_AND_GO":
                        stop_loss_pct = self.config.gap_and_go_stop_loss_pct
                        profit_target_pct = self.config.gap_and_go_profit_target_pct
                    elif best_strategy == "FADE_SHORT":
                        stop_loss_pct = self.config.fade_short_stop_loss_pct
                        profit_target_pct = self.config.fade_short_profit_target_pct
                    else:
                        stop_loss_pct = self.config.stop_loss_pct
                        profit_target_pct = self.config.profit_target_pct

                # Support-aware stop placement (Phase 2)
                # When a support level was identified during entry analysis, place the stop
                # just below that level.  This produces a tighter, more meaningful stop than
                # a flat percentage when price is near support.  The result is capped at the
                # configured stop_loss_pct so account-risk hard limits are never exceeded.
                support_stop_used = False
                support_price_at_entry = None
                if best_strategy in ('MOMENTUM', 'SWING_PULLBACK'):
                    result_with_support = (
                        momentum_signal_result if best_strategy == 'MOMENTUM' and momentum_signal_result
                        else pullback_result if best_strategy == 'SWING_PULLBACK' and pullback_result
                        else None
                    )
                    if result_with_support and result_with_support.get('support_price'):
                        sp = result_with_support['support_price']
                        buffer = getattr(self.config, 'support_stop_buffer_pct', 0.01)
                        candidate_stop = sp * (1 - buffer)
                        hard_stop_floor = realtime_price * (1 - stop_loss_pct)
                        if candidate_stop > hard_stop_floor and candidate_stop < realtime_price:
                            stop_price = candidate_stop
                            support_stop_used = True
                            support_price_at_entry = sp
                            self.logger.debug(
                                f"{symbol}: Support-aware stop ${stop_price:.2f} "
                                f"(support {sp:.2f}, {((realtime_price - stop_price) / realtime_price):.1%} risk)"
                            )
                        else:
                            stop_price = realtime_price * (1 - stop_loss_pct)
                    else:
                        stop_price = realtime_price * (1 - stop_loss_pct)
                else:
                    stop_price = realtime_price * (1 - stop_loss_pct)

                target_price = realtime_price * (1 + profit_target_pct)
                
                # Calculate position size
                position_size_dollars = self.config.max_position_dollars
                
                # Create signal with strategy-specific metadata
                time_horizon_days = 2.5 if best_strategy == "SWING_PULLBACK" else 1.5
                signal = AISignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=confidence,
                    time_horizon_days=time_horizon_days,
                    entry_price=realtime_price,
                    stop_price=stop_price,
                    target_price=target_price,
                    position_size_dollars=position_size_dollars,
                    signal_timestamp=datetime.now(),
                    features_used={
                        "rsi": current_rsi,
                        "volume_surge": volume_surge,
                        "volume_ratio": volume_ratio,
                        "base_confidence": base_confidence,
                        "quality_enhanced": confidence > base_confidence,
                        "strategy": best_strategy.lower(),
                        "entry_reason": f"{best_strategy}_SIGNAL",
                        # Strategy-specific features
                        "gap_and_go_conf": gap_and_go_confidence,
                        "fade_short_conf": fade_short_confidence,
                        "momentum_conf": momentum_confidence,
                        "swing_pullback_conf": swing_pullback_confidence,
                        "support_distance": (
                            momentum_signal_result['support_distance'] if best_strategy == 'MOMENTUM' and momentum_signal_result
                            else pullback_result['support_distance'] if best_strategy == 'SWING_PULLBACK' and pullback_result
                            else None
                        ),
                        "support_name": (
                            momentum_signal_result['support_name'] if best_strategy == 'MOMENTUM' and momentum_signal_result
                            else pullback_result['support_name'] if best_strategy == 'SWING_PULLBACK' and pullback_result
                            else None
                        ),
                        "pullback_volume_ratio": (
                            momentum_signal_result['pullback_volume_ratio'] if best_strategy == 'MOMENTUM' and momentum_signal_result
                            else pullback_result['pullback_volume_ratio'] if best_strategy == 'SWING_PULLBACK' and pullback_result
                            else None
                        ),
                        "bounce_volume_ratio": (
                            momentum_signal_result['bounce_volume_ratio'] if best_strategy == 'MOMENTUM' and momentum_signal_result
                            else pullback_result['bounce_volume_ratio'] if best_strategy == 'SWING_PULLBACK' and pullback_result
                            else None
                        ),
                        "extension_pct": (
                            momentum_signal_result['extension_pct'] if best_strategy == 'MOMENTUM' and momentum_signal_result
                            else pullback_result['extension_pct'] if best_strategy == 'SWING_PULLBACK' and pullback_result
                            else None
                        ),
                        # Support-aware stop metadata (Phase 2)
                        "support_stop_used": support_stop_used,
                        "support_price_at_entry": support_price_at_entry,
                        # Adaptive parameters
                        "adaptive_stop_loss_pct": stop_loss_pct if self.adaptive_params_enabled else None,
                        "adaptive_profit_target_pct": profit_target_pct if self.adaptive_params_enabled else None,
                        # Sentiment & Dark Pool (Nov 26, 2025)
                        "sentiment_boost": sentiment_boost if self.sentiment_analyzer else 0.0,
                        "dark_pool_boost": dark_pool_boost if self.dark_pool_detector else 0.0,
                        "sentiment_signal": sentiment.get('signal', 'N/A') if self.sentiment_analyzer else 'N/A',
                        "dark_pool_signal": dark_pool_activity.get('institutional_signal', 'N/A') if self.dark_pool_detector else 'N/A'
                    }
                )
                
                # Store adaptive parameters in signal for exit manager
                if self.adaptive_params_enabled:
                    signal.adaptive_stop_loss_pct = stop_loss_pct
                    signal.adaptive_profit_target_pct = profit_target_pct
                    signal.adaptive_rsi_exit = rsi_exit_threshold
                
                return signal
            else:
                # DETAILED REJECTION LOGGING
                # Show exactly why no signal was generated
                rejection_reasons = []
                
                if not best_signal:
                    rejection_reasons.append("No strategy triggered")
                    rejection_reasons.append(f"(GG: {gap_and_go_signal}, FS: {fade_short_signal})")
                
                if best_signal and confidence < confidence_threshold:
                    rejection_reasons.append(f"Confidence {confidence:.3f} < {confidence_threshold:.3f}")
                
                rejection_msg = " AND ".join(rejection_reasons)
                self.logger.debug(f"   ❌ REJECT {symbol}: {rejection_msg}")
                
        except Exception as e:
            self.logger.error(f"Error in symbol analysis for {symbol}: {e}")

        return None
    
    def _check_gap_and_go(self, symbol: str, data: pd.DataFrame) -> Optional[dict]:
        """
        Gap & Go Strategy Detection (Issue 1.1: Enhanced with gap confirmation)
        
        Backtest: +830% over 30 days, 54.3% win rate, 748 trades
        Entry: Morning gap 2-8% at open (9:35-9:45 AM)
        Filter: RSI < 75, gap HOLDING (not filling), confirmation check
        Exit: Next day (D+1) at open/intraday/close
        
        Issue 1.1: Two-phase confirmation
        - Gap must be holding (within 0.5% of gap low)
        - Current price must be above yesterday's close
        
        Args:
            symbol: Stock symbol
            data: Price data (normalized columns)
            
        Returns:
            dict with gap info if valid signal, None otherwise
        """
        try:
            # Check if we're in gap scan window (9:35-9:45 AM)
            # We scan at 9:35 to let opening chaos settle
            now = datetime.now()
            if not (now.hour == 9 and 35 <= now.minute <= 50):
                return None  # Only scan for gaps in this window
            
            # Get today's open and yesterday's close
            today_open = data['open'].iloc[-1]
            today_low = data['low'].iloc[-1]  # Today's low so far
            yesterday_close = data['close'].iloc[-2]
            current_close = data['close'].iloc[-1]
            
            # Calculate gap
            gap_pct = (today_open - yesterday_close) / yesterday_close
            
            # Check gap is within range (2-8%)
            if not (self.config.gap_min_pct <= gap_pct <= self.config.gap_max_pct):
                return None
            
            # Issue 1.1: GAP CONFIRMATION - Check if gap is HOLDING (not filling)
            # The gap low should be near the open (within 0.5% retracement)
            gap_low_threshold = today_open * 0.995  # 0.5% below open
            gap_is_holding = today_low >= gap_low_threshold
            
            if not gap_is_holding:
                self.logger.debug(
                    f"❌ {symbol}: Gap filled - low ${today_low:.2f} < threshold ${gap_low_threshold:.2f}"
                )
                return None
            
            # Calculate RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            # RSI must be < 72 (not too overbought) — tightened from 75
            if current_rsi >= self.config.gap_rsi_max:
                return None
            
            # Gap must be holding (price > yesterday's close)
            if current_close < yesterday_close:
                return None  # Gap fading, skip
            
            # Volume check: require at least 1.5x average volume for gap entries
            avg_volume_20d = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            if avg_volume_20d > 0:
                volume_ratio = current_volume / avg_volume_20d
                if volume_ratio < 1.5:
                    self.logger.debug(
                        f"❌ {symbol}: Gap volume ratio {volume_ratio:.2f}x < 1.5x minimum"
                    )
                    return None
            
            # Gap extension check: reject if price has run >3% above open (chasing)
            gap_extension = (current_close - today_open) / today_open
            if gap_extension > 0.03:
                self.logger.debug(
                    f"❌ {symbol}: Gap extension {gap_extension*100:.1f}% > 3% — chasing"
                )
                return None
            
            # Calculate confidence based on gap size and RSI
            # Larger gaps = higher confidence (up to 8%)
            gap_confidence = (gap_pct - self.config.gap_min_pct) / (self.config.gap_max_pct - self.config.gap_min_pct)
            
            # RSI bonus: lower RSI = more room to run
            rsi_bonus = (self.config.gap_rsi_max - current_rsi) / self.config.gap_rsi_max * 0.2
            
            # Gap holding bonus
            gap_strength = (current_close - yesterday_close) / yesterday_close
            holding_bonus = min(gap_strength / gap_pct, 0.3)  # Cap at 30% bonus
            
            # Issue 1.1: CONFIRMATION BONUS - gap is strongly holding
            # If we're 5+ minutes into trading and gap is still above threshold
            confirmation_bonus = 0.0
            if now.minute >= 35:  # At least 5 mins after open
                gap_held_pct = (today_low - yesterday_close) / yesterday_close
                if gap_held_pct >= gap_pct * 0.5:  # Gap held at least 50% of initial move
                    confirmation_bonus = 0.15  # 15% confidence boost for confirmed gaps
                    self.logger.debug(
                        f"✅ {symbol}: Gap CONFIRMED - held {gap_held_pct*100:.1f}% "
                        f"(50% of {gap_pct*100:.1f}% gap = {gap_pct*50:.1f}%)"
                    )
            
            confidence = min(gap_confidence + rsi_bonus + holding_bonus + confirmation_bonus, 1.0)
            
            return {
                'gap_pct': gap_pct,
                'rsi': current_rsi,
                'confidence': confidence,
                'gap_strength': gap_strength,
                'confirmed': confirmation_bonus > 0  # Track if gap was confirmed
            }
            
        except Exception as e:
            self.logger.debug(f"{symbol}: Gap & Go check failed: {e}")
            return None

    def _is_choppy_or_weak_trend(self, data: pd.DataFrame) -> bool:
        """Detect range-bound/weak-trend tape where pullback entries are more suitable."""
        if len(data) < 20:
            return False
        try:
            close = data['close']
            current_price = close.iloc[-1]
            sma20 = close.rolling(20).mean().iloc[-1]
            if sma20 <= 0:
                return False

            # Flat-to-weak direction over 5d and modest distance from trend anchor.
            ret_5d = (current_price - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0.0
            dist_to_sma = abs((current_price - sma20) / sma20)
            max_abs_5d = getattr(self.config, 'swing_weak_trend_abs_5d_return_max', 0.03)
            max_dist_to_sma = getattr(self.config, 'swing_weak_trend_dist_to_sma_max', 0.04)

            return abs(ret_5d) <= max_abs_5d and dist_to_sma <= max_dist_to_sma
        except Exception:
            return False

    def _build_support_context(
        self,
        data: pd.DataFrame,
        support_tolerance_attr: str,
        ema_tolerance_attr: Optional[str] = None,
    ) -> Optional[dict]:
        try:
            if len(data) < 20:
                return None

            current_price = data['close'].iloc[-1]
            ema9 = data['close'].ewm(span=9, adjust=False).mean().iloc[-1]
            ema20 = data['close'].ewm(span=20, adjust=False).mean().iloc[-1]
            sma20 = data['close'].rolling(20).mean().iloc[-1]
            swing_low = data['low'].tail(10).min()

            levels = {
                'ema9': ema9,
                'ema20': ema20,
                'sma20': sma20,
                'swing_low': swing_low,
            }
            valid_levels = {
                name: price for name, price in levels.items() if pd.notna(price) and price > 0
            }
            if not valid_levels:
                return None

            support_name, support_price = min(
                valid_levels.items(),
                key=lambda item: abs((current_price - item[1]) / item[1]),
            )

            support_distance = abs((current_price - support_price) / support_price)
            ema_distance = min(
                abs((current_price - ema9) / ema9) if ema9 > 0 else 1.0,
                abs((current_price - ema20) / ema20) if ema20 > 0 else 1.0,
            )
            support_tolerance = getattr(self.config, support_tolerance_attr, 0.03)
            ema_tolerance = getattr(self.config, ema_tolerance_attr, support_tolerance)

            return {
                'support_name': support_name,
                'support_price': support_price,
                'support_distance': support_distance,
                'ema9': ema9,
                'ema20': ema20,
                'sma20': sma20,
                'ema_distance': ema_distance,
                'near_support': support_distance <= support_tolerance,
                'near_ema': ema_distance <= ema_tolerance,
            }
        except Exception:
            return None

    def _check_pullback_volume_contraction(self, data: pd.DataFrame, max_ratio: float) -> Optional[dict]:
        try:
            if len(data) < 8 or 'volume' not in data.columns:
                return None

            pullback_volumes = data['volume'].iloc[-4:-1]
            baseline_volumes = data['volume'].iloc[-8:-4]
            if len(pullback_volumes) < 3 or len(baseline_volumes) < 4:
                return None

            pullback_avg = pullback_volumes.mean()
            baseline_avg = baseline_volumes.mean()
            if baseline_avg <= 0:
                return None

            ratio = pullback_avg / baseline_avg
            pullback_price_change = (
                (data['close'].iloc[-2] - data['close'].iloc[-4]) / data['close'].iloc[-4]
            )

            return {
                'passed': ratio <= max_ratio and pullback_price_change <= 0.015,
                'ratio': ratio,
                'pullback_price_change': pullback_price_change,
            }
        except Exception:
            return None

    def _check_bounce_volume_expansion(self, data: pd.DataFrame, min_ratio: float) -> Optional[dict]:
        try:
            if len(data) < 4 or 'volume' not in data.columns:
                return None

            pullback_volumes = data['volume'].iloc[-4:-1]
            pullback_avg = pullback_volumes.mean()
            if pullback_avg <= 0:
                return None

            current_volume = data['volume'].iloc[-1]
            ratio = current_volume / pullback_avg
            current_close = data['close'].iloc[-1]
            previous_close = data['close'].iloc[-2]
            candle_range = max(data['high'].iloc[-1] - data['low'].iloc[-1], 1e-6)
            close_location = (current_close - data['low'].iloc[-1]) / candle_range

            return {
                'passed': ratio >= min_ratio and current_close > previous_close and close_location >= 0.55,
                'ratio': ratio,
                'close_location': close_location,
            }
        except Exception:
            return None

    def _check_reversal_confirmation(self, data: pd.DataFrame, support_context: dict) -> Optional[dict]:
        try:
            if len(data) < 2:
                return None

            current_open = data['open'].iloc[-1] if 'open' in data.columns else data['close'].iloc[-2]
            current_close = data['close'].iloc[-1]
            previous_close = data['close'].iloc[-2]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            candle_range = max(current_high - current_low, 1e-6)
            support_price = support_context['support_price']

            bullish_close = current_close > previous_close and current_close >= current_open
            close_location = (current_close - current_low) / candle_range
            tested_support = current_low <= support_price * 1.015
            reclaimed_support = current_close >= support_price * 0.995

            return {
                'passed': bullish_close and close_location >= 0.55 and tested_support and reclaimed_support,
                'close_location': close_location,
                'tested_support': tested_support,
                'reclaimed_support': reclaimed_support,
            }
        except Exception:
            return None

    def _check_extension_from_support(self, current_price: float, support_context: dict, max_extension_pct: float) -> Optional[dict]:
        try:
            support_price = support_context['support_price']
            if support_price <= 0:
                return None

            extension_pct = (current_price - support_price) / support_price
            return {
                'passed': extension_pct <= max_extension_pct,
                'extension_pct': extension_pct,
            }
        except Exception:
            return None

    def _check_swing_pullback(self, symbol: str, data: pd.DataFrame, current_rsi: float) -> Optional[dict]:
        try:
            if len(data) < 20:
                self._set_strategy_gate_rejection("SWING_PULLBACK", "data_window", "Need at least 20 bars")
                return None

            now = datetime.now()
            swing_scan_start = getattr(self.config, 'swing_pullback_scan_start', '09:35')
            swing_scan_end = getattr(self.config, 'swing_pullback_scan_end', '14:30')
            if not self._is_within_scan_window(now, swing_scan_start, swing_scan_end):
                self._set_strategy_gate_rejection("SWING_PULLBACK", "time_window", "Outside swing pullback scan window")
                return None

            current_price = data['close'].iloc[-1]
            support_context = self._build_support_context(data, 'swing_pullback_support_tolerance')
            if not support_context or not support_context['near_support']:
                self._set_strategy_gate_rejection("SWING_PULLBACK", "support_proximity", "Price not near pullback support")
                return None

            sma20 = support_context['sma20']
            if sma20 <= 0:
                self._set_strategy_gate_rejection("SWING_PULLBACK", "trend_anchor", "Invalid SMA20 anchor")
                return None

            swing_rsi_min = getattr(self.config, 'swing_pullback_rsi_min', 38.0)
            swing_rsi_max = getattr(self.config, 'swing_pullback_rsi_max', 52.0)
            if not (swing_rsi_min <= current_rsi <= swing_rsi_max):
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "rsi_band",
                    f"RSI {current_rsi:.1f} outside [{swing_rsi_min:.1f}, {swing_rsi_max:.1f}]",
                )
                return None

            three_day_return = (current_price - data['close'].iloc[-3]) / data['close'].iloc[-3]
            if not (-0.10 <= three_day_return <= -0.003):
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "three_day_return",
                    f"3d return {three_day_return*100:.1f}% outside [-10.0%, -0.3%]",
                )
                return None

            price_vs_sma = (current_price - sma20) / sma20
            if not (-0.03 <= price_vs_sma <= 0.01):
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "price_vs_sma",
                    f"Price vs SMA {price_vs_sma*100:.1f}% outside [-3.0%, +1.0%]",
                )
                return None

            adr = ((data['high'] - data['low']) / data['close']).tail(14).mean()
            if adr < 0.018:
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "adr_floor",
                    f"ADR {adr*100:.2f}% below min 1.80%",
                )
                return None

            avg_volume_20d = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            volume_ratio = (current_volume / avg_volume_20d) if avg_volume_20d > 0 else 0.0
            min_volume_ratio = getattr(self.config, 'swing_pullback_min_volume_ratio', 0.85)
            if volume_ratio < min_volume_ratio:
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "volume_ratio",
                    f"Volume ratio {volume_ratio:.2f} below min {min_volume_ratio:.2f}",
                )
                return None

            pullback_volume = self._check_pullback_volume_contraction(
                data,
                getattr(self.config, 'swing_pullback_volume_max_ratio', 1.05),
            )
            if not pullback_volume or not pullback_volume['passed']:
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "pullback_volume",
                    "Pullback volume indicates distribution",
                )
                return None

            reversal = self._check_reversal_confirmation(data, support_context)
            if not reversal or not reversal['passed']:
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "reversal_confirmation",
                    "No valid reversal confirmation",
                )
                return None

            bounce = self._check_bounce_volume_expansion(
                data,
                getattr(self.config, 'swing_pullback_bounce_volume_min_ratio', 1.0),
            )
            if not bounce or not bounce['passed']:
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "bounce_volume",
                    "Bounce volume did not improve",
                )
                return None

            extension = self._check_extension_from_support(
                current_price,
                support_context,
                getattr(self.config, 'swing_pullback_extension_reject_pct', 0.05),
            )
            if not extension or not extension['passed']:
                self._set_strategy_gate_rejection(
                    "SWING_PULLBACK",
                    "extension",
                    "Entry too extended from support",
                )
                return None

            rsi_score = 1.0 - min(abs(current_rsi - 45.0) / 15.0, 1.0)
            pullback_score = min(max((-three_day_return - 0.005) / 0.075, 0.0), 1.0)
            proximity_score = 1.0 - min(abs(price_vs_sma) / 0.03, 1.0)
            reversal_score = reversal['close_location']
            bounce_score = min(max((bounce['ratio'] - 1.0) / 0.5, 0.0), 1.0)
            volume_score = 1.0 - min(max(pullback_volume['ratio'] - 1.0, 0.0), 1.0)
            confidence = min(
                0.20
                + rsi_score * 0.20
                + pullback_score * 0.20
                + proximity_score * 0.15
                + reversal_score * 0.15
                + bounce_score * 0.15
                + volume_score * 0.10,
                1.0,
            )

            return {
                'rsi': current_rsi,
                'three_day_return': three_day_return,
                'price_vs_sma': price_vs_sma,
                'adr': adr,
                'volume_ratio': volume_ratio,
                'support_price': support_context['support_price'],
                'support_distance': support_context['support_distance'],
                'support_name': support_context['support_name'],
                'pullback_volume_ratio': pullback_volume['ratio'],
                'bounce_volume_ratio': bounce['ratio'],
                'extension_pct': extension['extension_pct'],
                'confidence': confidence,
            }
        except Exception as e:
            self.logger.debug(f"{symbol}: Swing pullback check failed: {e}")
            return None
    
    def _check_fade_short(self, symbol: str, data: pd.DataFrame, current_rsi: float) -> Optional[dict]:
        """
        Fade/Short Strategy Detection
        
        Backtest: +174% over 30 days, 62.8% win rate, 914 trades
        Entry: RSI > 70 + 10%+ above SMA20 (overbought extreme)
        Exit: Next day (D+1) when reverses or hits stop
        
        Issue 1.2: Enhanced with exhaustion signals
        - Volume divergence: Price up but volume declining = exhaustion
        - RSI divergence: Price making highs but RSI declining = exhaustion
        
        Args:
            symbol: Stock symbol
            data: Price data (normalized columns)
            current_rsi: Pre-calculated RSI value
            
        Returns:
            dict with fade info if valid signal, None otherwise
        """
        try:
            # Check if we're in trading window (10:00 AM - 2:00 PM)
            now = datetime.now()
            scan_start = int(self.config.fade_scan_start.split(':')[0])
            scan_end = int(self.config.fade_scan_end.split(':')[0])
            
            if not (scan_start <= now.hour < scan_end):
                return None  # Only scan during specified window
            
            # RSI must be > 70 (overbought)
            if current_rsi < self.config.fade_rsi_min:
                return None
            
            # Calculate 20-day SMA
            sma_20 = data['close'].rolling(20).mean().iloc[-1]
            current_price = data['close'].iloc[-1]
            
            # Price must be 10%+ above SMA20
            extension_pct = (current_price - sma_20) / sma_20
            if extension_pct < self.config.fade_extension_min_pct:
                return None

            # Require stronger volume surge for fade/short entries
            if 'volume' in data.columns and len(data) >= 20:
                avg_volume_20d = data['volume'].tail(20).mean()
                current_volume = data['volume'].iloc[-1]
                volume_surge = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
                if volume_surge < self.config.fade_min_volume_surge:
                    return None
            
            # Calculate confidence based on RSI level and extension
            # Higher RSI = higher confidence (up to RSI 100)
            rsi_confidence = (current_rsi - self.config.fade_rsi_min) / (100 - self.config.fade_rsi_min)
            
            # Greater extension = higher confidence
            # 10% extension = 0.5, 20% = 1.0
            extension_confidence = min((extension_pct - self.config.fade_extension_min_pct) / 0.10, 0.5)
            
            # Issue 1.2: EXHAUSTION SIGNALS - volume and RSI divergence
            exhaustion_bonus = 0.0
            
            # Check for volume divergence (price up, volume declining)
            if 'volume' in data.columns and len(data) >= 5:
                recent_prices = data['close'].tail(5)
                recent_volumes = data['volume'].tail(5)
                
                price_direction = 1 if recent_prices.iloc[-1] > recent_prices.iloc[0] else -1
                volume_direction = 1 if recent_volumes.iloc[-1] > recent_volumes.iloc[0] else -1
                
                # Price up + volume down = bearish divergence (good for fade)
                if price_direction > 0 and volume_direction < 0:
                    exhaustion_bonus += 0.10
                    self.logger.debug(
                        f"🔻 {symbol}: Volume divergence detected - price up, volume down"
                    )
            
            # Check for RSI divergence (price making new highs, RSI declining)
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi_series = 100 - (100 / (1 + gain / loss))
            
            if len(rsi_series) >= 5:
                recent_rsi = rsi_series.tail(5)
                recent_closes = data['close'].tail(5)
                
                # Price at new high but RSI declining = bearish divergence
                price_at_high = recent_closes.iloc[-1] >= recent_closes.max() * 0.99
                rsi_declining = recent_rsi.iloc[-1] < recent_rsi.max() - 2  # RSI dropped 2+ points
                
                if price_at_high and rsi_declining:
                    exhaustion_bonus += 0.10
                    self.logger.debug(
                        f"🔻 {symbol}: RSI divergence detected - price at high, RSI declining"
                    )
            
            confidence = min(rsi_confidence + extension_confidence + exhaustion_bonus, 1.0)
            
            return {
                'rsi': current_rsi,
                'extension_pct': extension_pct,
                'confidence': confidence,
                'sma_20': sma_20,
                'exhaustion_signals': exhaustion_bonus > 0  # Track if exhaustion detected
            }
            
        except Exception as e:
            self.logger.debug(f"{symbol}: Fade/Short check failed: {e}")
            return None

    def _check_momentum(self, symbol: str, data: pd.DataFrame, current_rsi: float) -> Optional[dict]:
        try:
            now = datetime.now()
            momentum_scan_start = getattr(self.config, 'momentum_scan_start', '10:30')
            momentum_scan_end = getattr(self.config, 'momentum_scan_end', '14:30')
            if not self._is_within_scan_window(now, momentum_scan_start, momentum_scan_end):
                return None

            if len(data) < 20:
                return None

            sma_period = getattr(self.config, 'momentum_sma_period', 20)
            rsi_min = getattr(self.config, 'momentum_rsi_min', 45.0)
            rsi_max = getattr(self.config, 'momentum_rsi_max', 65.0)
            min_adr = getattr(self.config, 'momentum_min_adr_pct', 0.02)
            min_5d_return = getattr(self.config, 'momentum_min_5d_return', 0.03)
            max_5d_return = getattr(self.config, 'momentum_max_5d_return', 0.15)
            min_volume_ratio = getattr(self.config, 'momentum_min_volume_ratio', 1.0)
            scored_mode = getattr(self.config, 'momentum_scored_mode', False)
            min_gate_score = getattr(self.config, 'momentum_min_gate_score', 0.60)

            # Track gate pass/fail for scored mode
            gate_results = {}
            gate_weights = {
                'rsi_band': 0.15,
                'trend_structure': 0.15,
                'five_day_return': 0.10,
                'adr_floor': 0.05,
                'volume_ratio': 0.05,
                'pullback_depth': 0.10,
                'support_proximity': 0.15,
                'pullback_volume': 0.05,
                'reversal_confirmation': 0.10,
                'bounce_volume': 0.05,
                'extension': 0.05,
            }

            if not (rsi_min <= current_rsi <= rsi_max):
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "rsi_band",
                        f"RSI {current_rsi:.1f} outside [{rsi_min:.1f}, {rsi_max:.1f}]",
                    )
                    return None
                gate_results['rsi_band'] = False
            else:
                gate_results['rsi_band'] = True

            current_price = data['close'].iloc[-1]
            sma = data['close'].rolling(sma_period).mean().iloc[-1]
            ema9 = data['close'].ewm(span=9, adjust=False).mean().iloc[-1]
            ema20 = data['close'].ewm(span=20, adjust=False).mean().iloc[-1]
            ema_break_tolerance = getattr(self.config, 'momentum_ema_break_tolerance_pct', 0.0)
            ema_floor = ema20 * (1 - max(ema_break_tolerance, 0.0))
            trend_soft_mode = getattr(self.config, 'momentum_trend_soft_mode', False)
            trend_fail = current_price < sma or ema9 < ema20 or current_price < ema_floor
            if trend_fail:
                if trend_soft_mode and ema9 > ema20 and current_rsi > 45.0:
                    gate_results['trend_structure'] = True  # Soft pass
                elif scored_mode:
                    gate_results['trend_structure'] = False
                else:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "trend_structure",
                        (
                            "Price/EMA structure not bullish "
                            "(price<SMA or ema9<ema20 or price<ema20-tolerance)"
                        ),
                    )
                    return None
            else:
                gate_results['trend_structure'] = True

            price_vs_sma = (current_price - sma) / sma
            five_day_ago = data['close'].iloc[-5]
            five_day_return = (current_price - five_day_ago) / five_day_ago
            if not (min_5d_return <= five_day_return <= max_5d_return):
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "five_day_return",
                        f"5d return {five_day_return*100:.1f}% outside [{min_5d_return*100:.1f}%, {max_5d_return*100:.1f}%]",
                    )
                    return None
                gate_results['five_day_return'] = False
            else:
                gate_results['five_day_return'] = True

            adr = ((data['high'] - data['low']) / data['close']).tail(14).mean()
            if adr < min_adr:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "adr_floor",
                        f"ADR {adr*100:.2f}% below min {min_adr*100:.2f}%",
                    )
                    return None
                gate_results['adr_floor'] = False
            else:
                gate_results['adr_floor'] = True

            avg_volume_20d = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            volume_ratio = (current_volume / avg_volume_20d) if avg_volume_20d > 0 else 0.0
            if volume_ratio < min_volume_ratio:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "volume_ratio",
                        f"Volume ratio {volume_ratio:.2f} below min {min_volume_ratio:.2f}",
                    )
                    return None
                gate_results['volume_ratio'] = False
            else:
                gate_results['volume_ratio'] = True

            recent_high = data['high'].iloc[-5:-1].max()
            if recent_high <= 0:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "recent_high",
                        "Insufficient valid recent highs for pullback check",
                    )
                    return None
                gate_results['pullback_depth'] = False
            else:
                pullback_from_high = (current_price - recent_high) / recent_high
                if not (-0.06 <= pullback_from_high <= 0.015):
                    if not scored_mode:
                        self._set_strategy_gate_rejection(
                            "MOMENTUM",
                            "pullback_depth",
                            f"Pullback {pullback_from_high*100:.1f}% not within [-6.0%, +1.5%]",
                        )
                        return None
                    gate_results['pullback_depth'] = False
                else:
                    gate_results['pullback_depth'] = True

            support_context = self._build_support_context(
                data,
                'momentum_support_tolerance',
                'momentum_pullback_ema_tolerance',
            )
            if not support_context or not support_context['near_support'] or not support_context['near_ema']:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "support_proximity",
                        "Price not near support and EMA pullback zone",
                    )
                    return None
                gate_results['support_proximity'] = False
            else:
                gate_results['support_proximity'] = True

            pullback_volume = self._check_pullback_volume_contraction(
                data,
                getattr(self.config, 'momentum_pullback_volume_max_ratio', 0.95),
            )
            if not pullback_volume or not pullback_volume['passed']:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "pullback_volume",
                        "Pullback volume did not contract enough",
                    )
                    return None
                gate_results['pullback_volume'] = False
            else:
                gate_results['pullback_volume'] = True

            reversal = self._check_reversal_confirmation(data, support_context) if support_context else None
            if not reversal or not reversal['passed']:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "reversal_confirmation",
                        "No valid reversal confirmation near support",
                    )
                    return None
                gate_results['reversal_confirmation'] = False
            else:
                gate_results['reversal_confirmation'] = True

            bounce = self._check_bounce_volume_expansion(
                data,
                getattr(self.config, 'momentum_bounce_volume_min_ratio', 1.05),
            )
            if not bounce or not bounce['passed']:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "bounce_volume",
                        "Bounce volume did not re-expand",
                    )
                    return None
                gate_results['bounce_volume'] = False
            else:
                gate_results['bounce_volume'] = True

            extension = self._check_extension_from_support(
                current_price,
                support_context,
                getattr(self.config, 'momentum_extension_reject_pct', 0.06),
            ) if support_context else None
            if not extension or not extension['passed']:
                if not scored_mode:
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "extension",
                        "Price is too extended from support",
                    )
                    return None
                gate_results['extension'] = False
            else:
                gate_results['extension'] = True

            # In scored mode, compute gate score and pass if above threshold
            if scored_mode:
                total_weight = sum(gate_weights.values())
                passed_weight = sum(gate_weights[g] for g, passed in gate_results.items() if passed)
                gate_score = passed_weight / total_weight if total_weight > 0 else 0.0
                if gate_score < min_gate_score:
                    failed_gates = [g for g, passed in gate_results.items() if not passed]
                    self._set_strategy_gate_rejection(
                        "MOMENTUM",
                        "gate_score",
                        f"Gate score {gate_score:.2f} < {min_gate_score:.2f} (failed: {', '.join(failed_gates)})",
                    )
                    return None
                self.logger.debug(
                    f"⚡ {symbol}: Scored momentum pass — gate_score={gate_score:.2f} "
                    f"(passed {len([g for g in gate_results.values() if g])}/{len(gate_results)})"
                )

            rsi_score = 1.0 - abs(current_rsi - 55) / 20
            return_score = min((five_day_return - min_5d_return) / (max_5d_return - min_5d_return), 1.0) if 'five_day_return' in gate_results and gate_results['five_day_return'] else 0.5
            support_score = 1.0 - min(support_context['support_distance'] / max(getattr(self.config, 'momentum_support_tolerance', 0.03), 1e-6), 1.0) if support_context else 0.5
            pullback_score = 1.0 - min(abs(pullback_from_high) / 0.05, 1.0) if 'pullback_from_high' in dir() else 0.5
            reversal_score = reversal['close_location'] if reversal else 0.5
            bounce_score = min(max((bounce['ratio'] - 1.0) / 0.6, 0.0), 1.0) if bounce else 0.5
            volume_score = 1.0 - min(pullback_volume['ratio'] / max(getattr(self.config, 'momentum_pullback_volume_max_ratio', 0.95), 1e-6), 1.0) if pullback_volume else 0.5
            adr_bonus = min((adr - min_adr) / 0.02, 0.15)

            confidence = min(
                rsi_score * 0.18
                + return_score * 0.22
                + support_score * 0.18
                + pullback_score * 0.12
                + reversal_score * 0.15
                + bounce_score * 0.10
                + volume_score * 0.05
                + adr_bonus,
                1.0,
            )

            return {
                'rsi': current_rsi,
                'sma': sma,
                'price_vs_sma': price_vs_sma,
                'five_day_return': five_day_return,
                'adr': adr,
                'volume_ratio': volume_ratio,
                'support_price': support_context['support_price'] if support_context else None,
                'support_distance': support_context['support_distance'] if support_context else None,
                'support_name': support_context['support_name'] if support_context else None,
                'pullback_from_high': pullback_from_high if 'pullback_from_high' in dir() else None,
                'pullback_volume_ratio': pullback_volume['ratio'] if pullback_volume else None,
                'bounce_volume_ratio': bounce['ratio'] if bounce else None,
                'extension_pct': extension['extension_pct'] if extension else None,
                'confidence': confidence,
            }

        except Exception as e:
            self.logger.debug(f"{symbol}: Momentum check failed: {e}")
            return None

    def _apply_time_weight(self, strategy: str, base_confidence: float) -> float:
        """
        Issue 1.3: Time-weighted confidence scoring.
        
        Adjusts confidence based on time of day and strategy type.
        Based on intraday pattern research:
        - 10:00-10:30 AM: Common reversal window (economic data releases)
        - 11:30 AM - 1:00 PM: Lunch lull (lower volume, choppier)
        - 2:00-3:00 PM: Afternoon trend continuation
        
        Args:
            strategy: "GAP_AND_GO", "FADE_SHORT", or "MOMENTUM"
            base_confidence: The pre-adjusted confidence score
            
        Returns:
            Time-weighted confidence score
        """
        import pytz
        
        try:
            now = datetime.now(pytz.timezone('America/New_York'))
            time_decimal = now.hour + now.minute / 60
            
            if strategy == 'GAP_AND_GO':
                # Gap & Go: Best early, worse after 10 AM
                if 9.5 <= time_decimal < 10.0:
                    weight = 1.0  # Prime time for gaps
                elif 10.0 <= time_decimal < 10.5:
                    weight = 0.90  # Still okay
                elif 10.5 <= time_decimal < 11.0:
                    weight = 0.80  # Getting late for gaps
                else:
                    weight = 0.70  # Too late for gaps
                    
            elif strategy == 'FADE_SHORT':
                # Fade/Short: Avoid lunch, best at reversal times
                if 10.0 <= time_decimal < 10.5:
                    weight = 1.10  # Economic data reversal window
                elif 10.5 <= time_decimal < 11.5:
                    weight = 1.0  # Normal
                elif 11.5 <= time_decimal < 13.0:
                    weight = 0.85  # Lunch lull - choppy
                elif 13.0 <= time_decimal < 14.5:
                    weight = 1.05  # Afternoon continuation
                else:
                    weight = 0.95  # Late afternoon
                    
            elif strategy == 'MOMENTUM':
                # Momentum: Best mid-day when trend is established
                if 10.5 <= time_decimal < 11.5:
                    weight = 1.0  # Trend establishing
                elif 11.5 <= time_decimal < 13.0:
                    weight = 0.90  # Lunch lull (reduced)
                elif 13.0 <= time_decimal < 14.5:
                    weight = 1.10  # Prime time - afternoon continuation
                else:
                    weight = 0.85  # Outside optimal window
            else:
                weight = 1.0  # Unknown strategy, no adjustment
                
            adjusted_confidence = base_confidence * weight
            
            # Log significant adjustments
            if weight != 1.0:
                self.logger.debug(
                    f"⏰ Time weight: {strategy} at {now.strftime('%H:%M')} → "
                    f"{base_confidence:.2f} * {weight:.2f} = {adjusted_confidence:.2f}"
                )
                
            return adjusted_confidence
            
        except Exception as e:
            self.logger.debug(f"Time weight calculation failed: {e}")
            return base_confidence  # Return unmodified on error
