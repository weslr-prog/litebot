#!/usr/bin/env python3
"""
ML Model Training Infrastructure for Short-Cycle Trading
Sprint 1: Implement ML models for Weekly High Yield ROI
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import pickle
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    import xgboost as xgb
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️  ML libraries not available. Install with: pip install scikit-learn xgboost")

# Import real-time data integration
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

@dataclass
class MLModelConfig:
    """Configuration for ML model training"""
    model_type: str = "ensemble"  # ensemble, random_forest, xgboost, logistic
    training_days: int = 252  # 1 year of data
    feature_selection: bool = True
    cross_validation_folds: int = 5
    test_size: float = 0.2
    random_state: int = 42
    min_samples_per_symbol: int = 100
    target_return_threshold: float = 0.01  # 1% daily return threshold

class MLFeatureEngineer:
    """Advanced feature engineering for short-cycle trading"""
    
    def __init__(self):
        self.logger = logging.getLogger('MLFeatureEngineer')
        self.feature_names = []
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer comprehensive features for ML training"""
        self.logger.info(f"Engineering features from {len(df)} data points")
        
        features = df.copy()
        
        # Price-based features
        features = self._add_price_features(features)
        
        # Technical indicators
        features = self._add_technical_indicators(features)
        
        # Momentum features
        features = self._add_momentum_features(features)
        
        # Volatility features
        features = self._add_volatility_features(features)
        
        # Volume features
        features = self._add_volume_features(features)
        
        # Time-based features
        features = self._add_time_features(features)
        
        # Market regime features
        features = self._add_regime_features(features)
        
        # Target variables
        features = self._add_target_variables(features)
        
        # Clean and validate
        features = self._clean_features(features)
        
        self.feature_names = [col for col in features.columns if col not in ['symbol', 'timestamp', 'target_return', 'target_direction', 'target_high_yield']]
        
        self.logger.info(f"Generated {len(self.feature_names)} features")
        return features
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        # Basic returns
        df['returns_1d'] = df['close'].pct_change()
        df['returns_2d'] = df['close'].pct_change(2)
        df['returns_3d'] = df['close'].pct_change(3)
        df['returns_5d'] = df['close'].pct_change(5)
        
        # Log returns
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Price ratios
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        df['close_high_ratio'] = df['close'] / df['high']
        df['close_low_ratio'] = df['close'] / df['low']
        
        # Gap features
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        df['gap_filled'] = ((df['low'] <= df['close'].shift(1)) & (df['gap'] > 0)).astype(int)
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features"""
        # Moving averages
        for period in [5, 10, 20, 50]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'price_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
        
        # Exponential moving averages
        for period in [12, 26]:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            df[f'price_ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'])
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        
        # Bollinger Bands
        df = self._add_bollinger_bands(df)
        
        # Stochastic
        df = self._add_stochastic(df)
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum-based features"""
        # Price momentum
        for period in [3, 5, 10, 20]:
            df[f'momentum_{period}d'] = df['close'] / df['close'].shift(period) - 1
        
        # ROC (Rate of Change)
        for period in [5, 10, 20]:
            df[f'roc_{period}d'] = (df['close'] - df['close'].shift(period)) / df['close'].shift(period) * 100
        
        # Momentum acceleration
        df['momentum_acceleration'] = df['momentum_5d'] - df['momentum_10d']
        
        # Consecutive gains/losses
        df['price_direction'] = np.where(df['returns_1d'] > 0, 1, -1)
        df['consecutive_gains'] = (df['price_direction'] == 1).astype(int).groupby((df['price_direction'] != df['price_direction'].shift()).cumsum()).cumsum()
        df['consecutive_losses'] = (df['price_direction'] == -1).astype(int).groupby((df['price_direction'] != df['price_direction'].shift()).cumsum()).cumsum()
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based features"""
        # Historical volatility
        for period in [5, 10, 20]:
            df[f'volatility_{period}d'] = df['returns_1d'].rolling(period).std()
        
        # Realized volatility
        df['realized_volatility'] = df['returns_1d'].rolling(20).std() * np.sqrt(252)
        
        # True Range and ATR
        df['true_range'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['true_range'].rolling(14).mean()
        df['price_atr_ratio'] = df['close'] / df['atr']
        
        # Volatility ratio
        df['volatility_ratio'] = df['volatility_5d'] / df['volatility_20d']
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features"""
        if 'volume' not in df.columns:
            return df
        
        # Volume moving averages
        for period in [5, 10, 20]:
            df[f'volume_sma_{period}'] = df['volume'].rolling(period).mean()
            df[f'volume_ratio_{period}'] = df['volume'] / df[f'volume_sma_{period}']
        
        # Volume momentum
        df['volume_momentum'] = df['volume'] / df['volume'].shift(5)
        
        # On-Balance Volume (OBV)
        df['obv'] = (np.sign(df['returns_1d']) * df['volume']).cumsum()
        df['obv_momentum'] = df['obv'] / df['obv'].shift(10)
        
        # Volume-Price Trend (VPT)
        df['vpt'] = (df['returns_1d'] * df['volume']).cumsum()
        
        return df
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features"""
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df['timestamp'] = df.index
        
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['quarter'] = df['timestamp'].dt.quarter
        
        # Binary time features
        df['is_monday'] = (df['day_of_week'] == 0).astype(int)
        df['is_friday'] = (df['day_of_week'] == 4).astype(int)
        df['is_quarter_end'] = df['timestamp'].dt.is_quarter_end.astype(int)
        df['is_month_end'] = df['timestamp'].dt.is_month_end.astype(int)
        
        return df
    
    def _add_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market regime features"""
        # Trend strength
        df['trend_strength'] = abs(df['close'].rolling(20).apply(lambda x: np.polyfit(range(20), x, 1)[0]))
        
        # Market state
        df['above_sma_20'] = (df['close'] > df['sma_20']).astype(int)
        df['above_sma_50'] = (df['close'] > df['sma_50']).astype(int)
        
        # Volatility regime
        vol_20 = df['volatility_20d']
        df['high_volatility_regime'] = (vol_20 > vol_20.rolling(60).quantile(0.8)).astype(int)
        df['low_volatility_regime'] = (vol_20 < vol_20.rolling(60).quantile(0.2)).astype(int)
        
        return df
    
    def _add_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add target variables for different prediction horizons"""
        # Next day return
        df['target_return'] = df['returns_1d'].shift(-1)
        df['target_direction'] = (df['target_return'] > 0).astype(int)
        
        # High yield target (for weekly ROI goal)
        df['target_high_yield'] = (abs(df['target_return']) > 0.02).astype(int)  # 2%+ moves
        
        # Multi-day targets
        df['target_return_3d'] = df['close'].shift(-3) / df['close'] - 1
        df['target_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _add_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands features"""
        period = 20
        std_mult = 2
        
        rolling_mean = df['close'].rolling(period).mean()
        rolling_std = df['close'].rolling(period).std()
        
        df['bb_upper'] = rolling_mean + (rolling_std * std_mult)
        df['bb_lower'] = rolling_mean - (rolling_std * std_mult)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_squeeze'] = (df['bb_upper'] - df['bb_lower']) / rolling_mean
        
        return df
    
    def _add_stochastic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Stochastic Oscillator"""
        period = 14
        
        low_min = df['low'].rolling(period).min()
        high_max = df['high'].rolling(period).max()
        
        df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        return df
    
    def _clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate features"""
        # Remove infinite values
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Drop rows with too many NaN values
        df = df.dropna(thresh=len(df.columns) * 0.8)
        
        return df

class MLModelTrainer:
    """ML model training for short-cycle trading predictions"""
    
    def __init__(self, config: MLModelConfig = None):
        self.config = config or MLModelConfig()
        self.feature_engineer = MLFeatureEngineer()
        self.models = {}
        self.scalers = {}
        self.logger = logging.getLogger('MLModelTrainer')
        
        # Performance tracking
        self.training_history = []
        self.model_performance = {}
    
    def prepare_training_data(self, market_data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare data for ML training"""
        self.logger.info("Preparing training data...")
        
        # Engineer features
        engineered_data = self.feature_engineer.engineer_features(market_data)
        
        # Remove rows with NaN targets
        clean_data = engineered_data.dropna(subset=['target_direction', 'target_high_yield'])
        
        if len(clean_data) < self.config.min_samples_per_symbol:
            raise ValueError(f"Insufficient training data: {len(clean_data)} samples")
        
        # Prepare features and targets
        feature_columns = self.feature_engineer.feature_names
        X = clean_data[feature_columns].fillna(0)
        y_direction = clean_data['target_direction']
        y_high_yield = clean_data['target_high_yield']
        
        self.logger.info(f"Training data prepared: {X.shape[0]} samples, {X.shape[1]} features")
        
        return X.values, y_direction.values, y_high_yield.values, feature_columns
    
    def train_models(self, X: np.ndarray, y_direction: np.ndarray, y_high_yield: np.ndarray, feature_names: List[str]) -> Dict[str, Any]:
        """Train multiple ML models"""
        self.logger.info("Training ML models...")
        
        if not ML_AVAILABLE:
            raise ImportError("ML libraries not available")
        
        # Split data
        X_train, X_test, y_dir_train, y_dir_test, y_yield_train, y_yield_test = train_test_split(
            X, y_direction, y_high_yield, 
            test_size=self.config.test_size, 
            random_state=self.config.random_state,
            stratify=y_direction
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        self.scalers['main'] = scaler
        
        # Train direction prediction models
        direction_models = self._train_direction_models(X_train_scaled, y_dir_train, X_test_scaled, y_dir_test)
        
        # Train high yield prediction models
        yield_models = self._train_yield_models(X_train_scaled, y_yield_train, X_test_scaled, y_yield_test)
        
        # Combine results
        results = {
            'direction_models': direction_models,
            'yield_models': yield_models,
            'feature_names': feature_names,
            'scaler': scaler,
            'training_samples': X_train.shape[0],
            'test_samples': X_test.shape[0],
            'timestamp': datetime.now()
        }
        
        self.models = results
        self.training_history.append(results)
        
        self.logger.info("✅ Model training completed")
        return results
    
    def _train_direction_models(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Train models for direction prediction"""
        models = {}
        
        # Random Forest
        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=self.config.random_state,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        models['random_forest'] = {
            'model': rf_model,
            'train_accuracy': rf_model.score(X_train, y_train),
            'test_accuracy': rf_model.score(X_test, y_test),
            'feature_importance': rf_model.feature_importances_
        }
        
        # XGBoost
        try:
            xgb_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=self.config.random_state,
                eval_metric='logloss'
            )
            xgb_model.fit(X_train, y_train)
            models['xgboost'] = {
                'model': xgb_model,
                'train_accuracy': xgb_model.score(X_train, y_train),
                'test_accuracy': xgb_model.score(X_test, y_test),
                'feature_importance': xgb_model.feature_importances_
            }
        except Exception as e:
            self.logger.warning(f"XGBoost training failed: {e}")
        
        # Logistic Regression
        lr_model = LogisticRegression(
            random_state=self.config.random_state,
            max_iter=1000
        )
        lr_model.fit(X_train, y_train)
        models['logistic_regression'] = {
            'model': lr_model,
            'train_accuracy': lr_model.score(X_train, y_train),
            'test_accuracy': lr_model.score(X_test, y_test),
            'coefficients': lr_model.coef_[0]
        }
        
        return models
    
    def _train_yield_models(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Train models for high yield prediction"""
        models = {}
        
        # Gradient Boosting for high yield prediction
        gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=self.config.random_state
        )
        gb_model.fit(X_train, y_train)
        models['gradient_boosting'] = {
            'model': gb_model,
            'train_accuracy': gb_model.score(X_train, y_train),
            'test_accuracy': gb_model.score(X_test, y_test),
            'feature_importance': gb_model.feature_importances_
        }
        
        return models
    
    def predict(self, X: np.ndarray, model_type: str = 'ensemble') -> Dict[str, np.ndarray]:
        """Make predictions using trained models"""
        if not self.models:
            raise ValueError("No trained models available")
        
        # Scale features
        X_scaled = self.scalers['main'].transform(X)
        
        predictions = {}
        
        # Direction predictions
        if model_type == 'ensemble':
            direction_preds = []
            yield_preds = []
            
            # Collect predictions from all models
            for model_name, model_info in self.models['direction_models'].items():
                pred = model_info['model'].predict_proba(X_scaled)[:, 1]
                direction_preds.append(pred)
            
            for model_name, model_info in self.models['yield_models'].items():
                pred = model_info['model'].predict_proba(X_scaled)[:, 1]
                yield_preds.append(pred)
            
            # Ensemble predictions (average)
            predictions['direction_probability'] = np.mean(direction_preds, axis=0)
            predictions['yield_probability'] = np.mean(yield_preds, axis=0)
            
        else:
            # Single model predictions
            if model_type in self.models['direction_models']:
                model = self.models['direction_models'][model_type]['model']
                predictions['direction_probability'] = model.predict_proba(X_scaled)[:, 1]
        
        # Convert probabilities to binary predictions
        predictions['direction_prediction'] = (predictions['direction_probability'] > 0.5).astype(int)
        if 'yield_probability' in predictions:
            predictions['yield_prediction'] = (predictions['yield_probability'] > 0.5).astype(int)
        
        return predictions
    
    def save_models(self, filepath: str):
        """Save trained models to disk"""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self.models, f)
            self.logger.info(f"Models saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    def load_models(self, filepath: str):
        """Load trained models from disk"""
        try:
            with open(filepath, 'rb') as f:
                self.models = pickle.load(f)
            self.logger.info(f"Models loaded from {filepath}")
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get comprehensive model performance metrics"""
        if not self.models:
            return {}
        
        performance = {
            'direction_models': {},
            'yield_models': {},
            'training_timestamp': self.models.get('timestamp'),
            'training_samples': self.models.get('training_samples'),
            'test_samples': self.models.get('test_samples')
        }
        
        # Direction model performance
        for model_name, model_info in self.models.get('direction_models', {}).items():
            performance['direction_models'][model_name] = {
                'train_accuracy': model_info.get('train_accuracy'),
                'test_accuracy': model_info.get('test_accuracy')
            }
        
        # Yield model performance
        for model_name, model_info in self.models.get('yield_models', {}).items():
            performance['yield_models'][model_name] = {
                'train_accuracy': model_info.get('train_accuracy'),
                'test_accuracy': model_info.get('test_accuracy')
            }
        
        return performance

def main():
    """Sprint 1 ML model training demonstration"""
    print("🤖 Sprint 1: ML Model Training for Weekly High Yield ROI")
    print("=" * 60)
    
    if not ML_AVAILABLE:
        print("❌ ML libraries not available")
        print("Install with: pip install scikit-learn xgboost")
        return
    
    # Initialize trainer
    trainer = MLModelTrainer()
    
    # Generate sample training data (replace with real data integration)
    print("📊 Generating sample training data...")
    
    # Create sample data for demonstration
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    sample_data = []
    for symbol in symbols:
        n_days = len(dates)
        
        # Generate realistic price data
        returns = np.random.normal(0.001, 0.02, n_days)
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'timestamp': dates[:len(prices)],
            'symbol': symbol,
            'open': prices * (1 + np.random.normal(0, 0.005, len(prices))),
            'high': prices * (1 + abs(np.random.normal(0, 0.01, len(prices)))),
            'low': prices * (1 - abs(np.random.normal(0, 0.01, len(prices)))),
            'close': prices,
            'volume': np.random.lognormal(15, 1, len(prices))
        })
        
        sample_data.append(df)
    
    market_data = pd.concat(sample_data, ignore_index=True)
    print(f"Generated {len(market_data)} data points for {len(symbols)} symbols")
    
    try:
        # Prepare training data
        print("🔧 Engineering features...")
        X, y_direction, y_high_yield, feature_names = trainer.prepare_training_data(market_data)
        
        print(f"Features engineered: {len(feature_names)} features")
        print(f"Training samples: {len(X)}")
        
        # Train models
        print("🎯 Training ML models...")
        results = trainer.train_models(X, y_direction, y_high_yield, feature_names)
        
        # Show results
        print("\n📈 Training Results:")
        print(f"Direction Models:")
        for model_name, model_info in results['direction_models'].items():
            print(f"  {model_name}: Train={model_info['train_accuracy']:.3f}, Test={model_info['test_accuracy']:.3f}")
        
        print(f"High Yield Models:")
        for model_name, model_info in results['yield_models'].items():
            print(f"  {model_name}: Train={model_info['train_accuracy']:.3f}, Test={model_info['test_accuracy']:.3f}")
        
        # Test predictions
        print("\n🔮 Testing predictions...")
        test_sample = X[:10]  # First 10 samples
        predictions = trainer.predict(test_sample)
        
        print(f"Direction predictions: {predictions['direction_prediction'][:5]}")
        print(f"Direction probabilities: {predictions['direction_probability'][:5]}")
        
        # Save models
        model_path = "/home/wes/Desktop/litebotx-usb-deployment/models/sprint1_ml_models.pkl"
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        trainer.save_models(model_path)
        
        print("\n✅ Sprint 1 ML Training: SUCCESS!")
        print("🎯 Ready for integration with real-time trading system")
        
        # Performance summary
        performance = trainer.get_model_performance()
        print(f"\n📊 Model Performance Summary:")
        print(f"Training completed: {performance['training_timestamp']}")
        print(f"Training samples: {performance['training_samples']}")
        print(f"Best direction accuracy: {max([m['test_accuracy'] for m in performance['direction_models'].values()]):.3f}")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
