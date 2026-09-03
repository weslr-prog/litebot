#!/usr/bin/env python3
"""
ML Signal Enhancer for LiteBotX - Lightweight ML integration for local trading systems
Optimized for local deployment with minimal computational overhead
"""

import pandas as pd
import numpy as np
import logging
import pickle
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Lightweight ML libraries suitable for local deployment
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("Scikit-learn not available. ML features disabled.")

logger = logging.getLogger("LiteBot")

class MLSignalEnhancer:
    """
    Lightweight ML enhancement for trading signals
    - Uses Random Forest for signal classification (fast, interpretable)
    - Minimal memory footprint suitable for local systems
    - Feature engineering from existing technical indicators
    - Model persistence for quick loading
    """
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.is_trained = False
        self.training_data = []
        
        # Create model directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Model configuration optimized for local systems
        self.model_config = {
            'n_estimators': 50,        # Reduced from 100 for faster training
            'max_depth': 10,           # Prevent overfitting
            'min_samples_split': 20,   # Require sufficient samples
            'min_samples_leaf': 10,    # Ensure robustness
            'random_state': 42,
            'n_jobs': 2,              # Use 2 cores max for local systems
            'class_weight': 'balanced' # Handle imbalanced data
        }
        
        logger.info("🤖 MLSignalEnhancer initialized for local deployment")
    
    def engineer_features(self, price_data: pd.DataFrame, regime: str) -> np.ndarray:
        """
        Engineer features from price data and technical indicators
        Optimized for speed and relevance
        """
        features = []
        
        try:
            # Price-based features
            if len(price_data) >= 20:
                # Returns and volatility
                returns = price_data['close'].pct_change(periods=1).fillna(0)
                features.extend([
                    returns.iloc[-1],                    # 1-day return
                    returns.rolling(5).mean().iloc[-1],  # 5-day avg return
                    returns.rolling(5).std().iloc[-1],   # 5-day volatility
                ])
                
                # Price position indicators
                close = price_data['close'].iloc[-1]
                high_20 = price_data['high'].rolling(20).max().iloc[-1]
                low_20 = price_data['low'].rolling(20).min().iloc[-1]
                
                features.extend([
                    (close - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5,  # Price position
                    close / price_data['close'].rolling(10).mean().iloc[-1] - 1,          # Price vs MA10
                    close / price_data['close'].rolling(20).mean().iloc[-1] - 1,          # Price vs MA20
                ])
                
                # Volume indicators (if available)
                if 'volume' in price_data.columns:
                    vol_avg = price_data['volume'].rolling(10).mean().iloc[-1]
                    vol_current = price_data['volume'].iloc[-1]
                    features.append(vol_current / vol_avg if vol_avg > 0 else 1.0)
                else:
                    features.append(1.0)  # Default volume ratio
                
                # Technical indicators (simplified)
                # RSI approximation
                gains = returns.where(returns > 0, 0).rolling(14).mean().iloc[-1]
                losses = (-returns.where(returns < 0, 0)).rolling(14).mean().iloc[-1]
                rsi = 100 - (100 / (1 + gains / losses)) if losses > 0 else 50
                features.append(rsi / 100.0)  # Normalize RSI
                
                # MACD approximation
                ema12 = price_data['close'].ewm(span=12).mean().iloc[-1]
                ema26 = price_data['close'].ewm(span=26).mean().iloc[-1]
                macd = (ema12 - ema26) / close
                features.append(macd)
                
                # Regime encoding
                regime_encoding = {
                    'UP_LOWVOL': [1, 0, 0, 0, 0],
                    'UP_HIGHVOL': [0, 1, 0, 0, 0],
                    'DOWN_LOWVOL': [0, 0, 1, 0, 0],
                    'DOWN_HIGHVOL': [0, 0, 0, 1, 0],
                    'SIDEWAYS': [0, 0, 0, 0, 1]
                }
                features.extend(regime_encoding.get(regime, [0, 0, 0, 0, 1]))
                
        except Exception as e:
            logger.warning(f"Feature engineering error: {e}")
            # Return default features if calculation fails
            features = [0.0] * 15
        
        # Ensure we always return the same number of features
        while len(features) < 15:
            features.append(0.0)
        
        return np.array(features[:15])  # Limit to 15 features for consistency
    
    def enhance_signal(self, base_signal: str, base_confidence: float, 
                      price_data: pd.DataFrame, regime: str) -> Dict:
        """
        Enhance base trading signal with ML prediction
        """
        if not self.is_trained or not ML_AVAILABLE:
            return {
                'signal': base_signal,
                'confidence': base_confidence,
                'ml_enhancement': False,
                'ml_confidence': 0.0
            }
        
        try:
            # Engineer features
            features = self.engineer_features(price_data, regime)
            features_scaled = self.scalers['signal'].transform(features.reshape(1, -1))
            
            # Get ML prediction
            ml_prediction = self.models['signal'].predict(features_scaled)[0]
            ml_probabilities = self.models['signal'].predict_proba(features_scaled)[0]
            
            # Convert prediction back to signal
            ml_signal_map = {1: 'buy', -1: 'sell', 0: 'hold'}
            ml_signal = ml_signal_map.get(ml_prediction, 'hold')
            
            # Calculate ML confidence (max probability)
            ml_confidence = np.max(ml_probabilities)
            
            # Enhanced signal logic
            if ml_signal == base_signal:
                # ML agrees with base signal - boost confidence
                enhanced_confidence = min(1.0, base_confidence * 1.2 + ml_confidence * 0.3)
                enhanced_signal = base_signal
            elif ml_signal == 'hold':
                # ML suggests hold - reduce confidence
                enhanced_confidence = base_confidence * 0.8
                enhanced_signal = base_signal
            else:
                # ML disagrees - use weighted average
                if ml_confidence > 0.7:  # High ML confidence
                    enhanced_signal = ml_signal
                    enhanced_confidence = (base_confidence + ml_confidence) / 2
                else:
                    enhanced_signal = base_signal
                    enhanced_confidence = base_confidence * 0.9
            
            return {
                'signal': enhanced_signal,
                'confidence': enhanced_confidence,
                'ml_enhancement': True,
                'ml_signal': ml_signal,
                'ml_confidence': ml_confidence,
                'base_signal': base_signal,
                'base_confidence': base_confidence
            }
            
        except Exception as e:
            logger.warning(f"ML enhancement failed: {e}")
            return {
                'signal': base_signal,
                'confidence': base_confidence,
                'ml_enhancement': False,
                'error': str(e)
            }
        
    def load_model(self):
        """
        Load trained models and scalers from the model directory.
        """
        try:
            model_path = os.path.join(self.model_dir, 'signal_model.pkl')
            scaler_path = os.path.join(self.model_dir, 'signal_scaler.pkl')

            if os.path.exists(model_path) and os.path.exists(scaler_path):
                with open(model_path, 'rb') as model_file:
                    self.models['signal'] = pickle.load(model_file)
                with open(scaler_path, 'rb') as scaler_file:
                    self.scalers['signal'] = pickle.load(scaler_file)
                self.is_trained = True
                logger.info("✅ Models and scalers loaded successfully.")
            else:
                logger.warning("⚠️ Model or scaler files not found. ML features disabled.")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.is_trained = False