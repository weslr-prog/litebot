#!/usr/bin/env python3
"""
Quick test of Sprint 1 integrated dashboard
"""

from sprint1_alpaca_integration import Sprint1AlpacaIntegration
from config import Sprint1Config
import time

def main():
    """Test the integrated dashboard launch"""
    print("🧪 Testing Sprint 1 + Alpaca + Dashboard Integration")
    print("=" * 60)
    
    try:
        # Create config
        config = Sprint1Config()
        
        # Create integration with GUI enabled
        integration = Sprint1AlpacaIntegration(launch_gui=True)
        
        print("✅ Integration system created")
        print("🚀 Testing system initialization...")
        
        # Initialize system
        if integration.initialize_system():
            print("✅ System initialized successfully")
            print("📊 Dashboard should launch in a separate window")
            print("🎯 Running one test cycle...")
            
            # Run one cycle
            cycle_result = integration.run_trading_cycle(['AAPL', 'MSFT'])
            print(f"✅ Test cycle completed: {cycle_result}")
            
            print("\n🎉 Test successful!")
            print("📱 Dashboard window should be visible")
            print("🔄 Dashboard will update every 30 seconds")
            print("⚠️  Close dashboard window or press Ctrl+C to stop")
            
            # Keep running for demo
            time.sleep(60)  # Run for 1 minute
            
        else:
            print("❌ System initialization failed")
            
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean shutdown
        if 'integration' in locals():
            integration.stop_dashboard()
        print("✅ Test completed")

if __name__ == "__main__":
    main()
