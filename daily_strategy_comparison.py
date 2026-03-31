#!/usr/bin/env python3
"""
Daily Strategy Comparison Tool
Compare 5 trading strategies on today's market data

Strategies:
1. Mean Reversion (current bot strategy)
2. Momentum/Breakout
3. Gap & Go
4. Continuation
5. Fade (short overbought)

Usage:
    python3 daily_strategy_comparison.py

Safe: Read-only simulation, no trading, doesn't modify bot
"""

import sys
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Import bot components (read-only)
try:
    from bot_v2.config.trading_config import ShortCycleConfig
    from bot_v2.data.data_loader import DataLoader
except ImportError as e:
    logger.error(f"❌ Failed to import bot components: {e}")
    logger.error("Make sure you're running from the litebotx-usb-deployment directory")
    sys.exit(1)

# Default universe (same stocks your bot uses)
DEFAULT_UNIVERSE = [
    'AAL', 'AEO', 'AES', 'AI', 'APA', 'AR', 'BEAM', 'BEKE', 'CAG', 'CCL',
    'CDNA', 'CHWY', 'CLF', 'CMCSA', 'CPB', 'CPNG', 'CTRA', 'F', 'FTRE', 'HAL',
    'HIMS', 'HRL', 'JACK', 'JD', 'KDP', 'KHC', 'LC', 'LCID', 'LI', 'LYFT',
    'MGY', 'MRNA', 'MUR', 'NCLH', 'NOV', 'NRIX', 'NTLA', 'NU', 'NWSA', 'OSCR',
    'PATH', 'PENN', 'PINS', 'PL', 'PR', 'RIVN', 'S', 'SCVL', 'SDGR', 'SM',
    'SOFI', 'SOUN', 'STLA', 'T', 'TAL', 'TLRY', 'TU', 'TWST', 'VALE', 'VFC',
    'VIPS', 'VIRT', 'VOD', 'WBD', 'WEN', 'WOLF', 'XPEV'
]


class StrategyResult:
    """Result from a strategy simulation"""
    def __init__(self, name: str):
        self.name = name
        self.signals = []
        self.total_candidates = 0
    
    def add_signal(self, symbol: str, confidence: float, reason: str, rsi: float = None):
        self.signals.append({
            'symbol': symbol,
            'confidence': confidence,
            'reason': reason,
            'rsi': rsi
        })
    
    def get_summary(self):
        if not self.signals:
            return f"0 signals"
        
        avg_conf = sum(s['confidence'] for s in self.signals) / len(self.signals)
        top_signal = max(self.signals, key=lambda x: x['confidence'])
        return f"{len(self.signals)} signals (avg {avg_conf:.1%}), top: {top_signal['symbol']} ({top_signal['confidence']:.1%})"


class BaseStrategy:
    """Base class for all strategies"""
    def __init__(self, name: str):
        self.name = name
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        Analyze symbol and return signal if triggered
        Returns: {'symbol': str, 'confidence': float, 'reason': str, 'rsi': float} or None
        """
        raise NotImplementedError


class MeanReversionStrategy(BaseStrategy):
    """Strategy 1: Mean Reversion (current bot strategy)"""
    
    def __init__(self):
        super().__init__("Mean Reversion")
        self.rsi_threshold = 35
        self.sma_period = 20
        self.momentum_threshold = -0.05
        self.confidence_threshold = 0.25
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 30:
            return None
        
        # Calculate indicators
        close = data['close'].iloc[-1]
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # SMA
        sma_20 = data['close'].rolling(20).mean().iloc[-1]
        sma_diff_pct = (close - sma_20) / sma_20
        
        # Momentum
        momentum = (close - data['close'].iloc[-5]) / data['close'].iloc[-5]
        
        # Volume
        vol_avg = data['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = data['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
        
        # Check filters (same as bot)
        if current_rsi >= self.rsi_threshold:
            return None
        
        if sma_diff_pct < -0.06:
            return None
        
        if momentum < self.momentum_threshold:
            return None
        
        if vol_ratio < 1.5:
            return None
        
        # Calculate confidence (same formula as bot)
        rsi_confidence = (35 - current_rsi) / 20.0
        volume_bonus = min((vol_ratio - 1.5) / 5.0, 0.15)
        confidence = min(rsi_confidence + volume_bonus, 1.0)
        
        if confidence < self.confidence_threshold:
            return None
        
        return {
            'symbol': symbol,
            'confidence': confidence,
            'reason': f"Oversold RSI {current_rsi:.1f}",
            'rsi': current_rsi
        }


class MomentumBreakoutStrategy(BaseStrategy):
    """Strategy 2: Momentum/Breakout"""
    
    def __init__(self):
        super().__init__("Momentum/Breakout")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 50:
            return None
        
        close = data['close'].iloc[-1]
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # 20-day high
        high_20 = data['high'].rolling(20).max().iloc[-2]  # Previous 20-day high
        
        # 50-day SMA
        sma_50 = data['close'].rolling(50).mean().iloc[-1]
        
        # Volume
        vol_avg = data['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = data['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
        
        # Entry criteria
        if current_rsi < 60 or current_rsi > 80:
            return None
        
        if close <= high_20:  # Not breaking out
            return None
        
        if close <= sma_50:  # Not in uptrend
            return None
        
        if vol_ratio < 2.0:  # Need volume confirmation
            return None
        
        # Confidence: Higher RSI = stronger momentum
        confidence = (current_rsi - 60) / 20.0
        confidence = min(confidence, 1.0)
        
        return {
            'symbol': symbol,
            'confidence': confidence,
            'reason': f"Breakout RSI {current_rsi:.1f}",
            'rsi': current_rsi
        }


class GapAndGoStrategy(BaseStrategy):
    """Strategy 3: Gap & Go"""
    
    def __init__(self):
        super().__init__("Gap & Go")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 20:
            return None
        
        # Gap calculation
        today_open = data['open'].iloc[-1]
        yesterday_close = data['close'].iloc[-2]
        gap_pct = (today_open - yesterday_close) / yesterday_close
        
        # Current price
        close = data['close'].iloc[-1]
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Volume
        vol_avg = data['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = data['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
        
        # Entry criteria
        if gap_pct < 0.02 or gap_pct > 0.08:  # 2-8% gap
            return None
        
        if current_rsi > 75:  # Too overbought
            return None
        
        if close < yesterday_close:  # Gap filled (bearish)
            return None
        
        if vol_ratio < 1.5:  # Need volume
            return None
        
        # Confidence based on gap size
        confidence = min(gap_pct * 10.0, 1.0)  # 5% gap = 50% conf
        
        return {
            'symbol': symbol,
            'confidence': confidence,
            'reason': f"Gap {gap_pct*100:.1f}%, RSI {current_rsi:.1f}",
            'rsi': current_rsi
        }


class ContinuationStrategy(BaseStrategy):
    """Strategy 4: Continuation (trend following)"""
    
    def __init__(self):
        super().__init__("Continuation")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 200:
            return None
        
        close = data['close'].iloc[-1]
        
        # Moving averages
        sma_20 = data['close'].rolling(20).mean().iloc[-1]
        sma_50 = data['close'].rolling(50).mean().iloc[-1]
        sma_200 = data['close'].rolling(200).mean().iloc[-1]
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Volume
        vol_avg = data['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = data['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
        
        # Entry criteria: Established uptrend + pullback to SMA_20
        if not (sma_50 > sma_200):  # Uptrend confirmation
            return None
        
        if not (close > sma_50):  # Above 50-day
            return None
        
        if current_rsi < 40 or current_rsi > 60:  # Neutral RSI range
            return None
        
        # Check if near SMA_20 (pullback opportunity)
        sma_20_diff = abs((close - sma_20) / sma_20)
        if sma_20_diff > 0.03:  # More than 3% away from SMA_20
            return None
        
        if vol_ratio < 1.2:
            return None
        
        # Confidence: Closer to neutral RSI = better
        confidence = (60 - current_rsi) / 20.0 if current_rsi < 60 else (current_rsi - 40) / 20.0
        confidence = min(confidence, 1.0)
        
        return {
            'symbol': symbol,
            'confidence': confidence,
            'reason': f"Trend pullback, RSI {current_rsi:.1f}",
            'rsi': current_rsi
        }


class FadeStrategy(BaseStrategy):
    """Strategy 5: Fade (short overbought)"""
    
    def __init__(self):
        super().__init__("Fade/Short")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 30:
            return None
        
        close = data['close'].iloc[-1]
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # SMA
        sma_20 = data['close'].rolling(20).mean().iloc[-1]
        sma_diff_pct = (close - sma_20) / sma_20
        
        # Volume
        vol_avg = data['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = data['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
        
        # Entry criteria: Overbought + extended
        if current_rsi < 70:
            return None
        
        if sma_diff_pct < 0.10:  # Not extended enough above trend
            return None
        
        if vol_ratio < 1.5:  # Need volume spike
            return None
        
        # Confidence based on how overbought
        confidence = (current_rsi - 70) / 30.0
        confidence = min(confidence, 1.0)
        
        return {
            'symbol': symbol,
            'confidence': confidence,
            'reason': f"Overbought RSI {current_rsi:.1f}",
            'rsi': current_rsi
        }


def main():
    """Run strategy comparison"""
    print("=" * 80)
    print("📊 Daily Strategy Comparison Tool")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print()
    print("Analyzing today's market with 5 different strategies...")
    print("(Read-only simulation - no trading, no bot modifications)")
    print()
    
    # Initialize
    config = ShortCycleConfig()
    data_loader = DataLoader()
    
    # Use default universe
    print("🔍 Using default universe...")
    candidates = DEFAULT_UNIVERSE
    print(f"✅ {len(candidates)} candidates to analyze")
    print()
    print(f"📈 Fetching market data for {len(candidates)} stocks...")
    
    # Fetch data for all candidates
    market_data = {}
    failed = 0
    for symbol in candidates:
        try:
            data = data_loader.get_historical_data(symbol, days=200)
            if not data.empty:
                market_data[symbol] = data
        except:
            failed += 1
    
    print(f"✅ Loaded data for {len(market_data)} stocks ({failed} failed)")
    print()
    
    # Initialize strategies
    strategies = [
        MeanReversionStrategy(),
        MomentumBreakoutStrategy(),
        GapAndGoStrategy(),
        ContinuationStrategy(),
        FadeStrategy()
    ]
    
    # Run each strategy
    results = {}
    for strategy in strategies:
        result = StrategyResult(strategy.name)
        result.total_candidates = len(market_data)
        
        for symbol, data in market_data.items():
            signal = strategy.analyze(symbol, data)
            if signal:
                result.add_signal(
                    signal['symbol'],
                    signal['confidence'],
                    signal['reason'],
                    signal.get('rsi')
                )
        
        results[strategy.name] = result
    
    # Display results
    print("=" * 80)
    print("📊 STRATEGY COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    # Summary table
    print(f"{'Strategy':<25} {'Signals':<10} {'Avg Conf':<12} {'Top Pick'}")
    print("-" * 80)
    
    for strategy_name, result in results.items():
        if result.signals:
            avg_conf = sum(s['confidence'] for s in result.signals) / len(result.signals)
            top = max(result.signals, key=lambda x: x['confidence'])
            top_str = f"{top['symbol']} ({top['confidence']:.1%})"
        else:
            avg_conf = 0
            top_str = "None"
        
        # Highlight current bot strategy
        marker = "👉 " if strategy_name == "Mean Reversion" else "   "
        print(f"{marker}{strategy_name:<23} {len(result.signals):<10} {avg_conf:>6.1%}{'':6} {top_str}")
    
    print()
    print("-" * 80)
    
    # Find best strategy
    best_strategy = max(results.items(), key=lambda x: len(x[1].signals))
    print(f"🏆 Best Strategy Today: {best_strategy[0]} ({len(best_strategy[1].signals)} signals)")
    
    # Show detailed signals for each strategy
    print()
    print("=" * 80)
    print("📋 DETAILED SIGNALS BY STRATEGY")
    print("=" * 80)
    
    for strategy_name, result in results.items():
        print()
        marker = "👉 " if strategy_name == "CURRENT BOT" else ""
        print(f"{marker}{strategy_name}: {len(result.signals)} signals")
        
        if result.signals:
            # Sort by confidence
            sorted_signals = sorted(result.signals, key=lambda x: x['confidence'], reverse=True)
            for sig in sorted_signals[:10]:  # Show top 10
                rsi_str = f"RSI {sig['rsi']:.1f}" if sig['rsi'] else ""
                print(f"   • {sig['symbol']:<6} {sig['confidence']:>6.1%}  {sig['reason']:<30} {rsi_str}")
            
            if len(result.signals) > 10:
                print(f"   ... and {len(result.signals) - 10} more")
        else:
            print("   (No signals generated)")
    
    print()
    print("=" * 80)
    print("✅ Comparison complete!")
    print()
    print("💡 Next Steps:")
    print("   • If results look promising, consider Option B (30-day backtest)")
    print("   • Your bot continues running unchanged")
    print("   • Safe to run this anytime for daily market analysis")
    print()


if __name__ == "__main__":
    main()
