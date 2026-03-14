import xgboost as xgb
import numpy as np
import logging

logger = logging.getLogger(__name__)

class XGBPredictor:
    """
    XGBoost based short-term directional predictor.
    Predicts 1 (Up) or 0 (Down) based on historical features.
    """
    def __init__(self):
        self.model = xgb.XGBClassifier(
            objective="binary:logistic",
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            random_state=42
        )
        self.is_fitted = False
        
    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Trains the XGBoost classifier on feature matrix X to predict target y (0 or 1).
        """
        if len(X) < 100:
            logger.warning("XGBoost train: Not enough data points.")
            return
            
        try:
            self.model.fit(X, y)
            self.is_fitted = True
            logger.info("XGBoost model fitted successfully.")
        except Exception as e:
            logger.error(f"XGBoost training failed: {e}")
            
    def predict_direction(self, recent_features: np.ndarray) -> int:
        """
        Predicts the direction for the immediate next candle.
        Returns: 1 for UP, 0 for DOWN.
        """
        if not self.is_fitted:
            # Default fallback when untrained
            return -1 
            
        try:
            # Predict expects a 2D array, ensuring correct shape
            if len(recent_features.shape) == 1:
                recent_features = recent_features.reshape(1, -1)
                
            prediction = self.model.predict(recent_features)
            return int(prediction[-1])
        except Exception as e:
            logger.error(f"XGBoost predict failed: {e}")
            return -1
