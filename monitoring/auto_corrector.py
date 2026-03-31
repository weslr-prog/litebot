#!/usr/bin/env python3
"""
Auto-Corrector System
=====================
Automatically adjusts trading parameters when issues are detected,
enabling the bot to adapt to data limitations and market conditions.

Author: LiteBotX Self-Monitoring System
Date: October 5, 2025
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Correction:
    """Represents an automatic correction action"""
    timestamp: str
    issue_type: str
    parameter: str
    old_value: any
    new_value: any
    reason: str
    success: bool
    
    def to_dict(self):
        return asdict(self)


class AutoCorrector:
    """
    Automatic parameter adjustment system that responds to detected issues
    by progressively relaxing filters and adjusting thresholds.
    """
    
    def __init__(self, config_file: str = "monitoring/auto_config.json",
                 history_file: str = "monitoring/correction_history.json"):
        
        self.config_file = Path(config_file)
        self.history_file = Path(history_file)
        
        # Ensure directories exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Load correction history
        self.correction_history = self._load_history()
        
        # Safety limits - never adjust beyond these
        self.min_safe_min_rows = 15  # Never go below 15 days of data
        self.min_safe_volume = 20_000  # Never go below 20k volume
        self.max_adjustments_per_day = 3  # Max 3 auto-corrections per day
        
    def apply_corrections(self, health_report: Dict) -> List[Correction]:
        """
        Apply automatic corrections based on health report issues.
        
        Args:
            health_report: Health report from DailyHealthChecker
            
        Returns:
            List of corrections applied
        """
        self.logger.info("🔧 Analyzing issues for auto-correction...")
        
        corrections = []
        issues = health_report.get('issues', [])
        
        # Check daily correction limit
        today = datetime.now().strftime("%Y-%m-%d")
        today_corrections = sum(
            1 for c in self.correction_history
            if c['timestamp'].startswith(today)
        )
        
        if today_corrections >= self.max_adjustments_per_day:
            self.logger.warning(
                f"⚠️ Daily correction limit reached ({today_corrections}/{self.max_adjustments_per_day})"
            )
            return corrections
        
        for issue in issues:
            if not issue.get('auto_fixable', False):
                continue
            
            issue_type = issue['issue_type']
            
            if issue_type == 'NO_TRADES' or issue_type == 'FILTER_FAILURE':
                # Try to relax filters
                correction = self._fix_filter_issue(health_report['metrics'])
                if correction:
                    corrections.append(correction)
                    
            elif issue_type == 'NO_SIGNALS':
                # Check pre-filter settings
                correction = self._fix_signal_generation(health_report['metrics'])
                if correction:
                    corrections.append(correction)
        
        # Save all corrections
        for correction in corrections:
            self._record_correction(correction)
        
        # Log summary
        if corrections:
            self.logger.info(f"✅ Applied {len(corrections)} auto-corrections")
            for c in corrections:
                self.logger.info(f"  • {c.parameter}: {c.old_value} → {c.new_value}")
        else:
            self.logger.info("ℹ️ No auto-corrections needed")
        
        return corrections
    
    def _fix_filter_issue(self, metrics: Dict) -> Optional[Correction]:
        """Fix pre-filter returning too few candidates"""
        
        # Identify the primary bottleneck
        prefilter_candidates = metrics.get('prefilter_candidates', 0)
        
        if prefilter_candidates == 0:
            self.logger.warning("🔧 Pre-filter returned 0 candidates - relaxing data requirements")
            
            # Strategy: Relax data completeness filter
            correction = self._relax_data_completeness()
            
            if correction:
                return correction
        
        elif prefilter_candidates < 10:
            self.logger.warning(f"🔧 Pre-filter returned only {prefilter_candidates} - relaxing liquidity")
            
            # Strategy: Relax liquidity filter
            correction = self._relax_liquidity_filter()
            
            if correction:
                return correction
        
        return None
    
    def _relax_data_completeness(self) -> Optional[Correction]:
        """Reduce min_rows requirement for data completeness"""
        
        # Read current setting from pre_filter.py
        prefilter_file = Path("pre_filter.py")
        
        if not prefilter_file.exists():
            self.logger.error("❌ pre_filter.py not found")
            return None
        
        try:
            with open(prefilter_file, 'r') as f:
                content = f.read()
            
            # Find current min_rows setting
            import re
            pattern = r'min_rows=(\d+)'
            matches = re.findall(pattern, content)
            
            if not matches:
                self.logger.error("❌ Could not find min_rows in pre_filter.py")
                return None
            
            current_min_rows = int(matches[0])  # Get first occurrence
            
            # Calculate new value (reduce by 5, minimum 15)
            new_min_rows = max(self.min_safe_min_rows, current_min_rows - 5)
            
            if new_min_rows == current_min_rows:
                self.logger.warning(f"⚠️ Already at minimum safe limit (min_rows={current_min_rows})")
                return None
            
            # Apply correction
            new_content = re.sub(
                r'min_rows=\d+',
                f'min_rows={new_min_rows}',
                content,
                count=2  # Update first 2 occurrences
            )
            
            with open(prefilter_file, 'w') as f:
                f.write(new_content)
            
            correction = Correction(
                timestamp=datetime.now().isoformat(),
                issue_type='FILTER_FAILURE',
                parameter='min_rows',
                old_value=current_min_rows,
                new_value=new_min_rows,
                reason='Pre-filter returned insufficient candidates - relaxing data requirement',
                success=True
            )
            
            self.logger.info(f"✅ Adjusted min_rows: {current_min_rows} → {new_min_rows}")
            
            return correction
        
        except Exception as e:
            self.logger.error(f"❌ Error adjusting min_rows: {e}")
            return None
    
    def _relax_liquidity_filter(self) -> Optional[Correction]:
        """Reduce liquidity requirements"""
        
        prefilter_file = Path("pre_filter.py")
        
        if not prefilter_file.exists():
            return None
        
        try:
            with open(prefilter_file, 'r') as f:
                content = f.read()
            
            # Find current min_avg_volume
            import re
            pattern = r'min_avg_volume=(\d+)'
            matches = re.findall(pattern, content)
            
            if not matches:
                return None
            
            current_volume = int(matches[0])
            
            # Reduce by 30%, minimum safety limit
            new_volume = max(self.min_safe_volume, int(current_volume * 0.7))
            
            if new_volume == current_volume:
                return None
            
            # Apply correction
            new_content = re.sub(
                r'min_avg_volume=\d+',
                f'min_avg_volume={new_volume}',
                content,
                count=1
            )
            
            with open(prefilter_file, 'w') as f:
                f.write(new_content)
            
            correction = Correction(
                timestamp=datetime.now().isoformat(),
                issue_type='FILTER_FAILURE',
                parameter='min_avg_volume',
                old_value=current_volume,
                new_value=new_volume,
                reason='Insufficient candidates - relaxing liquidity requirements',
                success=True
            )
            
            self.logger.info(f"✅ Adjusted min_avg_volume: {current_volume:,} → {new_volume:,}")
            
            return correction
        
        except Exception as e:
            self.logger.error(f"❌ Error adjusting liquidity: {e}")
            return None
    
    def _fix_signal_generation(self, metrics: Dict) -> Optional[Correction]:
        """Fix issues with signal generation"""
        
        # If no signals generated, check if it's a scheduling issue
        signals_generated = metrics.get('signals_generated', 0)
        
        if signals_generated == 0:
            self.logger.warning("🔧 No signals generated - may be a timing/scheduling issue")
            
            # Check if pre-filter ran
            if metrics.get('prefilter_candidates', 0) == 0:
                # Already handled by filter issue
                return None
            
            # Log diagnostic info
            correction = Correction(
                timestamp=datetime.now().isoformat(),
                issue_type='NO_SIGNALS',
                parameter='diagnostic',
                old_value='no_signals',
                new_value='logged_diagnostic',
                reason='No signals generated despite candidates available - check signal logic',
                success=True
            )
            
            return correction
        
        return None
    
    def _load_history(self) -> List[Dict]:
        """Load correction history"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load history: {e}")
            return []
    
    def _record_correction(self, correction: Correction):
        """Record correction in history"""
        self.correction_history.append(correction.to_dict())
        
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.correction_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving history: {e}")
    
    def get_correction_summary(self, days: int = 7) -> Dict:
        """Get summary of recent corrections"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        recent = [
            c for c in self.correction_history
            if datetime.fromisoformat(c['timestamp']).timestamp() > cutoff
        ]
        
        # Group by parameter
        by_parameter = {}
        for c in recent:
            param = c['parameter']
            if param not in by_parameter:
                by_parameter[param] = []
            by_parameter[param].append(c)
        
        summary = {
            'period_days': days,
            'total_corrections': len(recent),
            'successful_corrections': sum(1 for c in recent if c['success']),
            'by_parameter': {
                param: {
                    'count': len(corrections),
                    'latest': corrections[-1] if corrections else None
                }
                for param, corrections in by_parameter.items()
            }
        }
        
        return summary


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Test auto-corrector
    corrector = AutoCorrector()
    
    # Get recent corrections
    summary = corrector.get_correction_summary()
    
    print("\n🔧 AUTO-CORRECTOR STATUS")
    print("=" * 60)
    print(f"Total corrections (7 days): {summary['total_corrections']}")
    print(f"Successful: {summary['successful_corrections']}")
    
    if summary['by_parameter']:
        print("\nRecent Adjustments:")
        for param, info in summary['by_parameter'].items():
            print(f"  • {param}: {info['count']} adjustments")
            if info['latest']:
                latest = info['latest']
                print(f"    Last: {latest['old_value']} → {latest['new_value']}")
    
    print("=" * 60)
