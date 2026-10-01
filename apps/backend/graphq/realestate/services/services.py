# services.py
class InstantValuationService:
    def __init__(self):
        import joblib
        from sklearn.ensemble import RandomForestRegressor
        self.model = joblib.load('valuation_model.pkl')
        self.scaler = joblib.load('scaler.pkl')
    
    def estimate_value(self, features):
        """Estimate property value based on features"""
        # Preprocess features
        scaled_features = self.scaler.transform([features])
        
        # Predict value
        predicted_value = self.model.predict(scaled_features)[0]
        
        # Calculate confidence interval
        std_dev = self._calculate_std_dev(features)
        
        return {
            'estimate': predicted_value,
            'range': {
                'low': predicted_value - std_dev,
                'high': predicted_value + std_dev
            },
            'confidence': self._calculate_confidence(std_dev, predicted_value)
        }
    
    def _calculate_std_dev(self, features):
        """Calculate standard deviation for prediction"""
        # Implementation depends on model type
        return predicted_value * 0.1  # Example: 10% of value
    
    def _calculate_confidence(self, std_dev, value):
        """Convert std deviation to confidence score"""
        return max(0, min(100, 100 - (std_dev / value * 100 * 2)))