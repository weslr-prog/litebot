"""
AI Position Tracker - Active position management and broker synchronization
Extracted from ShortCycleTrader for modular architecture
"""
import logging
import datetime as dt
import pytz
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

from ..utils.datetime_utils import get_next_trading_day, is_trading_day


class AIPositionTracker:
    """
    Manages position tracking, persistence, and synchronization with broker.
    
    Responsibilities:
    - Load/save positions from disk
    - Sync positions with live broker data (Alpaca)
    - Create position trackers for orphaned broker positions
    - Handle position file I/O with proper serialization
    """
    
    def __init__(self, config, execution_engine=None, logger: Optional[logging.Logger] = None):
        """
        Initialize position tracker
        
        Args:
            config: ShortCycleConfig with trading parameters
            execution_engine: Optional broker API for live position sync
            logger: Optional logger instance
        """
        self.config = config
        self.execution_engine = execution_engine
        self.logger = logger or logging.getLogger(__name__)
        self.positions: List[Any] = []  # Will hold ShortCyclePosition objects
        self.positions_file = "positions.json"
        self._needs_broker_sync = False  # Flag for corruption recovery
    
    def load_positions(self) -> List[Any]:
        """
        Load positions from previous session.
        
        Returns:
            List of ShortCyclePosition objects
        """
        try:
            from ..models.positions import ShortCyclePosition, PositionStatus
            from ..models.signals import AISignal
            
            if not Path(self.positions_file).exists():
                self.logger.info("📋 No previous positions found - starting fresh")
                self.positions = []
                return self.positions
            
            with open(self.positions_file, 'r') as f:
                position_data = json.load(f)
            
            self.positions = []
            for data in position_data:
                # Reconstruct dates
                entry_date = dt.datetime.fromisoformat(data['entry_date']).date()
                exit_date = None
                if data.get('exit_date'):
                    exit_date = dt.datetime.fromisoformat(data['exit_date']).date()
                else:
                    # For active positions without exit_date, set D+3 (swing strategy)
                    if data.get('status') == 'entered':
                        # Add ~5 calendar days (~3 trading days) from entry
                        exit_date = entry_date + dt.timedelta(days=5)

                # Reconstruct AI signal (fallbacks for older schema)
                ai = data.get('ai_signal', {}) or {}
                ai_ts = None
                if ai.get('timestamp'):
                    try:
                        ai_ts = dt.datetime.fromisoformat(ai['timestamp'])
                    except Exception:
                        ai_ts = None

                ai_signal = AISignal(
                    symbol=data['symbol'],
                    action=ai.get('action', 'BUY'),
                    confidence=ai.get('confidence', data.get('confidence', 0.5)),
                    time_horizon_days=ai.get('time_horizon_days', data.get('time_horizon_days', 1.5)),
                    entry_price=data.get('entry_price'),
                    target_price=ai.get('target_price', data.get('target_price')),
                    signal_timestamp=ai_ts,
                    features_used=ai.get('features_used', {})
                )
                
                # Parse timestamp fields for accurate D+1 tracking
                entry_timestamp = None
                if data.get('entry_timestamp'):
                    try:
                        entry_timestamp = dt.datetime.fromisoformat(data['entry_timestamp'])
                    except Exception:
                        pass
                
                filled_at = None
                if data.get('filled_at'):
                    try:
                        filled_at = dt.datetime.fromisoformat(data['filled_at'])
                    except Exception:
                        pass
                
                # Fix: If entry_timestamp is None but filled_at exists, use filled_at
                if entry_timestamp is None and filled_at is not None:
                    entry_timestamp = filled_at

                # Reconstruct position object
                position = ShortCyclePosition(
                    symbol=data['symbol'],
                    entry_date=entry_date,
                    exit_date=exit_date,
                    entry_price=data['entry_price'],
                    position_size_shares=data.get('position_size_shares', 0),
                    position_size_dollars=data['position_size_dollars'],
                    stop_price=data.get('stop_price', 0.0),
                    target_price=data.get('target_price'),
                    status=PositionStatus(data['status']),
                    ai_signal=ai_signal,
                    max_risk_dollars=data.get('max_risk_dollars', 0.0),
                    entry_timestamp=entry_timestamp,
                    filled_at=filled_at,
                    order_id=data.get('order_id')
                )
                
                # Restore exit data
                if data.get('exit_price'):
                    position.exit_price = data['exit_price']
                if data.get('exit_reason'):
                    position.exit_reason = data['exit_reason']
                if data.get('realized_pnl') is not None:
                    position.realized_pnl = data['realized_pnl']
                
                # Restore exit_timestamp for same-day activity detection
                if data.get('exit_timestamp'):
                    try:
                        position.exit_timestamp = dt.datetime.fromisoformat(data['exit_timestamp'])
                    except Exception:
                        position.exit_timestamp = None
                
                self.positions.append(position)
            
            self.logger.info(f"📋 Loaded {len(self.positions)} positions from previous session")
            return self.positions
            
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            self.positions = []
            return self.positions
    
    def save_positions(self):
        """Save current positions to file (backup - Alpaca is source of truth)"""
        try:
            if not self.positions:
                return
            
            from ..models.positions import PositionStatus, ShortCyclePosition
            
            # Pre-save validation: Filter out corrupted entries
            valid_positions = []
            corrupted_count = 0
            for p in self.positions:
                if isinstance(p, ShortCyclePosition):
                    valid_positions.append(p)
                else:
                    corrupted_count += 1
                    self.logger.error(
                        f"❌ CORRUPTION DETECTED: Removing invalid position "
                        f"(type={type(p).__name__}): {str(p)[:100]}"
                    )
            
            if corrupted_count > 0:
                self.logger.warning(f"🧹 Removed {corrupted_count} corrupted position entries before save")
                self.positions = valid_positions  # Clean up in-memory list
            
            # Filter out old exited positions (keep only last 7 days for analysis)
            cutoff_date = dt.date.today() - dt.timedelta(days=7)
            positions_to_save = []
            removed_count = 0
            
            for position in self.positions:
                # Keep all ENTERED positions
                if position.status == PositionStatus.ENTERED:
                    positions_to_save.append(position)
                # Keep recent EXITED positions (last 7 days)
                elif position.status == PositionStatus.EXITED:
                    if position.entry_date >= cutoff_date:
                        positions_to_save.append(position)
                    else:
                        removed_count += 1
                # Keep other statuses (if any)
                else:
                    positions_to_save.append(position)
            
            if removed_count > 0:
                self.logger.info(f"🧹 Cleaned {removed_count} old exited positions (older than {cutoff_date})")
                self.positions = positions_to_save  # Update in-memory list
            
            position_data = []
            for position in positions_to_save:
                # Validate shares from broker if needed
                shares = position.position_size_shares
                
                # Only sync for ACTIVE positions
                if (shares is None or shares == 0) and position.status == PositionStatus.ENTERED:
                    if self.execution_engine:
                        try:
                            live_positions = self.get_live_positions()
                            live_data = live_positions.get(position.symbol.upper())
                            if live_data:
                                shares = int(abs(live_data.get('quantity', 0)))
                                position.position_size_shares = shares
                                self.logger.info(f"✅ {position.symbol}: Synced {shares} shares from Alpaca")
                            else:
                                self.logger.warning(f"⚠️ {position.symbol}: Active position but no shares in Alpaca!")
                        except Exception as e:
                            self.logger.error(f"❌ Failed to sync {position.symbol}: {e}")
                elif (shares is None or shares == 0) and position.status != PositionStatus.ENTERED:
                    shares = 0
                
                data = {
                    'symbol': position.symbol,
                    'entry_date': position.entry_date.isoformat(),
                    'exit_date': position.exit_date.isoformat(),
                    'entry_price': position.entry_price,
                    'position_size_shares': shares,
                    'position_size_dollars': position.position_size_dollars,
                    'stop_price': position.stop_price,
                    'target_price': position.target_price,
                    'status': position.status.value if hasattr(position.status, 'value') else position.status,
                    'max_risk_dollars': position.max_risk_dollars,
                    'entry_timestamp': position.entry_timestamp.isoformat() if position.entry_timestamp else None,
                    'filled_at': position.filled_at.isoformat() if position.filled_at else None,
                    'exit_timestamp': position.exit_timestamp.isoformat() if hasattr(position, 'exit_timestamp') and position.exit_timestamp else None,
                    'order_id': str(position.order_id) if position.order_id else None,
                    'ai_signal': {
                        'action': position.ai_signal.action,
                        'confidence': position.ai_signal.confidence,
                        'time_horizon_days': position.ai_signal.time_horizon_days,
                        'entry_price': position.ai_signal.entry_price,
                        'target_price': position.ai_signal.target_price,
                        'features_used': position.ai_signal.features_used,
                        'timestamp': position.ai_signal.signal_timestamp.isoformat() if position.ai_signal.signal_timestamp else None
                    },
                    'exit_price': position.exit_price,
                    'exit_reason': position.exit_reason,
                    'realized_pnl': position.realized_pnl
                }
                position_data.append(data)
            
            with open(self.positions_file, 'w') as f:
                json.dump(position_data, f, indent=2, default=str)
                
            self.logger.info(f"💾 Saved {len(self.positions)} positions to {self.positions_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")
    
    def get_live_positions(self) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Fetch normalized live positions from broker.
        
        Returns:
            Dictionary keyed by symbol with position data
        """
        try:
            if not self.execution_engine:
                return {}
            
            raw_positions = self.execution_engine.get_positions()
            if raw_positions is None:
                self.logger.warning("⚠️ Broker returned no position payload; skipping sync this cycle")
                return None
            normalized: Dict[str, Dict[str, float]] = {}
            
            for symbol, pos in raw_positions.items():
                try:
                    qty = float(pos.get('quantity', 0) or 0)
                except Exception:
                    qty = 0.0
                    
                side = (pos.get('side') or '').lower()
                qty = -abs(qty) if side == 'short' else abs(qty)
                
                normalized[symbol.upper()] = {
                    'quantity': qty,
                    'avg_cost': float(pos.get('avg_cost', 0) or 0),
                    'market_value': float(pos.get('market_value', 0) or 0),
                    'unrealized_pnl': float(pos.get('unrealized_pnl', 0) or 0),
                    'side': pos.get('side'),
                }
            
            return normalized
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch live positions: {e}")
            return None
    
    def sync_positions_with_broker(self, live_positions: Optional[Dict] = None) -> bool:
        """
        Align internal position tracker with broker to avoid phantom exits.
        
        Args:
            live_positions: Optional pre-fetched live positions (if None, will fetch)
            
        Returns:
            True if state changed, False otherwise
        """
        # Reset sync flag
        self._needs_broker_sync = False
        
        if live_positions is None:
            live_positions = self.get_live_positions()
            if live_positions is None:
                self.logger.warning("⚠️ Skipping broker sync due unavailable live positions data")
                return False
        
        from ..models.positions import PositionStatus
        from ..models.signals import AISignal
        
        state_changed = False
        live_symbols = {
            symbol.upper(): data for symbol, data in live_positions.items()
            if abs(data.get('quantity', 0)) > 1e-6
        }

        tracked_active_symbols = set()
        duplicate_positions = []  # Track duplicates to clean up

        # Check existing positions - track duplicates
        for position in self.positions:
            symbol_key = position.symbol.upper()
            live_data = live_symbols.get(symbol_key)

            if position.status == PositionStatus.ENTERED:
                if not live_data:
                    self.logger.info(
                        f"🔕 {position.symbol}: No live holdings; marking as exited (PORTFOLIO_MISMATCH)"
                    )
                    position.status = PositionStatus.EXITED
                    position.exit_reason = "PORTFOLIO_MISMATCH"
                    position.exit_timestamp = dt.datetime.now(pytz.UTC)
                    state_changed = True
                    continue

                # FIX: Check if this symbol is already tracked (duplicate detection)
                if symbol_key in tracked_active_symbols:
                    self.logger.warning(
                        f"⚠️ DUPLICATE DETECTED: {position.symbol} already has an active tracker - marking as replaced"
                    )
                    duplicate_positions.append(position)
                    continue
                    
                tracked_active_symbols.add(symbol_key)

                live_qty = int(round(abs(live_data.get('quantity', 0))))
                if live_qty > 0 and live_qty != position.position_size_shares:
                    self.logger.info(
                        f"🔄 {position.symbol}: Aligning shares {position.position_size_shares} → {live_qty}"
                    )
                    position.position_size_shares = live_qty
                    avg_cost = live_data.get('avg_cost') or position.entry_price
                    if avg_cost:
                        position.entry_price = float(avg_cost)
                    position.position_size_dollars = live_qty * position.entry_price
                    state_changed = True

        # Create trackers for orphaned broker positions
        for symbol_key, live_data in live_symbols.items():
            if symbol_key not in tracked_active_symbols:
                self.logger.info(
                    f"📊 Alpaca position detected: {symbol_key} - creating tracker"
                )
                
                try:
                    qty = int(round(abs(live_data.get('quantity', 0))))
                    avg_cost = float(live_data.get('avg_cost', 0))
                    
                    if qty > 0 and avg_cost > 0:
                        # Try to get fill time from order history
                        entry_timestamp = None
                        entry_date = dt.date.today()
                        
                        try:
                            if self.execution_engine:
                                orders = self.execution_engine.get_order_history(days_back=5, status='closed')
                                
                                for order in orders:
                                    if (order.get('symbol') == symbol_key and 
                                        order.get('side') == 'buy' and
                                        order.get('filled_at')):
                                        filled_at_str = order.get('filled_at')
                                        entry_timestamp = dt.datetime.fromisoformat(filled_at_str.replace('Z', '+00:00'))
                                        entry_date = entry_timestamp.date()
                                        self.logger.info(f"✅ {symbol_key}: Found entry from {entry_date}")
                                        break
                        except Exception as e:
                            self.logger.warning(f"⚠️ No order history for {symbol_key}: {e}")
                        
                        if not entry_timestamp:
                            entry_timestamp = dt.datetime.now(pytz.UTC)
                            entry_date = dt.date.today()
                        
                        exit_date = entry_date + dt.timedelta(days=5)  # D+3 swing strategy
                        
                        # Create minimal AI signal
                        ai_signal = AISignal(
                            symbol=symbol_key,
                            action="BUY",
                            confidence=0.5,
                            time_horizon_days=3.0,
                            entry_price=avg_cost,
                            signal_timestamp=entry_timestamp
                        )
                        
                        # Create position tracker
                        from ..models.positions import ShortCyclePosition
                        
                        position = ShortCyclePosition(
                            symbol=symbol_key,
                            entry_date=entry_date,
                            exit_date=exit_date,
                            entry_price=avg_cost,
                            position_size_shares=qty,
                            position_size_dollars=qty * avg_cost,
                            stop_price=avg_cost * 0.975,
                            target_price=None,
                            status=PositionStatus.ENTERED,
                            ai_signal=ai_signal,
                            max_risk_dollars=qty * avg_cost * 0.025,
                            entry_timestamp=entry_timestamp,
                            filled_at=entry_timestamp
                        )
                        
                        self.positions.append(position)
                        state_changed = True
                        self.logger.info(f"✅ {symbol_key}: Tracker created (D+1 exit: {exit_date})")
                        
                except Exception as e:
                    self.logger.error(f"❌ Failed to create tracker for {symbol_key}: {e}")

        # Clean up duplicate positions detected earlier
        if duplicate_positions:
            for dup in duplicate_positions:
                dup.status = PositionStatus.EXITED
                dup.exit_reason = "Duplicate position replaced"
                dup.exit_timestamp = dt.datetime.now(pytz.UTC)
                dup.exit_date = dt.date.today()
                # Estimate exit price from entry if not available
                if not dup.exit_price:
                    dup.exit_price = dup.entry_price
                if dup.exit_price:
                    dup.realized_pnl = (dup.exit_price - dup.entry_price) * dup.position_size_shares
            self.logger.info(f"🧹 Cleaned up {len(duplicate_positions)} duplicate position trackers")
            state_changed = True

        return state_changed
    
    def add_position(self, position):
        """Add a new position to tracking with type validation and duplicate prevention"""
        from ..models.positions import ShortCyclePosition, PositionStatus
        
        # Critical: Validate position type before adding
        if not isinstance(position, ShortCyclePosition):
            self.logger.error(
                f"❌ CORRUPTION PREVENTED: Attempted to add non-Position object "
                f"(type={type(position).__name__}): {str(position)[:100]}"
            )
            return False
        
        # Validate critical fields
        if not position.symbol or not isinstance(position.symbol, str):
            self.logger.error(f"❌ CORRUPTION PREVENTED: Position has invalid symbol: {position.symbol}")
            return False
        
        # FIX: Check for existing active position with same symbol
        symbol_key = position.symbol.upper()
        existing_active = [p for p in self.positions 
                          if isinstance(p, ShortCyclePosition) 
                          and p.symbol.upper() == symbol_key 
                          and p.status == PositionStatus.ENTERED]
        
        if existing_active:
            # Mark existing as replaced before adding new one
            for old_pos in existing_active:
                old_pos.status = PositionStatus.EXITED
                old_pos.exit_reason = "Position replaced with new entry"
                old_pos.exit_timestamp = dt.datetime.now(pytz.UTC)
                old_pos.exit_date = dt.date.today()
                # Estimate exit price from entry if not available
                if not old_pos.exit_price:
                    old_pos.exit_price = old_pos.entry_price
                if old_pos.exit_price:
                    old_pos.realized_pnl = (old_pos.exit_price - old_pos.entry_price) * old_pos.position_size_shares
                self.logger.info(f"🔄 {symbol_key}: Replacing old position tracker with new one")
            
        self.positions.append(position)
        self.logger.debug(f"✅ Added position: {position.symbol}")
        return True
        
    def get_positions(self) -> List[Any]:
        """Get all tracked positions"""
        return self.positions
    
    def needs_broker_sync(self) -> bool:
        """Check if broker sync is needed (e.g., after corruption cleanup)"""
        return self._needs_broker_sync
    
    def get_active_positions(self) -> List[Any]:
        """Get only active (non-closed) positions with corruption detection"""
        from ..models.positions import PositionStatus, ShortCyclePosition
        
        # Filter out any invalid entries and only return actual position objects
        active = []
        corrupted_entries = []
        
        for i, p in enumerate(self.positions):
            # Detect corrupted entries (not a position object)
            if not isinstance(p, ShortCyclePosition):
                self.logger.error(
                    f"❌ CORRUPTION DETECTED at index {i}: Expected ShortCyclePosition, "
                    f"got {type(p).__name__}: {str(p)[:100]}"
                )
                corrupted_entries.append(i)
                continue
            
            # Only include ENTERED positions
            if p.status == PositionStatus.ENTERED:
                active.append(p)
        
        # Clean up corrupted entries from in-memory list
        if corrupted_entries:
            self.logger.warning(f"🧹 Cleaning {len(corrupted_entries)} corrupted entries from position list")
            self.positions = [p for i, p in enumerate(self.positions) if i not in corrupted_entries]
            # Request a sync to ensure broker is source of truth
            self._needs_broker_sync = True
        
        if len(self.positions) > 0 and len(active) == 0:
            self.logger.warning(f"⚠️ Have {len(self.positions)} total positions but 0 active (all non-ENTERED status)")
        
        return active
