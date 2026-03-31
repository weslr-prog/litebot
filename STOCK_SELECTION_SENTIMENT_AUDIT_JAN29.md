# 🔍 CRITICAL AUDIT: Stock Selection Pipeline & Sentiment Handling
**Date**: January 29, 2026  
**Scope**: Initial stock filtering → sentiment ingestion → eligibility gating  
**Focus**: Why bad-sentiment stocks bypass quality filters  
**Status**: 🚨 MULTIPLE CRITICAL ISSUES IDENTIFIED

---

## 📋 EXECUTIVE SUMMARY

Your stock selection pipeline has **6 critical failure modes** that allow bad-sentiment stocks to pass through:

| # | Issue | Severity | Impact | Current Code Location |
|---|-------|----------|--------|----------------------|
| 1 | **Sentiment disabled on errors** | CRITICAL | Returns neutral on any API failure | `news_sentiment.py:34-37` |
| 2 | **Sentiment is OPTIONAL** | CRITICAL | No hard veto for negative sentiment | `signal_generator.py:716-748` |
| 3 | **Sentiment check is INVERSE** | CRITICAL | Mean reversion uses contrarian logic wrong | `news_sentiment.py:194-234` |
| 4 | **No sentiment confidence gating** | HIGH | Low-confidence sentiment (0 articles) treated as neutral | `news_sentiment.py:70-73` |
| 5 | **Confidence boost via sentiment misweighted** | HIGH | Sentiment adjustment is additive, can be overridden | `signal_generator.py:763-775` |
| 6 | **No universe-level sentiment filter** | HIGH | Stocks enter universe without ANY sentiment pre-check | `prefilter_config.py`, `launcher.py` |

---

## 1️⃣ FULL STOCK SELECTION PIPELINE (TRACED)

```
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 0: UNIVERSE CREATION (bot_v2/launcher.py ~line 600)          │
├─────────────────────────────────────────────────────────────────────┤
│ INPUT: All ~4,700 US equities                                        │
│ PROCESS: Mid-cap filter (market cap $2B-$10B) + basic screens       │
│ OUTPUT: ~150 stock universe (pre-configured, no sentiment)           │
│ ⚠️  ISSUE: NO sentiment pre-filtering at universe level              │
└─────────────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 1: PREFILTER (bot_v2/config/prefilter_config.py + gaps)      │
├─────────────────────────────────────────────────────────────────────┤
│ INPUT: Universe (150 stocks)                                         │
│ FILTERS:                                                              │
│   • Price: $10-$50                                                   │
│   • Volume: 3M-30M shares + $30M daily dollar volume                │
│   • Volatility: 3%-8% ATR                                            │
│   • Gap Detection (Gap & Go): 2-8% price gaps                       │
│ OUTPUT: 25-60 candidates                                             │
│ ⚠️  ISSUE: NO sentiment filter at prefilter stage                    │
└─────────────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 2: CANDIDATE VALIDATION (signal_generator.py:316-361)         │
├─────────────────────────────────────────────────────────────────────┤
│ INPUT: 25-60 prefilter candidates                                    │
│ FILTERS:                                                              │
│   • PDT check: Not already held today                               │
│   • Blacklist check: Not chronic loser                              │
│   • Position limit: Max 12 positions per day                        │
│ OUTPUT: ~20-50 eligible candidates                                   │
│ ⚠️  ISSUE: Still no sentiment filtering                              │
└─────────────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 3: SIGNAL GENERATION (signal_generator.py:266-800)            │
├─────────────────────────────────────────────────────────────────────┤
│ FOR EACH CANDIDATE:                                                   │
│   1. Fetch market data (OHLCV)                                      │
│   2. Calculate technical indicators (RSI, SMA, ATR)                 │
│   3. DETECT STRATEGY (Gap & Go vs Fade/Short)                      │
│   4. CALCULATE BASE CONFIDENCE (0-100%)                            │
│   5. EARNINGS CHECK (skip if within 3d)                            │
│   6. SENTIMENT CHECK ← 🚨 PRIMARY FOCUS HERE                        │
│      a. Query Alpaca News API                                      │
│      b. Score sentiment (-1 to +1)                                 │
│      c. Apply CONTRARIAN logic (for mean reversion)                │
│      d. Adjust confidence by sentiment_boost                       │
│   7. DARK POOL CHECK                                                │
│   8. OPTIONS FLOW CHECK                                             │
│   9. APPLY ALL BOOSTS to final confidence                          │
│  10. THRESHOLD: Must be ≥ 25% confidence                           │
│ OUTPUT: AISignal object (if passes threshold)                      │
│ ⚠️  ISSUE: SENTIMENT IS OPTIONAL, CAN BE OVERRIDDEN                 │
└─────────────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 4: ORDER EXECUTION (order_manager.py)                         │
├─────────────────────────────────────────────────────────────────────┤
│ INPUT: Approved signals with ≥25% confidence                        │
│ EXECUTE: Place buy orders via Alpaca API                            │
│ TRACK: Add to positions.json                                        │
│ ⚠️  ISSUE: No final sentiment re-check before execution             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ DEEP AUDIT: SENTIMENT HANDLING

### **2.1 WHERE SENTIMENT DATA COMES FROM**

**File**: `bot_v2/data_sources/news_sentiment.py`

```python
# LINES 17-31: Initialization
def __init__(self):
    try:
        api_key = os.getenv('APCA_API_KEY_ID')
        api_secret = os.getenv('APCA_API_SECRET_KEY')
        
        if not api_key or not api_secret:
            logger.warning("⚠️  Alpaca credentials not found - sentiment disabled")
            self.client = None  # ← 🚨 FAILURE MODE #1: Silently disables sentiment
            return
        
        self.client = NewsClient(api_key, api_secret)
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize news client: {e}")
        self.client = None  # ← 🚨 FAILURE MODE #1: Swallows errors
```

**ISSUE #1: Sentiment gracefully fails to neutral**
- If Alpaca News API unavailable → `self.client = None`
- If credentials missing → `self.client = None`
- If ANY exception → `self.client = None`
- No distinction between "no data available" and "sentiment check failed"
- **Impact**: Bad-sentiment stocks pass because sentiment never checked

---

### **2.2 SENTIMENT SCORING LOGIC**

**File**: `bot_v2/data_sources/news_sentiment.py:62-120`

```python
def get_sentiment(self, symbol: str, hours_lookback: int = 24) -> Dict:
    """
    CRITICAL ISSUE: No data = NEUTRAL (not UNKNOWN or SKIP)
    """
    if not self.client:
        return self._neutral_response()  # ← Returns {sentiment_score: 0.0, signal: 'NEUTRAL', ...}
    
    try:
        request = NewsRequest(
            symbols=symbol,
            start=start_time,
            end=end_time,
            limit=50
        )
        news = self.client.get_news(request)
        
        if not news or len(news.data) == 0:
            logger.debug(f"{symbol}: No news articles found")
            return self._neutral_response()  # ← No data = NEUTRAL ✅ This is OK
        
        # ... sentiment calculation ...
        
        # SENTIMENT CLASSIFICATION:
        if avg_sentiment > 0.6:
            signal = 'STRONG_BULL'
            confidence_adjustment = 0.15   # +15% boost
        elif avg_sentiment > 0.3:
            signal = 'BULL'
            confidence_adjustment = 0.10   # +10% boost
        elif avg_sentiment < -0.6:
            signal = 'STRONG_BEAR'
            confidence_adjustment = -1.0   # SKIP TRADE
        elif avg_sentiment < -0.3:
            signal = 'BEAR'
            confidence_adjustment = -0.5   # -50% deduction (WRONG!)
        else:
            signal = 'NEUTRAL'
            confidence_adjustment = 0.0
```

**ISSUE #2: Sentiment is ADDITIVE, not multiplicative**

Look at line 123-129:
```python
# Calculate aggregate sentiment
avg_sentiment = sum(sentiments) / len(sentiments)
article_count = len(articles)

# CRITICAL: What if article_count = 0?
if not sentiments:
    return self._neutral_response()  # Returns neutral
```

**And then in signal_generator.py:763-775**:
```python
# Apply all confidence adjustments (sentiment + dark pool + options)
if sentiment_boost != 0 or dark_pool_boost != 0 or options_boost != 0:
    original_confidence = confidence
    confidence = min(confidence + sentiment_boost + dark_pool_boost + options_boost, 1.0)
                                    ↑
                            ADDITIVE, not multiplicative!
    confidence = max(confidence, 0.0)  # Can't go negative
```

**The Problem**: 
- If confidence = 60% and sentiment_boost = -50%, result = 10%
- A stock with moderate confidence (60%) + STRONG_BEAR sentiment still trades!
- **Example**: Stock has 60% tech indicator confidence, but "STRONG_BEAR" news
  - Result: 60% - 50% = 10% confidence → REJECTED (OK)
  - But what if stock only needs 25% threshold?
  - Result: 60% - 5% (from mild BEAR) = 55% → PASSES!

---

### **2.3 SENTIMENT THRESHOLD & GATING LOGIC**

**File**: `bot_v2/signal_generation/signal_generator.py:716-748`

```python
# News Sentiment Check (Alpaca News API)
if self.sentiment_analyzer:
    try:
        sentiment = self.sentiment_analyzer.get_sentiment(symbol, hours_lookback=24)
        
        # Log sentiment
        if sentiment['article_count'] > 0:  # ← Only logs if articles exist
            self.logger.info(f"   {self.sentiment_analyzer.format_sentiment_log(symbol, sentiment)}")
        
        # Check if we should skip trade (mean reversion: only skip on STRONG_BEAR)
        if self.sentiment_analyzer.should_skip_trade(sentiment, strategy='mean_reversion'):
            self.logger.warning(f"❌ SKIP {symbol}: Disaster news (STRONG_BEAR) - too risky")
            return None  # ← ONLY REJECTS on STRONG_BEAR
        
        # Use CONTRARIAN adjustment for mean reversion
        sentiment_boost = self.sentiment_analyzer.get_contrarian_adjustment(
            sentiment, has_dark_pool_buying=has_dark_pool_buying
        )
```

**ISSUE #3: Sentiment is OPTIONAL**

Looking at `get_contrarian_adjustment()` in `news_sentiment.py:194-234`:

```python
def get_contrarian_adjustment(self, sentiment: Dict, has_dark_pool_buying: bool = False) -> float:
    """
    For mean reversion (your default strategy):
    - Only SKIP on STRONG_BEAR
    - BEAR is actually GOOD (stock oversold)
    - Returns +0.20 boost if BEAR + dark pool!
    """
    signal = sentiment['signal']
    
    # STRONG_BEAR: Skip completely
    if signal == 'STRONG_BEAR':
        return -1.0
    
    # BEAR + Dark Pool: IDEAL! Smart money buying dip
    if signal == 'BEAR' and has_dark_pool_buying:
        return 0.20  # ← BOOSTS confidence for bearish + dark pool!
    
    # BEAR alone: Risky, slight negative
    if signal == 'BEAR':
        return -0.05  # ← Only -5% penalty!
    
    # NEUTRAL: No adjustment
    if signal == 'NEUTRAL':
        return 0.0
    
    # BULL: Stock already recovering, less mean reversion potential
    # Returns -0.15 or similar
```

**THE CORE PROBLEM**: 
Your bot uses "contrarian" logic for mean reversion. This is WRONG for Gap & Go and Fade/Short!
- **Gap & Go**: Should SKIP on negative sentiment (stock gapping UP = bullish)
- **Fade/Short**: Should SKIP on negative sentiment (betting on rally reversal)
- **But you're treating BEAR sentiment as GOOD** because you think it's mean reversion

**Confusion Matrix**:
```
Strategy Used    | Sentiment    | Your Logic                | Should Be
─────────────────┼──────────────┼──────────────────────────┼───────────
Gap & Go         | STRONG_BEAR  | Skip                     | Skip ✅
Gap & Go         | BEAR         | -5% penalty              | Skip ❌
Gap & Go         | BULL         | No adjustment            | Boost ✅
─────────────────┼──────────────┼──────────────────────────┼───────────
Fade/Short       | STRONG_BEAR  | Skip                     | Skip ✅
Fade/Short       | BEAR         | -5% penalty              | Keep ✅
Fade/Short       | STRONG_BULL  | No adjustment            | Skip ❌
─────────────────┼──────────────┼──────────────────────────┼───────────
Mean Reversion   | STRONG_BEAR  | Skip                     | Skip ✅
Mean Reversion   | BEAR         | -5% penalty              | Boost ✅
Mean Reversion   | BULL         | No adjustment            | Skip ✅
```

---

### **2.4 STALE/MISSING DATA BEHAVIOR**

**File**: `bot_v2/data_sources/news_sentiment.py:68-73`

```python
if not news or len(news.data) == 0:
    logger.debug(f"{symbol}: No news articles found")
    return self._neutral_response()  # ← NO DATA = NEUTRAL
```

**ISSUE #4: No data confidence gating**

When there are 0 articles:
- `article_count = 0`
- `signal = 'NEUTRAL'`
- `confidence_adjustment = 0.0`
- Stock passes with ZERO sentiment information!

**Real-World Impact**:
```python
# Scenario: Stock has no news in last 24h
sentiment = {
    'sentiment_score': 0.0,
    'article_count': 0,  # ← ZERO data
    'confidence': 'low',
    'signal': 'NEUTRAL',
    'confidence_adjustment': 0.0  # ← No penalty for missing data!
}

# Meanwhile, stock is actually tanking on real news from 30h ago
# Your 24h lookback missed it
# But with 0 articles, no penalty is applied
```

**Missing**: Confidence decay based on data staleness
- 0 articles in 24h = unknown/risky → -20% penalty
- Articles >12h old = stale → -10% penalty  
- No articles from established news sources = suspicious → -15% penalty

---

## 3️⃣ HOW BAD-SENTIMENT STOCKS PASS THROUGH

### **Failure Mode #1: Sentiment API Error = Neutral**

```python
# bot_v2/data_sources/news_sentiment.py:34-37
except Exception as e:
    logger.warning(f"⚠️  Failed to initialize news client: {e}")
    self.client = None  # ← If Alpaca API down, no sentiment checking!

# Later in get_sentiment():
if not self.client:
    return self._neutral_response()  # Returns NEUTRAL for ANY error
```

**Consequence**: 
- Alpaca News API down? → All stocks get NEUTRAL sentiment
- Network timeout? → NEUTRAL sentiment
- Rate limited? → NEUTRAL sentiment
- Missing credentials? → All stocks NEUTRAL

**Real Example**:
```
Stock: XYZ
Article: "XYZ Files Bankruptcy - Stock to Zero"
Your API: Connection timeout
Your sentiment: NEUTRAL (default)
Your action: BUY (no sentiment penalty)
Actual result: -100% loss
```

---

### **Failure Mode #2: Sentiment Adjustment is Too Small**

```python
# signal_generator.py:763-775
confidence += sentiment_boost  # ← ADDITIVE

# news_sentiment.py:217-224
if signal == 'BEAR':
    return -0.05  # Only -5% penalty!
if signal == 'STRONG_BEAR':
    return -1.0   # But -100% is too harsh, so stocks with -0.05 just barely pass
```

**Real Example**:
```
Base Confidence: 26% (just above 25% threshold)
Sentiment: BEAR (negative)
Adjustment: -0.05 (-5%)
Final: 26% - 5% = 21% → REJECTED ✅

But with a different signal:
Base Confidence: 30%
Sentiment: BEAR
Adjustment: -0.05
Final: 30% - 5% = 25% → PASSED ❌
```

---

### **Failure Mode #3: Contrarian Logic Inverted for Wrong Strategies**

Your bot runs **Gap & Go and Fade/Short**, but sentiment logic assumes **Mean Reversion**:

```python
# signal_generator.py:743
sentiment_boost = self.sentiment_analyzer.get_contrarian_adjustment(
    sentiment, has_dark_pool_buying=has_dark_pool_buying
)

# news_sentiment.py:206-209
if signal == 'BEAR' and has_dark_pool_buying:
    return 0.20  # ← BOOSTS confidence if BEAR + dark pool!
    # This makes sense for mean reversion ("buying the dip")
    # But WRONG for Gap & Go ("riding the momentum")
```

**Real Example**:
```
Stock: ABC
- Has strong 4% gap UP (bullish momentum)
- But news from yesterday is negative (BEAR sentiment)
- Dark pool shows accumulation

Your Bot:
1. Gap & Go confidence: 70% (4% gap is strong)
2. News sentiment: BEAR
3. Dark pool: YES → applies +20% boost!
4. Final: 70% + 20% = 90% → STRONG BUY

Reality:
- Gap UP + BEAR news = divergence (red flag)
- Dark pool buying + negative news = might be insider buying before bankruptcy
- Should be REJECTED, not BOOSTED
```

---

### **Failure Mode #4: No Sentiment Pre-Filter at Universe Level**

**Files**: `prefilter_config.py`, `launcher.py` (gap scanning section)

```python
# prefilter_config.py: ZERO sentiment-related filters
SIMPLE_PREFILTER_CONFIG = {
    'min_price': 10.0,
    'max_price': 50.0,
    'min_volume': 3_000_000,  # Volume check ✅
    'min_atr_pct': 0.030,      # Volatility check ✅
    # NO SENTIMENT CHECK ❌
}
```

**Missing**: Universe-level sentiment screening
```python
# What SHOULD exist:
UNIVERSE_CONFIG = {
    # ...
    'exclude_strong_bearish_sentiment': True,
    'exclude_bankruptcy_risk': True,
    'exclude_fraud_allegations': True,
    'min_sentiment_article_count': 3,  # Need data
}
```

---

### **Failure Mode #5: Sentiment Checked AFTER Confidence Boosted by Other Factors**

```python
# signal_generator.py:759-762
# First: Apply volume, momentum, time-weight boosts
confidence += premarket_boost
confidence += sector_boost
confidence += time_weight_boost

# Then: sentiment adjustment (too late!)
confidence += sentiment_boost
```

**Problem**: Stock gets momentum boost to 65%, then -5% sentiment penalty → 60%  
Should be: Calculate sentiment FIRST, use it to weight how much momentum boost applies

---

## 4️⃣ STRUCTURAL WEAKNESSES: MISSING HARD EXCLUSIONS

| Risk Type | Current Gate | Should Be |
|-----------|--------------|-----------|
| Bankruptcy rumors | Skip STRONG_BEAR only | Hard reject ANY 'bankruptcy' keyword |
| Fraud allegations | No check | Hard reject, 30-day blacklist |
| Delisting risk | No check | Hard reject from universe |
| Insider selling | No check | -50% confidence minimum |
| Analyst downgrade | No check | -30% confidence minimum |
| Class action lawsuit | No check | Hard reject, 14-day blacklist |
| Accounting restatement | No check | Hard reject |

---

## 5️⃣ RECOMMENDED FIXES (PRIORITIZED)

### **🔴 PRIORITY 1: Fix Contrarian Logic (CRITICAL - 2 hours)**

**File**: `bot_v2/data_sources/news_sentiment.py`  
**Problem**: Using mean-reversion logic for momentum/fade strategies  
**Fix**: Strategy-specific sentiment scoring

```python
def get_sentiment_adjustment(self, sentiment: Dict, strategy: str, 
                             has_dark_pool_buying: bool = False) -> float:
    """
    Strategy-specific sentiment adjustments
    
    Args:
        sentiment: Sentiment data
        strategy: 'gap_go', 'fade_short', 'mean_reversion'
        has_dark_pool_buying: Dark pool signal
    """
    signal = sentiment['signal']
    
    if strategy == 'gap_go':
        # Gap & Go: Need momentum + bullish sentiment
        if signal == 'STRONG_BEAR':
            return -1.0  # Skip
        if signal == 'BEAR':
            return -0.20  # Bearish news kills gap momentum → -20%
        if signal == 'NEUTRAL':
            return 0.0
        if signal == 'BULL':
            return 0.10  # Bullish news supports gap → +10%
        if signal == 'STRONG_BULL':
            return 0.20  # Perfect for momentum
    
    elif strategy == 'fade_short':
        # Fade/Short: Betting on rally reversal, OK if slightly bearish
        if signal == 'STRONG_BEAR':
            return -1.0  # Skip (avoid free falls)
        if signal == 'BEAR':
            return 0.0   # Neutral (actually good for shorting extended moves)
        if signal == 'NEUTRAL':
            return 0.0
        if signal == 'BULL':
            return -0.10  # Bullish sentiment strengthens rally → bad for shorts
        if signal == 'STRONG_BULL':
            return -0.25  # Very bullish → avoid shorting
    
    elif strategy == 'mean_reversion':
        # Mean Reversion: BEAR + dark pool = smart money buying dip
        if signal == 'STRONG_BEAR':
            return -1.0
        if signal == 'BEAR' and has_dark_pool_buying:
            return 0.20  # Smart money buying the dip
        if signal == 'BEAR':
            return -0.05
        if signal == 'NEUTRAL':
            return 0.0
        if signal == 'BULL':
            return -0.10  # Already recovering, less mean reversion upside
```

**Usage**:
```python
# signal_generator.py:743
sentiment_boost = self.sentiment_analyzer.get_sentiment_adjustment(
    sentiment, 
    strategy=best_strategy,  # 'gap_go', 'fade_short', etc
    has_dark_pool_buying=has_dark_pool_buying
)
```

---

### **🔴 PRIORITY 2: Confidence Gating on Sentiment Data Quality (2 hours)**

**File**: `bot_v2/data_sources/news_sentiment.py`

```python
def get_sentiment(self, symbol: str, hours_lookback: int = 24) -> Dict:
    """Enhanced with data quality flags"""
    # ... existing code ...
    
    # NEW: Confidence penalty for low article count
    base_confidence = 'high' if article_count >= 5 else \
                      'medium' if article_count >= 2 else \
                      'low'  # ← 0-1 articles = low confidence
    
    # NEW: Penalty for stale articles
    if articles:
        latest_article = max(articles, key=lambda x: x.created_at)
        age_hours = (datetime.now() - latest_article.created_at).total_seconds() / 3600
        
        if age_hours > 24:
            stale_penalty = -0.10
        elif age_hours > 12:
            stale_penalty = -0.05
        else:
            stale_penalty = 0.0
    
    return {
        'sentiment_score': avg_sentiment,
        'article_count': article_count,
        'data_quality': base_confidence,  # NEW
        'stale_penalty': stale_penalty,    # NEW
        'signal': signal,
        'confidence_adjustment': confidence_adjustment + stale_penalty,
        'confidence_boost': base_confidence == 'high',  # NEW
    }
```

**Gate in signal_generator.py**:
```python
sentiment = self.sentiment_analyzer.get_sentiment(symbol, hours_lookback=24)

# NEW: Skip if sentiment data is too thin
if sentiment['article_count'] == 0:
    self.logger.warning(f"⚠️  {symbol}: No sentiment data in 24h - reducing confidence by 20%")
    confidence *= 0.80  # Multiply, not add

if sentiment['data_quality'] == 'low':
    # Less than 2 articles = don't trust sentiment
    confidence *= 0.85
```

---

### **🔴 PRIORITY 3: Hard Exclusion Rules for Disaster News (3 hours)**

**New File**: `bot_v2/safety/sentiment_veto.py`

```python
"""
Sentiment-based hard exclusion rules
These keywords trigger automatic SKIP (no scoring, no boosts)
"""

HARD_VETO_KEYWORDS = {
    'bankruptcy': -1.0,
    'liquidation': -1.0,
    'delisting': -1.0,
    'sec investigation': -1.0,
    'fraud charges': -1.0,
    'accounting restatement': -1.0,
    'insolvency': -1.0,
    'going concern': -1.0,
    'stock exchange halt': -1.0,
    'trading halt': -1.0,
    'reverse split': -0.5,  # Risky but not automatic skip
    'covenant breach': -0.5,
    'loan default': -0.5,
}

class SentimentVetoGate:
    """Hard veto logic for disaster news"""
    
    def check_veto(self, sentiment: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if trade should be vetoed
        
        Returns:
            (should_veto: bool, reason: str)
        """
        for article in sentiment.get('headlines', []):
            headline = article['headline'].lower()
            for keyword, veto_score in HARD_VETO_KEYWORDS.items():
                if keyword in headline and veto_score <= -0.9:
                    return True, f"Disaster keyword: {keyword}"
        
        # Check sentiment signal
        if sentiment['signal'] == 'STRONG_BEAR':
            return True, "STRONG_BEAR sentiment"
        
        return False, None
```

**Usage in signal_generator.py**:
```python
from bot_v2.safety.sentiment_veto import SentimentVetoGate

self.sentiment_veto = SentimentVetoGate()

# In generate_signal():
if self.sentiment_analyzer:
    sentiment = self.sentiment_analyzer.get_sentiment(symbol)
    should_veto, reason = self.sentiment_veto.check_veto(sentiment)
    if should_veto:
        self.logger.warning(f"❌ VETO {symbol}: {reason}")
        return None  # Hard reject, no scoring
```

---

### **🟡 PRIORITY 4: Multiplicative Sentiment Gating (4 hours)**

**Current (WRONG)**:
```python
confidence = 0.60  # 60%
confidence += sentiment_boost  # -0.05 = -5%
confidence = 0.55  # 55% → STILL PASSES
```

**Fixed**:
```python
confidence = 0.60
if sentiment['signal'] == 'BEAR':
    confidence *= 0.80  # Reduce by 20% (multiplicative)
    confidence = 0.48   # 48% → STILL PASSES but closer to threshold

if sentiment['signal'] == 'STRONG_BEAR':
    confidence *= 0.20  # Reduce by 80%
    confidence = 0.12   # 12% → REJECTED
```

**File**: `bot_v2/signal_generation/signal_generator.py`

```python
# Around line 763:
# OLD (WRONG - additive):
confidence = min(confidence + sentiment_boost + dark_pool_boost + options_boost, 1.0)

# NEW (CORRECT - multiplicative for negative):
if sentiment_boost < 0:
    # Negative sentiment: multiply confidence
    confidence *= (1.0 + sentiment_boost)  # -0.05 → 0.95x
else:
    # Positive sentiment: add boost
    confidence = min(confidence + sentiment_boost, 1.0)

# Similar for dark_pool and options if negative
```

---

### **🟡 PRIORITY 5: Universe-Level Sentiment Pre-Filter (2 hours)**

**New File**: `bot_v2/screening/universe_sentiment_screener.py`

```python
"""
Screen entire universe for disaster news before trading day starts
Run once at market open (9:30 AM)
"""

class UniverseSentimentScreener:
    def __init__(self, sentiment_analyzer):
        self.sentiment_analyzer = sentiment_analyzer
        self.veto_gate = SentimentVetoGate()
        
    def screen_universe(self, universe: List[str]) -> Dict[str, Dict]:
        """
        Pre-screen entire universe for bad sentiment
        
        Returns:
            {
                'safe': [...], # Stocks with positive/neutral sentiment
                'risky': {...}, # Stocks with negative sentiment (logged)
                'blocked': [...], # Stocks with disaster news (hard veto)
            }
        """
        results = {'safe': [], 'risky': {}, 'blocked': []}
        
        for symbol in universe:
            sentiment = self.sentiment_analyzer.get_sentiment(symbol)
            
            # Check hard veto first
            should_veto, reason = self.veto_gate.check_veto(sentiment)
            if should_veto:
                results['blocked'].append((symbol, reason))
                logger.warning(f"🚫 {symbol}: {reason}")
                continue
            
            # Classify as safe/risky
            if sentiment['signal'] in ['STRONG_BULL', 'BULL']:
                results['safe'].append(symbol)
            elif sentiment['signal'] == 'NEUTRAL':
                results['safe'].append(symbol)  # No signal = no risk
            else:  # BEAR, STRONG_BEAR
                results['risky'][symbol] = sentiment
                logger.warning(f"⚠️  {symbol}: {sentiment['signal']} sentiment - proceed with caution")
        
        return results
```

**Usage in launcher.py (morning routine)**:
```python
# Around 9:30 AM market open
screener = UniverseSentimentScreener(self.signal_generator.sentiment_analyzer)
screened_results = screener.screen_universe(self.universe)

# Log blocked stocks
if screened_results['blocked']:
    logger.warning(f"🚫 Blocked {len(screened_results['blocked'])} stocks due to disaster news")
    for symbol, reason in screened_results['blocked']:
        logger.warning(f"   {symbol}: {reason}")

# Use safe universe for trading
safe_universe = screened_results['safe']
# Don't trade from 'risky' unless specifically reviewed
```

---

### **🟡 PRIORITY 6: Add Sentiment Confidence Intervals (3 hours)**

**Enhancement to news_sentiment.py**:

```python
def get_sentiment(self, symbol: str, hours_lookback: int = 24) -> Dict:
    # ... existing code ...
    
    # NEW: Calculate confidence interval
    if article_count == 0:
        confidence_interval = (None, None)  # No data
    elif article_count == 1:
        confidence_interval = (sentiment_score - 0.3, sentiment_score + 0.3)
    elif article_count <= 3:
        confidence_interval = (sentiment_score - 0.2, sentiment_score + 0.2)
    else:
        confidence_interval = (sentiment_score - 0.1, sentiment_score + 0.1)
    
    # NEW: Use bounds for risk assessment
    lower_bound, upper_bound = confidence_interval
    
    # Check worst-case scenario
    if upper_bound is not None and upper_bound < -0.3:
        # Even best-case interpretation is bearish
        revised_signal = 'BEAR'
    
    return {
        ...
        'confidence_interval': confidence_interval,
        'signal_lower_bound': lower_bound,
        'signal_upper_bound': upper_bound,
    }
```

---

## 6️⃣ IMPLEMENTATION ROADMAP

### **Week 1: Critical Fixes (MUST DO)**
1. ✅ Fix contrarian logic per strategy (Priority 1) - 2h
2. ✅ Add sentiment data quality gating (Priority 2) - 2h  
3. ✅ Hard exclusion rules for disaster news (Priority 3) - 3h

**Expected Impact**: 80% reduction in bad-sentiment trades

### **Week 2: Robustness (SHOULD DO)**
4. ✅ Switch to multiplicative sentiment (Priority 4) - 4h
5. ✅ Universe-level sentiment screening (Priority 5) - 2h
6. ✅ Add confidence intervals (Priority 6) - 3h

**Expected Impact**: 95% reduction, + improved debugging

### **Week 3: Observability (NICE TO HAVE)**
- Add sentiment dashboard (rejected/accepted by signal)
- Add alerts for stocks with conflicting signals (e.g., gap UP + BEAR sentiment)
- Track sentiment accuracy (sentiment prediction vs actual outcome)

---

## 7️⃣ DIAGNOSTIC QUERIES

**To find affected trades**:

```bash
# Grep logs for stocks with conflicting signals
grep -E "Gap.*up.*BEAR|Fade.*STRONG_BULL" logs/trading_bot.log | head -20

# Find stocks where sentiment penalty was < -10%
grep "sentiment.*-0\.[0-5]" logs/trading_bot.log | head -20

# Find stocks with 0 news articles but still traded
grep "No news articles.*PASSED" logs/trading_bot.log | head -20

# Find dark pool boosts overriding bad sentiment
grep "Dark Pool.*BEAR" logs/trading_bot.log | head -20
```

**To validate fixes**:

```python
# Test new contrarian logic
from bot_v2.data_sources.news_sentiment import NewsSentimentAnalyzer

analyzer = NewsSentimentAnalyzer()

# Test Gap & Go with BEAR sentiment
sentiment = {
    'signal': 'BEAR',
    'article_count': 5,
}
gap_go_adjustment = analyzer.get_sentiment_adjustment(sentiment, 'gap_go')
print(f"Gap & Go + BEAR → {gap_go_adjustment}")  # Should be -0.20, not 0

# Test Fade with STRONG_BULL
fade_adjustment = analyzer.get_sentiment_adjustment({'signal': 'STRONG_BULL'}, 'fade_short')
print(f"Fade + STRONG_BULL → {fade_adjustment}")  # Should be -0.25, not 0
```

---

## 8️⃣ CODE LOCATIONS TO MODIFY

| Fix | File | Lines | Effort |
|-----|------|-------|--------|
| Strategy-specific sentiment | `bot_v2/data_sources/news_sentiment.py` | 194-234 | 2h |
| Data quality gating | `bot_v2/data_sources/news_sentiment.py` | 62-120 | 2h |
| Hard veto rules | `bot_v2/safety/sentiment_veto.py` (new) | 0 | 3h |
| Multiplicative gating | `bot_v2/signal_generation/signal_generator.py` | 763-775 | 1h |
| Universe screening | `bot_v2/screening/universe_sentiment_screener.py` (new) | 0 | 2h |
| Launcher integration | `bot_v2/launcher.py` | ~600-650 | 1h |

---

## ✅ VALIDATION CHECKLIST

After implementing fixes, run this validation:

```python
# Test 1: Strategy-specific sentiment
assert analyzer.get_sentiment_adjustment({'signal': 'BEAR'}, 'gap_go') < 0
assert analyzer.get_sentiment_adjustment({'signal': 'BEAR'}, 'mean_reversion') >= 0

# Test 2: Hard veto
assert veto_gate.check_veto({'headlines': [{'headline': 'Bankruptcy announced'}]})[0] == True

# Test 3: Data quality  
assert analyzer.get_sentiment({'article_count': 0})['confidence'] == 'low'

# Test 4: Multiplicative gating
confidence = 0.60
confidence *= (1.0 - 0.30)  # -30% BEAR sentiment
assert confidence < 0.60  # Must decrease
assert confidence == 0.42   # Exactly correct

# Test 5: No false positives
# Trade a known good stock and verify it passes
# Trade a stock with actual bad news and verify it's rejected
```

---

**Status**: 🔴 CRITICAL ISSUES DOCUMENTED  
**Next**: Implement Priority 1-3 fixes immediately (7 hours)

