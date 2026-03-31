#!/usr/bin/env python3
"""
Test script to verify logging configuration works for Sprint1AlpacaIntegration
"""

import logging
import os
from datetime import datetime

# Ensure logs directory exists  
os.makedirs('logs', exist_ok=True)

# Configure logging with file handler (same as launch script now does)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sprint1_alpaca.log'),
        logging.StreamHandler()
    ]
)

# Test the logging
logger = logging.getLogger('TestLoggingFix')
logger.info(f"🧪 Testing logging fix at {datetime.now()}")

# Now test with the actual Sprint1AlpacaIntegration class
try:
    from test.sprint1_alpaca_integration import Sprint1AlpacaIntegration
    
    # Create integration (without launching GUI)
    integration = Sprint1AlpacaIntegration(launch_gui=False)
    
    # Test that its logger works
    integration.logger.info("✅ Sprint1AlpacaIntegration logging test successful!")
    
    print("✅ Logging fix test completed!")
    print("📋 Check logs/sprint1_alpaca.log for the test entries")
    
except Exception as e:
    logger.error(f"❌ Error testing integration: {e}")
    print(f"❌ Test failed: {e}")
