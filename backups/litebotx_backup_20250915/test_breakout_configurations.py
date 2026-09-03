#!/usr/bin/env python3
"""
Test script to compare different breakout filter configurations
"""

import logging
from dynamic_watchlist_generator import DynamicWatchlistGenerator, WatchlistConfig

def test_breakout_configurations():
    """Test different breakout filter configurations and compare results"""

    print("🧪 Breakout Filter Configuration Test")
    print("=" * 60)

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Create generator
    config = WatchlistConfig(
        max_watchlist_size=15,
        min_watchlist_size=5,
        save_to_config=False,
        save_to_file=False  # Don't save during testing
    )

    generator = DynamicWatchlistGenerator(config)

    # Define test configurations
    test_configs = [
        {
            'name': 'Original Strict',
            'params': {'volume_multiplier': 1.5, 'price_breakout_pct': 2.0, 'lookback_days': 10},
            'description': 'Original strict criteria - fewest assets'
        },
        {
            'name': 'Medium Lenient',
            'params': {'volume_multiplier': 1.2, 'price_breakout_pct': 1.0, 'lookback_days': 15},
            'description': 'Balanced approach - good for swing trading'
        },
        {
            'name': 'Very Lenient',
            'params': {'volume_multiplier': 1.1, 'price_breakout_pct': 0.5, 'lookback_days': 20},
            'description': 'Most inclusive - more assets but less selective'
        }
    ]

    results = {}

    print("\n📊 Testing Configurations:")
    print("-" * 60)

    for i, config in enumerate(test_configs, 1):
        print(f"\n{i}. {config['name']}")
        print(f"   Description: {config['description']}")
        print(f"   Parameters: {config['params']}")
        print("   Testing...")
        # Test the configuration
        try:
            result = generator.run_daily_generation(breakout_params=config['params'])

            results[config['name']] = {
                'params': config['params'],
                'watchlist': result['watchlist'],
                'count': len(result['watchlist']),
                'success': result['success'],
                'message': result['message']
            }

            print(f"   ✅ Success: {result['success']}")
            print(f"   📈 Symbols: {len(result['watchlist'])}")
            print(f"   📋 Sample: {result['watchlist'][:5]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[config['name']] = {'error': str(e)}

    # Summary comparison
    print("\n📊 Configuration Comparison:")
    print("-" * 60)
    print(f"{'Configuration':<15} {'Symbols':<10} {'Volume Mult':<12} {'Price %':<10} {'Lookback':<10}")
    print("-" * 60)

    for config_name, result in results.items():
        if 'error' not in result:
            params = result['params']
            print(f"{config_name:<15} {result['count']:<10} {params['volume_multiplier']:<12} {params['price_breakout_pct']:<10} {params['lookback_days']:<10}")
        else:
            print(f"{config_name:<15} {'ERROR':<10}")

    # Recommendation
    print("\n🎯 Recommendation:")
    print("-" * 60)

    if results:
        # Find the configuration with the most symbols (but not the most lenient)
        best_config = None
        max_symbols = 0

        for config_name, result in results.items():
            if 'count' in result and result['count'] > max_symbols and config_name != 'Very Lenient':
                max_symbols = result['count']
                best_config = config_name

        if best_config:
            print(f"Recommended: {best_config}")
            print(f"   - Provides {max_symbols} symbols")
            print(f"   - Good balance of selectivity and opportunity")
        else:
            print("Recommended: Medium Lenient (balanced approach)")

    return results

def run_single_test(config_name: str, params: dict):
    """Run a single test with specific parameters"""
    print(f"\n🧪 Running single test: {config_name}")
    print(f"Parameters: {params}")

    config = WatchlistConfig(
        max_watchlist_size=15,
        min_watchlist_size=5,
        save_to_config=False,
        save_to_file=False
    )

    generator = DynamicWatchlistGenerator(config)
    result = generator.run_daily_generation(breakout_params=params)

    print(f"Success: {result['success']}")
    print(f"Symbols found: {len(result['watchlist'])}")
    print(f"Watchlist: {result['watchlist']}")

    return result

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run single test
        config_name = sys.argv[1]
        if config_name == "strict":
            run_single_test("Strict", {'volume_multiplier': 1.5, 'price_breakout_pct': 2.0, 'lookback_days': 10})
        elif config_name == "medium":
            run_single_test("Medium", {'volume_multiplier': 1.2, 'price_breakout_pct': 1.0, 'lookback_days': 15})
        elif config_name == "lenient":
            run_single_test("Lenient", {'volume_multiplier': 1.1, 'price_breakout_pct': 0.5, 'lookback_days': 20})
    else:
        # Run full comparison
        test_breakout_configurations()
