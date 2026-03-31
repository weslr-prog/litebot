# Terminal Output Enhancements
**Date**: December 30, 2024  
**Purpose**: Enhanced visibility into bot operations during foreground execution

## What Was Changed

### 1. Enhanced Countdown Sleep (`_countdown_sleep()`)
**Location**: `bot_v2/launcher.py` lines 1062-1095

**Before**:
- Updates every 60 seconds
- Only showed minutes remaining
- No target time

**After**:
- Updates every 30 seconds for better feedback
- Shows target completion time (e.g., "until 10:45:32 AM")
- Clearer formatting with print() for immediate stdout visibility
- Shows seconds remaining when < 1 minute

**Example Output**:
```
⏰ Entry Window - Next scan in 5.0 minutes (until 10:45:32 AM)
   ... 4.5 minutes remaining (until 10:45:32 AM)
   ... 4.0 minutes remaining (until 10:45:32 AM)
   ... 3.5 minutes remaining (until 10:45:32 AM)
```

### 2. Phase Transition Announcements
**Location**: `bot_v2/launcher.py` lines 993-1000

**New Feature**: Clear phase banners when transitioning between trading phases

**Example Output**:
```
================================================================================
📍 PHASE: ENTRY_WINDOW | Time: 09:45:23 AM | Active Positions: 2
================================================================================
```

**Phases**:
- `PREMARKET` (9:00-9:30 AM) - Gap scanning
- `ENTRY_WINDOW` (9:45-10:30 AM) - Primary entry scanning
- `MIDDAY_REFRESH` (11 AM, 12 PM, 1 PM) - Additional opportunities
- `CONTINUOUS_ENTRY` (10:30 AM-2:00 PM) - Opportunistic scanning
- `MONITORING` (2:00-3:45 PM) - Exit monitoring only
- `FORCE_EXIT` (3:45-4:00 PM Friday) - Weekend closure
- `POSTMARKET` (4:00 PM+) - Watchlist refresh
- `CLOSED` - Market closed

### 3. Task Status Updates
**Location**: `bot_v2/launcher.py` throughout main loop

**New Feature**: Clear start/finish markers for all tasks

**Example Output**:
```
🔍 Running entry scan (2/7 positions)...
✅ Entry scan complete (3.2s)

👁️  Monitoring exits (2 positions)...
✅ Exit monitoring complete
```

**Status Indicators**:
- 🔍 Scanning for entries
- 👁️  Monitoring exits
- 🔄 Refreshing data
- ⚠️  Force exit window
- 💤 Market closed
- ✅ Task complete
- ⏰ Countdown timer

### 4. Error/Warning Visibility
**Location**: `logger.py` lines 28-33

**New Feature**: Separate console handler for errors and warnings

**Changes**:
- All INFO logs still go to file only (prevents duplication)
- WARNING, ERROR, and CRITICAL messages now also print to stdout
- Immediate visibility for issues without checking log file

**Example Output**:
```
WARNING - bot_v2.launcher - Failed to fetch quote for AAPL: API timeout
ERROR - bot_v2.execution_engine - Order rejected: Insufficient buying power
```

**Log Levels**:
- `INFO` - File only (normal operations, not spammy)
- `WARNING` - File + Console (potential issues)
- `ERROR` - File + Console (failures that need attention)
- `CRITICAL` - File + Console (severe problems)

## Benefits

### 1. Real-Time Visibility
- See what the bot is doing without checking log files
- Clear phase transitions prevent confusion
- Countdown timers show progress

### 2. Debugging Support
- Errors/warnings immediately visible
- Task completion timing helps identify bottlenecks
- Position counts visible at phase transitions

### 3. Confidence Building
- Regular updates confirm bot is working
- Clear status messages reduce anxiety
- No need to constantly check log files

### 4. Balanced Verbosity
- Not minute-by-minute spam
- Updates every 30 seconds during waits
- Task-based updates only when active

## Usage

### Foreground Execution (Recommended)
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python bot_v2/launcher.py
```

**Advantages**:
- See all status messages in real-time
- Errors/warnings immediately visible
- Easy Ctrl+C to stop
- Clear understanding of bot state

### Background Execution (If Needed)
```bash
nohup python bot_v2/launcher.py > bot_output.log 2>&1 &
```

**Notes**:
- Status messages written to `bot_output.log`
- Detailed logs still in `logs/sprint1_alpaca.log`
- Errors/warnings visible in both files

## Example Full Output

```
================================================================================
📍 PHASE: ENTRY_WINDOW | Time: 09:45:00 AM | Active Positions: 0
================================================================================

🔍 Running entry scan (0/7 positions)...
✅ Entry scan complete (12.3s)

⏰ Entry Window - Next scan in 5.0 minutes (until 09:50:00 AM)
   ... 4.5 minutes remaining (until 09:50:00 AM)
   ... 4.0 minutes remaining (until 09:50:00 AM)
   ... 3.5 minutes remaining (until 09:50:00 AM)
   ... 3.0 minutes remaining (until 09:50:00 AM)
   ... 2.5 minutes remaining (until 09:50:00 AM)
   ... 2.0 minutes remaining (until 09:50:00 AM)
   ... 1.5 minutes remaining (until 09:50:00 AM)
   ... 1.0 minutes remaining (until 09:50:00 AM)
   ... 30 seconds remaining

🔍 Running entry scan (2/7 positions)...
✅ Entry scan complete (8.7s)

⏰ Entry Window - Next scan in 5.0 minutes (until 09:55:00 AM)
```

## Technical Details

### Print vs Logger
- **print()**: Used for status updates (immediate stdout visibility)
- **logger.info()**: Used for detailed logging (file only, prevents spam)
- **logger.warning/error()**: Used for issues (file + console)

### sys.stdout.flush()
- Forces immediate output to terminal
- Prevents buffering delays
- Critical for real-time status updates

### Phase Tracking
- `self._last_logged_phase`: Prevents duplicate phase banners
- Only shows phase transition once per change
- Includes timestamp, phase name, and position count

## Validation

### Test 1: Phase Transitions
**Expected**: Clear banner when entering new phase
**Actual**: ✅ Banner shows phase, time, and position count

### Test 2: Countdown Updates
**Expected**: Updates every 30 seconds with target time
**Actual**: ✅ Shows remaining time and target completion time

### Test 3: Task Status
**Expected**: Start/finish messages for each task
**Actual**: ✅ Shows 🔍 start and ✅ finish with timing

### Test 4: Error Visibility
**Expected**: Warnings and errors appear on console
**Actual**: ✅ Separate handler shows WARNING+ on stdout

### Test 5: No Spam
**Expected**: Updates only when needed (not every second)
**Actual**: ✅ Task-based + 30s countdown intervals

## Future Enhancements

### Potential Additions
1. **Signal Quality Summary**: "Scanned 25 candidates → 3 signals (12% conversion)"
2. **Position Performance**: Real-time P&L updates during monitoring
3. **Exit Reason Tracking**: Count exits by reason (profit, stop, time, etc.)
4. **Daily Summary**: End-of-day recap with win rate, P&L, etc.

### Configuration Options
Consider adding verbosity levels:
- `QUIET`: Errors only
- `NORMAL`: Current behavior (default)
- `VERBOSE`: Include signal details, candidate lists

## Related Files

### Modified
- `bot_v2/launcher.py` - Enhanced countdown, phase transitions, task status
- `logger.py` - Added error/warning console handler

### Documentation
- `MEAN_REVERSION_STRATEGY_GUIDE.md` - Strategy explanation
- `FILTER_VS_STRATEGY_FLOW.md` - Execution flow with timing
- `FILTER_OPTIMIZATION_DEC29.md` - Filter optimization details

## Changelog

**December 30, 2024**:
- Enhanced `_countdown_sleep()` with 30s updates and target times
- Added phase transition banners
- Added task start/finish status messages
- Added error/warning console handler for immediate visibility
- All updates use print() + sys.stdout.flush() for real-time output

**December 29, 2024**:
- Disabled general console handler (prevents duplication with nohup)
- Basic countdown implementation

## Summary

The bot now provides clear, real-time visibility into its operations:
- **What it's doing**: Phase banners and task status
- **When it will act**: Countdown with target times
- **Any problems**: Errors/warnings immediately visible
- **No spam**: Balanced updates every 30s during waits

Perfect for foreground execution and debugging without overwhelming output.
