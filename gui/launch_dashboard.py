#!/usr/bin/env python3
"""
Launch Script for LitebotX Dashboard
Simple launcher with dependency checking and error handling
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are available"""
    required_modules = ['tkinter', 'pandas', 'numpy']
    optional_modules = ['matplotlib']
    
    missing_required = []
    missing_optional = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_required.append(module)
    
    for module in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(module)
    
    return missing_required, missing_optional

def install_dependencies(modules):
    """Install missing dependencies"""
    if not modules:
        return True
    
    print(f"📦 Installing missing dependencies: {', '.join(modules)}")
    
    for module in modules:
        try:
            if module == 'tkinter':
                print("⚠️  tkinter is usually built into Python. If missing, please install python3-tk")
                continue
            
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', module])
            print(f"✅ {module} installed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {module}")
            return False
    
    return True

def launch_dashboard():
    """Launch the LitebotX dashboard"""
    # Get the directory of this script
    script_dir = Path(__file__).parent
    dashboard_path = script_dir / 'enhanced_trading_dashboard.py'
    
    # Check if dashboard file exists
    if not dashboard_path.exists():
        print("❌ Dashboard file not found!")
        print(f"Expected location: {dashboard_path}")
        return False
    
    print("🚀 Launching LitebotX Dashboard...")
    
    try:
        # Import and run the dashboard
        sys.path.insert(0, str(script_dir))
        from enhanced_trading_dashboard import main
        main()
        return True
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        return False

def main():
    """Main launcher function"""
    print("=" * 60)
    print("🚀 LiteBotX Dashboard Launcher")
    print("=" * 60)
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    missing_required, missing_optional = check_dependencies()
    
    if missing_required:
        print(f"❌ Missing required dependencies: {', '.join(missing_required)}")
        
        # Ask user if they want to install
        response = input("Would you like to install missing dependencies? (y/n): ")
        if response.lower() in ['y', 'yes']:
            if not install_dependencies(missing_required):
                print("❌ Failed to install required dependencies. Exiting.")
                return
        else:
            print("❌ Cannot continue without required dependencies. Exiting.")
            return
    
    if missing_optional:
        print(f"⚠️  Missing optional dependencies: {', '.join(missing_optional)}")
        print("Dashboard will work without these, but some features may be limited.")
        
        response = input("Would you like to install optional dependencies? (y/n): ")
        if response.lower() in ['y', 'yes']:
            install_dependencies(missing_optional)
    
    print("✅ Dependencies checked!")
    
    # Launch dashboard
    print("\n📊 Starting dashboard...")
    success = launch_dashboard()
    
    if success:
        print("✅ Dashboard launched successfully!")
    else:
        print("❌ Failed to launch dashboard")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you're in the correct directory")
        print("2. Check that all trading bot files are present")
        print("3. Verify Python environment is set up correctly")
        print("4. Try running: python3 enhanced_trading_dashboard.py")

def quick_launch():
    """Quick launch without dependency checks (for development)"""
    print("🚀 Quick launching dashboard...")
    launch_dashboard()

if __name__ == "__main__":
    # Check if user wants quick launch
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_launch()
    else:
        main()