#!/usr/bin/env python3
"""
Risk Manager Enhanced Configuration
Applies drawdown mitigation improvements
"""

# Import this in your trader to apply new risk settings
RISK_SETTINGS_V2 = {
    'max_position_size_dollars': 400,  # Down from ~1200
    'stop_loss_percentage': 0.02,      # Down from ~0.03
    'max_loss_per_trade': 100,         # New hard cap
    'fast_exit_threshold': 0.008,      # Down from ~0.015
    'min_confidence_threshold': 0.08,  # Up from 0.055
    'position_scale_factor': 0.7,      # Start with 70% of max size
}

def apply_conservative_sizing(base_size, confidence):
    """Progressive position sizing based on confidence"""
    if confidence < 0.10:
        return base_size * 0.5  # Very conservative
    elif confidence < 0.15:
        return base_size * 0.7  # Moderately conservative
    else:
        return base_size  # Full size for high confidence
        
def check_loss_limit(current_loss, max_allowed=100):
    """Check if loss exceeds maximum allowed"""
    if abs(current_loss) > max_allowed:
        return True, f"Loss ${abs(current_loss):.2f} exceeds ${max_allowed} limit"
    return False, None

def enhanced_stop_loss(entry_price, current_price, stop_pct=0.02):
    """Enhanced stop loss logic with tighter threshold"""
    loss_pct = (current_price - entry_price) / entry_price
    if loss_pct <= -stop_pct:
        return True, f"Stop loss triggered at {loss_pct*100:.1f}%"
    return False, None
