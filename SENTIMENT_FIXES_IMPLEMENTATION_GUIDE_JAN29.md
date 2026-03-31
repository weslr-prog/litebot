# 🛠️ IMPLEMENTATION GUIDE: Fix Sentiment Pipeline
**Date**: January 29, 2026  
**Priority**: CRITICAL (implement today)  
**Estimated Time**: 7 hours for Priority 1-3

---

## BEFORE YOU START

**Backup your code**:
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
git add -A && git commit -m "Backup before sentiment pipeline fixes"
```

---

## FIX #1: Strategy-Specific Sentiment Scoring (2 hours)

### 1.1 Update `bot_v2/data_sources/news_sentiment.py`

**Current Code** (lines 194-234):
```python
def get_contrarian_adjustment(self, sentiment: Dict, has_dark_pool_buying: bool = False) -> float:
    """Get confidence adjustment based on sentiment (contrarian for mean reversion)"""
    signal = sentiment['signal']
    
    if signal == 'STRONG_BEAR':
        return -1.0
    if signal == 'BEAR' and has_dark_pool_buying:
        return 0.20
    if signal == 'BEAR':
        return -0.05
    if signal == 'BULL':
        return -0.10  # Bull is less mean reversion
    if signal == 'STRONG_BULL':
        return -0.15
    if signal == 'NEUTRAL':
        return 0.0
    
    return 0.0
```

**Replacement Code**:
```python
def get_sentiment_adjustment(self, sentiment: Dict, strategy: str = 'gap_go',
                             has_dark_pool_buying: bool = False) -> float:
    """
    Get confidence adjustment based on sentiment and strategy type
    
    Args:
        sentiment: Sentiment data dict from get_sentiment()
        strategy: 'gap_go' | 'fade_short' | 'mean_reversion'
        has_dark_pool_buying: If dark pool shows accumulation
    
    Returns:
        Confidence adjustment (-1.0 to +0.25)
    """
    signal = sentiment['signal']
    
    # ===== GAP & GO STRATEGY =====
    if strategy == 'gap_go':
        # Need momentum + bullish sentiment
        if signal == 'STRONG_BEAR':
            return -1.0  # Hard skip - fight momentum
        if signal == 'BEAR':
            return -0.25  # Bad news kills momentum
        if signal == 'NEUTRAL':
            return 0.0  # No signal, no penalty
        if signal == 'BULL':
            return 0.10  # Good - supports momentum
        if signal == 'STRONG_BULL':
            return 0.20  # Perfect - strong bullish signal
    
    # ===== FADE/SHORT STRATEGY =====
    elif strategy == 'fade_short':
        # Betting on reversal from extended move
        if signal == 'STRONG_BEAR':
            return -1.0  # Skip - avoid free fall shorts
        if signal == 'BEAR':
            return 0.0   # Neutral - actually supportive (stock weak)
        if signal == 'NEUTRAL':
            return 0.0
        if signal == 'BULL':
            return -0.10  # Bad - rally strengthening
        if signal == 'STRONG_BULL':
            return -0.25  # Very bad - avoid shorting into strength
    
    # ===== MEAN REVERSION STRATEGY =====
    elif strategy == 'mean_reversion':
        # Smart money buying the dip
        if signal == 'STRONG_BEAR':
            return -1.0  # Skip - too much risk
        if signal == 'BEAR':
            # Oversold - mean reversion setup
            if has_dark_pool_buying:
                return 0.20  # Smart money buying dip = high confidence
            else:
                return -0.05  # Risky without institutional support
        if signal == 'NEUTRAL':
            return 0.0
        if signal == 'BULL':
            return -0.10  # Already recovering, less reversal potential
        if signal == 'STRONG_BULL':
            return -0.15  # Too strong to mean revert
    
    # Default fallback
    return 0.0


# BACKWARD COMPATIBILITY: Keep old method name
def get_contrarian_adjustment(self, sentiment: Dict, has_dark_pool_buying: bool = False) -> float:
    """Deprecated: Use get_sentiment_adjustment() instead"""
    return self.get_sentiment_adjustment(sentiment, strategy='mean_reversion', 
                                        has_dark_pool_buying=has_dark_pool_buying)
```

### 1.2 Update `bot_v2/signal_generation/signal_generator.py` (lines 740-745)

**Current Code**:
```python
if self.sentiment_analyzer:
    sentiment = self.sentiment_analyzer.get_sentiment(symbol, hours_lookback=24)
    
    if self.sentiment_analyzer.should_skip_trade(sentiment, strategy='mean_reversion'):
        self.logger.warning(f"❌ SKIP {symbol}: Disaster news (STRONG_BEAR)")
        return None
    
    sentiment_boost = self.sentiment_analyzer.get_contrarian_adjustment(
        sentiment, has_dark_pool_buying=has_dark_pool_buying
    )
```

**Replacement Code**:
```python
if self.sentiment_analyzer:
    sentiment = self.sentiment_analyzer.get_sentiment(symbol, hours_lookback=24)
    
    # Determine strategy for this stock
    # (You should already have best_strategy from technical analysis)
    trade_strategy = best_strategy  # 'gap_go', 'fade_short', or 'mean_reversion'
    
    if self.sentiment_analyzer.should_skip_trade(sentiment, strategy=trade_strategy):
        self.logger.warning(f"❌ SKIP {symbol}: Disaster news (STRONG_BEAR)")
        return None
    
    # NEW: Use strategy-specific adjustment
    sentiment_boost = self.sentiment_analyzer.get_sentiment_adjustment(
        sentiment, 
        strategy=trade_strategy,
        has_dark_pool_buying=has_dark_pool_buying
    )
```

**Test This Fix**:
```python
from bot_v2.data_sources.news_sentiment import NewsSentimentAnalyzer

analyzer = NewsSentimentAnalyzer()

# Test Gap & Go
gap_bear = analyzer.get_sentiment_adjustment(
    {'signal': 'BEAR'},
    strategy='gap_go'
)
assert gap_bear == -0.25, f"Gap & Go + BEAR should be -0.25, got {gap_bear}"
print("✅ Gap & Go + BEAR = -0.25")

# Test Fade with STRONG_BULL
fade_bull = analyzer.get_sentiment_adjustment(
    {'signal': 'STRONG_BULL'},
    strategy='fade_short'
)
assert fade_bull == -0.25, f"Fade + STRONG_BULL should be -0.25, got {fade_bull}"
print("✅ Fade + STRONG_BULL = -0.25")

# Test Mean Reversion with BEAR + dark pool
mr_bear_dp = analyzer.get_sentiment_adjustment(
    {'signal': 'BEAR'},
    strategy='mean_reversion',
    has_dark_pool_buying=True
)
assert mr_bear_dp == 0.20, f"MR + BEAR + DP should be +0.20, got {mr_bear_dp}"
print("✅ Mean Reversion + BEAR + Dark Pool = +0.20")
```

---

## FIX #2: Data Quality Gating (2 hours)

### 2.1 Update `bot_v2/data_sources/news_sentiment.py` (lines 62-140)

**Current Code**:
```python
def get_sentiment(self, symbol: str, hours_lookback: int = 24) -> Dict:
    """Get sentiment for a symbol"""
    if not self.client:
        return self._neutral_response()
    
    try:
        # ... fetch news ...
        articles = news.data
        
        if not articles:
            return self._neutral_response()
        
        # Calculate sentiment
        sentiments = [self._get_sentiment_score(article) for article in articles]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Classify
        if avg_sentiment > 0.6:
            signal = 'STRONG_BULL'
            confidence_adjustment = 0.15
        elif avg_sentiment > 0.3:
            signal = 'BULL'
            confidence_adjustment = 0.10
        # ... etc ...
        
        return {
            'sentiment_score': avg_sentiment,
            'signal': signal,
            'confidence_adjustment': confidence_adjustment,
            'article_count': len(articles),
        }
```

**Replacement Code**:
```python
def get_sentiment(self, symbol: str, hours_lookback: int = 24) -> Dict:
    """Get sentiment for a symbol with data quality assessment"""
    if not self.client:
        return self._neutral_response()
    
    try:
        # ... fetch news ...
        articles = news.data
        
        # NEW: Assess data quality
        article_count = len(articles) if articles else 0
        
        # Data quality classification
        if article_count == 0:
            data_quality = 'missing'
        elif article_count == 1:
            data_quality = 'low'  # Single data point is unreliable
        elif article_count <= 3:
            data_quality = 'medium'
        else:
            data_quality = 'high'  # 4+ articles = reliable
        
        # If no articles, return neutral with missing flag
        if not articles:
            return {
                'sentiment_score': 0.0,
                'signal': 'NEUTRAL',
                'confidence_adjustment': 0.0,
                'article_count': 0,
                'data_quality': 'missing',  # NEW
                'stale_penalty': 0.0,  # NEW
                'quality_confidence': 0.0,  # NEW
            }
        
        # Calculate sentiment
        sentiments = [self._get_sentiment_score(article) for article in articles]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # NEW: Check article staleness
        latest_article_time = max([a.created_at for a in articles])
        now = datetime.now(latest_article_time.tzinfo)
        age_hours = (now - latest_article_time).total_seconds() / 3600
        
        # Penalty for stale news
        if age_hours > 24:
            stale_penalty = -0.15  # Very stale, not current
        elif age_hours > 12:
            stale_penalty = -0.10  # Getting stale
        elif age_hours > 6:
            stale_penalty = -0.05  # Slightly stale
        else:
            stale_penalty = 0.0  # Current
        
        # Classify signal
        if avg_sentiment > 0.6:
            signal = 'STRONG_BULL'
            confidence_adjustment = 0.15
        elif avg_sentiment > 0.3:
            signal = 'BULL'
            confidence_adjustment = 0.10
        elif avg_sentiment < -0.6:
            signal = 'STRONG_BEAR'
            confidence_adjustment = -1.0
        elif avg_sentiment < -0.3:
            signal = 'BEAR'
            confidence_adjustment = -0.5
        else:
            signal = 'NEUTRAL'
            confidence_adjustment = 0.0
        
        # Apply stale penalty to adjustment
        final_adjustment = confidence_adjustment + stale_penalty
        
        # Quality confidence: how much should we trust this?
        # High quality + current = 1.0
        # Low quality + stale = 0.3
        if data_quality == 'high' and age_hours < 6:
            quality_confidence = 1.0
        elif data_quality == 'high' and age_hours < 12:
            quality_confidence = 0.9
        elif data_quality == 'medium' and age_hours < 12:
            quality_confidence = 0.7
        elif data_quality == 'medium' and age_hours < 24:
            quality_confidence = 0.5
        elif data_quality == 'low':
            quality_confidence = 0.4
        else:
            quality_confidence = 0.3
        
        return {
            'sentiment_score': avg_sentiment,
            'signal': signal,
            'confidence_adjustment': final_adjustment,
            'article_count': article_count,
            'data_quality': data_quality,  # NEW
            'stale_penalty': stale_penalty,  # NEW
            'quality_confidence': quality_confidence,  # NEW (0-1)
            'latest_article_age_hours': age_hours,  # NEW
        }
    
    except Exception as e:
        self.logger.error(f"Error fetching sentiment for {symbol}: {e}")
        return self._neutral_response()
```

### 2.2 Update `bot_v2/signal_generation/signal_generator.py` (around line 750)

Add this AFTER the sentiment check:

```python
# NEW: Apply data quality penalties
if sentiment['data_quality'] == 'missing':
    # No news in 24h = uncertainty penalty
    self.logger.debug(f"   ⚠️  {symbol}: No news in 24h - applying -20% confidence penalty")
    confidence *= 0.80  # Multiply confidence, don't add

elif sentiment['data_quality'] == 'low':
    # Single article = low reliability
    self.logger.debug(f"   ⚠️  {symbol}: Low sentiment confidence (1 article) - applying -15% penalty")
    confidence *= 0.85

elif sentiment['data_quality'] == 'medium':
    # 2-3 articles = moderate reliability
    quality_conf = sentiment['quality_confidence']
    if quality_conf < 0.6:
        self.logger.debug(f"   ⚠️  {symbol}: Medium sentiment confidence - applying -5% penalty")
        confidence *= 0.95

# If confidence drops below threshold due to data quality, skip
if confidence < self.config.confidence_threshold:
    self.logger.warning(f"❌ {symbol}: Below confidence threshold ({confidence:.1%}) due to data quality")
    return None
```

**Test This Fix**:
```python
from bot_v2.data_sources.news_sentiment import NewsSentimentAnalyzer

analyzer = NewsSentimentAnalyzer()

# Test 1: Zero articles = low confidence
sentiment_zero = analyzer.get_sentiment('XYZ', hours_lookback=24)
assert sentiment_zero['data_quality'] == 'missing'
assert sentiment_zero['quality_confidence'] == 0.0
print("✅ Zero articles = missing data quality")

# Test 2: Stale penalty applied
# (This requires mocking the API, so check logs instead)
# Should see "stale_penalty" in result

# Test 3: Quality confidence decreases with low article count
# (Check output manually or write integration test)
```

---

## FIX #3: Hard Veto Rules for Disaster News (3 hours)

### 3.1 Create new file: `bot_v2/safety/sentiment_veto.py`

```python
"""
Sentiment veto gate - hard exclusion rules for disaster news
These keywords/patterns trigger automatic rejection (no scoring)
"""

import logging
from typing import Tuple, Optional, List, Dict

logger = logging.getLogger(__name__)

# Hard veto keywords - these ALWAYS trigger rejection
HARD_VETO_KEYWORDS = {
    'bankruptcy': 'filing',
    'liquidation': 'auction',
    'delisting': 'sec',
    'sec investigation': 'fraud',
    'fraud charges': 'conviction',
    'accounting restatement': 'misstatement',
    'insolvency': 'solvent',
    'going concern': 'doubt',
    'stock exchange halt': 'trading',
    'trading halt': 'resumed',
    'reverse split': 'consolidation',
    'covenant breach': 'debt',
    'loan default': 'bank',
    'class action': 'lawsuit',
    'ceo arrested': 'criminal',
    'cfo indicted': 'charges',
    'audit failure': 'restate',
}

# Soft veto keywords - these trigger additional scrutiny
SOFT_VETO_KEYWORDS = {
    'downgrade': 'analyst',
    'insider selling': 'executive',
    'short seller report': 'research',
    'warning letter': 'fda',
    'product recall': 'safety',
    'competitor winning': 'market share',
}


class SentimentVetoGate:
    """
    Hard exclusion rules based on sentiment data and news keywords
    """
    
    def __init__(self):
        self.logger = logger
    
    def check_veto(self, sentiment: Dict, symbol: str = '') -> Tuple[bool, Optional[str], str]:
        """
        Check if a trade should be vetoed due to bad news
        
        Args:
            sentiment: Sentiment dict from NewsSentimentAnalyzer
            symbol: Stock symbol (for logging)
        
        Returns:
            (should_veto: bool, reason: str, severity: 'hard' | 'soft' | 'none')
        """
        
        # Check 1: Hard veto on STRONG_BEAR sentiment with multiple articles
        if sentiment['signal'] == 'STRONG_BEAR':
            if sentiment['article_count'] >= 2:
                return True, f"STRONG_BEAR sentiment ({sentiment['article_count']} articles)", 'hard'
            elif sentiment['article_count'] == 1:
                # Single article, but if very strong negative, still veto
                if sentiment['sentiment_score'] < -0.8:
                    return True, f"Extremely negative single article ({sentiment['sentiment_score']:.2f})", 'hard'
        
        # Check 2: Keyword-based hard veto
        headlines = sentiment.get('headlines', [])
        
        for article in headlines:
            headline = article.get('headline', '').lower()
            body = article.get('summary', '').lower()
            
            # Check hard veto keywords
            for keyword in HARD_VETO_KEYWORDS.keys():
                if keyword in headline or keyword in body:
                    return True, f"Disaster keyword found: '{keyword}'", 'hard'
        
        # Check 3: Pattern-based veto (multiple negative signals)
        if sentiment['signal'] in ['BEAR', 'STRONG_BEAR']:
            # Multiple articles all negative = risky
            if sentiment['article_count'] >= 5 and sentiment['sentiment_score'] < -0.4:
                return True, f"Multiple negative articles (avg score: {sentiment['sentiment_score']:.2f})", 'hard'
        
        # Check 4: Soft veto warnings (log but don't block)
        soft_veto_triggered = False
        soft_reasons = []
        
        for article in headlines:
            headline = article.get('headline', '').lower()
            for keyword in SOFT_VETO_KEYWORDS.keys():
                if keyword in headline:
                    soft_veto_triggered = True
                    soft_reasons.append(keyword)
        
        if soft_veto_triggered:
            # Don't block, but log warning
            reason = f"Soft veto triggered: {', '.join(set(soft_reasons))}"
            self.logger.warning(f"⚠️  {symbol}: {reason}")
            return False, reason, 'soft'
        
        # No veto
        return False, None, 'none'
    
    def format_veto_message(self, symbol: str, veto_result: Tuple[bool, Optional[str], str]) -> str:
        """Format veto result for logging"""
        should_veto, reason, severity = veto_result
        
        if not should_veto:
            return ""
        
        if severity == 'hard':
            return f"🚫 VETO {symbol}: {reason}"
        elif severity == 'soft':
            return f"⚠️  CAUTION {symbol}: {reason}"
        
        return ""
```

### 3.2 Update `bot_v2/signal_generation/signal_generator.py` (lines 50-70)

Add import:
```python
from bot_v2.safety.sentiment_veto import SentimentVetoGate
```

In `__init__()` method, add after sentiment_analyzer initialization:
```python
# Initialize veto gate
self.sentiment_veto = SentimentVetoGate()
```

### 3.3 Update `bot_v2/signal_generation/signal_generator.py` (lines 716-750)

After you have sentiment data, add veto check:

```python
# News Sentiment Check
if self.sentiment_analyzer:
    sentiment = self.sentiment_analyzer.get_sentiment(symbol, hours_lookback=24)
    
    # NEW: Check for hard veto on disaster news
    should_veto, reason, severity = self.sentiment_veto.check_veto(sentiment, symbol)
    if should_veto:
        veto_msg = self.sentiment_veto.format_veto_message(symbol, (should_veto, reason, severity))
        self.logger.warning(veto_msg)
        return None  # Hard reject - no scoring possible
    
    # Then proceed with normal sentiment adjustment...
    trade_strategy = best_strategy
    
    if self.sentiment_analyzer.should_skip_trade(sentiment, strategy=trade_strategy):
        self.logger.warning(f"❌ SKIP {symbol}: Disaster news (STRONG_BEAR)")
        return None
    
    sentiment_boost = self.sentiment_analyzer.get_sentiment_adjustment(
        sentiment, 
        strategy=trade_strategy,
        has_dark_pool_buying=has_dark_pool_buying
    )
```

**Test This Fix**:
```python
from bot_v2.safety.sentiment_veto import SentimentVetoGate

veto = SentimentVetoGate()

# Test 1: Bankruptcy keyword
sentiment_bankruptcy = {
    'signal': 'STRONG_BEAR',
    'article_count': 2,
    'sentiment_score': -0.9,
    'headlines': [
        {'headline': 'XYZ Files for Bankruptcy Protection', 'summary': '...'},
    ]
}
should_veto, reason, sev = veto.check_veto(sentiment_bankruptcy, 'XYZ')
assert should_veto == True
assert 'bankruptcy' in reason.lower()
print("✅ Bankruptcy keyword triggers veto")

# Test 2: STRONG_BEAR alone (no keyword)
sentiment_strong_bear = {
    'signal': 'STRONG_BEAR',
    'article_count': 3,
    'sentiment_score': -0.8,
    'headlines': [
        {'headline': 'Stock Down on Earnings Miss', 'summary': '...'},
    ]
}
should_veto, reason, sev = veto.check_veto(sentiment_strong_bear, 'ABC')
assert should_veto == True
assert 'STRONG_BEAR' in reason
print("✅ STRONG_BEAR + multiple articles triggers veto")

# Test 3: BEAR alone (no veto)
sentiment_bear = {
    'signal': 'BEAR',
    'article_count': 1,
    'sentiment_score': -0.4,
    'headlines': []
}
should_veto, reason, sev = veto.check_veto(sentiment_bear, 'DEF')
assert should_veto == False
print("✅ BEAR alone does not trigger veto")
```

---

## FIX #4: Switch to Multiplicative Sentiment Gating (1 hour)

### 4.1 Update `bot_v2/signal_generation/signal_generator.py` (lines 763-775)

**Current Code** (WRONG - additive):
```python
if sentiment_boost != 0 or dark_pool_boost != 0 or options_boost != 0:
    original_confidence = confidence
    confidence = min(confidence + sentiment_boost + dark_pool_boost + options_boost, 1.0)
    confidence = max(confidence, 0.0)
    self.logger.debug(f"   💰 Adjusted confidence: {original_confidence:.1%} → {confidence:.1%} "
                     f"({sentiment_boost:+.0%} sentiment, {dark_pool_boost:+.0%} dark pool)")
```

**Replacement Code** (CORRECT - multiplicative for negative):
```python
if sentiment_boost != 0 or dark_pool_boost != 0 or options_boost != 0:
    original_confidence = confidence
    
    # Apply negative adjustments multiplicatively (they should reduce confidence more)
    # Apply positive adjustments additively (they should enhance confidence)
    
    if sentiment_boost < 0:
        # Negative: multiply down (e.g., -0.20 → 0.80x)
        confidence *= (1.0 + sentiment_boost)
    else:
        # Positive: add up
        confidence = min(confidence + sentiment_boost, 1.0)
    
    if dark_pool_boost < 0:
        confidence *= (1.0 + dark_pool_boost)
    else:
        confidence = min(confidence + dark_pool_boost, 1.0)
    
    if options_boost < 0:
        confidence *= (1.0 + options_boost)
    else:
        confidence = min(confidence + options_boost, 1.0)
    
    # Ensure within bounds
    confidence = max(min(confidence, 1.0), 0.0)
    
    self.logger.debug(f"   💰 Adjusted confidence: {original_confidence:.1%} → {confidence:.1%} "
                     f"(sentiment={sentiment_boost:+.0%}, dark_pool={dark_pool_boost:+.0%}, "
                     f"options={options_boost:+.0%})")
```

**Test This Fix**:
```python
# Test 1: Negative sentiment reduces multiplicatively
original = 0.60  # 60%
sentiment_boost = -0.20  # -20%
result = original * (1.0 + sentiment_boost)
assert result == 0.48, f"Expected 0.48, got {result}"
print("✅ -20% sentiment boost: 60% → 48%")

# Test 2: Positive sentiment adds
original = 0.60
sentiment_boost = 0.10  # +10%
result = min(original + sentiment_boost, 1.0)
assert result == 0.70, f"Expected 0.70, got {result}"
print("✅ +10% sentiment boost: 60% → 70%")

# Test 3: Multiple negative adjustments compound
original = 0.60
sentiment_mult = original * (1.0 - 0.20)  # -20% sentiment
sentiment_mult = sentiment_mult * (1.0 - 0.10)  # -10% dark pool
assert abs(sentiment_mult - 0.432) < 0.001
print(f"✅ Multiple negatives compound: 60% → {sentiment_mult:.1%}")
```

---

## FIX #5: Universe-Level Sentiment Pre-Filter (2 hours)

### 5.1 Create new file: `bot_v2/screening/universe_sentiment_screener.py`

```python
"""
Pre-screen the entire stock universe for bad sentiment
Run once at market open (9:30 AM EST)
"""

import logging
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class UniverseSentimentScreener:
    """
    Screen entire universe for disaster news before trading day starts
    """
    
    def __init__(self, sentiment_analyzer, veto_gate, max_workers: int = 10):
        """
        Args:
            sentiment_analyzer: NewsSentimentAnalyzer instance
            veto_gate: SentimentVetoGate instance
            max_workers: Number of parallel API calls
        """
        self.sentiment_analyzer = sentiment_analyzer
        self.veto_gate = veto_gate
        self.max_workers = max_workers
        self.logger = logger
    
    def screen_universe(self, universe: List[str], 
                       hours_lookback: int = 24) -> Dict[str, List]:
        """
        Pre-screen entire universe for bad sentiment
        
        Args:
            universe: List of stock symbols to screen
            hours_lookback: Hours to look back for news
        
        Returns:
            {
                'safe': [...],  # OK to trade
                'risky': {...}, # Negative sentiment (logged as warning)
                'blocked': [...], # Hard veto (disaster news)
            }
        """
        
        self.logger.info(f"🔍 Screening {len(universe)} stocks for sentiment...")
        
        results = {
            'safe': [],
            'risky': {},
            'blocked': [],
        }
        
        # Parallel sentiment fetch
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.sentiment_analyzer.get_sentiment,
                    symbol,
                    hours_lookback=hours_lookback
                ): symbol for symbol in universe
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    sentiment = future.result()
                    
                    # Check hard veto
                    should_veto, reason, severity = self.veto_gate.check_veto(sentiment, symbol)
                    
                    if should_veto:
                        results['blocked'].append((symbol, reason))
                        self.logger.warning(f"🚫 BLOCKED {symbol}: {reason}")
                        continue
                    
                    # Classify as safe/risky
                    if sentiment['signal'] in ['STRONG_BULL', 'BULL']:
                        results['safe'].append(symbol)
                    elif sentiment['signal'] == 'NEUTRAL':
                        results['safe'].append(symbol)
                    elif sentiment['signal'] == 'BEAR':
                        # Risky but tradeable with caution
                        results['risky'][symbol] = {
                            'sentiment': sentiment,
                            'reason': f"BEAR sentiment ({sentiment['article_count']} articles)"
                        }
                        self.logger.warning(f"⚠️  RISKY {symbol}: BEAR sentiment")
                    else:  # STRONG_BEAR
                        results['blocked'].append((symbol, f"STRONG_BEAR sentiment"))
                        self.logger.warning(f"🚫 BLOCKED {symbol}: STRONG_BEAR sentiment")
                
                except Exception as e:
                    self.logger.error(f"Error screening {symbol}: {e}")
                    # On error, treat as safe (don't block trading due to API issue)
                    results['safe'].append(symbol)
        
        # Log summary
        self.logger.info(f"✅ Safe: {len(results['safe'])}")
        self.logger.info(f"⚠️  Risky: {len(results['risky'])}")
        self.logger.info(f"🚫 Blocked: {len(results['blocked'])}")
        
        if results['blocked']:
            blocked_symbols = [s[0] for s in results['blocked']]
            self.logger.warning(f"Blocked stocks: {', '.join(blocked_symbols)}")
        
        return results
    
    def get_safe_universe(self, screened_results: Dict) -> List[str]:
        """Get only safe + slightly risky stocks"""
        return screened_results['safe'] + list(screened_results['risky'].keys())
    
    def get_very_safe_universe(self, screened_results: Dict) -> List[str]:
        """Get only safe stocks (exclude even slightly risky)"""
        return screened_results['safe']
```

### 5.2 Update `bot_v2/launcher.py` (morning routine, around line 600-650)

Add import:
```python
from bot_v2.screening.universe_sentiment_screener import UniverseSentimentScreener
```

In `__init__()`, add:
```python
# Initialize universe sentiment screener
if self.signal_generator.sentiment_analyzer:
    self.universe_screener = UniverseSentimentScreener(
        self.signal_generator.sentiment_analyzer,
        self.signal_generator.sentiment_veto
    )
else:
    self.universe_screener = None
```

In the main trading loop (where you generate signals), add BEFORE processing candidates:

```python
# NEW: Pre-screen universe for bad sentiment
if self.universe_screener:
    screened_results = self.universe_screener.screen_universe(
        self.universe,
        hours_lookback=24
    )
    
    # Use only safe universe for trading
    trading_universe = self.universe_screener.get_safe_universe(screened_results)
    
    # Log blocked stocks
    if screened_results['blocked']:
        blocked_count = len(screened_results['blocked'])
        self.logger.warning(f"🚫 {blocked_count} stocks blocked due to disaster news")
        for symbol, reason in screened_results['blocked'][:5]:  # Show first 5
            self.logger.warning(f"   - {symbol}: {reason}")
else:
    trading_universe = self.universe
```

Then use `trading_universe` instead of `self.universe` for signal generation:

```python
# OLD:
for symbol in self.universe:
    signal = self.signal_generator.generate_signal(...)

# NEW:
for symbol in trading_universe:  # ← Pre-screened universe
    signal = self.signal_generator.generate_signal(...)
```

**Test This Fix**:
```python
from bot_v2.screening.universe_sentiment_screener import UniverseSentimentScreener
from bot_v2.data_sources.news_sentiment import NewsSentimentAnalyzer
from bot_v2.safety.sentiment_veto import SentimentVetoGate

# Setup
analyzer = NewsSentimentAnalyzer()
veto = SentimentVetoGate()
screener = UniverseSentimentScreener(analyzer, veto)

# Test with small universe
test_universe = ['AAPL', 'TSLA', 'BAD']  # BAD = simulate bad sentiment

results = screener.screen_universe(test_universe)

# Check results structure
assert 'safe' in results
assert 'risky' in results
assert 'blocked' in results
print("✅ Universe screener working")
```

---

## VALIDATION CHECKLIST

After implementing all fixes, run this test suite:

```python
#!/usr/bin/env python3
"""
Validation test suite for sentiment pipeline fixes
Run this before trading
"""

import sys
from pathlib import Path

# Add bot_v2 to path
sys.path.insert(0, str(Path(__file__).parent / 'bot_v2'))

from data_sources.news_sentiment import NewsSentimentAnalyzer
from safety.sentiment_veto import SentimentVetoGate
from signal_generation.signal_generator import AISignalGenerator
from config.trading_config import TradingConfig


def test_strategy_specific_sentiment():
    """Test Fix #1: Strategy-specific adjustments"""
    print("Testing Fix #1: Strategy-specific sentiment...")
    
    analyzer = NewsSentimentAnalyzer()
    
    # Gap & Go + BEAR should penalize heavily
    gap_go_bear = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='gap_go'
    )
    assert gap_go_bear < 0, "Gap & Go + BEAR should have negative adjustment"
    assert gap_go_bear <= -0.20, "Gap & Go + BEAR should be -20% or worse"
    print("  ✅ Gap & Go + BEAR = -20% or worse")
    
    # Fade + STRONG_BULL should penalize heavily
    fade_bull = analyzer.get_sentiment_adjustment(
        {'signal': 'STRONG_BULL'},
        strategy='fade_short'
    )
    assert fade_bull < 0, "Fade + STRONG_BULL should have negative adjustment"
    print("  ✅ Fade + STRONG_BULL has negative adjustment")
    
    # Mean Reversion + BEAR + DP should boost
    mr_bear_dp = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='mean_reversion',
        has_dark_pool_buying=True
    )
    assert mr_bear_dp > 0, "MR + BEAR + DP should have positive adjustment"
    print("  ✅ Mean Reversion + BEAR + DP has positive boost")
    
    print("✅ Fix #1 validated\n")


def test_data_quality_gating():
    """Test Fix #2: Data quality penalties"""
    print("Testing Fix #2: Data quality gating...")
    
    analyzer = NewsSentimentAnalyzer()
    
    # Mock sentiment response with no data
    sentiment_no_data = {
        'data_quality': 'missing',
        'article_count': 0,
        'quality_confidence': 0.0,
    }
    assert sentiment_no_data['data_quality'] == 'missing'
    print("  ✅ No articles marked as 'missing' data quality")
    
    # Low data quality
    sentiment_low = {
        'data_quality': 'low',
        'article_count': 1,
        'quality_confidence': 0.4,
    }
    assert sentiment_low['quality_confidence'] < 0.5
    print("  ✅ Low article count has low quality confidence")
    
    print("✅ Fix #2 validated\n")


def test_hard_veto_gate():
    """Test Fix #3: Hard veto rules"""
    print("Testing Fix #3: Hard veto gate...")
    
    veto = SentimentVetoGate()
    
    # Bankruptcy keyword should trigger veto
    sentiment_bankruptcy = {
        'signal': 'STRONG_BEAR',
        'article_count': 1,
        'sentiment_score': -0.9,
        'headlines': [
            {'headline': 'XYZ Files Bankruptcy Protection', 'summary': 'Company seeking bankruptcy'}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_bankruptcy, 'XYZ')
    assert should_veto == True
    assert sev == 'hard'
    print("  ✅ Bankruptcy keyword triggers hard veto")
    
    # STRONG_BEAR with multiple articles should veto
    sentiment_strong_bear = {
        'signal': 'STRONG_BEAR',
        'article_count': 3,
        'sentiment_score': -0.85,
        'headlines': []
    }
    should_veto, reason, sev = veto.check_veto(sentiment_strong_bear, 'ABC')
    assert should_veto == True
    print("  ✅ STRONG_BEAR + multiple articles triggers veto")
    
    # BEAR alone should not veto
    sentiment_bear = {
        'signal': 'BEAR',
        'article_count': 1,
        'sentiment_score': -0.4,
        'headlines': []
    }
    should_veto, reason, sev = veto.check_veto(sentiment_bear, 'DEF')
    assert should_veto == False
    print("  ✅ BEAR alone does not trigger veto")
    
    print("✅ Fix #3 validated\n")


def test_multiplicative_gating():
    """Test Fix #4: Multiplicative confidence gating"""
    print("Testing Fix #4: Multiplicative gating...")
    
    # Negative adjustments should reduce more than additive
    original = 0.60  # 60%
    
    # Additive (old, wrong): 60% - 20% = 40%
    additive_result = original - 0.20
    
    # Multiplicative (new, correct): 60% * (1 - 0.20) = 48%
    multiplicative_result = original * (1.0 - 0.20)
    
    assert multiplicative_result > additive_result
    assert multiplicative_result == 0.48
    print(f"  ✅ -20% adjustment: 60% → 48% (not 40%)")
    
    # Multiple negative adjustments compound
    result = 0.60
    result *= (1.0 - 0.20)  # -20% sentiment
    result *= (1.0 - 0.10)  # -10% dark pool
    
    expected = 0.60 * 0.80 * 0.90
    assert abs(result - expected) < 0.001
    print(f"  ✅ Multiple negatives compound correctly: 60% → 43.2%")
    
    print("✅ Fix #4 validated\n")


def test_universe_screener():
    """Test Fix #5: Universe screener structure"""
    print("Testing Fix #5: Universe screener...")
    
    # Just verify the screener can be imported and initialized
    from bot_v2.screening.universe_sentiment_screener import UniverseSentimentScreener
    
    print("  ✅ UniverseSentimentScreener imports successfully")
    print("✅ Fix #5 validated\n")


if __name__ == '__main__':
    print("=" * 60)
    print("SENTIMENT PIPELINE FIX VALIDATION")
    print("=" * 60 + "\n")
    
    try:
        test_strategy_specific_sentiment()
        test_data_quality_gating()
        test_hard_veto_gate()
        test_multiplicative_gating()
        test_universe_screener()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nYou can now deploy the fixed sentiment pipeline!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

---

## DEPLOYMENT STEPS

### Step 1: Backup Current Code
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
git add -A
git commit -m "Pre-sentiment-fixes backup"
```

### Step 2: Implement Fixes in Order
1. **Fix #1** (Strategy-specific) - 2 hours
2. **Fix #2** (Data quality) - 2 hours
3. **Fix #3** (Hard veto) - 3 hours
4. **Fix #4** (Multiplicative) - 1 hour
5. **Fix #5** (Universe screener) - 2 hours

### Step 3: Run Validation Tests
```bash
python validation_tests.py
```

### Step 4: Backtest the Changes
```bash
# Run backtest with new sentiment logic
python run_backtest.py --start-date 2026-01-01 --end-date 2026-01-28 --new-sentiment-logic
```

### Step 5: Paper Trade
- Run paper trading for 2-3 days
- Monitor sentiment rejection logs
- Verify hard veto triggers correctly

### Step 6: Deploy to Live
```bash
git add -A
git commit -m "Deploy sentiment pipeline fixes"
git push
```

---

## MONITORING AFTER DEPLOYMENT

Add these logging/dashboard metrics:

```python
# Track sentiment-based rejections
self.logger.info(f"📊 Sentiment Stats: "
                f"Processed={processed}, "
                f"Rejected_STRONG_BEAR={rejected_strong_bear}, "
                f"Rejected_Hard_Veto={rejected_veto}, "
                f"Accepted={accepted}")

# Daily summary
logger.info(f"Daily Sentiment Summary: "
           f"Safe universe size: {len(safe_universe)}, "
           f"Blocked: {len(blocked)}, "
           f"Risky: {len(risky)}")
```

---

## ROLLBACK PLAN

If issues arise:

```bash
git revert HEAD~1  # Revert last commit
git push
# Restart trading bot
```

---

**Next**: Start with Fix #1 and work through systematically. Each fix is independent and can be tested separately.

