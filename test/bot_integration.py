#!/usr/bin/env python3
"""
Bot Integration Module for Daily Performance Validation
Simple integration point to add daily validation to your bot's routine
"""

import json
import logging
from datetime import datetime
from daily_performance_validator import run_integrated_validation

logger = logging.getLogger(__name__)

def should_run_daily_validation() -> bool:
    """
    Determine if daily validation should run
    Run once per day after market close (5:00 PM ET)
    """
    now = datetime.now()
    
    # Check if it's after market close (5:00 PM ET)
    if now.hour < 17:
        return False
    
    # Check if we already ran today
    try:
        with open('/home/wes/Desktop/litebotx-usb-deployment/logs/daily_validation.json', 'r') as f:
            logs = json.load(f)
            
        # Check if last log is from today
        if logs:
            last_log_date = logs[-1]['timestamp'][:10]  # YYYY-MM-DD
            today_date = now.strftime('%Y-%m-%d')
            
            if last_log_date == today_date:
                return False  # Already ran today
        
        return True
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return True  # No previous logs, should run

def integrate_daily_validation_into_bot():
    """
    Integration function to call from your bot's main loop
    
    Usage in your bot:
    ```python
    from bot_integration import integrate_daily_validation_into_bot
    
    # In your main trading loop:
    validation_result = integrate_daily_validation_into_bot()
    if validation_result and validation_result['critical_alerts'] > 0:
        logger.warning("Critical performance alerts detected!")
    ```
    """
    if not should_run_daily_validation():
        return None
    
    try:
        logger.info("🤖 Running integrated daily performance validation...")
        
        # Run validation
        result = run_integrated_validation()
        
        # Log results to main bot log
        if result['performance_ok']:
            logger.info(f"✅ Daily validation passed: {result['recommendation']}")
        else:
            logger.warning(f"⚠️ Daily validation concerns: {result['recommendation']} ({result['alert_count']} alerts)")
        
        if result['critical_alerts'] > 0:
            logger.critical(f"🚨 Critical performance alerts detected! Recommendation: {result['recommendation']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Daily validation failed: {e}")
        return {'status': 'error', 'error': str(e)}

# Example integration code for your main bot
def example_bot_integration():
    """
    Example of how to integrate this into your main bot routine
    """
    logger.info("🤖 Bot starting daily routine...")
    
    # Your existing bot logic here...
    # market analysis, signal generation, position management, etc.
    
    # Add daily validation check
    validation_result = integrate_daily_validation_into_bot()
    
    if validation_result:
        if validation_result['critical_alerts'] > 0:
            logger.critical("🚨 CRITICAL: Performance validation failed!")
            # You might want to pause trading or alert yourself
            
        elif not validation_result['performance_ok']:
            logger.warning("⚠️ Performance validation has concerns")
            # You might want to be more conservative
            
        else:
            logger.info("✅ Performance validation passed")
    
    logger.info("🤖 Bot daily routine completed")

if __name__ == "__main__":
    # Test the integration
    example_bot_integration()