#!/usr/bin/env python3
"""
Simple RL Position Optimizer for local deployment
Uses Q-learning for position sizing optimization
"""

import numpy as np
import pandas as pd
import logging
import pickle
import os
from typing import Dict, List, Tuple
from collections import defaultdict, deque

logger = logging.getLogger("LiteBot")

class SimpleRLPositionOptimizer:
    """
    Lightweight Q-learning agent for position sizing
    Optimized for local systems with minimal computational overhead
    """
    
    def __init__(self, learning_rate=0.1, discount_factor=0.95, 
                 epsilon=0.1, model_dir="models"):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.model_dir = model_dir
        
        # Q-table for state-action values
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        # Experience replay buffer (limited size for local systems)
        self.experience_buffer = deque(maxlen=1000)
        
        # Action space: position size multipliers
        self.actions = [0.5, 0.75, 1.0, 1.25, 1.5]  # 50% to 150% of base size
        
        # Performance tracking
        self.performance_history = []
        self.total_trades = 0
        
        os.makedirs(model_dir, exist_ok=True)
        logger.info("🎯 SimpleRLPositionOptimizer initialized")
    
    def get_state(self, regime: str, confidence: float, recent_performance: float) -> str:
        """
        Convert market conditions to discrete state
        """
        # Discretize confidence
        conf_bucket = "low" if confidence < 0.5 else "med" if confidence < 0.75 else "high"
        
        # Discretize recent performance
        perf_bucket = "loss" if recent_performance < -0.02 else "flat" if recent_performance < 0.02 else "gain"
        
        return f"{regime}_{conf_bucket}_{perf_bucket}"
    
    def select_action(self, state: str, training: bool = True) -> int:
        """
        Select action using epsilon-greedy policy
        """
        if training and np.random.random() < self.epsilon:
            return np.random.choice(len(self.actions))
        
        # Get action with highest Q-value
        q_values = [self.q_table[state][a] for a in range(len(self.actions))]
        return np.argmax(q_values)
    
    def update_q_table(self, state: str, action: int, reward: float, next_state: str):
        """
        Update Q-table using Q-learning update rule
        """
        current_q = self.q_table[state][action]
        next_max_q = max(self.q_table[next_state].values()) if self.q_table[next_state] else 0
        
        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max_q - current_q
        )
        
        self.q_table[state][action] = new_q
    
    def optimize_position_size(self, base_size: float, regime: str, 
                             confidence: float, recent_performance: float) -> float:
        """
        Optimize position size using RL agent
        """
        state = self.get_state(regime, confidence, recent_performance)
        action_idx = self.select_action(state, training=False)
        multiplier = self.actions[action_idx]
        
        optimized_size = base_size * multiplier
        
        logger.debug(f"RL Position optimization: {base_size:.2f} -> {optimized_size:.2f} "
                    f"(state: {state}, multiplier: {multiplier:.2f})")
        
        return optimized_size
    
    def record_trade_result(self, state: str, action: int, return_pct: float):
        """
        Record trade result for learning
        """
        # Convert return to reward (encourage positive returns, penalize losses)
        reward = return_pct * 10  # Scale for better learning
        
        # Add to experience buffer
        self.experience_buffer.append({
            'state': state,
            'action': action,
            'reward': reward,
            'timestamp': pd.Timestamp.now()
        })
        
        self.performance_history.append(return_pct)
        self.total_trades += 1
        
        # Learn from recent experiences
        if len(self.experience_buffer) > 10:
            self._replay_learning()
    
    def _replay_learning(self):
        """
        Learn from recent experiences using replay
        """
        # Sample recent experiences for learning
        sample_size = min(5, len(self.experience_buffer))
        recent_experiences = list(self.experience_buffer)[-sample_size:]
        
        for i, exp in enumerate(recent_experiences[:-1]):
            next_exp = recent_experiences[i + 1]
            self.update_q_table(
                exp['state'], 
                exp['action'], 
                exp['reward'], 
                next_exp['state']
            )
    
    def get_performance_stats(self) -> Dict:
        """
        Get RL agent performance statistics
        """
        if not self.performance_history:
            return {'trades': 0, 'avg_return': 0, 'win_rate': 0}
        
        avg_return = np.mean(self.performance_history)
        win_rate = len([r for r in self.performance_history if r > 0]) / len(self.performance_history)
        
        return {
            'trades': self.total_trades,
            'avg_return': avg_return,
            'win_rate': win_rate,
            'total_return': sum(self.performance_history),
            'states_learned': len(self.q_table)
        }
    
    def save_model(self):
        """Save Q-table to disk"""
        try:
            model_path = os.path.join(self.model_dir, 'rl_position_optimizer.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'q_table': dict(self.q_table),
                    'performance_history': self.performance_history,
                    'total_trades': self.total_trades
                }, f)
            logger.info(f"💾 RL model saved to {model_path}")
        except Exception as e:
            logger.error(f"Failed to save RL model: {e}")
    
    def load_model(self) -> bool:
        """Load Q-table from disk"""
        try:
            model_path = os.path.join(self.model_dir, 'rl_position_optimizer.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                
                self.q_table = defaultdict(lambda: defaultdict(float), data['q_table'])
                self.performance_history = data.get('performance_history', [])
                self.total_trades = data.get('total_trades', 0)
                
                logger.info("📂 RL model loaded from disk")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to load RL model: {e}")
            return False