import numpy as np
from hmmlearn import hmm
import logging

logger = logging.getLogger(__name__)

class HMMRegimeModel:
    """
    Hidden Markov Model for Regime Classification.
    Classifies market into: Trend, Range, Volatile (or 2-state equivalent) based on simple features.
    """
    def __init__(self, n_components: int = 3):
        self.n_components = n_components
        self.model = hmm.GaussianHMM(n_components=n_components, covariance_type="full", n_iter=100)
        self.is_fitted = False
        
    def fit(self, features: np.ndarray):
        """
        Fits the HMM model on historical features.
        Features could be a 2D array: [Returns, ATR] over time.
        """
        if len(features) < 100:
            logger.warning("HMM fit: Not enough data points (need >= 100)")
            return
            
        try:
            self.model.fit(features)
            self.is_fitted = True
            logger.info("HMM model fitted successfully.")
        except Exception as e:
            logger.error(f"HMM fit failed: {e}")
            
    def predict_regime(self, recent_features: np.ndarray) -> int:
        """
        Predicts the current regime (returns standard int state 0, 1, or 2).
        Args:
            recent_features: 2D array of the most recent observations.
        """
        if not self.is_fitted:
            return 0  # Default to 0 (Unknown)
            
        try:
            hidden_states = self.model.predict(recent_features)
            # Return the state of the most recent observation
            return int(hidden_states[-1])
        except Exception as e:
            logger.error(f"HMM predict failed: {e}")
            return 0
