"""
Test earnings blocking logic with simulated scenarios.
"""

import logging
from datetime import datetime, timedelta
from earnings_calendar import EarningsCalendar

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("\n" + "="*80)
print("EARNINGS BLOCKING TEST")
print("="*80)

calendar = EarningsCalendar(entry_blackout_days=3, exit_buffer_days=1)

# Test 1: NVDA (12 days until earnings - should be safe)
print("\nTest 1: NVDA (Earnings Nov 19 - 12 days away)")
print("-" * 40)
should_block = calendar.should_avoid_entry('NVDA')
should_exit = calendar.should_exit_before_earnings('NVDA')
print(f"Block entry: {should_block} (expected: False)")
print(f"Force exit: {should_exit} (expected: False)")
assert should_block == False, "NVDA should allow entries (12 days out)"
assert should_exit == False, "NVDA should not force exit (12 days out)"
print("✅ PASSED")

# Test 2: Manually override for simulation
print("\nTest 2: Simulating stock 2 days before earnings")
print("-" * 40)

class MockEarningsCalendar(EarningsCalendar):
    """Mock calendar to simulate different scenarios."""
    
    def get_next_earnings_date(self, symbol):
        # Simulate earnings 2 days from now
        if symbol == 'TEST_2D':
            return datetime.now() + timedelta(days=2)
        return super().get_next_earnings_date(symbol)

mock_calendar = MockEarningsCalendar(entry_blackout_days=3, exit_buffer_days=1)

should_block = mock_calendar.should_avoid_entry('TEST_2D')
should_exit = mock_calendar.should_exit_before_earnings('TEST_2D')
print(f"Block entry: {should_block} (expected: True - within 3 day blackout)")
print(f"Force exit: {should_exit} (expected: False - outside 1 day buffer)")
assert should_block == True, "Should block entries 2 days before earnings"
assert should_exit == False, "Should not force exit yet (>1 day)"
print("✅ PASSED")

# Test 3: Same day as earnings
print("\nTest 3: Simulating earnings day (T+0)")
print("-" * 40)

class MockSameDayCalendar(EarningsCalendar):
    def get_next_earnings_date(self, symbol):
        if symbol == 'TEST_0D':
            return datetime.now()
        return super().get_next_earnings_date(symbol)

same_day_calendar = MockSameDayCalendar(entry_blackout_days=3, exit_buffer_days=1)

should_block = same_day_calendar.should_avoid_entry('TEST_0D')
should_exit = same_day_calendar.should_exit_before_earnings('TEST_0D')
print(f"Block entry: {should_block} (expected: True)")
print(f"Force exit: {should_exit} (expected: True)")
assert should_block == True, "Should block entries on earnings day"
assert should_exit == True, "Should force exit on earnings day"
print("✅ PASSED")

# Test 4: Next day (T+1 - within exit buffer)
print("\nTest 4: Simulating 1 day before earnings (T-1)")
print("-" * 40)

class MockNextDayCalendar(EarningsCalendar):
    def get_next_earnings_date(self, symbol):
        if symbol == 'TEST_1D':
            return datetime.now() + timedelta(days=1)
        return super().get_next_earnings_date(symbol)

next_day_calendar = MockNextDayCalendar(entry_blackout_days=3, exit_buffer_days=1)

should_block = next_day_calendar.should_avoid_entry('TEST_1D')
should_exit = next_day_calendar.should_exit_before_earnings('TEST_1D')
print(f"Block entry: {should_block} (expected: True)")
print(f"Force exit: {should_exit} (expected: True - within 1 day buffer)")
assert should_block == True, "Should block entries 1 day before earnings"
assert should_exit == True, "Should force exit 1 day before earnings"
print("✅ PASSED")

# Test 5: 4 days out (outside blackout window)
print("\nTest 5: Simulating 4 days before earnings (T-4)")
print("-" * 40)

class Mock4DayCalendar(EarningsCalendar):
    def get_next_earnings_date(self, symbol):
        if symbol == 'TEST_4D':
            return datetime.now() + timedelta(days=4)
        return super().get_next_earnings_date(symbol)

four_day_calendar = Mock4DayCalendar(entry_blackout_days=3, exit_buffer_days=1)

should_block = four_day_calendar.should_avoid_entry('TEST_4D')
should_exit = four_day_calendar.should_exit_before_earnings('TEST_4D')
print(f"Block entry: {should_block} (expected: False - outside 3 day blackout)")
print(f"Force exit: {should_exit} (expected: False)")
assert should_block == False, "Should allow entries 4 days before earnings"
assert should_exit == False, "Should not force exit 4 days out"
print("✅ PASSED")

print("\n" + "="*80)
print("🎉 ALL EARNINGS BLOCKING TESTS PASSED!")
print("="*80)
print("\nSummary:")
print("  ✅ Safe stocks (12+ days): Allow entries, no exits")
print("  ✅ 4 days out: Allow entries, no exits")
print("  ✅ 2-3 days out: BLOCK entries, no forced exits")
print("  ✅ 1 day out: BLOCK entries, FORCE exits")
print("  ✅ Earnings day: BLOCK entries, FORCE exits")
print("\nEarnings protection is working correctly!")
print("="*80 + "\n")
