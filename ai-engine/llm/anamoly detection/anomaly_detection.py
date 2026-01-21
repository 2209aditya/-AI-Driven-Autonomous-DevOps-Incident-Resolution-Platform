# ai-engine/anomaly-detection/predict.py
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio

class AnomalyPredictor:
    """
    ML-based anomaly detection for infrastructure metrics.
    Uses Isolation Forest for unsupervised anomaly detection.
    """
    
    def __init__(self, model_path: str = "models/anomaly_detector.pkl"):
        self.model_path = model_path
        self.scaler = StandardScaler()
        
        # Load pre-trained model or create new one
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(model_path.replace(".pkl", "_scaler.pkl"))
        else:
            # Initialize with default parameters
            self.model = IsolationForest(
                contamination=0.02,  # 2% anomaly rate
                random_state=42,
                n_estimators=100
            )
    
    async def predict(self, service_name: str, time_window: str = "1h") -> List[Dict[str, Any]]:
        """
        Predict anomalies for a service over a time window.
        """
        
        # Fetch metrics from Prometheus (simplified example)
        metrics_data = await self._fetch_metrics(service_name, time_window)
        
        # Prepare features
        features = self._prepare_features(metrics_data)
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict anomalies
        predictions = self.model.predict(features_scaled)
        anomaly_scores = self.model.score_samples(features_scaled)
        
        # Prepare results
        results = []
        for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
            is_anomaly = pred == -1  # -1 indicates anomaly in Isolation Forest
            
            results.append({
                "timestamp": metrics_data[idx]["timestamp"],
                "is_anomaly": is_anomaly,
                "score": float(score),
                "confidence": float(abs(score)),
                "metrics": metrics_data[idx],
                "recommendation": self._get_recommendation(is_anomaly, metrics_data[idx])
            })
        
        return results
    
    def _prepare_features(self, metrics_data: List[Dict]) -> np.ndarray:
        """
        Prepare feature matrix from metrics.
        """
        features = []
        
        for metric in metrics_data:
            feature_vector = [
                metric.get("cpu_usage", 0),
                metric.get("memory_usage", 0),
                metric.get("response_time", 0),
                metric.get("error_rate", 0),
                metric.get("request_rate", 0),
                metric.get("network_rx", 0),
                metric.get("network_tx", 0)
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    async def _fetch_metrics(self, service_name: str, time_window: str) -> List[Dict]:
        """
        Fetch metrics from Prometheus.
        In production, this would use Prometheus API.
        """
        
        # Simulated metrics for demonstration
        # In production, use: prometheus_api_client or direct HTTP calls
        
        now = datetime.utcnow()
        metrics = []
        
        # Generate 60 data points (1 per minute for 1 hour)
        for i in range(60):
            timestamp = now - timedelta(minutes=60-i)
            
            # Simulate normal behavior with some noise
            base_cpu = 50 + np.random.normal(0, 10)
            base_memory = 60 + np.random.normal(0, 8)
            base_response_time = 200 + np.random.normal(0, 30)
            
            # Inject anomaly at minute 45 (simulated incident)
            if i == 45:
                base_cpu = 95
                base_memory = 92
                base_response_time = 3500
            
            metrics.append({
                "timestamp": timestamp,
                "cpu_usage": max(0, min(100, base_cpu)),
                "memory_usage": max(0, min(100, base_memory)),
                "response_time": max(0, base_response_time),
                "error_rate": max(0, min(1, np.random.normal(0.01, 0.005))),
                "request_rate": max(0, 100 + np.random.normal(0, 15)),
                "network_rx": max(0, 1000 + np.random.normal(0, 200)),
                "network_tx": max(0, 800 + np.random.normal(0, 150))
            })
        
        return metrics
    
    def _get_recommendation(self, is_anomaly: bool, metrics: Dict) -> str:
        """
        Generate recommendation based on anomaly detection.
        """
        if not is_anomaly:
            return "No action required - metrics within normal range"
        
        recommendations = []
        
        if metrics.get("cpu_usage", 0) > 80:
            recommendations.append("High CPU detected - consider scaling horizontally")
        
        if metrics.get("memory_usage", 0) > 85:
            recommendations.append("High memory usage - check for memory leaks or increase limits")
        
        if metrics.get("response_time", 0) > 1000:
            recommendations.append("Elevated response time - investigate database queries or external API calls")
        
        if metrics.get("error_rate", 0) > 0.05:
            recommendations.append("High error rate - check application logs for exceptions")
        
        return " | ".join(recommendations) if recommendations else "Anomaly detected - manual investigation recommended"
    
    def train(self, historical_data: pd.DataFrame):
        """
        Train the anomaly detection model on historical data.
        """
        
        # Prepare features
        feature_columns = [
            "cpu_usage", "memory_usage", "response_time",
            "error_rate", "request_rate", "network_rx", "network_tx"
        ]
        
        X = historical_data[feature_columns].values
        
        # Fit scaler
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled)
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.model_path.replace(".pkl", "_scaler.pkl"))
        
        print(f"Model trained and saved to {self.model_path}")


# Training script
def train_anomaly_detector():
    """
    Example training script for the anomaly detector.
    In production, run this periodically (e.g., weekly) with new data.
    """
    
    # Load historical metrics from database or data warehouse
    # This is simulated data
    np.random.seed(42)
    
    # Generate 30 days of normal metrics
    n_samples = 30 * 24 * 60  # 30 days, 1 sample per minute
    
    data = {
        "cpu_usage": np.random.normal(50, 15, n_samples),
        "memory_usage": np.random.normal(60, 12, n_samples),
        "response_time": np.random.normal(250, 50, n_samples),
        "error_rate": np.abs(np.random.normal(0.01, 0.005, n_samples)),
        "request_rate": np.random.normal(100, 20, n_samples),
        "network_rx": np.random.normal(1000, 200, n_samples),
        "network_tx": np.random.normal(800, 150, n_samples)
    }
    
    # Inject some anomalies (2%)
    anomaly_indices = np.random.choice(n_samples, size=int(n_samples * 0.02), replace=False)
    for idx in anomaly_indices:
        data["cpu_usage"][idx] = np.random.uniform(85, 98)
        data["memory_usage"][idx] = np.random.uniform(80, 95)
        data["response_time"][idx] = np.random.uniform(2000, 5000)
    
    df = pd.DataFrame(data)
    
    # Train model
    predictor = AnomalyPredictor()
    predictor.train(df)
    
    print("Training complete!")


if __name__ == "__main__":
    # Train the model
    train_anomaly_detector()
    
    # Test prediction
    async def test_prediction():
        predictor = AnomalyPredictor()
        results = await predictor.predict("payment-service", "1h")
        
        print(f"\nDetected {sum(1 for r in results if r['is_anomaly'])} anomalies in last hour:")
        for result in results:
            if result["is_anomaly"]:
                print(f"  - {result['timestamp']}: {result['recommendation']}")
    
    # asyncio.run(test_prediction())