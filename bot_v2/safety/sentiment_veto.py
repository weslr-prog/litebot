"""
Sentiment veto gate - hard exclusion rules for disaster news
These keywords/patterns trigger automatic rejection (no scoring)
"""

import logging
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)

# Hard veto keywords - these ALWAYS trigger rejection
HARD_VETO_KEYWORDS = [
    'bankruptcy',
    'liquidation',
    'delisting',
    'sec investigation',
    'fraud charges',
    'accounting restatement',
    'insolvency',
    'going concern',
    'stock exchange halt',
    'trading halt',
    'reverse split',
    'covenant breach',
    'loan default',
    'class action',
    'ceo arrested',
    'cfo indicted',
    'audit failure',
]

# Soft veto keywords - these trigger additional scrutiny (log warning but don't block)
SOFT_VETO_KEYWORDS = [
    'downgrade',
    'insider selling',
    'short seller report',
    'warning letter',
    'product recall',
    'competitor winning',
]


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
            (should_veto: bool, reason: Optional[str], severity: 'hard' | 'soft' | 'none')
        """
        
        # Check 1: Keyword-based hard veto (check this FIRST)
        headlines = sentiment.get('headlines', [])
        
        for article in headlines:
            headline = article.get('headline', '').lower()
            summary = article.get('summary', '')
            if summary:
                summary = summary.lower()
            
            # Check hard veto keywords
            for keyword in HARD_VETO_KEYWORDS:
                if keyword in headline or (summary and keyword in summary):
                    return True, f"Disaster keyword found: '{keyword}'", 'hard'
        
        # Check 2: STRONG_BEAR sentiment with multiple articles
        if sentiment.get('signal') == 'STRONG_BEAR':
            article_count = sentiment.get('article_count', 0)
            if article_count >= 2:
                return True, f"STRONG_BEAR sentiment ({article_count} articles)", 'hard'
            elif article_count == 1:
                # Single article, but if very strong negative, still veto
                score = sentiment.get('sentiment_score', 0)
                if score < -0.8:
                    return True, f"Extremely negative single article (score={score:.2f})", 'hard'
        
        # Check 3: Pattern-based veto (multiple negative signals)
        signal = sentiment.get('signal')
        article_count = sentiment.get('article_count', 0)
        score = sentiment.get('sentiment_score', 0)
        
        if signal in ['BEAR', 'STRONG_BEAR']:
            # Multiple articles all negative = risky
            if article_count >= 5 and score < -0.4:
                return True, f"Multiple negative articles (avg score={score:.2f}, count={article_count})", 'hard'
        
        # Check 4: Soft veto warnings (log but don't block)
        soft_veto_triggered = False
        soft_reasons = []
        
        for article in headlines:
            headline = article.get('headline', '').lower()
            for keyword in SOFT_VETO_KEYWORDS:
                if keyword in headline:
                    soft_veto_triggered = True
                    soft_reasons.append(keyword)
        
        if soft_veto_triggered:
            # Don't block, but log warning
            unique_reasons = list(set(soft_reasons))[:3]  # First 3 unique
            reason = f"Soft veto: {', '.join(unique_reasons)}"
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
