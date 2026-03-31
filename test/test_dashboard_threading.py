#!/usr/bin/env python3
"""
Quick test for dashboard threading issues
"""

import time
import threading
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_threading():
    """Test dashboard initialization without GUI display issues"""
    try:
        print("🧪 Testing Dashboard Threading...")
        
        from config import Sprint1Config
        from sprint1_alpaca_integration import Sprint1AlpacaIntegration
        from sprint1_integrated_dashboard import Sprint1Dashboard
        
        # Initialize components
        config = Sprint1Config()
        trading_system = Sprint1AlpacaIntegration(launch_gui=False)
        
        print("✅ Trading system initialized")
        
        # Create dashboard (but don't run mainloop)
        dashboard = Sprint1Dashboard(trading_system, config)
        
        print("✅ Dashboard created successfully")
        
        # Test starting monitoring
        dashboard.start_monitoring()
        
        print("✅ Monitoring started successfully")
        
        # Wait a moment to see if any threading errors occur
        time.sleep(2)
        
        # Stop monitoring
        dashboard.stop_monitoring()
        
        print("✅ Monitoring stopped successfully")
        print("🎉 All threading tests passed!")
        
        # Clean up
        dashboard.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard threading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dashboard_threading()
    sys.exit(0 if success else 1)
