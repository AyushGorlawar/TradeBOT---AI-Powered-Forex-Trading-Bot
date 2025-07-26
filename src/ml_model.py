#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Machine Learning Model for AI-powered forex trading signal generation
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime
import joblib

# ML libraries
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

logger = logging.getLogger("TradeBOT.MLModel")


class MLModel:
    """Machine Learning Model for predicting forex price movements and generating signals"""
    
    def __init__(self, config=None):
        """
        Initialize the ML model
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        self.config = config or {}
        self.ml_config = self.config.get('ml_model', {})
        
        # Model parameters
        self.model_type = self.ml_config.get('model_type', 'random_forest')
        self.model_params = self.ml_config.get('model_params', {})
        self.feature_columns = self.ml_config.get('feature_columns', [])
        self.target_column = self.ml_config.get('target_column', 'signal')
        self.prediction_horizon = self.ml_config.get('prediction_horizon', 5)
        self.train_size = self.ml_config.get('train_size', 0.8)
        self.random_state = self.ml_config.get('random_state', 42)
        
        # Model storage
        self.models_dir = self.ml_config.get('models_dir', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Initialize model and scaler
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the machine learning model based on configuration"""
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=self.model_params.get('n_estimators', 100),
                max_depth=self.model_params.get('max_depth', None),
                min_samples_split=self.model_params.get('min_samples_split', 2),
                min_samples_leaf=self.model_params.get('min_samples_leaf', 1),
                random_state=self.random_state
            )
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=self.model_params.get('n_estimators', 100),
                learning_rate=self.model_params.get('learning_rate', 0.1),
                max_depth=self.model_params.get('max_depth', 3),
                random_state=self.random_state
            )
        elif self.model_type == 'neural_network':
            self.model = MLPClassifier(
                hidden_layer_sizes=self.model_params.get('hidden_layer_sizes', (100,)),
                activation=self.model_params.get('activation', 'relu'),
                solver=self.model_params.get('solver', 'adam'),
                alpha=self.model_params.get('alpha', 0.0001),
                batch_size=self.model_params.get('batch_size', 'auto'),
                learning_rate=self.model_params.get('learning_rate', 'constant'),
                learning_rate_init=self.model_params.get('learning_rate_init', 0.001),
                max_iter=self.model_params.get('max_iter', 200),
                random_state=self.random_state
            )
        else:
            logger.warning(f"Unknown model type: {self.model_type}, defaulting to RandomForestClassifier")
            self.model_type = 'random_forest'
            self.model = RandomForestClassifier(random_state=self.random_state)
    
    def prepare_data(self, data):
        """
        Prepare data for training or prediction
        
        Args:
            data (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            tuple: X (features) and y (target) DataFrames
        """
        if data.empty:
            logger.warning("Empty DataFrame provided for data preparation")
            return None, None
        
        # Make a copy to avoid modifying the original
        df = data.copy()
        
        # Create target variable based on future price movement
        if self.target_column not in df.columns:
            # Calculate future returns
            df['future_return'] = df['close'].pct_change(periods=self.prediction_horizon).shift(-self.prediction_horizon)
            
            # Create target variable (1: buy, 0: hold, -1: sell)
            threshold = self.ml_config.get('signal_threshold', 0.001)  # 0.1% threshold
            df[self.target_column] = 0
            df.loc[df['future_return'] > threshold, self.target_column] = 1  # Buy signal
            df.loc[df['future_return'] < -threshold, self.target_column] = -1  # Sell signal
        
        # Drop rows with NaN values
        df.dropna(inplace=True)
        
        # Select features
        if not self.feature_columns:
            # Use all available technical indicators if not specified
            exclude_columns = ['open', 'high', 'low', 'close', 'volume', 'future_return', self.target_column]
            self.feature_columns = [col for col in df.columns if col not in exclude_columns]
        
        # Ensure all feature columns exist
        available_features = [col for col in self.feature_columns if col in df.columns]
        if len(available_features) < len(self.feature_columns):
            missing_features = set(self.feature_columns) - set(available_features)
            logger.warning(f"Missing feature columns: {missing_features}")
        
        # Select features and target
        X = df[available_features]
        y = df[self.target_column]
        
        return X, y
    
    def train(self, data, optimize=False):
        """
        Train the machine learning model
        
        Args:
            data (pandas.DataFrame): DataFrame with price data and indicators
            optimize (bool, optional): Whether to optimize hyperparameters. Defaults to False.
            
        Returns:
            dict: Training metrics
        """
        # Prepare data
        X, y = self.prepare_data(data)
        if X is None or y is None or X.empty or y.empty:
            logger.error("Failed to prepare data for training")
            return {}
        
        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, train_size=self.train_size, random_state=self.random_state
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Optimize hyperparameters if requested
        if optimize:
            self._optimize_hyperparameters(X_train_scaled, y_train)
        
        # Train the model
        logger.info(f"Training {self.model_type} model with {len(X_train)} samples")
        self.model.fit(X_train_scaled, y_train)
        
        # Calculate feature importance if available
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = dict(zip(X.columns, self.model.feature_importances_))
        
        # Evaluate the model
        y_pred = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1': f1_score(y_test, y_pred, average='weighted'),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'feature_importance': self.feature_importance
        }
        
        logger.info(f"Model training completed with accuracy: {metrics['accuracy']:.4f}")
        
        return metrics
    
    def _optimize_hyperparameters(self, X_train, y_train):
        """
        Optimize model hyperparameters using grid search
        
        Args:
            X_train (numpy.ndarray): Training features
            y_train (numpy.ndarray): Training targets
        """
        logger.info("Optimizing model hyperparameters")
        
        # Define parameter grid based on model type
        if self.model_type == 'random_forest':
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        elif self.model_type == 'gradient_boosting':
            param_grid = {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.2],
                'max_depth': [3, 5, 7]
            }
        elif self.model_type == 'neural_network':
            param_grid = {
                'hidden_layer_sizes': [(50,), (100,), (50, 50), (100, 50)],
                'activation': ['relu', 'tanh'],
                'alpha': [0.0001, 0.001, 0.01],
                'learning_rate_init': [0.001, 0.01]
            }
        else:
            logger.warning(f"Hyperparameter optimization not implemented for {self.model_type}")
            return
        
        # Create grid search
        grid_search = GridSearchCV(
            self.model, param_grid, cv=5, scoring='f1_weighted', n_jobs=-1
        )
        
        # Fit grid search
        grid_search.fit(X_train, y_train)
        
        # Update model with best parameters
        self.model = grid_search.best_estimator_
        logger.info(f"Best parameters: {grid_search.best_params_}")
    
    def predict(self, data):
        """
        Generate predictions for new data
        
        Args:
            data (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            numpy.ndarray: Predicted signals
        """
        if self.model is None:
            logger.error("Model not trained yet")
            return None
        
        # Prepare data
        X, _ = self.prepare_data(data)
        if X is None or X.empty:
            logger.error("Failed to prepare data for prediction")
            return None
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Generate predictions
        predictions = self.model.predict(X_scaled)
        
        # Get prediction probabilities if available
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X_scaled)
            # Add probabilities to the result
            result = {
                'predictions': predictions,
                'probabilities': probabilities
            }
            return result
        
        return {'predictions': predictions}
    
    def save_model(self, filename=None):
        """
        Save the trained model to disk
        
        Args:
            filename (str, optional): Filename to save the model. Defaults to None.
            
        Returns:
            str: Path to the saved model
        """
        if self.model is None:
            logger.error("No trained model to save")
            return None
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.model_type}_{timestamp}.joblib"
        
        # Ensure .joblib extension
        if not filename.endswith('.joblib'):
            filename += '.joblib'
        
        # Create full path
        model_path = os.path.join(self.models_dir, filename)
        
        # Save model and scaler
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'model_type': self.model_type,
                'feature_importance': self.feature_importance,
                'config': self.ml_config
            }
            joblib.dump(model_data, model_path)
            logger.info(f"Model saved to {model_path}")
            return model_path
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return None
    
    def load_model(self, filename=None):
        """
        Load a trained model from disk
        
        Args:
            filename (str, optional): Filename of the model to load. Defaults to None.
            
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        # If filename not provided, try to load the latest model
        if filename is None:
            model_files = [f for f in os.listdir(self.models_dir) if f.endswith('.joblib')]
            if not model_files:
                logger.warning("No saved models found")
                return False
            
            # Sort by modification time (newest first)
            model_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.models_dir, x)), reverse=True)
            filename = model_files[0]
        
        # Ensure .joblib extension
        if not filename.endswith('.joblib'):
            filename += '.joblib'
        
        # Create full path
        model_path = os.path.join(self.models_dir, filename) if not os.path.isabs(filename) else filename
        
        # Load model
        try:
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
            
            model_data = joblib.load(model_path)
            
            # Extract model components
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data.get('feature_columns', self.feature_columns)
            self.model_type = model_data.get('model_type', self.model_type)
            self.feature_importance = model_data.get('feature_importance', None)
            
            # Update config if available
            if 'config' in model_data:
                self.ml_config.update(model_data['config'])
            
            logger.info(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def get_feature_importance(self):
        """
        Get feature importance from the trained model
        
        Returns:
            dict: Feature importance dictionary
        """
        if self.feature_importance is None:
            logger.warning("Feature importance not available")
            return {}
        
        # Sort by importance
        sorted_importance = dict(sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True))
        return sorted_importance