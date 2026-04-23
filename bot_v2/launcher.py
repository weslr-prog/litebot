#!/usr/bin/env python3
"""
bot_v2 Main Launcher - Continuous Trading Loop
================================================

Modular implementation of ShortCycleTrader with clean architecture.
Supports the configurable bot_v2 strategy stack.

Features:
- Post-market watchlist refresh (4:00 PM)
- Premarket portfolio summary + gap scan (9:00 AM)
- Entry scanning with prefilter and signal generation
- Optional late-entry scanning (1:00 PM - 2:30 PM)
- Exit monitoring (continuous during market hours)
- Config-driven risk management and force-exit behavior

Author: LiteBotX Team
Version: 2.0
Date: March 16, 2026
"""

import os
import sys
import time
import logging
import datetime as dt
import pytz
import warnings
from typing import Any, List, Optional, Dict
from pathlib import Path

# Suppress FutureWarnings from pandas and other libraries
warnings.simplefilter(action='ignore', category=FutureWarning)

# Suppress yfinance logging errors (rate limit warnings, "possibly delisted" errors)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("⚠️  Continuing without .env file support...")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import bot_v2 modules
from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.config.settings_verifier import verify_settings_on_startup
from bot_v2.signal_generation.signal_generator import AISignalGenerator
from bot_v2.portfolio.portfolio_manager import AIPortfolioManager
from bot_v2.execution.position_tracker import AIPositionTracker
from bot_v2.execution.order_manager import AIOrderManager
from bot_v2.execution.exit_manager import AIExitManager
from bot_v2.earnings import EarningsCalendar
from bot_v2.gap_scanner import MorningGapScanner
from bot_v2.pattern import PatternRecognizer
from bot_v2.safety import SafetyMonitor, SafetyConfig
from bot_v2.sector import SectorSpecificExitManager
from bot_v2.utils.day_trade_tracker import DayTradeTracker
from bot_v2.utils.enhanced_logger import EnhancedLogger
from bot_v2.maintenance import UniverseHealthChecker
from bot_v2.reporting import MarketBrief, DailySummary

# Import core LiteBotX components (for data and execution)
try:
    from bot_v2.data.data_loader import DataLoader  # Standalone bot_v2 data loader
    from logger import setup_logger
    from connect_real_trading import RealPaperTradingEngine
except ImportError as e:
    print(f"❌ Failed to import LiteBotX components: {e}")
    sys.exit(1)


class BotV2Launcher:
    """Main launcher for bot_v2 with continuous trading loop"""
    
    def __init__(self, config: Optional[ShortCycleConfig] = None, paper_trading: bool = True):
        """Initialize bot_v2 launcher
        
        Args:
            config: Trading configuration (defaults to ShortCycleConfig)
            paper_trading: True for paper trading, False for live trading
        """
        self.config = config or ShortCycleConfig()
        self.paper_trading = paper_trading
        # Set log path to short_cycle_trader.log for consistency with monitoring
        os.environ['LITEBOTX_LOG_PATH'] = 'logs/short_cycle_trader.log'
        self.logger = setup_logger("bot_v2_launcher")
        
        # Initialize enhanced logging system
        self.enhanced_logger = EnhancedLogger(self.logger)
        
        # Initialize timezone
        self.tz = pytz.timezone('America/New_York')
        
        # ✅ Startup Settings Verification (prevents config drift)
        verify_settings_on_startup(self.logger)
        
        # Initialize core components
        self._initialize_components()
        
        # State tracking
        self.is_running = False
        self.last_watchlist_refresh = None
        self.last_gap_scan = None
        self.last_entry_scan = None
        self.entries_today = 0
        self.last_midday_refresh = None
        self.last_morning_brief = None
        self.last_daily_summary = None
        self.last_health_check = None  # Track last connection health check
        self._entry_guard_date = dt.date.today()
        self._entered_symbols_today = set()
        self._rejected_symbols_today = {}
        
        # Session tracking for daily summary
        self.session_data = self._new_session_data()
        
        self.logger.info("=" * 80)
        self.logger.info("🚀 bot_v2 Launcher Initialized")
        self.logger.info("=" * 80)
        self.logger.info(f"📊 Configuration:")
        self.logger.info(f"   Portfolio Value: ${self.config.portfolio_value:,.2f}")
        self.logger.info(f"   Max Universe Size: {self.config.max_universe_size}")
        self.logger.info(f"   Max Positions/Day: {self.config.max_positions_per_day}")
        self.logger.info(f"   Paper Trading: {self.paper_trading}")
        self.logger.info("=" * 80)
        
        # Enhanced logging: Session start (after components initialized)
        # Will be called in _initialize_components after positions loaded

    def _new_session_data(self) -> Dict[str, Any]:
        """Create a fresh session telemetry container."""
        return {
            'scans_run': 0,
            'candidates_reviewed': [],
            'signals_generated': 0,
            'entries_executed': [],
            'rejections': {},  # reason -> count
            'rejection_samples': {},  # reason -> symbols (capped)
            'exit_reasons': {}  # normalized exit reason tag -> count
        }

    def _record_rejection(self, reason: str, symbol: Optional[str] = None):
        """Track rejection reasons as counts (with optional symbol samples)."""
        reason_key = (reason or "unknown_rejection").strip().lower().replace(" ", "_")
        if not reason_key:
            reason_key = "unknown_rejection"

        self.session_data['rejections'][reason_key] = self.session_data['rejections'].get(reason_key, 0) + 1

        if symbol:
            samples = self.session_data['rejection_samples'].setdefault(reason_key, [])
            if symbol not in samples and len(samples) < 20:
                samples.append(symbol)

    def _record_rejection_counts(self, counts: Dict[str, int]):
        """Merge a reason->count mapping into session rejection telemetry."""
        for reason, count in (counts or {}).items():
            if not count:
                continue
            reason_key = (reason or "unknown_rejection").strip().lower().replace(" ", "_")
            self.session_data['rejections'][reason_key] = self.session_data['rejections'].get(reason_key, 0) + int(count)

    def _log_signal_rejections(self, phase: str, rejection_stats: Dict[str, Any], sample_limit: int = 5):
        """Log per-scan signal rejection breakdown to the main launcher log."""
        counts = (rejection_stats or {}).get('counts', {}) or {}
        details = (rejection_stats or {}).get('details', []) or []
        total_rejected = int((rejection_stats or {}).get('total_rejected') or 0)

        if total_rejected <= 0 and not details:
            return

        if total_rejected > 0:
            nonzero_counts = {k: int(v) for k, v in counts.items() if int(v) > 0}
            self.logger.info(f"📉 Signal rejections ({phase}): {total_rejected} total | {nonzero_counts}")

        if details:
            for detail in details[:sample_limit]:
                self.logger.info(f"   • {detail}")
            remaining = len(details) - sample_limit
            if remaining > 0:
                self.logger.info(f"   • ... and {remaining} more")

    def _classify_exit_reason(self, reason: Optional[str]) -> str:
        """Normalize free-form exit reason text to stable tags for analysis."""
        reason_upper = (reason or "").upper()
        if "FAST" in reason_upper:
            return "FAST_EXIT"
        if "TRAIL" in reason_upper:
            return "TRAILING_STOP"
        if "TARGET" in reason_upper or "PROFIT" in reason_upper:
            return "TARGET"
        if "STOP" in reason_upper or "LOSS" in reason_upper:
            return "STOP_LOSS"
        if "D+1" in reason_upper or "FORCE EXIT" in reason_upper or "FRIDAY" in reason_upper or "TIME" in reason_upper:
            return "TIME_EXIT"
        return "OTHER"

    def _record_exit_reason(self, reason: Optional[str]) -> str:
        """Increment exit reason telemetry and return the normalized tag."""
        tag = self._classify_exit_reason(reason)
        self.session_data['exit_reasons'][tag] = self.session_data['exit_reasons'].get(tag, 0) + 1
        return tag

    def _reset_daily_entry_guards_if_needed(self):
        """Reset same-day symbol guard when date changes."""
        today = dt.date.today()
        if getattr(self, "_entry_guard_date", None) != today:
            self._entry_guard_date = today
            self._entered_symbols_today = set()
            self._rejected_symbols_today = {}

    def _record_entered_symbol(self, symbol: str):
        """Mark a symbol as entered today to prevent repeat churn."""
        self._reset_daily_entry_guards_if_needed()
        self._entered_symbols_today.add(symbol.upper())

    def _should_block_entry_symbol(self, symbol: str) -> bool:
        """Block entries for symbols already active or already entered today."""
        self._reset_daily_entry_guards_if_needed()
        sym = (symbol or "").upper()
        if not sym:
            return True

        active_symbols = {
            pos.symbol.upper()
            for pos in self.position_tracker.get_active_positions()
            if getattr(pos, "symbol", None)
        }
        if sym in active_symbols:
            return True

        return sym in self._entered_symbols_today

    def _record_rejected_symbol(self, symbol: str):
        """Track temporary entry rejections to avoid immediate re-attempt loops."""
        self._reset_daily_entry_guards_if_needed()
        sym = (symbol or "").upper()
        if sym:
            self._rejected_symbols_today[sym] = dt.datetime.now(self.tz)

    def _is_rejected_symbol_on_cooldown(self, symbol: str) -> bool:
        """Return True if symbol had a recent rejection and should cool down."""
        self._reset_daily_entry_guards_if_needed()
        sym = (symbol or "").upper()
        if not sym:
            return True

        last_rejection = self._rejected_symbols_today.get(sym)
        if not last_rejection:
            return False

        cooldown_minutes = int(getattr(self.config, 'rejected_symbol_cooldown_minutes', 45))
        elapsed = (dt.datetime.now(self.tz) - last_rejection).total_seconds() / 60.0
        return elapsed < cooldown_minutes

    def _dedupe_signals_by_symbol(self, signals: List[Any]) -> List[Any]:
        """Keep highest-confidence signal per symbol to avoid duplicate same-cycle entries."""
        by_symbol: Dict[str, Any] = {}
        duplicate_count = 0
        for signal in signals:
            sym = getattr(signal, "symbol", "").upper()
            if not sym:
                continue
            if sym in by_symbol:
                duplicate_count += 1
                if getattr(signal, "confidence", 0.0) > getattr(by_symbol[sym], "confidence", 0.0):
                    by_symbol[sym] = signal
            else:
                by_symbol[sym] = signal

        if duplicate_count > 0:
            self.logger.warning(
                f"⚠️ Duplicate symbol signals detected: {duplicate_count} dropped before execution"
            )
            self._record_rejection_counts({"duplicate_symbol_signal": duplicate_count})

        return sorted(by_symbol.values(), key=lambda s: getattr(s, "confidence", 0.0), reverse=True)
    
    def _initialize_components(self):
        """Initialize all bot_v2 modules"""
        try:
            # Data and execution
            self.data_loader = DataLoader()
            
            # Paper trading connection (always enabled - no simulation mode)
            if self.paper_trading:
                self.trading_engine = RealPaperTradingEngine()
                self.logger.info("✅ Connected to Alpaca Paper Trading")
                
                # Health check: Verify connection
                try:
                    account_info = self.trading_engine.get_account_info()
                    if account_info:
                        self.logger.info(f"✅ Connection verified - Account equity: ${account_info['portfolio_value']:,.2f}")
                    else:
                        self.logger.error("❌ Failed to verify Alpaca connection - check internet/credentials")
                except Exception as e:
                    self.logger.error(f"❌ Connection health check failed: {e}")
                    self.logger.warning("⚠️ Bot will continue but may have connectivity issues")
            else:
                self.logger.error("❌ Live trading not implemented - use paper_trading=True")
                raise ValueError("Paper trading must be enabled")
            
            # Signal generation
            self.signal_generator = AISignalGenerator(
                config=self.config,
                price_fetcher=self._get_realtime_price
            )
            
            # Portfolio management
            self.portfolio_manager = AIPortfolioManager(config=self.config)
            self.position_tracker = AIPositionTracker(config=self.config)
            loaded_positions = self.position_tracker.load_positions()  # Load existing positions from file
            self.logger.info(f"📋 Position tracker initialized with {len(loaded_positions)} positions")
            self.order_manager = AIOrderManager(
                config=self.config,
                execution_engine=self.trading_engine  # Use real Alpaca connection, not simulator
            )
            
            # Exit manager needs stop_manager first
            from bot_v2.risk_management.stop_loss_manager import AIStopLossManager
            self.stop_manager = AIStopLossManager(config=self.config)
            
            self.exit_manager = AIExitManager(
                config=self.config,
                stop_manager=self.stop_manager,
                order_manager=self.order_manager
            )
            
            # Smart exit manager for intelligent exit decisions (Dec 26: Added for smart exits)
            from bot_v2.utils.smart_exit_manager import SmartExitManager
            self.smart_exit_manager = SmartExitManager(config=self.config)
            self.logger.info("✅ Smart exit manager initialized (9 intelligent exit strategies)")
            
            # Specialized modules
            self.earnings_calendar = EarningsCalendar(
                entry_blackout_days=3,
                exit_buffer_days=1
            )
            
            self.gap_scanner = MorningGapScanner(data_loader=self.data_loader)
            self.pattern_recognizer = PatternRecognizer()
            
            self.safety_monitor = SafetyMonitor(
                config=SafetyConfig(),
                portfolio_value=self.config.portfolio_value
            )
            
            self.sector_exit_manager = SectorSpecificExitManager()
            
            # PDT compliance
            self.day_trade_tracker = DayTradeTracker(
                max_trades=3,
                window_business_days=5
            )
            
            # Reporting components
            self.market_brief = MarketBrief(self.data_loader, self.logger)
            self.daily_summary = DailySummary(self.data_loader, self.position_tracker, self.logger, trading_engine=self.trading_engine)
            self.logger.info("✅ Reporting components initialized (morning brief + daily summary)")
            
            # Universe health checker
            self.health_checker = UniverseHealthChecker(
                config=self.config,
                data_source=self.data_loader,
                logger=self.logger
            )
            
            self.logger.info("✅ All modules initialized successfully")
            
            # Build sector lookup for concentration checks
            self._build_sector_lookup()
            
            # CRITICAL: Sync positions with Alpaca (source of truth)
            self._sync_positions_with_alpaca()
            
            # Enhanced logging: Session start
            buying_power = self.config.portfolio_value
            try:
                if self.trading_engine and hasattr(self.trading_engine, 'api'):
                    account = self.trading_engine.api.get_account()
                    buying_power = float(account.buying_power)
            except:
                pass
            
            # Get actual position count after sync
            synced_positions = self.position_tracker.get_active_positions()
            self.enhanced_logger.log_session_start(
                portfolio_value=self.config.portfolio_value,
                active_positions=len(synced_positions),
                buying_power=buying_power
            )
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    def _sync_positions_with_alpaca(self):
        """
        Sync position tracker with Alpaca (source of truth)
        
        This prevents position quantity mismatches that cause:
        - Wrong exit quantities
        - Buying power calculation errors
        - Stuck positions
        """
        try:
            if not self.trading_engine:
                self.logger.warning("⚠️ No trading engine - skipping position sync")
                return
            
            self.logger.info("🔄 Syncing positions with Alpaca...")
            
            # Pre-fetch recent closed orders to reconcile exits with real fills
            recent_sell_fills = {}
            try:
                from alpaca.trading.requests import GetOrdersRequest
                from alpaca.trading.enums import QueryOrderStatus
                
                request = GetOrdersRequest(
                    status=QueryOrderStatus.CLOSED,
                    limit=500,
                    after=dt.datetime.now(pytz.UTC) - dt.timedelta(days=7)
                )
                orders = self.trading_engine.client.get_orders(filter=request)
                for order in orders:
                    if not getattr(order, 'filled_at', None):
                        continue
                    side = getattr(order.side, 'value', order.side)
                    if side != 'sell':
                        continue
                    symbol = order.symbol.upper()
                    price = getattr(order, 'filled_avg_price', None)
                    if price is None:
                        price = getattr(order, 'avg_fill_price', None)
                    if price is None:
                        price = getattr(order, 'filled_price', None)
                    recent_sell_fills.setdefault(symbol, []).append({
                        'filled_at': order.filled_at,
                        'price': float(price) if price else None
                    })
                for symbol, fills in recent_sell_fills.items():
                    fills.sort(key=lambda x: x['filled_at'])
            except Exception as e:
                self.logger.warning(f"⚠️ Could not fetch recent closed orders for exit reconciliation: {e}")
            
            # Backfill missing exit data for exited positions using recent sell fills
            try:
                from bot_v2.models.positions import PositionStatus
                def _parse_date(value):
                    if isinstance(value, dt.date):
                        return value
                    if isinstance(value, str):
                        try:
                            return dt.date.fromisoformat(value)
                        except Exception:
                            return None
                    return None
                
                all_positions = self.position_tracker.get_positions()
                backfilled = 0
                for pos in all_positions:
                    if pos.status != PositionStatus.EXITED:
                        continue
                    if pos.exit_price is not None and pos.realized_pnl is not None:
                        continue
                    fills = recent_sell_fills.get(pos.symbol.upper())
                    if not fills:
                        continue
                    entry_date = _parse_date(getattr(pos, 'entry_date', None))
                    candidates = [f for f in fills if (entry_date is None or f['filled_at'].date() >= entry_date)]
                    if not candidates:
                        continue
                    best = candidates[-1]
                    if best.get('price') is None:
                        continue
                    pos.exit_price = best['price']
                    pos.exit_timestamp = best['filled_at']
                    pos.exit_date = best['filled_at'].date()
                    pos.realized_pnl = (pos.exit_price - pos.entry_price) * pos.position_size_shares
                    backfilled += 1
                if backfilled > 0:
                    self.logger.info(f"✅ Backfilled exit data for {backfilled} positions from Alpaca sells")
                    self.position_tracker.save_positions()
            except Exception as e:
                self.logger.warning(f"⚠️ Exit backfill failed: {e}")
            
            # Get actual positions from Alpaca
            alpaca_positions = self.trading_engine.get_positions()
            
            if not alpaca_positions:
                self.logger.info("   Alpaca: 0 positions")
                
                # Clear any tracked positions that don't exist in Alpaca
                tracked = self.position_tracker.get_active_positions()
                if tracked:
                    self.logger.warning(f"   ⚠️ Tracker has {len(tracked)} positions but Alpaca has 0 - clearing tracker")
                    for pos in tracked:
                        from bot_v2.models.positions import PositionStatus
                        pos.status = PositionStatus.EXITED
                        # TIER 1 FIX: Use actual sell fill or zero P&L for phantom exits
                        sell_fills = recent_sell_fills.get(pos.symbol.upper(), [])
                        latest_fill = sell_fills[-1] if sell_fills else None
                        if latest_fill and latest_fill.get('price') is not None:
                            pos.exit_price = latest_fill['price']
                            pos.exit_timestamp = latest_fill['filled_at']
                            pos.exit_date = latest_fill['filled_at'].date()
                            pos.exit_reason = "Exited via Alpaca (sync reconciled)"
                            pos.realized_pnl = (pos.exit_price - pos.entry_price) * pos.position_size_shares
                        else:
                            pos.exit_timestamp = dt.datetime.now(pytz.UTC)
                            pos.exit_date = dt.date.today()
                            pos.exit_price = pos.entry_price
                            pos.exit_reason = "Sync cleanup (no Alpaca fill found — phantom)"
                            pos.realized_pnl = 0.0  # ZERO P&L for phantom exits
                            self.logger.warning(
                                f"      ⚠️ {pos.symbol}: Phantom exit — P&L set to $0.00"
                            )
                    self.position_tracker.save_positions()
                return
            
            self.logger.info(f"   Alpaca: {len(alpaca_positions)} positions")
            
            # Get bot's tracked positions
            tracked_positions = self.position_tracker.get_active_positions()
            self.logger.info(f"   Tracker: {len(tracked_positions)} positions")
            
            # Check each Alpaca position
            synced_count = 0
            added_count = 0
            updated_count = 0
            
            for symbol, alpaca_pos in alpaca_positions.items():
                alpaca_qty = int(float(alpaca_pos['quantity']))
                
                # Find in tracked positions
                tracked = next((p for p in tracked_positions if p.symbol == symbol), None)
                
                if not tracked:
                    self.logger.warning(
                        f"   ⚠️ {symbol}: Alpaca has {alpaca_qty} shares but NOT in tracker"
                    )
                    self.logger.info(f"      Creating position entry for {symbol}")
                    
                    # Get ACTUAL entry date from Alpaca order history
                    entry_date_actual = None
                    filled_at_actual = None
                    
                    try:
                        from alpaca.trading.requests import GetOrdersRequest
                        from alpaca.trading.enums import QueryOrderStatus
                        
                        # Get recent buy orders for this symbol
                        request = GetOrdersRequest(
                            status=QueryOrderStatus.CLOSED,
                            limit=100,
                            after=dt.datetime.now(pytz.UTC) - dt.timedelta(days=7)
                        )
                        orders = self.trading_engine.client.get_orders(filter=request)
                        
                        # Find most recent buy order for this symbol
                        for order in orders:
                            if order.symbol == symbol and order.side.value == 'buy' and order.filled_at:
                                entry_date_actual = order.filled_at.date()
                                filled_at_actual = order.filled_at
                                self.logger.info(f"      Found actual entry date: {entry_date_actual}")
                                break
                    except Exception as e:
                        self.logger.warning(f"      Could not fetch entry date from orders: {e}")
                    
                    # If we couldn't find the actual date, estimate conservatively
                    if not entry_date_actual:
                        entry_date_actual = dt.date.today()  # Assume today to avoid PDT issues
                        filled_at_actual = dt.datetime.now(pytz.timezone('US/Eastern'))
                        self.logger.warning(f"      Using TODAY as entry date (conservative estimate)")
                    
                    # Create new position from Alpaca data
                    from bot_v2.models.positions import ShortCyclePosition, PositionStatus
                    from bot_v2.models.signals import AISignal
                    
                    # Create minimal signal for orphaned position
                    dummy_signal = AISignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=0.5,
                        time_horizon_days=1.0,
                        signal_timestamp=dt.datetime.now(pytz.timezone('US/Eastern')),
                        features_used={}
                    )
                    
                    entry_price = float(alpaca_pos['avg_cost'])
                    position_value = entry_price * alpaca_qty
                    
                    # Calculate exit date (D+3 default for swing strategy)
                    exit_date_calculated = entry_date_actual + dt.timedelta(days=5)  # ~3 trading days
                    
                    new_pos = ShortCyclePosition(
                        symbol=symbol,
                        entry_price=entry_price,
                        position_size_shares=alpaca_qty,
                        position_size_dollars=position_value,
                        entry_date=entry_date_actual,  # Use ACTUAL date from Alpaca
                        exit_date=exit_date_calculated,  # D+3 swing strategy
                        stop_price=entry_price * (1 - self.config.stop_loss_pct),  # Use config stop
                        target_price=entry_price * (1 + self.config.profit_target_pct),  # Use config target
                        status=PositionStatus.ENTERED,
                        ai_signal=dummy_signal,
                        filled_at=filled_at_actual
                    )
                    # TIER 1 FIX: Flag synced positions so P&L tracking can distinguish them
                    new_pos.exit_reason = 'synced_from_alpaca'
                    self.position_tracker.add_position(new_pos)
                    self.logger.warning(
                        f"      ⚠️ SYNCED POSITION (not a real signal entry): {symbol} "
                        f"{alpaca_qty} shares @ ${entry_price:.2f}"
                    )
                    added_count += 1
                    
                elif tracked.position_size_shares != alpaca_qty:
                    # Check if this is a quantity change or a completely new position
                    alpaca_entry_price = float(alpaca_pos['avg_cost'])
                    price_diff_pct = abs(alpaca_entry_price - tracked.entry_price) / tracked.entry_price
                    
                    # If entry price differs significantly (>1%), this is likely a NEW position
                    if price_diff_pct > 0.01:
                        self.logger.warning(
                            f"   ⚠️ {symbol}: Entry price mismatch - "
                            f"Tracker: ${tracked.entry_price:.2f}, Alpaca: ${alpaca_entry_price:.2f}"
                        )
                        self.logger.info(f"      This appears to be a NEW position - marking old one as exited")
                        
                        # Mark old position as exited
                        from bot_v2.models.positions import PositionStatus
                        tracked.status = PositionStatus.EXITED
                        tracked.exit_reason = "Position closed, new entry detected"
                        
                        # Create new position for the Alpaca position
                        from bot_v2.models.positions import ShortCyclePosition
                        from bot_v2.models.signals import AISignal
                        
                        dummy_signal = AISignal(
                            symbol=symbol,
                            action='BUY',
                            confidence=0.5,
                            time_horizon_days=1.0,
                            signal_timestamp=dt.datetime.now(pytz.timezone('US/Eastern')),
                            features_used={}
                        )
                        
                        position_value = alpaca_entry_price * alpaca_qty
                        
                        new_pos = ShortCyclePosition(
                            symbol=symbol,
                            entry_price=alpaca_entry_price,
                            position_size_shares=alpaca_qty,
                            position_size_dollars=position_value,
                            entry_date=dt.date.today(),  # NEW position today
                            exit_date=dt.date.today() + dt.timedelta(days=5),  # D+3 swing
                            stop_price=alpaca_entry_price * 0.98,
                            target_price=None,
                            status=PositionStatus.ENTERED,
                            ai_signal=dummy_signal,
                            filled_at=dt.datetime.now(pytz.timezone('US/Eastern'))
                        )
                        self.position_tracker.add_position(new_pos)
                        added_count += 1
                    else:
                        # Same position, just quantity changed (partial fill/exit)
                        self.logger.warning(
                            f"   ⚠️ {symbol}: Quantity mismatch - "
                            f"Tracker: {tracked.position_size_shares}, Alpaca: {alpaca_qty}"
                        )
                        self.logger.info(f"      Updating {symbol} to {alpaca_qty} shares")
                        tracked.position_size_shares = alpaca_qty
                        tracked.position_size_dollars = alpaca_entry_price * alpaca_qty
                        updated_count += 1
                else:
                    # Quantity matches - check entry price to be sure it's the same position
                    alpaca_entry_price = float(alpaca_pos['avg_cost'])
                    price_diff_pct = abs(alpaca_entry_price - tracked.entry_price) / tracked.entry_price
                    
                    if price_diff_pct > 0.01:
                        # Different entry price = different position
                        self.logger.warning(
                            f"   ⚠️ {symbol}: Same quantity but different entry price - "
                            f"Tracker: ${tracked.entry_price:.2f}, Alpaca: ${alpaca_entry_price:.2f}"
                        )
                        self.logger.info(f"      Marking old position as exited and creating new one")
                        
                        # Mark old as exited
                        from bot_v2.models.positions import PositionStatus
                        tracked.status = PositionStatus.EXITED
                        tracked.exit_reason = "Position replaced with new entry"
                        
                        # Create new position
                        from bot_v2.models.positions import ShortCyclePosition
                        from bot_v2.models.signals import AISignal
                        
                        dummy_signal = AISignal(
                            symbol=symbol,
                            action='BUY',
                            confidence=0.5,
                            time_horizon_days=1.0,
                            signal_timestamp=dt.datetime.now(pytz.timezone('US/Eastern')),
                            features_used={}
                        )
                        
                        position_value = alpaca_entry_price * alpaca_qty
                        
                        new_pos = ShortCyclePosition(
                            symbol=symbol,
                            entry_price=alpaca_entry_price,
                            position_size_shares=alpaca_qty,
                            position_size_dollars=position_value,
                            entry_date=dt.date.today(),
                            exit_date=dt.date.today() + dt.timedelta(days=5),  # D+3 swing
                            stop_price=alpaca_entry_price * 0.98,
                            target_price=None,
                            status=PositionStatus.ENTERED,
                            ai_signal=dummy_signal,
                            filled_at=dt.datetime.now(pytz.timezone('US/Eastern'))
                        )
                        self.position_tracker.add_position(new_pos)
                        added_count += 1
                    else:
                        # Perfect match
                        synced_count += 1
            
            # Check for positions in tracker but NOT in Alpaca
            exited_count = 0
            for pos in tracked_positions:
                if pos.symbol not in alpaca_positions:
                    self.logger.warning(
                        f"   ⚠️ {pos.symbol}: In tracker but NOT in Alpaca - marking as exited"
                    )
                    from bot_v2.models.positions import PositionStatus
                    pos.status = PositionStatus.EXITED
                    
                    # TIER 1 FIX: Use actual Alpaca sell fill if available.
                    # If no fill found, set P&L to $0 instead of fabricating a price.
                    # This prevents phantom P&L from corrupting performance tracking.
                    sell_fills = recent_sell_fills.get(pos.symbol.upper(), [])
                    latest_fill = sell_fills[-1] if sell_fills else None
                    if latest_fill and latest_fill.get('price') is not None:
                        pos.exit_price = latest_fill['price']
                        pos.exit_timestamp = latest_fill['filled_at']
                        pos.exit_date = latest_fill['filled_at'].date()
                        pos.exit_reason = "Exited via Alpaca (sync reconciled)"
                        pos.realized_pnl = (pos.exit_price - pos.entry_price) * pos.position_size_shares
                        self.logger.info(
                            f"      ✅ {pos.symbol}: Matched Alpaca sell fill @ ${pos.exit_price:.2f} "
                            f"(P&L: ${pos.realized_pnl:+.2f})"
                        )
                    else:
                        # No actual sell fill found — this is a phantom exit.
                        # Record P&L as $0 to avoid corrupting performance data.
                        pos.exit_timestamp = dt.datetime.now(pytz.UTC)
                        pos.exit_date = dt.date.today()
                        pos.exit_price = pos.entry_price  # Neutral exit
                        pos.exit_reason = "Sync cleanup (no Alpaca fill found — phantom)"
                        pos.realized_pnl = 0.0  # ZERO P&L for phantom exits
                        self.logger.warning(
                            f"      ⚠️ {pos.symbol}: No sell fill found in Alpaca. "
                            f"Setting P&L to $0.00 (phantom exit, not a real trade)."
                        )
                    
                    exited_count += 1
            
            # Save all changes (including exited positions for cleanup)
            if added_count > 0 or updated_count > 0 or exited_count > 0:
                self.position_tracker.save_positions()
            
            self.logger.info(
                f"✅ Sync complete: {synced_count} matched, "
                f"{updated_count} updated, {added_count} added, {exited_count} exited"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Position sync failed: {e}", exc_info=True)
    
    def _get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get real-time price for a symbol via Alpaca IEX.

        TIER 2 FIX (Feb 25, 2026): Previously referenced self.trading_engine.api
        which doesn't exist (engine has self.client), and TradingClient doesn't
        have get_latest_quote(). So this method ALWAYS returned None, causing
        exit monitoring to fall back to yfinance daily close (1-day stale).

        Now uses alpaca_data_helper → StockHistoricalDataClient.get_stock_latest_trade()
        (confirmed working), with data_loader.get_current_price() as secondary fallback.

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None if unavailable
        """
        # Primary: Alpaca IEX latest trade (real-time)
        try:
            from bot_v2.data.alpaca_data_helper import get_realtime_price
            price = get_realtime_price(symbol)
            if price is not None:
                return price
        except Exception as e:
            self.logger.debug(f"Alpaca helper price failed for {symbol}: {e}")

        # Secondary: DataLoader.get_current_price (also uses Alpaca, with yfinance fallback)
        try:
            price = self.data_loader.get_current_price(symbol)
            if price is not None:
                return price
        except Exception as e:
            self.logger.debug(f"DataLoader price failed for {symbol}: {e}")

        return None
    
    def _is_market_hours(self) -> bool:
        """Check if market is currently open"""
        now = dt.datetime.now(self.tz)
        
        # Weekend check
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def _get_trading_phase(self) -> str:
        """Determine current trading phase
        
        Returns:
            'premarket', 'entry_window', 'continuous_entry', 'late_entry', 'midday_refresh', 
            'monitoring', 'force_exit', 'force_exit_losers', 'postmarket', 'closed'
        """
        now = dt.datetime.now(self.tz)
        
        # Weekend
        if now.weekday() >= 5:
            return 'closed'
        
        current_time = now.time()
        
        # Premarket: 7:00 AM - 9:30 AM
        if current_time >= dt.time(7, 0) and current_time < dt.time(9, 30):
            return 'premarket'
        
        # Entry window: 9:35 AM - 10:30 AM (recovery mode: catch early post-open setups)
        if current_time >= dt.time(9, 35) and current_time < dt.time(10, 30):
            return 'entry_window'

        # Late-entry boundaries from config (used by both continuous and late phases)
        late_entry_start_str = getattr(self.config, 'late_entry_start_time', '11:00')
        late_entry_end_str = getattr(self.config, 'late_entry_end_time', '15:00')
        try:
            late_start_hour, late_start_min = [int(x) for x in late_entry_start_str.split(':', 1)]
            late_end_hour, late_end_min = [int(x) for x in late_entry_end_str.split(':', 1)]
            late_entry_start = dt.time(late_start_hour, late_start_min)
            late_entry_end = dt.time(late_end_hour, late_end_min)
        except Exception:
            late_entry_start = dt.time(11, 0)
            late_entry_end = dt.time(15, 0)

        # Continuous entry scanning: 10:30 AM until configured late-entry start
        if current_time >= dt.time(10, 30) and current_time < late_entry_start:
            return 'continuous_entry'

        # Late entry window: config-driven boundaries
        if current_time >= late_entry_start and current_time < late_entry_end:
            if getattr(self.config, 'enable_late_entry', True):
                return 'late_entry'
            return 'continuous_entry'  # Fall back to continuous if late entry disabled
        
        # Force exit window: 3:30 PM - 4:00 PM (Friday) - Start earlier for reliability
        # Keep trying until market close to ensure weekend positions are closed
        # Respects friday_force_exit_enabled config setting
        if current_time >= dt.time(15, 30) and current_time < dt.time(16, 0):
            if now.weekday() == 4:  # Friday
                # Check if force exit is enabled (default False - dynamic trailing protects gains)
                if getattr(self.config, 'friday_force_exit_enabled', False):
                    return 'force_exit'
                # Even if force exit disabled, still exit losers if enabled
                elif getattr(self.config, 'friday_exit_losers_only', True):
                    return 'force_exit_losers'
        
        # Mid-day refresh windows (if no entries): 11:00 AM, 12:00 PM, 1:00 PM
        midday_windows = [
            (dt.time(11, 0), dt.time(11, 15)),  # 11:00-11:15 AM
            (dt.time(12, 0), dt.time(12, 15)),  # 12:00-12:15 PM
            (dt.time(13, 0), dt.time(13, 15)),  # 1:00-1:15 PM
        ]
        for start, end in midday_windows:
            if start <= current_time < end:
                return 'midday_refresh'
        
        # Regular monitoring: 10:00 AM - 3:45 PM
        if current_time >= dt.time(10, 0) and current_time < dt.time(15, 45):
            return 'monitoring'
        
        # Postmarket: 4:00 PM - 7:00 PM
        if current_time >= dt.time(16, 0) and current_time < dt.time(19, 0):
            return 'postmarket'
        
        return 'closed'
    
    def _run_midday_refresh(self):
        """Run mid-day refresh to look for additional opportunities (11 AM, 12 PM, 1 PM)"""
        now = dt.datetime.now(self.tz)
        
        # Only refresh once per window
        if self.last_midday_refresh and self.last_midday_refresh >= now.replace(minute=0, second=0, microsecond=0):
            return
        
        # Check if we're at max positions
        active_positions = len(self.position_tracker.get_active_positions())
        if active_positions >= self.config.max_positions_per_day:
            self.logger.info(f"💼 At max positions ({active_positions}/{self.config.max_positions_per_day}) - skipping mid-day refresh")
            return
        
        self.logger.info("=" * 80)
        self.logger.info(f"🔄 MID-DAY REFRESH ({now.strftime('%I:%M %p')}) - Scanning for opportunities")
        self.logger.info(f"   Current positions: {active_positions}/{self.config.max_positions_per_day} | Entries today: {self.entries_today}")
        self.logger.info("=" * 80)
        self.logger.info("♻️ Re-scanning universe for new opportunities...")
        
        # Run a fresh entry scan
        self._run_entry_scan()
        
        self.last_midday_refresh = now
        
        active_positions = len(self.position_tracker.get_active_positions())
        if active_positions == 0:
            self.logger.info("⚠️ No positions yet - will continue scanning")
        elif active_positions < self.config.max_positions_per_day:
            self.logger.info(f"✅ {active_positions} positions active - room for more")
        else:
            self.logger.info(f"✅ At max positions ({active_positions}/{self.config.max_positions_per_day})")
    
    def _refresh_watchlist(self):
        """Refresh trading universe watchlist (postmarket)"""
        self.logger.info("=" * 80)
        self.logger.info("📋 WATCHLIST REFRESH (Postmarket)")
        self.logger.info("=" * 80)
        
        try:
            # Get universe from data loader or pre-filter
            # TODO: Integrate with PreFilter for dynamic universe
            universe = self._get_universe()
            
            self.logger.info(f"✅ Watchlist refreshed: {len(universe)} symbols")
            self.last_watchlist_refresh = dt.datetime.now(self.tz)
            
            return universe
            
        except Exception as e:
            self.logger.error(f"❌ Watchlist refresh failed: {e}")
            return []
    
    def _run_gap_predictions(self):
        """Run overnight gap predictor to identify next-day opportunities (4:45 PM)"""
        self.logger.info("=" * 80)
        self.logger.info("🌙 OVERNIGHT GAP PREDICTIONS (Postmarket)")
        self.logger.info("=" * 80)
        
        try:
            from bot_v2.gap_scanner.overnight_gap_predictor import OvernightGapPredictor
            
            # Get universe
            universe = self._get_universe()
            
            # Initialize predictor
            predictor = OvernightGapPredictor(self.data_loader, logger=self.logger)
            
            # Generate predictions
            predictions = predictor.predict_next_day_gaps(universe[:100])  # Top 100 for speed
            
            # Print predictions
            predictor.print_predictions(predictions)
            
            # Get actionable recommendations
            buy_eod = [p for p in predictions.values() if p.recommendation == 'BUY_EOD']
            
            if buy_eod:
                self.logger.info(f"\n🎯 {len(buy_eod)} stocks recommended for EOD buy:")
                for p in buy_eod[:5]:
                    self.logger.info(
                        f"   {p.symbol}: Expected gap +{p.predicted_gap_pct*100:.1f}% "
                        f"({p.confidence:.0%} confidence)"
                    )
            else:
                self.logger.info("📊 No high-confidence gap-up predictions for tomorrow")
            
            # Store for reference
            self._last_gap_predictions = predictions
            
        except Exception as e:
            self.logger.error(f"❌ Gap prediction failed: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def _build_sector_lookup(self):
        """Build symbol → sector mapping from mid_cap_universe.json for concentration checks"""
        import json
        from pathlib import Path
        
        self.sector_lookup = {}  # symbol → sector name
        try:
            universe_file = Path(__file__).parent / "data" / "mid_cap_universe.json"
            with open(universe_file) as f:
                data = json.load(f)
            for sector_name, symbols in data.items():
                if isinstance(symbols, list):
                    for sym in symbols:
                        self.sector_lookup[sym] = sector_name
            self.logger.info(f"📊 Sector lookup built: {len(self.sector_lookup)} symbols across {len(data)} sectors")
        except Exception as e:
            self.logger.error(f"❌ Failed to build sector lookup: {e}")
            self.sector_lookup = {}
    
    def _check_sector_cap(self, symbol: str, max_per_sector: int = 2) -> bool:
        """Check if adding a position in this symbol's sector would exceed concentration limit.
        
        Args:
            symbol: Stock symbol to check
            max_per_sector: Maximum positions allowed per sector (default 2)
            
        Returns:
            True if entry is allowed, False if sector is at capacity
        """
        sector = self.sector_lookup.get(symbol)
        if not sector:
            # Unknown sector — allow entry but warn
            self.logger.warning(f"⚠️ {symbol} not found in sector lookup — allowing entry")
            return True
        
        # Count active positions in the same sector
        active_positions = self.position_tracker.get_active_positions()
        same_sector_count = 0
        same_sector_symbols = []
        for pos in active_positions:
            pos_symbol = pos.symbol if hasattr(pos, 'symbol') else str(pos)
            pos_sector = self.sector_lookup.get(pos_symbol)
            if pos_sector == sector:
                same_sector_count += 1
                same_sector_symbols.append(pos_symbol)
        
        if same_sector_count >= max_per_sector:
            self.logger.warning(
                f"🚫 SECTOR CAP: {symbol} ({sector}) blocked — "
                f"already {same_sector_count} positions in sector: {same_sector_symbols}"
            )
            return False
        
        return True
    
    def _get_universe(self) -> List[str]:
        """Load 150-stock curated mid-cap universe from JSON (excluding REITs)"""
        import json
        from pathlib import Path
        
        try:
            universe_file = Path(__file__).parent / "data" / "mid_cap_universe.json"
            with open(universe_file) as f:
                data = json.load(f)
            
            # Flatten all sectors into single list, EXCLUDING REITs
            all_stocks = []
            for key, value in data.items():
                # Skip REIT sector - REITs are dividend-focused, not mean reversion candidates
                if key.lower() == 'reits' or 'reit' in key.lower():
                    self.logger.info(f"🚫 Skipping {key}: {len(value)} REITs excluded (dividend stocks, not mean reversion)")
                    continue
                    
                if isinstance(value, list):
                    all_stocks.extend(value)
            
            self.logger.info(f"📊 Loaded universe: {len(all_stocks)} stocks (REITs filtered out)")
            return all_stocks
        except Exception as e:
            self.logger.error(f"❌ Failed to load universe: {e}, using fallback mid-cap stocks")
            # Fallback uses only mid-cap stocks ($2B-$10B) to preserve strategy integrity
            return ["LCID", "RIVN", "NCLH", "NTLA", "PLTR", "SOFI", "UPST", "AI", "NET", "CRWD"]
    
    def _run_morning_brief(self):
        """Generate and display morning market brief (9:00 AM)"""
        self.logger.info("=" * 80)
        self.logger.info("🌅 GENERATING MORNING BRIEF")
        self.logger.info("=" * 80)
        
        try:
            universe = self._get_universe()
            brief = self.market_brief.generate_brief(universe)
            self.market_brief.print_brief(brief)
            self.last_morning_brief = dt.datetime.now(self.tz)
        except Exception as e:
            self.logger.error(f"❌ Failed to generate morning brief: {e}")
    
    def _run_daily_summary(self):
        """Generate and display daily summary (4:30 PM)"""
        self.logger.info("=" * 80)
        self.logger.info("📊 GENERATING DAILY SUMMARY")
        self.logger.info("=" * 80)
        
        try:
            summary = self.daily_summary.generate_summary(self.session_data)
            self.daily_summary.print_summary(summary, show_details=False)
            
            # Record P&L for tracking
            try:
                from bot_v2.reporting.pnl_tracker import PnLTracker
                pnl_tracker = PnLTracker(logger=self.logger)
                
                # Get account equity from Alpaca (source of truth)
                try:
                    account_info = self.trading_engine.get_account_info()
                    account_equity = float(account_info['portfolio_value'])
                except:
                    account_equity = self.config.portfolio_value
                
                # Extract P&L data from summary
                pnl_data = summary.get('pnl', {})
                activity = summary.get('activity', {})
                
                pnl_tracker.record_day(
                    realized_pnl=pnl_data.get('realized', 0),
                    unrealized_pnl=pnl_data.get('unrealized', 0),
                    trades=activity.get('entries_executed', 0) + len(summary.get('exits', [])),
                    wins=sum(1 for e in summary.get('exits', []) if (e.get('realized_pnl', e.get('pnl', 0)) or 0) > 0),
                    entries=activity.get('entries_executed', 0),
                    exits=len(summary.get('exits', [])),
                    deployed_capital=pnl_data.get('deployed_capital', 0),
                    account_equity=account_equity
                )
                
                # Show P&L summary
                pnl_tracker.print_summary()
                
            except Exception as e:
                self.logger.warning(f"⚠️ P&L tracking failed: {e}")
            
            # Offer to show details
            print("\n💡 To see detailed breakdowns (entries, exits, positions), ")
            print("   run: python3 -c \"from bot_v2.launcher import show_daily_details; show_daily_details()\"")
            
            self.last_daily_summary = dt.datetime.now(self.tz)
            
            # Reset session data for tomorrow
            self.session_data = self._new_session_data()
        except Exception as e:
            self.logger.error(f"❌ Failed to generate daily summary: {e}")
    
    def _run_premarket_scan(self):
        """Run premarket gap scan and portfolio summary"""
        self.logger.info("=" * 80)
        self.logger.info("🌅 PREMARKET SCAN (9:00 AM)")
        self.logger.info("=" * 80)
        
        try:
            # Fetch VIX/SPY only when Gap&Go or Fade/Short are enabled.
            # In momentum-only mode this would be misleading noise.
            if self.config.enable_gap_and_go or self.config.enable_fade_short:
                self.logger.info("📊 Fetching market conditions for strategy allocation...")
                try:
                    gap_alloc, fade_alloc = self.config.get_live_market_allocation()
                    self.logger.info(f"📊 Strategy Allocation: Gap&Go {gap_alloc:.0%} | Fade {fade_alloc:.0%}")

                    # Update config with live allocation
                    self.config.gap_and_go_allocation = gap_alloc
                    self.config.fade_short_allocation = fade_alloc

                    # Store for reference
                    self._today_gap_allocation = gap_alloc
                    self._today_fade_allocation = fade_alloc
                except Exception as e:
                    self.logger.warning(f"⚠️ Market allocation fetch failed: {e} - Using defaults")
            else:
                self.logger.info("📊 Strategy Mode: Momentum-only (Gap&Go/Fade disabled)")
            
            # Portfolio summary
            positions = self.position_tracker.get_active_positions()
            self.logger.info(f"📊 Active Positions: {len(positions)}")
            
            for pos in positions:
                # Update current price if available
                current_price = self._get_realtime_price(pos.symbol)
                if current_price:
                    pos.current_price = current_price
                    pnl_pct = ((pos.current_price - pos.entry_price) / pos.entry_price) * 100
                    self.logger.info(
                        f"   {pos.symbol}: ${pos.current_price:.2f} "
                        f"({pnl_pct:+.1f}%) - Day {pos.days_held}"
                    )
                else:
                    self.logger.info(
                        f"   {pos.symbol}: ${pos.entry_price:.2f} (entry) - Day {pos.days_held} - Price unavailable"
                    )
            
            # Gap scan (optional - requires market data API)
            if self.gap_scanner:
                try:
                    universe = self._get_universe()
                    gap_results = self.gap_scanner.scan_premarket_gaps(universe)
                    
                    if gap_results:
                        self.logger.info(f"\n📈 Gap Scan Results: {len(gap_results)} gaps detected")
                        for symbol, gap_info in gap_results.items():
                            self.logger.info(
                                f"   {symbol}: {gap_info['gap_pct']*100:+.1f}% gap, "
                                f"quality: {gap_info.get('gap_quality', 'N/A')}"
                            )
                    else:
                        self.logger.info("📊 No significant gaps detected")
                except Exception as e:
                    self.logger.warning(f"⚠️ Gap scan unavailable (market data API issue): {e}")
            
            self.last_gap_scan = dt.datetime.now(self.tz)
            
        except Exception as e:
            self.logger.error(f"❌ Premarket scan failed: {e}")
    
    def _run_entry_scan(self):
        """Run entry scan with PreFilter during entry window (9:45-10:00 AM)"""
        self.logger.info("=" * 80)
        self.logger.info("🎯 ENTRY SCAN (9:45-10:00 AM)")
        self.logger.info("=" * 80)
        
        try:
            # Get full 150-stock universe
            full_universe = self._get_universe()
            
            # Run PreFilter (3-stage: Price/Volume/Volatility)
            from bot_v2.core.pre_filter import PreFilter
            from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG
            
            import time
            start_time = time.time()
            prefilter = PreFilter(self.data_loader, SIMPLE_PREFILTER_CONFIG)
            candidates = prefilter.run_filter(full_universe)
            prefilter_duration = (time.time() - start_time) * 1000
            prefilter_stats = prefilter.get_last_run_stats()
            
            self.logger.info(f"📊 PreFilter: {len(candidates)} candidates from {len(full_universe)} stocks")
            
            # Enhanced logging: PreFilter results
            self.enhanced_logger.log_prefilter_results(
                total=len(full_universe),
                passed=len(candidates),
                failed=len(full_universe) - len(candidates),
                duration_ms=prefilter_duration,
                reasons=prefilter_stats.get('rejection_reasons', {})
            )
            self._record_rejection_counts(prefilter_stats.get('rejection_reasons', {}))
            
            # Track session data
            self.session_data['scans_run'] += 1
            self.session_data['candidates_reviewed'].extend(candidates)
            
            if not candidates:
                self.logger.warning("⚠️ PreFilter returned 0 candidates")
                return
            
            # Get market data for candidates only
            market_data = {}
            for symbol in candidates:
                try:
                    data = self.data_loader.get_historical_data(symbol, days=100)
                    market_data[symbol] = data
                except Exception as e:
                    self.logger.debug(f"Failed to load data for {symbol}: {e}")
            
            # TIER 2 (Feb 25, 2026): Batch-fetch real-time Alpaca IEX prices
            # and inject into signal generator before analysis.
            try:
                from bot_v2.data.alpaca_data_helper import get_batch_prices
                rt_prices = get_batch_prices(list(market_data.keys()))
                self.signal_generator.set_realtime_prices(rt_prices)
            except Exception as e:
                self.logger.debug(f"Alpaca batch price fetch skipped: {e}")
                self.signal_generator.set_realtime_prices({})
            
            # Generate signals on pre-filtered candidates
            active_positions = self.position_tracker.get_active_positions()
            signal_start = time.time()
            signals = self.signal_generator.generate_signals(
                universe=candidates,  # Use pre-filtered candidates
                market_data=market_data,
                active_positions=active_positions
            )
            signal_duration = (time.time() - signal_start) * 1000
            signal_rejections = self.signal_generator.get_last_rejection_stats()
            self._record_rejection_counts(signal_rejections.get('counts', {}))
            self._log_signal_rejections("entry_window", signal_rejections)
            
            signals = self._dedupe_signals_by_symbol(signals)
            self.logger.info(f"✅ Generated {len(signals)} entry signals")
            if len(signals) == 0:
                counts = signal_rejections.get('counts', {}) if signal_rejections else {}
                top_reasons = [
                    f"{reason}={count}"
                    for reason, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
                    if count > 0
                ][:6]
                top_text = ', '.join(top_reasons) if top_reasons else 'none'
                self.logger.warning(f"⚠️ No entry signals this scan. Top rejection counts: {top_text}")
            self.session_data['signals_generated'] += len(signals)
            
            # Enhanced logging: Signal generation
            self.enhanced_logger.log_signal_generation(
                phase="entry_window",
                candidates_in=len(candidates),
                candidates_out=len(signals),
                duration_ms=signal_duration
            )
            
            # Track last entry scan
            now = dt.datetime.now(self.tz)
            if self.last_entry_scan is None or self.last_entry_scan.date() < now.date():
                self.entries_today = 0  # Reset daily counter
            self.last_entry_scan = now
            
            # Execute entries
            for signal in signals:
                try:
                    # PDT compliance is handled by order_manager._record_day_trade_if_needed()
                    # For D+1 strategy (max_hold_days=2), trades are NOT day trades
                    # Only intraday trades (max_hold_days=0) trigger PDT counting
                    
                    # Check daily entry cap (efficiency improvement - fewer, higher quality entries)
                    max_daily_entries = getattr(self.config, 'max_daily_entries', 6)
                    if self.entries_today >= max_daily_entries:
                        self.logger.info(f"📊 Daily entry cap reached ({self.entries_today}/{max_daily_entries}) - no more entries today")
                        break  # Stop processing more signals
                    
                    # Check earnings blackout
                    if self._should_block_entry_symbol(signal.symbol):
                        self.logger.info(f"🚫 Entry blocked by symbol guard: {signal.symbol}")
                        self._record_rejection('symbol_guard_block', signal.symbol)
                        continue

                    if self._is_rejected_symbol_on_cooldown(signal.symbol):
                        self.logger.info(f"⏳ Entry cooldown after rejection: {signal.symbol}")
                        self._record_rejection('rejected_symbol_cooldown', signal.symbol)
                        continue

                    # Check earnings blackout
                    if self.earnings_calendar.should_avoid_entry(signal.symbol):
                        self.logger.warning(f"⚠️ Earnings Blackout: {signal.symbol} entry blocked")
                        self._record_rejection('earnings_blackout', signal.symbol)
                        continue
                    
                    # SECTOR CONCENTRATION CHECK: Max 2 positions per sector
                    if not self._check_sector_cap(signal.symbol, max_per_sector=2):
                        self._record_rejection('sector_cap', signal.symbol)
                        continue
                    
                    # Execute entry
                    position = self.order_manager.execute_entry(signal)
                    if position:
                        self.logger.info(f"✅ Entry executed: {signal.symbol} @ ${signal.entry_price:.2f}")
                        
                        # Enhanced logging: Position entry
                        strategy_name = signal.features_used.get("strategy", "UNKNOWN") if signal.features_used else "UNKNOWN"
                        self.enhanced_logger.log_position_entry(
                            symbol=signal.symbol,
                            price=signal.entry_price,
                            shares=position.position_size_shares,
                            signal_score=signal.confidence,
                            reason=strategy_name
                        )
                        
                        # Track position for exits
                        self.position_tracker.add_position(position)
                        self.position_tracker.save_positions()
                        # PDT tracking is handled by order_manager._record_day_trade_if_needed()
                        # Only intraday trades (max_hold_days=0) are recorded as day trades
                        self.entries_today += 1
                        self._record_entered_symbol(signal.symbol)
                        self._rejected_symbols_today.pop(signal.symbol.upper(), None)
                        self.session_data['entries_executed'].append(signal.symbol)
                    else:
                        self.logger.warning(f"⚠️ Entry rejected: {signal.symbol} (check order_manager logs for details)")
                        self._record_rejected_symbol(signal.symbol)
                        self._record_rejection('order_manager_rejected', signal.symbol)
                    
                except Exception as e:
                    self.logger.error(f"❌ Entry failed for {signal.symbol}: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ Entry scan failed: {e}")
    
    def _run_late_entry_scan(self):
        """Run late entry scan (1:00 PM - 2:30 PM) with higher confidence bar
        
        Late entries have:
        - Higher confidence requirement (1.2x default threshold)
        - Reduced position size (75% of normal)
        - Focus on afternoon momentum continuation
        - Requires higher ADR for volatility
        """
        conf_multiplier = getattr(self.config, 'late_entry_confidence_multiplier', 1.2)
        size_pct = getattr(self.config, 'late_entry_position_size_pct', 0.75)
        min_adr = getattr(self.config, 'late_entry_min_adr_pct', 0.025)
        
        self.logger.info("=" * 80)
        self.logger.info("🌅 LATE ENTRY SCAN (1:00 PM - 2:30 PM)")
        self.logger.info(f"   Confidence: {conf_multiplier:.1f}x | Size: {size_pct:.0%} | Min ADR: {min_adr:.1%}")
        self.logger.info("=" * 80)
        
        try:
            # Get full universe
            full_universe = self._get_universe()
            
            # Run PreFilter
            from bot_v2.core.pre_filter import PreFilter
            from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG
            
            import time
            start_time = time.time()
            prefilter = PreFilter(self.data_loader, SIMPLE_PREFILTER_CONFIG)
            candidates = prefilter.run_filter(full_universe)
            prefilter_duration = (time.time() - start_time) * 1000
            prefilter_stats = prefilter.get_last_run_stats()
            
            self.logger.info(f"📊 PreFilter: {len(candidates)} candidates from {len(full_universe)} stocks")
            
            # Track session data
            self.session_data['scans_run'] += 1
            self.session_data['candidates_reviewed'].extend(candidates)

            self.enhanced_logger.log_prefilter_results(
                total=len(full_universe),
                passed=len(candidates),
                failed=len(full_universe) - len(candidates),
                duration_ms=prefilter_duration,
                reasons=prefilter_stats.get('rejection_reasons', {})
            )
            self._record_rejection_counts(prefilter_stats.get('rejection_reasons', {}))
            
            if not candidates:
                self.logger.warning("⚠️ PreFilter returned 0 candidates for late entry")
                return
            
            # Filter for higher ADR (need volatility for afternoon moves)
            high_adr_candidates = []
            for symbol in candidates:
                try:
                    data = self.data_loader.get_historical_data(symbol, days=20)
                    if data is not None and len(data) >= 14:
                        # Calculate ADR as average of (high-low)/close
                        adr = ((data['high'] - data['low']) / data['close']).tail(14).mean()
                        if adr >= min_adr:
                            high_adr_candidates.append(symbol)
                except Exception:
                    pass
            
            self.logger.info(f"📊 ADR Filter ({min_adr:.1%}+): {len(high_adr_candidates)} candidates")
            
            if not high_adr_candidates:
                self.logger.info("⚠️ No candidates passed ADR filter for late entry")
                self._record_rejection('late_entry_adr_filter')
                return
            
            # Get market data
            market_data = {}
            for symbol in high_adr_candidates:
                try:
                    data = self.data_loader.get_historical_data(symbol, days=100)
                    market_data[symbol] = data
                except Exception:
                    pass
            
            # TIER 2: Batch-fetch Alpaca real-time prices for late entry scan
            try:
                from bot_v2.data.alpaca_data_helper import get_batch_prices
                rt_prices = get_batch_prices(list(market_data.keys()))
                self.signal_generator.set_realtime_prices(rt_prices)
            except Exception as e:
                self.logger.debug(f"Alpaca batch price fetch skipped: {e}")
                self.signal_generator.set_realtime_prices({})
            
            # Generate signals with higher confidence bar
            active_positions = self.position_tracker.get_active_positions()
            
            # Temporarily adjust confidence threshold for late entry
            original_threshold = self.config.confidence_threshold
            self.config.confidence_threshold = original_threshold * conf_multiplier
            
            try:
                signal_start = time.time()
                signals = self.signal_generator.generate_signals(
                    universe=high_adr_candidates,
                    market_data=market_data,
                    active_positions=active_positions
                )
                signal_duration = (time.time() - signal_start) * 1000
                signal_rejections = self.signal_generator.get_last_rejection_stats()
                self._record_rejection_counts(signal_rejections.get('counts', {}))
                self._log_signal_rejections("late_entry", signal_rejections)
            finally:
                # Restore original threshold
                self.config.confidence_threshold = original_threshold
            
            signals = self._dedupe_signals_by_symbol(signals)
            self.logger.info(f"✅ Late entry: {len(signals)} signals at {conf_multiplier:.1f}x confidence bar")
            self.session_data['signals_generated'] += len(signals)
            
            # Enhanced logging
            self.enhanced_logger.log_signal_generation(
                phase="late_entry",
                candidates_in=len(high_adr_candidates),
                candidates_out=len(signals),
                duration_ms=signal_duration
            )
            
            # Track scan time
            now = dt.datetime.now(self.tz)
            if self.last_entry_scan is None or self.last_entry_scan.date() < now.date():
                self.entries_today = 0
            self.last_entry_scan = now
            
            # Execute entries with reduced position size
            for signal in signals:
                try:
                    # Check daily entry cap
                    max_daily_entries = getattr(self.config, 'max_daily_entries', 6)
                    if self.entries_today >= max_daily_entries:
                        self.logger.info(f"📊 Daily entry cap reached ({self.entries_today}/{max_daily_entries}) - no late entries")
                        break
                    
                    if self._should_block_entry_symbol(signal.symbol):
                        self.logger.info(f"🚫 Late entry blocked by symbol guard: {signal.symbol}")
                        self._record_rejection('symbol_guard_block', signal.symbol)
                        continue

                    if self._is_rejected_symbol_on_cooldown(signal.symbol):
                        self.logger.info(f"⏳ Late entry cooldown after rejection: {signal.symbol}")
                        self._record_rejection('rejected_symbol_cooldown', signal.symbol)
                        continue

                    # Check earnings blackout
                    if self.earnings_calendar.should_avoid_entry(signal.symbol):
                        self.logger.warning(f"⚠️ Earnings Blackout: {signal.symbol} late entry blocked")
                        self._record_rejection('earnings_blackout', signal.symbol)
                        continue
                    
                    # SECTOR CONCENTRATION CHECK: Max 2 positions per sector
                    if not self._check_sector_cap(signal.symbol, max_per_sector=2):
                        self._record_rejection('sector_cap', signal.symbol)
                        continue
                    
                    # Reduce position size for late entries
                    original_max_position = self.config.max_position_dollars
                    self.config.max_position_dollars = original_max_position * size_pct
                    
                    try:
                        position = self.order_manager.execute_entry(signal)
                    finally:
                        self.config.max_position_dollars = original_max_position
                    
                    if position:
                        self.logger.info(f"🌅 Late entry executed: {signal.symbol} @ ${signal.entry_price:.2f} (size: {size_pct:.0%})")
                        
                        strategy_name = signal.features_used.get("strategy", "LATE_ENTRY") if signal.features_used else "LATE_ENTRY"
                        self.enhanced_logger.log_position_entry(
                            symbol=signal.symbol,
                            price=signal.entry_price,
                            shares=position.position_size_shares,
                            signal_score=signal.confidence,
                            reason=f"{strategy_name}_LATE"
                        )
                        
                        self.position_tracker.add_position(position)
                        self.position_tracker.save_positions()
                        self.entries_today += 1
                        self._record_entered_symbol(signal.symbol)
                        self._rejected_symbols_today.pop(signal.symbol.upper(), None)
                        self.session_data['entries_executed'].append(signal.symbol)
                    else:
                        self.logger.warning(f"⚠️ Late entry rejected: {signal.symbol}")
                        self._record_rejected_symbol(signal.symbol)
                        self._record_rejection('order_manager_rejected', signal.symbol)
                    
                except Exception as e:
                    self.logger.error(f"❌ Late entry failed for {signal.symbol}: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ Late entry scan failed: {e}")
    
    def _monitor_exits(self):
        """Monitor and execute exits (continuous during market hours)"""
        try:
            # Sync with Alpaca periodically to catch externally closed positions
            self._sync_positions_with_alpaca()
            
            self.logger.info(f"🔍 Checking exits: {len(self.position_tracker.positions)} total positions in tracker")
            active_positions = self.position_tracker.get_active_positions()
            self.logger.info(f"🔍 Found {len(active_positions)} active positions")
            
            if not active_positions:
                self.logger.info(f"No active positions to monitor")
                return
            
            # Debug: Check what type active_positions contains
            for i, pos in enumerate(active_positions):
                self.logger.debug(f"Position {i}: type={type(pos)}, value={pos if isinstance(pos, str) else getattr(pos, 'symbol', 'NO_SYMBOL')}")
            
            for position in active_positions:
                try:
                    # AGGRESSIVE DEBUG: Log exactly what we have
                    self.logger.debug(f"Processing position: type={type(position)}, repr={repr(position)[:100]}")
                    
                    # CRITICAL FIX: Sometimes position becomes a string (symbol) instead of object
                    # This is likely a bug in Alpaca sync or position tracker
                    # If position is a string, find the actual position object
                    if isinstance(position, str):
                        symbol_str = position
                        self.logger.warning(f"⚠️ Position object corrupted to string: {symbol_str}")
                        # Find the real position object
                        position = None
                        for p in self.position_tracker.positions:
                            if hasattr(p, 'symbol') and p.symbol == symbol_str:
                                from bot_v2.models.positions import PositionStatus
                                if p.status == PositionStatus.ENTERED:
                                    position = p
                                    break
                        
                        if not position:
                            self.logger.error(f"❌ Could not find position object for {symbol_str}, skipping")
                            continue
                    
                    # Safety check: Verify position object is valid
                    if not hasattr(position, 'symbol') or not hasattr(position, 'entry_price'):
                        self.logger.warning(f"⚠️ Invalid position object type: {type(position)}, value: {position}")
                        continue
                    
                    # Safety check: Verify entry_timestamp exists - if not, create from entry_date
                    if not hasattr(position, 'entry_timestamp') or position.entry_timestamp is None:
                        # Create timestamp from entry_date (assume 10:00 AM entry)
                        entry_dt = dt.datetime.combine(position.entry_date, dt.time(10, 0))
                        position.entry_timestamp = entry_dt.replace(tzinfo=pytz.UTC)
                        position.filled_at = position.entry_timestamp
                        self.logger.info(f"✅ {position.symbol}: Created entry_timestamp from entry_date: {position.entry_timestamp}")
                    
                    # Update current price - Alpaca IEX real-time (via _get_realtime_price)
                    # TIER 2 FIX: _get_realtime_price now uses Alpaca helper → DataLoader fallback.
                    # No need for separate yfinance historical fallback here.
                    current_price = self._get_realtime_price(position.symbol)
                    
                    if current_price:
                        position.current_price = current_price
                    else:
                        # Still no price - use entry price as fallback for D+1 check
                        self.logger.warning(f"⚠️ {position.symbol}: No price available, using entry price for exit check")
                        current_price = position.entry_price
                        position.current_price = current_price
                    
                    # Update highest price for trailing stops
                    if not hasattr(position, 'highest_price') or position.highest_price is None:
                        position.highest_price = position.entry_price
                    if current_price > position.highest_price:
                        position.highest_price = current_price
                        self.smart_exit_manager.update_position_high(position, current_price)
                    
                    # Calculate hours held (use timezone-aware datetime)
                    now_aware = dt.datetime.now(pytz.UTC)
                    hours_held = (now_aware - position.entry_timestamp).total_seconds() / 3600
                    
                    # Get RSI and volume data for smart exit evaluation
                    rsi = None
                    volume_ratio = None
                    try:
                        data = self.data_loader.get_historical_data(position.symbol, days=30)
                        if not data.empty:
                            # Calculate RSI
                            delta = data['close'].diff()
                            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                            rs = gain / loss
                            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
                            
                            # Calculate volume ratio
                            avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
                            current_volume = data['volume'].iloc[-1]
                            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                    except Exception as e:
                        self.logger.debug(f"{position.symbol}: Could not calculate RSI/volume: {e}")
                    
                    # Check smart exit conditions (9 intelligent strategies)
                    should_exit_smart, smart_reason, smart_exit_price = self.smart_exit_manager.should_exit(
                        position, current_price, rsi, volume_ratio, hours_held
                    )
                    
                    # No same-day blocks - exits allowed any time based on signals
                    # Check traditional exit as well
                    should_exit_traditional = False
                    traditional_reason = None
                    if not should_exit_smart:
                        should_exit_traditional, traditional_reason = self.exit_manager.should_exit(position)
                    
                    # Determine final exit decision
                    should_exit = should_exit_smart or should_exit_traditional
                    if should_exit_smart:
                        exit_reason = f"Smart Exit: {smart_reason}"
                        self.logger.info(f"🎯 {position.symbol}: {exit_reason}")
                    elif should_exit_traditional:
                        exit_reason = f"Traditional: {traditional_reason}"
                    else:
                        exit_reason = None
                    
                    # Check exit conditions
                    if should_exit:
                        self.logger.info(
                            f"🔔 Exit Signal: {position.symbol} - {exit_reason}"
                        )
                        
                        # Execute exit
                        success = self.order_manager.execute_sell_order(position, current_price, exit_reason)
                        if success:
                            self.logger.info(
                                f"✅ Exit executed: {position.symbol} @ ${current_price:.2f}"
                            )
                            
                            # CRITICAL: Record exit to block same-day re-entry (Jan 14, 2026 fix)
                            if hasattr(self, 'signal_generator') and self.signal_generator:
                                self.signal_generator.record_exit(position.symbol)
                            
                            # Enhanced logging: Position exit
                            pnl = (current_price - position.entry_price) * position.position_size_shares
                            days_held = (dt.date.today() - position.entry_date).days
                            exit_tag = self._record_exit_reason(exit_reason)
                            self.enhanced_logger.log_position_exit(
                                symbol=position.symbol,
                                entry_price=position.entry_price,
                                exit_price=current_price,
                                shares=position.position_size_shares,
                                pnl=pnl,
                                reason=exit_reason,
                                exit_tag=exit_tag,
                                days_held=days_held
                            )
                        else:
                            # ONLY log STUCK if this is a D+1 position that SHOULD have exited
                            # Don't log for same-day positions or early exits
                            today = dt.date.today()
                            days_overdue = (today - position.exit_date).days
                            
                            # Only log as STUCK if truly overdue (D+1 date has passed)
                            if days_overdue > 0:
                                self.enhanced_logger.log_position_stuck(
                                    symbol=position.symbol,
                                    entry_date=str(position.entry_date),
                                    exit_date=str(position.exit_date),
                                    days_overdue=days_overdue,
                                    reason="Order execution failed - position overdue"
                                )
                            else:
                                # Exit blocked (min hold time, same-day, etc) - not an error
                                self.logger.debug(
                                    f"📝 {position.symbol}: Exit blocked - "
                                    f"Entry: {position.entry_date}, Exit due: {position.exit_date}, "
                                    f"Reason: {exit_reason}"
                                )
                
                except Exception as e:
                    import traceback
                    self.logger.error(f"❌ Exit monitoring failed for {getattr(position, 'symbol', position)}: {e}")
                    self.logger.debug(f"Exception traceback:\n{traceback.format_exc()}")
        
        except Exception as e:
            self.logger.error(f"❌ Exit monitoring failed: {e}")
    
    def _force_exit_losers_only(self, reason: str = "Friday losers cleanup"):
        """Force exit only losing positions (Jan 23, 2026 - protect winners over weekend)
        
        This replaces the old "force exit all" on Friday 3:30 PM.
        Winners stay protected by dynamic trailing stops.
        Only positions with P&L below threshold (-3% default) get force exited.
        """
        loser_threshold = getattr(self.config, 'friday_loser_threshold', -0.03)
        
        self.logger.info("=" * 80)
        self.logger.info(f"🔍 FRIDAY LOSER CHECK: Exiting positions below {loser_threshold*100:.1f}%")
        self.logger.info("=" * 80)
        
        try:
            active_positions = self.position_tracker.get_active_positions()
            exited_count = 0
            holding_count = 0
            
            for position in active_positions:
                try:
                    # Get current price
                    current_price = self._get_realtime_price(position.symbol)
                    if not current_price:
                        current_price = position.entry_price
                    
                    # Calculate P&L
                    profit_pct = (current_price - position.entry_price) / position.entry_price
                    
                    if profit_pct < loser_threshold:
                        # This is a loser - exit it
                        self.logger.info(f"🔴 Exiting loser: {position.symbol} ({profit_pct*100:+.1f}%)")
                        success = self.order_manager.execute_sell_order(position, current_price, reason)
                        if success:
                            self.logger.info(f"✅ {position.symbol} exited @ ${current_price:.2f}")
                            pnl = (current_price - position.entry_price) * position.position_size_shares
                            days_held = (dt.date.today() - position.entry_date).days
                            exit_tag = self._record_exit_reason(reason)
                            self.enhanced_logger.log_position_exit(
                                symbol=position.symbol,
                                entry_price=position.entry_price,
                                exit_price=current_price,
                                shares=position.position_size_shares,
                                pnl=pnl,
                                reason=reason,
                                exit_tag=exit_tag,
                                days_held=days_held
                            )
                            exited_count += 1
                    else:
                        # Winner or breakeven - keep holding with dynamic trailing protection
                        self.logger.info(f"🟢 Holding winner: {position.symbol} ({profit_pct*100:+.1f}%) - Dynamic trail active")
                        holding_count += 1
                        
                except Exception as e:
                    self.logger.error(f"❌ Check failed for {position.symbol}: {e}")
            
            self.logger.info(f"📊 Friday summary: {exited_count} losers exited, {holding_count} winners holding")
            
        except Exception as e:
            self.logger.error(f"❌ Friday loser check failed: {e}")
    
    def _force_exit_all(self, reason: str = "End of day"):
        """Force exit all positions (Friday 3:45 PM or D+1)"""
        self.logger.info("=" * 80)
        self.logger.info(f"🚨 FORCE EXIT: {reason}")
        self.logger.info("=" * 80)
        
        try:
            active_positions = self.position_tracker.get_active_positions()
            
            for position in active_positions:
                try:
                    self.logger.info(f"🔴 Force exiting: {position.symbol}")
                    # Get current price
                    current_price = self._get_realtime_price(position.symbol)
                    if not current_price:
                        current_price = position.entry_price
                    
                    success = self.order_manager.execute_sell_order(position, current_price, reason)
                    if success:
                        self.logger.info(f"✅ {position.symbol} exited @ ${current_price:.2f}")
                        pnl = (current_price - position.entry_price) * position.position_size_shares
                        days_held = (dt.date.today() - position.entry_date).days
                        exit_tag = self._record_exit_reason(reason)
                        self.enhanced_logger.log_position_exit(
                            symbol=position.symbol,
                            entry_price=position.entry_price,
                            exit_price=current_price,
                            shares=position.position_size_shares,
                            pnl=pnl,
                            reason=reason,
                            exit_tag=exit_tag,
                            days_held=days_held
                        )
                except Exception as e:
                    self.logger.error(f"❌ Force exit failed for {position.symbol}: {e}")
        
        except Exception as e:
            self.logger.error(f"❌ Force exit failed: {e}")
    
    def run_continuous_loop(self):
        """Run continuous trading loop with phase-based execution"""
        self.is_running = True
        self.logger.info("🔄 Starting continuous trading loop...")
        
        try:
            while self.is_running:
                # Periodic connection health check (every 30 minutes)
                now = dt.datetime.now(self.tz)
                if self.last_health_check is None or \
                   (now - self.last_health_check).total_seconds() > 1800:
                    try:
                        account_info = self.trading_engine.get_account_info()
                        if account_info:
                            self.logger.debug(f"✅ Connection healthy - Equity: ${account_info['portfolio_value']:,.2f}")
                        else:
                            self.logger.warning("⚠️ Connection health check returned no data")
                        self.last_health_check = now
                    except Exception as e:
                        self.logger.error(f"❌ Connection health check failed: {e}")
                        self.logger.warning("⚠️ Internet connection may be down - retries will continue")
                        self.last_health_check = now  # Still update to avoid spamming
                
                # Get current trading phase
                phase = self._get_trading_phase()
                active_positions = len(self.position_tracker.get_active_positions())
                
                # Show phase transition if changed
                if not hasattr(self, '_last_logged_phase') or self._last_logged_phase != phase:
                    print(f"\n{'='*80}")
                    print(f"📍 PHASE: {phase.upper()} | Time: {now.strftime('%I:%M:%S %p')} | Active Positions: {active_positions}")
                    print(f"{'='*80}\n")
                    import sys
                    sys.stdout.flush()
                    self._last_logged_phase = phase
                
                if phase == 'premarket':
                    # Run morning brief once per day at 9:00 AM
                    if self.last_morning_brief is None or \
                       self.last_morning_brief.date() < now.date():
                        if now.time() >= dt.time(9, 0):  # Only after 9:00 AM
                            print(f"🌅 Generating morning market brief...")
                            import sys
                            sys.stdout.flush()
                            self._run_morning_brief()
                            print(f"✅ Morning brief complete\n")
                            import sys
                            sys.stdout.flush()
                    
                    # Run premarket scan once per day
                    if self.last_gap_scan is None or \
                       self.last_gap_scan.date() < now.date():
                        print(f"🔍 Running premarket gap scan...")
                        import sys
                        sys.stdout.flush()
                        self._run_premarket_scan()
                        print(f"✅ Premarket scan complete\n")
                        import sys
                        sys.stdout.flush()
                    self._countdown_sleep(60, "⏰ Premarket - Next check in")
                
                elif phase == 'entry_window':
                    # Run entry scan
                    print(f"🔍 Running entry scan ({active_positions}/{self.config.max_positions_per_day} positions)...")
                    import sys
                    sys.stdout.flush()
                    start_time = dt.datetime.now(self.tz)
                    self._run_entry_scan()
                    duration = (dt.datetime.now(self.tz) - start_time).total_seconds()
                    print(f"✅ Entry scan complete ({duration:.1f}s)\n")
                    import sys
                    sys.stdout.flush()
                    self._countdown_sleep(300, "⏰ Entry Window - Next scan in")  # Scan every 5 minutes
                
                elif phase == 'midday_refresh':
                    # Run mid-day refresh if no entries made
                    print(f"🔍 Running midday refresh ({active_positions}/{self.config.max_positions_per_day} positions)...")
                    import sys
                    sys.stdout.flush()
                    self._run_midday_refresh()
                    print(f"✅ Midday refresh complete")
                    import sys
                    sys.stdout.flush()
                    # Also monitor exits during midday windows
                    print(f"👁️  Monitoring exits...")
                    import sys
                    sys.stdout.flush()
                    self._monitor_exits()
                    print(f"✅ Exit monitoring complete\n")
                    import sys
                    sys.stdout.flush()
                    self._countdown_sleep(300, "⏰ Midday Refresh - Next check in")
                
                elif phase == 'continuous_entry':
                    # Check if we can add more positions
                    if active_positions < self.config.max_positions_per_day:
                        # Scan for entries every 15 minutes during continuous phase
                        if self.last_entry_scan is None or \
                           (now - self.last_entry_scan).total_seconds() >= 900:
                            print(f"🔍 Continuous entry scan ({active_positions}/{self.config.max_positions_per_day} positions)...")
                            import sys
                            sys.stdout.flush()
                            self._run_entry_scan()
                            print(f"✅ Entry scan complete\n")
                            import sys
                            sys.stdout.flush()
                    # Also monitor exits
                    print(f"👁️  Monitoring exits ({active_positions} positions)...")
                    import sys
                    sys.stdout.flush()
                    self._monitor_exits()
                    print(f"✅ Exit monitoring complete\n")
                    import sys
                    sys.stdout.flush()
                    self._countdown_sleep(60, "⏰ Continuous Trading - Next check in")
                
                elif phase == 'late_entry':
                    # Late entry window: 1:00 PM - 2:30 PM
                    # Higher confidence bar, reduced position size
                    if active_positions < self.config.max_positions_per_day:
                        scan_interval = getattr(self.config, 'late_entry_scan_interval_minutes', 15) * 60
                        if self.last_entry_scan is None or \
                           (now - self.last_entry_scan).total_seconds() >= scan_interval:
                            conf_mult = getattr(self.config, 'late_entry_confidence_multiplier', 1.2)
                            size_pct = getattr(self.config, 'late_entry_position_size_pct', 0.75)
                            print(f"🌅 LATE ENTRY SCAN ({active_positions}/{self.config.max_positions_per_day} positions)")
                            print(f"   Confidence multiplier: {conf_mult:.1f}x | Position size: {size_pct:.0%}")
                            import sys
                            sys.stdout.flush()
                            self._run_late_entry_scan()
                            print(f"✅ Late entry scan complete\n")
                            import sys
                            sys.stdout.flush()
                    # Also monitor exits during late entry window
                    print(f"👁️  Monitoring exits ({active_positions} positions)...")
                    import sys
                    sys.stdout.flush()
                    self._monitor_exits()
                    print(f"✅ Exit monitoring complete\n")
                    import sys
                    sys.stdout.flush()
                    self._countdown_sleep(60, "⏰ Late Entry Window - Next check in")
                
                elif phase == 'monitoring':
                    # Monitor exits continuously (after 2 PM, no more entries)
                    print(f"👁️  Monitoring exits ({active_positions} positions)...")
                    import sys
                    sys.stdout.flush()
                    self._monitor_exits()
                    print(f"✅ Exit monitoring complete\n")
                    import sys
                    sys.stdout.flush()
                    self._countdown_sleep(60, "⏰ Monitoring Exits - Next check in")
                
                elif phase == 'force_exit':
                    # Force exit ALL positions (only if friday_force_exit_enabled=True)
                    if now.weekday() == 4:  # Friday
                        print(f"⚠️  Force exit window - Friday 3:30 PM")
                        import sys
                        sys.stdout.flush()
                        self._force_exit_all("Friday 3:30 PM - Force exit enabled")
                        print(f"✅ Force exit complete\n")
                        import sys
                        sys.stdout.flush()
                    else:
                        # Check for D+1 positions
                        # TODO: Implement D+1 check logic
                        pass
                    self._countdown_sleep(300, "⏰ Force Exit Window - Next check in")
                
                elif phase == 'force_exit_losers':
                    # Smart Friday exit: only exit losers, let winners ride with trailing stops
                    print(f"🔍 Friday smart exit - Checking positions...")
                    import sys
                    sys.stdout.flush()
                    self._force_exit_losers_only("Friday smart exit - losers only")
                    print(f"✅ Friday smart exit complete\n")
                    import sys
                    sys.stdout.flush()
                    # Also run regular exit monitoring for dynamic trailing stops
                    self._monitor_exits()
                    self._countdown_sleep(300, "⏰ Friday Smart Exit - Next check in")
                
                elif phase == 'postmarket':
                    # Generate daily summary once per day at 4:30 PM
                    if self.last_daily_summary is None or \
                       self.last_daily_summary.date() < now.date():
                        if now.time() >= dt.time(16, 30):  # After 4:30 PM
                            print(f"📊 Generating daily summary...")
                            import sys
                            sys.stdout.flush()
                            self._run_daily_summary()
                            print(f"✅ Daily summary complete\n")
                            import sys
                            sys.stdout.flush()
                    
                    # Run overnight gap predictor once per day at 4:45 PM
                    if not hasattr(self, 'last_gap_prediction') or \
                       self.last_gap_prediction is None or \
                       self.last_gap_prediction.date() < now.date():
                        if now.time() >= dt.time(16, 45):  # After 4:45 PM
                            print(f"🌙 Running overnight gap predictor...")
                            import sys
                            sys.stdout.flush()
                            self._run_gap_predictions()
                            print(f"✅ Gap predictions complete\n")
                            import sys
                            sys.stdout.flush()
                            self.last_gap_prediction = now
                    
                    # Refresh watchlist once per day
                    if self.last_watchlist_refresh is None or \
                       self.last_watchlist_refresh.date() < now.date():
                        print(f"🔄 Refreshing watchlist...")
                        import sys
                        sys.stdout.flush()
                        self._refresh_watchlist()
                        print(f"✅ Watchlist refresh complete\n")
                        import sys
                        sys.stdout.flush()
                    
                    # Check if quarterly universe review is due
                    should_check, reason = self.health_checker.should_run_check()
                    if should_check:
                        print(f"\n{'=' * 80}")
                        print(f"🏥 QUARTERLY UNIVERSE REVIEW DUE")
                        print(f"{'=' * 80}")
                        print(f"📅 {reason}")
                        print(f"")
                        print(f"Would you like to run the universe health check now?")
                        print(f"This will validate all {280} stocks for:")
                        print(f"  • Delistings")
                        print(f"  • Volume drops below 100k shares/day")
                        print(f"  • Price outside $5-$50 range")
                        print(f"")
                        response = input("Run health check? (y/n): ").strip().lower()
                        
                        if response == 'y':
                            print(f"🔄 Running health check...")
                            sys.stdout.flush()
                            results = self.health_checker.run_health_check()
                            self.health_checker.mark_check_complete()
                            
                            # If issues found, ask about detailed report
                            if results['issues_found'] > 0:
                                print(f"\n⚠️  Found {results['issues_found']} issues")
                                print(f"Check logs for detailed report")
                        else:
                            print(f"⏭️  Skipping health check (will prompt again next quarter)")
                        
                        print(f"{'=' * 80}\n")
                        sys.stdout.flush()
                    
                    self._countdown_sleep(300, "⏰ Postmarket - Next check in")
                
                else:  # closed
                    print(f"💤 Market closed - waiting for next session")
                    import sys
                    sys.stdout.flush()
                    self._countdown_sleep(600, "⏰ Market Closed - Next check in")
        
        except KeyboardInterrupt:
            self.logger.info("\n⚠️ Received shutdown signal")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"❌ Critical error in main loop: {e}")
            self.shutdown()
    
    def _countdown_sleep(self, seconds: int, message: str):
        """
        Sleep with countdown status updates - Enhanced visibility
        
        Args:
            seconds: Total seconds to sleep
            message: Status message to display
        """
        import sys
        
        # Get current time and calculate next action time
        now = dt.datetime.now(self.tz)
        next_action = now + dt.timedelta(seconds=seconds)
        
        if seconds <= 60:
            # For short sleeps (1 minute), just display once with timestamp
            mins = seconds / 60
            print(f"\n{message} {mins:.1f} minutes (until {next_action.strftime('%I:%M:%S %p')})")
            sys.stdout.flush()
            time.sleep(seconds)
        else:
            # For longer sleeps, show countdown every 30 seconds
            remaining = seconds
            print(f"\n{message} {remaining/60:.1f} minutes (until {next_action.strftime('%I:%M:%S %p')})")
            sys.stdout.flush()
            
            while remaining > 0:
                # Sleep in 30-second chunks for better feedback
                sleep_time = min(30, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time
                
                # Show update every 30 seconds
                if remaining > 0:
                    mins_left = remaining / 60
                    if mins_left >= 1:
                        print(f"   ... {mins_left:.1f} minutes remaining (until {next_action.strftime('%I:%M:%S %p')})")
                    else:
                        print(f"   ... {remaining} seconds remaining")
                    sys.stdout.flush()
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("=" * 80)
        self.logger.info("🛑 SHUTTING DOWN bot_v2")
        self.logger.info("=" * 80)
        
        self.is_running = False
        
        # DISABLED: Force exit all positions (safety)
        # Emergency exits disabled per user request (Dec 29, 2025)
        # Positions will remain open during bot restarts/updates
        # self._force_exit_all("Emergency shutdown")
        
        self.logger.info("✅ Shutdown complete (positions remain open)")


def main():
    """Main entry point"""
    print("=" * 80)
    # Initialize config first so startup output reflects the actual active settings.
    config = ShortCycleConfig()
    from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG

    strategy_labels = []
    if config.enable_gap_and_go:
        strategy_labels.append("Gap & Go")
    if config.enable_fade_short:
        strategy_labels.append("Fade/Short")
    if config.enable_momentum:
        strategy_labels.append("Momentum")

    active_strategies = ", ".join(strategy_labels) if strategy_labels else "None"

    print(f"🚀 bot_v2 Launcher - Active Strategies: {active_strategies}")
    print("=" * 80)
    print("")
    print("Configuration:")
    print(f"  - Universe Limit: {config.max_universe_size} symbols")
    print(f"  - Max Positions: {config.max_positions_per_day} concurrent")
    print(f"  - Max Daily Entries: {config.max_daily_entries}")
    print(f"  - Confidence: {config.confidence_threshold:.0%} threshold")
    print(
        f"  - PreFilter: ${SIMPLE_PREFILTER_CONFIG['min_price']:.0f}-${SIMPLE_PREFILTER_CONFIG['max_price']:.0f}, "
        f"vol {SIMPLE_PREFILTER_CONFIG['min_volume']:,}-{SIMPLE_PREFILTER_CONFIG['max_volume']:,}, "
        f"ATR {SIMPLE_PREFILTER_CONFIG['min_atr_pct']:.1%}-{SIMPLE_PREFILTER_CONFIG['max_atr_pct']:.1%}"
    )
    print(f"  - Late Entry Enabled: {config.enable_late_entry}")
    print(f"  - Exit Time: {config.exit_time}")
    
    # Run bot with config
    print("")
    print("=" * 80)
    print("")
    
    # Initialize launcher with the config
    launcher = BotV2Launcher(config=config, paper_trading=True)
    
    # Run continuous loop
    launcher.run_continuous_loop()


if __name__ == "__main__":
    main()
