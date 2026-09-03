#!/usr/bin/env python3
"""
Short-Cycle Safety & Monitoring Framework
=========================================

Comprehensive safety systems for short-cycle trading with kill switches,
explainability logging, risk monitoring, and regulatory compliance.

Key Features:
- Real-time kill switches for daily/weekly loss limits
- Comprehensive trade explainability logging
- Risk monitoring and alerts
- Performance degradation detection
- Regulatory compliance logging
- Paper trading validation framework

Author: LiteBotX Team
Version: 1.0 (Sprint 0)
"""

import os
import sys
import json
import logging
import datetime as dt
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


class AlertLevel(Enum):
	"""Alert severity levels"""
	INFO = "info"
	WARNING = "warning" 
	CRITICAL = "critical"
	EMERGENCY = "emergency"


class KillSwitchType(Enum):
	"""Types of kill switches"""
	DAILY_LOSS = "daily_loss"
	WEEKLY_LOSS = "weekly_loss"
	DRAWDOWN = "drawdown"
	POSITION_LIMIT = "position_limit"
	SYSTEM_ERROR = "system_error"
	MARKET_CONDITION = "market_condition"
	PERFORMANCE_DECAY = "performance_decay"


@dataclass
class SafetyConfig:
	"""Configuration for safety and monitoring systems"""
	# Loss limits
	max_daily_loss_pct: float = 0.008  # 0.8% of portfolio
	max_weekly_loss_pct: float = 0.025  # 2.5% of portfolio
	max_drawdown_pct: float = 0.10  # 10% maximum drawdown
    
	# Position limits
	max_portfolio_concentration: float = 0.50  # 50% max in positions
	max_single_position_pct: float = 0.15  # 15% max single position
	max_sector_concentration: float = 0.40  # 40% max in single sector
    
	# Performance monitoring
	min_win_rate_threshold: float = 0.40  # 40% minimum win rate
	min_profit_factor_threshold: float = 1.0  # 1.0 minimum profit factor
	performance_decay_threshold: float = 0.30  # 30% performance decay
    
	# System monitoring
	max_consecutive_losses: int = 5
	max_system_errors_per_day: int = 3
	position_update_timeout_seconds: int = 30
    
	# Alerting
	enable_email_alerts: bool = False
	email_recipients: List[str] = field(default_factory=list)
	alert_cooldown_minutes: int = 15
    
	# Logging
	enable_explainability_logging: bool = True
	enable_regulatory_logging: bool = True
	log_retention_days: int = 90
	detailed_logging: bool = True


@dataclass
class RiskAlert:
	"""Risk alert structure"""
	timestamp: dt.datetime
	alert_level: AlertLevel
	alert_type: str
	message: str
	current_value: float
	threshold_value: float
	recommended_action: str
	auto_executed: bool = False


@dataclass
class KillSwitch:
	"""Kill switch state and configuration"""
	switch_type: KillSwitchType
	is_active: bool
	trigger_timestamp: Optional[dt.datetime]
	trigger_value: Optional[float]
	threshold_value: float
	reason: str
	auto_recovery: bool = False
	recovery_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplainabilityLog:
	"""Detailed trade explanation for regulatory compliance"""
	timestamp: dt.datetime
	trade_id: str
	symbol: str
	action: str  # ENTRY, EXIT, HOLD
    
	# AI Decision components
	ai_confidence: float
	ai_features: Dict[str, float]
	ai_model_version: str
    
	# Risk assessment
	position_risk: float
	portfolio_risk: float
	risk_factors: List[str]
    
	# Market conditions
	market_regime: str
	volatility_level: float
	liquidity_score: float
    
	# Regulatory info
	decision_timestamp: dt.datetime
	human_override: bool
	compliance_notes: str


class SafetyMonitor:
	"""Comprehensive safety monitoring and kill switch system"""
    
	def __init__(self, config: SafetyConfig, portfolio_value: float):
		self.config = config
		self.portfolio_value = portfolio_value
		self.logger = self._setup_logging()
        
		# Kill switches
		self.kill_switches: Dict[KillSwitchType, KillSwitch] = {}
		self._initialize_kill_switches()
        
		# Monitoring state
		self.daily_pnl = 0.0
		self.weekly_pnl = 0.0
		self.current_drawdown = 0.0
		self.consecutive_losses = 0
		self.system_errors_today = 0
		self.last_alert_times: Dict[str, dt.datetime] = {}
        
		# Performance tracking
		self.performance_metrics = {
			"win_rate": 0.0,
			"profit_factor": 0.0,
			"recent_trades": [],
			"baseline_performance": None
		}
        
		# Create logging directories
		self.log_dir = Path("logs/safety_monitoring")
		self.explainability_dir = Path("logs/explainability")
		self.regulatory_dir = Path("logs/regulatory")
        
		for directory in [self.log_dir, self.explainability_dir, self.regulatory_dir]:
			directory.mkdir(parents=True, exist_ok=True)
    
	def _setup_logging(self) -> logging.Logger:
		"""Setup comprehensive logging system"""
		logger = logging.getLogger("SafetyMonitor")
		if not logger.handlers:
			# Console handler
			console_handler = logging.StreamHandler()
			console_formatter = logging.Formatter(
				'%(asctime)s - SAFETY - %(levelname)s - %(message)s'
			)
			console_handler.setFormatter(console_formatter)
			logger.addHandler(console_handler)
            
			# File handler for safety logs
			safety_log_file = Path("logs/safety_monitoring/safety.log")
			safety_log_file.parent.mkdir(parents=True, exist_ok=True)
            
			file_handler = logging.FileHandler(safety_log_file)
			file_formatter = logging.Formatter(
				'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
			)
			file_handler.setFormatter(file_formatter)
			logger.addHandler(file_handler)
            
			logger.setLevel(logging.INFO)
        
		return logger
    
	def _initialize_kill_switches(self):
		"""Initialize all kill switches"""
		# Daily loss kill switch
		self.kill_switches[KillSwitchType.DAILY_LOSS] = KillSwitch(
			switch_type=KillSwitchType.DAILY_LOSS,
			is_active=False,
			trigger_timestamp=None,
			trigger_value=None,
			threshold_value=self.portfolio_value * self.config.max_daily_loss_pct,
			reason="",
			auto_recovery=True,
			recovery_conditions={"new_trading_day": True}
		)
        
		# Weekly loss kill switch
		self.kill_switches[KillSwitchType.WEEKLY_LOSS] = KillSwitch(
			switch_type=KillSwitchType.WEEKLY_LOSS,
			is_active=False,
			trigger_timestamp=None,
			trigger_value=None,
			threshold_value=self.portfolio_value * self.config.max_weekly_loss_pct,
			reason="",
			auto_recovery=True,
			recovery_conditions={"new_trading_week": True}
		)
        
		# Drawdown kill switch
		self.kill_switches[KillSwitchType.DRAWDOWN] = KillSwitch(
			switch_type=KillSwitchType.DRAWDOWN,
			is_active=False,
			trigger_timestamp=None,
			trigger_value=None,
			threshold_value=self.config.max_drawdown_pct,
			reason="",
			auto_recovery=False
		)
        
		# System error kill switch
		self.kill_switches[KillSwitchType.SYSTEM_ERROR] = KillSwitch(
			switch_type=KillSwitchType.SYSTEM_ERROR,
			is_active=False,
			trigger_timestamp=None,
			trigger_value=None,
			threshold_value=self.config.max_system_errors_per_day,
			reason="",
			auto_recovery=True,
			recovery_conditions={"manual_reset": True}
		)
        
		self.logger.info("🛡️ Kill switches initialized")
    
	def check_safety_conditions(self, current_positions: List[Any], daily_pnl: float, 
							   weekly_pnl: float, recent_trades: List[Any]) -> Dict[str, Any]:
		"""Comprehensive safety check - returns status and any triggered alerts"""
        
		safety_status = {
			"safe_to_trade": True,
			"active_kill_switches": [],
			"warnings": [],
			"alerts": [],
			"recommendations": []
		}
        
		try:
			# Update internal state
			self.daily_pnl = daily_pnl
			self.weekly_pnl = weekly_pnl
			self.performance_metrics["recent_trades"] = recent_trades[-20:]  # Last 20 trades
            
			# Check each safety condition
			self._check_loss_limits(safety_status)
			self._check_position_limits(current_positions, safety_status)
			self._check_performance_degradation(recent_trades, safety_status)
			self._check_system_health(safety_status)
            
			# Update kill switches
			self._update_kill_switches(safety_status)
            
			# Check if any kill switches are active
			active_switches = [ks for ks in self.kill_switches.values() if ks.is_active]
			if active_switches:
				safety_status["safe_to_trade"] = False
				safety_status["active_kill_switches"] = [ks.switch_type.value for ks in active_switches]
            
			# Log safety check
			self._log_safety_check(safety_status)
            
			return safety_status
            
		except Exception as e:
			self.logger.error(f"❌ Error in safety check: {e}")
			self._record_system_error("safety_check_error", str(e))
			safety_status["safe_to_trade"] = False
			safety_status["warnings"].append("Safety check system error")
			return safety_status
    
	def _check_loss_limits(self, safety_status: Dict[str, Any]):
		"""Check daily and weekly loss limits"""
		# Daily loss check
		daily_loss_amount = abs(self.daily_pnl) if self.daily_pnl < 0 else 0
		daily_threshold = self.kill_switches[KillSwitchType.DAILY_LOSS].threshold_value
        
		if daily_loss_amount > daily_threshold:
			alert = RiskAlert(
				timestamp=dt.datetime.now(),
				alert_level=AlertLevel.CRITICAL,
				alert_type="DAILY_LOSS_LIMIT",
				message=f"Daily loss ${daily_loss_amount:.2f} exceeds limit ${daily_threshold:.2f}",
				current_value=daily_loss_amount,
				threshold_value=daily_threshold,
				recommended_action="STOP_TRADING_TODAY",
				auto_executed=True
			)
			safety_status["alerts"].append(alert)
			self._trigger_kill_switch(KillSwitchType.DAILY_LOSS, daily_loss_amount, 
									f"Daily loss limit exceeded: ${daily_loss_amount:.2f}")
        
		# Weekly loss check
		weekly_loss_amount = abs(self.weekly_pnl) if self.weekly_pnl < 0 else 0
		weekly_threshold = self.kill_switches[KillSwitchType.WEEKLY_LOSS].threshold_value
        
		if weekly_loss_amount > weekly_threshold:
			alert = RiskAlert(
				timestamp=dt.datetime.now(),
				alert_level=AlertLevel.EMERGENCY,
				alert_type="WEEKLY_LOSS_LIMIT",
				message=f"Weekly loss ${weekly_loss_amount:.2f} exceeds limit ${weekly_threshold:.2f}",
				current_value=weekly_loss_amount,
				threshold_value=weekly_threshold,
				recommended_action="STOP_TRADING_THIS_WEEK",
				auto_executed=True
			)
			safety_status["alerts"].append(alert)
			self._trigger_kill_switch(KillSwitchType.WEEKLY_LOSS, weekly_loss_amount,
									f"Weekly loss limit exceeded: ${weekly_loss_amount:.2f}")
        
		# Warning levels (80% of limits)
		if daily_loss_amount > daily_threshold * 0.8:
			safety_status["warnings"].append(f"Daily loss approaching limit: ${daily_loss_amount:.2f}")
        
		if weekly_loss_amount > weekly_threshold * 0.8:
			safety_status["warnings"].append(f"Weekly loss approaching limit: ${weekly_loss_amount:.2f}")
    
	def _check_position_limits(self, current_positions: List[Any], safety_status: Dict[str, Any]):
		"""Check position concentration and limits"""
		if not current_positions:
			return
        
		try:
			# Calculate total position value
			total_position_value = sum(getattr(pos, 'position_size_dollars', 0) for pos in current_positions)
			position_concentration = total_position_value / self.portfolio_value
            
			# Check portfolio concentration
			if position_concentration > self.config.max_portfolio_concentration:
				safety_status["warnings"].append(
					f"High portfolio concentration: {position_concentration:.1%} "
					f"(limit: {self.config.max_portfolio_concentration:.1%})"
				)
            
			# Check individual position sizes
			for pos in current_positions:
				pos_size_pct = getattr(pos, 'position_size_dollars', 0) / self.portfolio_value
				if pos_size_pct > self.config.max_single_position_pct:
					safety_status["warnings"].append(
						f"Large position {getattr(pos, 'symbol', 'UNKNOWN')}: "
						f"{pos_size_pct:.1%} (limit: {self.config.max_single_position_pct:.1%})"
					)
            
			# Check sector concentration (simplified)
			sector_exposure = self._calculate_sector_exposure(current_positions)
			for sector, exposure in sector_exposure.items():
				if exposure > self.config.max_sector_concentration:
					safety_status["warnings"].append(
						f"High {sector} sector exposure: {exposure:.1%} "
						f"(limit: {self.config.max_sector_concentration:.1%})"
					)
                    
		except Exception as e:
			self.logger.error(f"Error checking position limits: {e}")
			safety_status["warnings"].append("Position limit check failed")
    
	def _check_performance_degradation(self, recent_trades: List[Any], safety_status: Dict[str, Any]):
		"""Check for performance degradation"""
		if len(recent_trades) < 10:  # Need minimum trades for analysis
			return
        
		try:
			# Calculate recent performance metrics
			recent_10 = recent_trades[-10:]
			winning_trades = [t for t in recent_10 if getattr(t, 'net_pnl', 0) > 0]
            
			current_win_rate = len(winning_trades) / len(recent_10)
            
			# Check win rate
			if current_win_rate < self.config.min_win_rate_threshold:
				alert = RiskAlert(
					timestamp=dt.datetime.now(),
					alert_level=AlertLevel.WARNING,
					alert_type="LOW_WIN_RATE",
					message=f"Win rate {current_win_rate:.1%} below threshold {self.config.min_win_rate_threshold:.1%}",
					current_value=current_win_rate,
					threshold_value=self.config.min_win_rate_threshold,
					recommended_action="REDUCE_POSITION_SIZE"
				)
				safety_status["alerts"].append(alert)
            
			# Check consecutive losses
			consecutive_losses = 0
			for trade in reversed(recent_trades):
				if getattr(trade, 'net_pnl', 0) <= 0:
					consecutive_losses += 1
				else:
					break
            
			if consecutive_losses >= self.config.max_consecutive_losses:
				alert = RiskAlert(
					timestamp=dt.datetime.now(),
					alert_level=AlertLevel.CRITICAL,
					alert_type="CONSECUTIVE_LOSSES",
					message=f"{consecutive_losses} consecutive losses (limit: {self.config.max_consecutive_losses})",
					current_value=consecutive_losses,
					threshold_value=self.config.max_consecutive_losses,
					recommended_action="PAUSE_TRADING",
					auto_executed=True
				)
				safety_status["alerts"].append(alert)
				self._trigger_kill_switch(KillSwitchType.PERFORMANCE_DECAY, consecutive_losses,
										f"Too many consecutive losses: {consecutive_losses}")
            
			# Update performance metrics
			self.performance_metrics.update({
				"win_rate": current_win_rate,
				"consecutive_losses": consecutive_losses
			})
            
		except Exception as e:
			self.logger.error(f"Error checking performance degradation: {e}")
    
	def _check_system_health(self, safety_status: Dict[str, Any]):
		"""Check system health indicators"""
		# System errors check
		if self.system_errors_today >= self.config.max_system_errors_per_day:
			safety_status["warnings"].append(
				f"High system error count: {self.system_errors_today}"
			)
			self._trigger_kill_switch(KillSwitchType.SYSTEM_ERROR, self.system_errors_today,
									f"Too many system errors: {self.system_errors_today}")
    
	def _calculate_sector_exposure(self, positions: List[Any]) -> Dict[str, float]:
		"""Calculate sector exposure (simplified mapping)"""
		# Simplified sector mapping for Sprint 0
		tech_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        
		sector_exposure = {"TECH": 0.0, "OTHER": 0.0}
		total_value = sum(getattr(pos, 'position_size_dollars', 0) for pos in positions)
        
		if total_value == 0:
			return sector_exposure
        
		for pos in positions:
			symbol = getattr(pos, 'symbol', '')
			pos_value = getattr(pos, 'position_size_dollars', 0)
			pos_weight = pos_value / total_value
            
			if symbol in tech_symbols:
				sector_exposure["TECH"] += pos_weight
			else:
				sector_exposure["OTHER"] += pos_weight
        
		return sector_exposure
    
	def _trigger_kill_switch(self, switch_type: KillSwitchType, trigger_value: float, reason: str):
		"""Trigger a kill switch"""
		kill_switch = self.kill_switches[switch_type]
        
		if not kill_switch.is_active:
			kill_switch.is_active = True
			kill_switch.trigger_timestamp = dt.datetime.now()
			kill_switch.trigger_value = trigger_value
			kill_switch.reason = reason
            
			self.logger.critical(f"🛑 KILL SWITCH ACTIVATED: {switch_type.value} - {reason}")
            
			# Send alert
			self._send_alert(AlertLevel.CRITICAL, f"Kill switch activated: {switch_type.value}", reason)
            
			# Log to regulatory file
			self._log_regulatory_event("KILL_SWITCH_ACTIVATED", {
				"switch_type": switch_type.value,
				"trigger_value": trigger_value,
				"reason": reason,
				"timestamp": dt.datetime.now().isoformat()
			})
    
	def _update_kill_switches(self, safety_status: Dict[str, Any]):
		"""Update kill switch states and check for auto-recovery"""
		for switch_type, kill_switch in self.kill_switches.items():
			if kill_switch.is_active and kill_switch.auto_recovery:
				if self._check_recovery_conditions(kill_switch):
					self._recover_kill_switch(switch_type)
    
	def _check_recovery_conditions(self, kill_switch: KillSwitch) -> bool:
		"""Check if kill switch recovery conditions are met"""
		if not kill_switch.recovery_conditions:
			return False
        
		# Check for new trading day recovery
		if kill_switch.recovery_conditions.get("new_trading_day"):
			if kill_switch.trigger_timestamp:
				trigger_date = kill_switch.trigger_timestamp.date()
				current_date = dt.date.today()
				if current_date > trigger_date and current_date.weekday() < 5:
					return True
        
		# Check for new trading week recovery
		if kill_switch.recovery_conditions.get("new_trading_week"):
			if kill_switch.trigger_timestamp:
				trigger_week = kill_switch.trigger_timestamp.isocalendar()[1]
				current_week = dt.datetime.now().isocalendar()[1]
				if current_week > trigger_week:
					return True
        
		return False
    
	def _recover_kill_switch(self, switch_type: KillSwitchType):
		"""Recover a kill switch"""
		kill_switch = self.kill_switches[switch_type]
		kill_switch.is_active = False
        
		self.logger.info(f"✅ Kill switch recovered: {switch_type.value}")
        
		# Reset related counters
		if switch_type == KillSwitchType.DAILY_LOSS:
			self.daily_pnl = 0.0
		elif switch_type == KillSwitchType.WEEKLY_LOSS:
			self.weekly_pnl = 0.0
		elif switch_type == KillSwitchType.SYSTEM_ERROR:
			self.system_errors_today = 0
    
	def log_trade_explanation(self, trade_id: str, symbol: str, action: str, 
							ai_decision: Dict[str, Any], risk_assessment: Dict[str, Any],
							market_conditions: Dict[str, Any]) -> str:
		"""Log comprehensive trade explanation for regulatory compliance"""
        
		if not self.config.enable_explainability_logging:
			return ""
        
		try:
			explanation = ExplainabilityLog(
				timestamp=dt.datetime.now(),
				trade_id=trade_id,
				symbol=symbol,
				action=action,
				ai_confidence=ai_decision.get("confidence", 0.0),
				ai_features=ai_decision.get("features", {}),
				ai_model_version=ai_decision.get("model_version", "v1.0"),
				position_risk=risk_assessment.get("position_risk", 0.0),
				portfolio_risk=risk_assessment.get("portfolio_risk", 0.0),
				risk_factors=risk_assessment.get("risk_factors", []),
				market_regime=market_conditions.get("regime", "UNKNOWN"),
				volatility_level=market_conditions.get("volatility", 0.0),
				liquidity_score=market_conditions.get("liquidity", 1.0),
				decision_timestamp=dt.datetime.now(),
				human_override=False,
				compliance_notes=""
			)
            
			# Save to explainability log
			log_file = self.explainability_dir / f"explanations_{dt.date.today().isoformat()}.jsonl"
            
			with open(log_file, "a") as f:
				f.write(json.dumps(asdict(explanation), default=str) + "\n")
            
			# Create human-readable explanation
			readable_explanation = self._create_readable_explanation(explanation)
            
			self.logger.info(f"📝 Trade explanation logged: {trade_id}")
			return readable_explanation
            
		except Exception as e:
			self.logger.error(f"Failed to log trade explanation: {e}")
			return f"Error logging explanation: {e}"
    
	def _create_readable_explanation(self, explanation: ExplainabilityLog) -> str:
		"""Create human-readable trade explanation"""
		readable = f"""
TRADE EXPLANATION - {explanation.trade_id}
Symbol: {explanation.symbol}
Action: {explanation.action}
Timestamp: {explanation.timestamp}

AI DECISION:
- Confidence: {explanation.ai_confidence:.1%}
- Key Features: {', '.join(f'{k}:{v:.3f}' for k, v in list(explanation.ai_features.items())[:5])}

RISK ASSESSMENT:
- Position Risk: ${explanation.position_risk:.2f}
- Portfolio Risk: {explanation.portfolio_risk:.1%}
- Risk Factors: {', '.join(explanation.risk_factors)}

MARKET CONDITIONS:
- Regime: {explanation.market_regime}
- Volatility: {explanation.volatility_level:.1%}
- Liquidity Score: {explanation.liquidity_score:.2f}
"""
		return readable
    
	def _log_regulatory_event(self, event_type: str, event_data: Dict[str, Any]):
		"""Log regulatory compliance events"""
		if not self.config.enable_regulatory_logging:
			return
        
		try:
			regulatory_entry = {
				"timestamp": dt.datetime.now().isoformat(),
				"event_type": event_type,
				"event_data": event_data,
				"system_version": "1.0",
				"compliance_framework": "SHORT_CYCLE_TRADING"
			}
            
			log_file = self.regulatory_dir / f"regulatory_{dt.date.today().isoformat()}.jsonl"
            
			with open(log_file, "a") as f:
				f.write(json.dumps(regulatory_entry, default=str) + "\n")
                
		except Exception as e:
			self.logger.error(f"Failed to log regulatory event: {e}")
    
	def _record_system_error(self, error_type: str, error_message: str):
		"""Record system error for tracking"""
		self.system_errors_today += 1
        
		error_entry = {
			"timestamp": dt.datetime.now().isoformat(),
			"error_type": error_type,
			"error_message": error_message,
			"daily_error_count": self.system_errors_today
		}
        
		# Log to safety log
		self.logger.error(f"System error #{self.system_errors_today}: {error_type} - {error_message}")
        
		# Log to regulatory file
		self._log_regulatory_event("SYSTEM_ERROR", error_entry)
    
	def _send_alert(self, level: AlertLevel, subject: str, message: str):
		"""Send alert notification"""
		# Check cooldown
		alert_key = f"{level.value}_{subject}"
		now = dt.datetime.now()
        
		if alert_key in self.last_alert_times:
			time_since_last = (now - self.last_alert_times[alert_key]).total_seconds() / 60
			if time_since_last < self.config.alert_cooldown_minutes:
				return  # Skip alert due to cooldown
        
		self.last_alert_times[alert_key] = now
        
		# Log alert
		self.logger.warning(f"🚨 ALERT [{level.value.upper()}]: {subject} - {message}")
        
		# Send email if configured
		if self.config.enable_email_alerts and self.config.email_recipients:
			self._send_email_alert(level, subject, message)
    
	def _send_email_alert(self, level: AlertLevel, subject: str, message: str):
		"""Send email alert (placeholder implementation)"""
		try:
			# This is a placeholder - implement with actual email configuration
			email_subject = f"LiteBotX Alert [{level.value.upper()}]: {subject}"
			email_body = f"""
LiteBotX Short-Cycle Trading Alert

Level: {level.value.upper()}
Subject: {subject}
Message: {message}
Timestamp: {dt.datetime.now()}

This is an automated alert from the LiteBotX safety monitoring system.
"""
            
			self.logger.info(f"📧 Email alert prepared: {email_subject}")
			# TODO: Implement actual email sending with SMTP configuration
            
		except Exception as e:
			self.logger.error(f"Failed to send email alert: {e}")
    
	def _log_safety_check(self, safety_status: Dict[str, Any]):
		"""Log safety check results"""
		if self.config.detailed_logging:
			log_entry = {
				"timestamp": dt.datetime.now().isoformat(),
				"safe_to_trade": safety_status["safe_to_trade"],
				"active_kill_switches": safety_status["active_kill_switches"],
				"warning_count": len(safety_status["warnings"]),
				"alert_count": len(safety_status["alerts"]),
				"daily_pnl": self.daily_pnl,
				"weekly_pnl": self.weekly_pnl,
				"system_errors_today": self.system_errors_today
			}
            
			log_file = self.log_dir / f"safety_checks_{dt.date.today().isoformat()}.jsonl"
            
			with open(log_file, "a") as f:
				f.write(json.dumps(log_entry, default=str) + "\n")
    
	def generate_daily_safety_report(self) -> str:
		"""Generate comprehensive daily safety report"""
		try:
			active_switches = [ks for ks in self.kill_switches.values() if ks.is_active]
            
			report = f"""
DAILY SAFETY REPORT - {dt.date.today()}
{'='*50}

KILL SWITCH STATUS:
{len(active_switches)} of {len(self.kill_switches)} kill switches active

ACTIVE KILL SWITCHES:
"""
            
			for switch in active_switches:
				report += f"- {switch.switch_type.value}: {switch.reason}\n"
            
			if not active_switches:
				report += "✅ All kill switches inactive\n"
            
			report += f"""
RISK METRICS:
- Daily P&L: ${self.daily_pnl:.2f}
- Weekly P&L: ${self.weekly_pnl:.2f}
- System Errors Today: {self.system_errors_today}
- Current Win Rate: {self.performance_metrics.get('win_rate', 0):.1%}

SAFETY THRESHOLDS:
- Daily Loss Limit: ${self.kill_switches[KillSwitchType.DAILY_LOSS].threshold_value:.2f}
- Weekly Loss Limit: ${self.kill_switches[KillSwitchType.WEEKLY_LOSS].threshold_value:.2f}
- Max Drawdown: {self.config.max_drawdown_pct:.1%}

SYSTEM STATUS: {'🔴 TRADING HALTED' if active_switches else '🟢 NORMAL OPERATION'}
"""
            
			return report
            
		except Exception as e:
			return f"Error generating safety report: {e}"
    
	def manual_kill_switch_reset(self, switch_type: KillSwitchType, reason: str = "Manual reset") -> bool:
		"""Manually reset a kill switch"""
		try:
			if switch_type in self.kill_switches:
				kill_switch = self.kill_switches[switch_type]
				kill_switch.is_active = False
				kill_switch.trigger_timestamp = None
				kill_switch.trigger_value = None
				kill_switch.reason = ""
                
				self.logger.warning(f"🔧 Manual kill switch reset: {switch_type.value} - {reason}")
                
				# Log regulatory event
				self._log_regulatory_event("MANUAL_KILL_SWITCH_RESET", {
					"switch_type": switch_type.value,
					"reset_reason": reason,
					"reset_timestamp": dt.datetime.now().isoformat()
				})
                
				return True
			else:
				self.logger.error(f"Unknown kill switch type: {switch_type}")
				return False
                
		except Exception as e:
			self.logger.error(f"Error resetting kill switch: {e}")
			return False


class PaperTradingValidator:
	"""Paper trading validation framework"""
    
	def __init__(self, config: SafetyConfig, duration_weeks: int = 12):
		self.config = config
		self.duration_weeks = duration_weeks
		self.logger = logging.getLogger("PaperTradingValidator")
        
		self.start_date = dt.date.today()
		self.end_date = self.start_date + dt.timedelta(weeks=duration_weeks)
        
		# Validation metrics
		self.validation_metrics = {
			"total_trades": 0,
			"winning_trades": 0,
			"total_pnl": 0.0,
			"max_drawdown": 0.0,
			"sharpe_ratio": 0.0,
			"d1_exit_compliance": 0.0,
			"avg_weekly_return": 0.0
		}
        
		# Validation thresholds
		self.validation_thresholds = {
			"min_trades": 50,
			"min_win_rate": 0.45,
			"min_sharpe": 0.8,
			"max_drawdown": 0.12,
			"min_d1_compliance": 0.85,
			"min_weekly_return": 0.01
		}
    
	def validate_system_readiness(self, backtest_results: Any) -> Dict[str, Any]:
		"""Validate if system is ready for live trading based on paper trading"""
		validation_result = {
			"ready_for_live": False,
			"validation_score": 0.0,
			"passed_criteria": [],
			"failed_criteria": [],
			"recommendations": []
		}
        
		try:
			# Extract metrics from backtest results
			if hasattr(backtest_results, 'total_trades'):
				self.validation_metrics.update({
					"total_trades": backtest_results.total_trades,
					"winning_trades": backtest_results.winning_trades,
					"total_pnl": backtest_results.total_return,
					"max_drawdown": backtest_results.max_drawdown,
					"sharpe_ratio": backtest_results.sharpe_ratio,
					"d1_exit_compliance": getattr(backtest_results, 'd1_exit_compliance', 0.0),
					"avg_weekly_return": getattr(backtest_results, 'avg_weekly_return', 0.0)
				})
            
			# Check each validation criterion
			passed_count = 0
			total_criteria = len(self.validation_thresholds)
            
			# Minimum trades
			if self.validation_metrics["total_trades"] >= self.validation_thresholds["min_trades"]:
				validation_result["passed_criteria"].append("Sufficient trade volume")
				passed_count += 1
			else:
				validation_result["failed_criteria"].append(
					f"Insufficient trades: {self.validation_metrics['total_trades']} < {self.validation_thresholds['min_trades']}"
				)
            
			# Win rate
			win_rate = self.validation_metrics["winning_trades"] / max(self.validation_metrics["total_trades"], 1)
			if win_rate >= self.validation_thresholds["min_win_rate"]:
				validation_result["passed_criteria"].append(f"Win rate: {win_rate:.1%}")
				passed_count += 1
			else:
				validation_result["failed_criteria"].append(
					f"Low win rate: {win_rate:.1%} < {self.validation_thresholds['min_win_rate']:.1%}"
				)
            
			# Sharpe ratio
			if self.validation_metrics["sharpe_ratio"] >= self.validation_thresholds["min_sharpe"]:
				validation_result["passed_criteria"].append(f"Sharpe ratio: {self.validation_metrics['sharpe_ratio']:.2f}")
				passed_count += 1
			else:
				validation_result["failed_criteria"].append(
					f"Low Sharpe ratio: {self.validation_metrics['sharpe_ratio']:.2f} < {self.validation_thresholds['min_sharpe']:.2f}"
				)
            
			# Max drawdown
			if self.validation_metrics["max_drawdown"] <= self.validation_thresholds["max_drawdown"]:
				validation_result["passed_criteria"].append(f"Drawdown control: {self.validation_metrics['max_drawdown']:.1%}")
				passed_count += 1
			else:
				validation_result["failed_criteria"].append(
					f"High drawdown: {self.validation_metrics['max_drawdown']:.1%} > {self.validation_thresholds['max_drawdown']:.1%}"
				)
            
			# D+1 exit compliance
			if self.validation_metrics["d1_exit_compliance"] >= self.validation_thresholds["min_d1_compliance"]:
				validation_result["passed_criteria"].append(f"D+1 compliance: {self.validation_metrics['d1_exit_compliance']:.1%}")
				passed_count += 1
			else:
				validation_result["failed_criteria"].append(
					f"Low D+1 compliance: {self.validation_metrics['d1_exit_compliance']:.1%} < {self.validation_thresholds['min_d1_compliance']:.1%}"
				)
            
			# Weekly return
			if self.validation_metrics["avg_weekly_return"] >= self.validation_thresholds["min_weekly_return"]:
				validation_result["passed_criteria"].append(f"Weekly return: {self.validation_metrics['avg_weekly_return']:.2%}")
				passed_count += 1
			else:
				validation_result["failed_criteria"].append(
					f"Low weekly return: {self.validation_metrics['avg_weekly_return']:.2%} < {self.validation_thresholds['min_weekly_return']:.2%}"
				)
            
			# Calculate validation score
			validation_result["validation_score"] = passed_count / total_criteria
            
			# Determine if ready for live trading (need 85% criteria passed)
			validation_result["ready_for_live"] = validation_result["validation_score"] >= 0.85
            
			# Generate recommendations
			if not validation_result["ready_for_live"]:
				validation_result["recommendations"] = self._generate_improvement_recommendations(validation_result)
            
			return validation_result
            
		except Exception as e:
			self.logger.error(f"Error in system validation: {e}")
			validation_result["failed_criteria"].append(f"Validation error: {e}")
			return validation_result
    
	def _generate_improvement_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
		"""Generate recommendations for improving system before live trading"""
		recommendations = []
        
		for failure in validation_result["failed_criteria"]:
			if "trade" in failure.lower():
				recommendations.append("Extend paper trading period to generate more trades")
			elif "win rate" in failure.lower():
				recommendations.append("Increase AI confidence threshold to improve trade quality")
			elif "sharpe" in failure.lower():
				recommendations.append("Reduce position sizes or tighten stop losses")
			elif "drawdown" in failure.lower():
				recommendations.append("Implement stricter daily loss limits")
			elif "compliance" in failure.lower():
				recommendations.append("Fix D+1 exit logic to ensure forced exits")
			elif "return" in failure.lower():
				recommendations.append("Increase profit targets or improve signal quality")
        
		if not recommendations:
			recommendations.append("Continue paper trading and monitor performance")
        
		return recommendations


# Testing function
def test_safety_monitoring():
	"""Test safety monitoring framework"""
	print("🧪 Testing Safety Monitoring Framework")
    
	try:
		# Create configuration
		config = SafetyConfig(
			max_daily_loss_pct=0.01,
			max_weekly_loss_pct=0.03,
			enable_explainability_logging=True
		)
        
		# Initialize safety monitor
		monitor = SafetyMonitor(config, portfolio_value=1000.0)
		print("✅ Safety monitor initialized")
        
		# Test safety check
		safety_status = monitor.check_safety_conditions(
			current_positions=[],
			daily_pnl=-5.0,  # Small loss
			weekly_pnl=-8.0,  # Small weekly loss
			recent_trades=[]
		)
        
		print(f"✅ Safety check completed: Safe to trade = {safety_status['safe_to_trade']}")
        
		# Test kill switch trigger
		safety_status = monitor.check_safety_conditions(
			current_positions=[],
			daily_pnl=-15.0,  # Trigger daily loss limit
			weekly_pnl=-8.0,
			recent_trades=[]
		)
        
		print(f"🛑 Kill switch test: Safe to trade = {safety_status['safe_to_trade']}")
        
		# Test explainability logging
		explanation = monitor.log_trade_explanation(
			trade_id="TEST001",
			symbol="AAPL",
			action="ENTRY",
			ai_decision={"confidence": 0.85, "features": {"momentum": 0.02, "volume": 1.5}},
			risk_assessment={"position_risk": 6.0, "portfolio_risk": 0.006},
			market_conditions={"regime": "BULL", "volatility": 0.15}
		)
        
		print("✅ Explainability logging tested")
        
		# Test daily safety report
		report = monitor.generate_daily_safety_report()
		print("✅ Daily safety report generated")
        
		# Test paper trading validator
		validator = PaperTradingValidator(config, duration_weeks=8)
		print("✅ Paper trading validator initialized")
        
		print("✅ Safety monitoring framework test complete")
		return True
        
	except Exception as e:
		print(f"❌ Test failed: {e}")
		import traceback
		traceback.print_exc()
		return False


if __name__ == "__main__":
	print("🚀 LiteBotX Safety & Monitoring Framework")
	print("=" * 60)
    
	# Run test
	if test_safety_monitoring():
		print("\n🎯 Safety framework ready for integration")
	else:
		print("\n❌ Fix issues before proceeding")
