#!/usr/bin/env python3
"""
Manual Report Viewer
Run this script to view morning brief or daily summary with full details
"""

import sys
import datetime as dt
import pytz
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from bot_v2.data.data_loader import DataLoader
from bot_v2.execution.position_tracker import AIPositionTracker
from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.reporting import MarketBrief, DailySummary
from logger import setup_logger


def show_morning_brief():
    """Display morning market brief"""
    print("\n" + "="*80)
    print("MORNING MARKET BRIEF - Manual View")
    print("="*80)
    
    try:
        # Initialize components
        logger = setup_logger('report_viewer')
        config = ShortCycleConfig()
        data_loader = DataLoader()
        
        # Generate brief
        market_brief = MarketBrief(data_loader, logger)
        
        # Load universe
        universe_file = Path('bot_v2/data/mid_cap_universe.json')
        import json
        with open(universe_file) as f:
            data = json.load(f)
        
        universe = []
        for key, value in data.items():
            if key.lower() == 'reits' or 'reit' in key.lower():
                continue
            if isinstance(value, list):
                universe.extend(value)
        
        # Generate and print
        brief = market_brief.generate_brief(universe)
        market_brief.print_brief(brief)
        
    except Exception as e:
        print(f"\n❌ Error generating brief: {e}")
        import traceback
        traceback.print_exc()


def show_daily_summary(show_details=True):
    """Display daily summary with optional details"""
    print("\n" + "="*80)
    print("DAILY SUMMARY - Manual View")
    print("="*80)
    
    try:
        # Initialize components
        logger = setup_logger('report_viewer')
        config = ShortCycleConfig()
        data_loader = DataLoader()
        position_tracker = AIPositionTracker(config=config)
        
        # Generate summary
        daily_summary = DailySummary(data_loader, position_tracker, logger)
        
        # Use placeholder session data (real data comes from running bot)
        session_data = {
            'scans_run': 0,
            'candidates_reviewed': [],
            'signals_generated': 0,
            'entries_executed': [],
            'rejections': {}
        }
        
        # Try to load from bot's session if available
        try:
            from bot_v2.launcher import BotLauncher
            # This won't work if bot not running, but that's OK
        except:
            pass
        
        # Generate and print
        summary = daily_summary.generate_summary(session_data)
        daily_summary.print_summary(summary, show_details=show_details)
        
    except Exception as e:
        print(f"\n❌ Error generating summary: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main menu for report viewer"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['brief', 'morning']:
            show_morning_brief()
        elif command in ['summary', 'daily']:
            show_details = '--details' in sys.argv or '-d' in sys.argv
            show_daily_summary(show_details=show_details)
        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python3 view_reports.py morning     # Show morning brief")
            print("  python3 view_reports.py daily       # Show daily summary")
            print("  python3 view_reports.py daily -d    # Show daily summary with details")
    else:
        # Interactive menu
        print("\n" + "="*80)
        print("📊 REPORT VIEWER MENU")
        print("="*80)
        print("\n1. Morning Market Brief")
        print("2. Daily Summary (overview)")
        print("3. Daily Summary (with full details)")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            show_morning_brief()
        elif choice == '2':
            show_daily_summary(show_details=False)
        elif choice == '3':
            show_daily_summary(show_details=True)
        elif choice == '4':
            print("\nGoodbye!")
        else:
            print("\nInvalid choice")


if __name__ == "__main__":
    main()
