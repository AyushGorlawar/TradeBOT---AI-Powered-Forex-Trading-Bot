#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Machine Learning Classifier for predicting forex price movements
"""

import os
import logging
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

logger = logging.getLogger("TradeBOT.MLClassifier")


class MLClassifier:
    """Machine Learning Classifier for predicting forex price movements"""
    
    def __init__(self, config=None):
        """Initialize the ML classifier
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        self.config = config or {}
        self.model_config = self.config.get('model', {})
        self.model_type = self.model_config.get('algorithm', 'random_forest')
        self.model = None
        self.scaler = None
        self.feature_columns = []
        self.last_trained = None
        
        # Create model directory if it doesn't exist
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'saved_models')
        os.makedirs(self.model_dir, exist_ok=True)
    
    def train(self, X, y):
        """Train the ML model
        
        Args:
            X (pandas.DataFrame): Feature DataFrame
            y (pandas.Series): Target variable
            
        Returns:
            dict: Training metrics
        """
        logger.info(f"Training {self.model_type} model with {X.shape[0]} samples and {X.shape[1]} features")
        
        # Store feature columns for prediction
        self.feature_columns = X.columns.tolist()
        
        # Split data into train and test sets
        test_size = self.model_config.get('train_test_split', 0.2)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Initialize and train the model
        if self.model_type == 'random_forest':
            self.model = self._train_random_forest(X_train_scaled, y_train)
        elif self.model_type == 'xgboost':
            self.model = self._train_xgboost(X_train_scaled, y_train)
        elif self.model_type == 'neural_network':
            self.model = self._train_neural_network(X_train_scaled, y_train)
        else:
            logger.warning(f"Unknown model type: {self.model_type}, defaulting to random_forest")
            self.model_type = 'random_forest'
            self.model = self._train_random_forest(X_train_scaled, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)
        
        # Save the model
        self._save_model()
        
        # Update last trained timestamp
        self.last_trained = datetime.now()
        
        return metrics
    
    def _train_random_forest(self, X_train, y_train):
        """Train a Random Forest classifier
        
        Args:
            X_train (numpy.ndarray): Scaled training features
            y_train (pandas.Series): Training target variable
            
        Returns:
            RandomForestClassifier: Trained model
        """
        # Get hyperparameters from config or use defaults
        params = self.model_config.get('random_forest_params', {})
        n_estimators = params.get('n_estimators', 100)
        max_depth = params.get('max_depth', None)
        min_samples_split = params.get('min_samples_split', 2)
        min_samples_leaf = params.get('min_samples_leaf', 1)
        
        # Initialize model
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            random_state=42,
            n_jobs=-1
        )
        
        # Train model
        model.fit(X_train, y_train)
        
        return model
    
    def _train_xgboost(self, X_train, y_train):
        """Train an XGBoost classifier
        
        Args:
            X_train (numpy.ndarray): Scaled training features
            y_train (pandas.Series): Training target variable
            
        Returns:
            XGBClassifier: Trained model
        """
        try:
            from xgboost import XGBClassifier
            
            # Get hyperparameters from config or use defaults
            params = self.model_config.get('xgboost_params', {})
            n_estimators = params.get('n_estimators', 100)
            max_depth = params.get('max_depth', 3)
            learning_rate = params.get('learning_rate', 0.1)
            subsample = params.get('subsample', 0.8)
            colsample_bytree = params.get('colsample_bytree', 0.8)
            
            # Initialize model
            model = XGBClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=subsample,
                colsample_bytree=colsample_bytree,
                random_state=42,
                n_jobs=-1
            )
            
            # Train model
            model.fit(X_train, y_train)
            
            return model
        
        except ImportError:
            logger.error("XGBoost not installed. Defaulting to Random Forest.")
            return self._train_random_forest(X_train, y_train)
    
    def _train_neural_network(self, X_train, y_train):
        """Train a neural network classifier
        
        Args:
            X_train (numpy.ndarray): Scaled training features
            y_train (pandas.Series): Training target variable
            
        Returns:
            keras.Model: Trained model
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import Dense, Dropout
            from tensorflow.keras.optimizers import Adam
            from tensorflow.keras.callbacks import EarlyStopping
            import tensorflow as tf
            
            # Set random seed for reproducibility
            tf.random.set_seed(42)
            
            # Get hyperparameters from config or use defaults
            params = self.model_config.get('neural_network_params', {})
            hidden_layers = params.get('hidden_layers', [64, 32])
            dropout_rate = params.get('dropout_rate', 0.2)
            learning_rate = params.get('learning_rate', 0.001)
            batch_size = params.get('batch_size', 32)
            epochs = params.get('epochs', 100)
            
            # Determine number of output neurons based on target values
            unique_targets = np.unique(y_train)
            n_outputs = len(unique_targets)
            
            # Determine activation function and loss based on number of outputs
            if n_outputs == 2:
                output_activation = 'sigmoid'
                loss = 'binary_crossentropy'
                output_dim = 1
            else:
                output_activation = 'softmax'
                loss = 'sparse_categorical_crossentropy'
                output_dim = n_outputs
            
            # Build model
            model = Sequential()
            
            # Input layer
            model.add(Dense(hidden_layers[0], activation='relu', input_shape=(X_train.shape[1],)))
            model.add(Dropout(dropout_rate))
            
            # Hidden layers
            for units in hidden_layers[1:]:
                model.add(Dense(units, activation='relu'))
                model.add(Dropout(dropout_rate))
            
            # Output layer
            model.add(Dense(output_dim, activation=output_activation))
            
            # Compile model
            model.compile(
                optimizer=Adam(learning_rate=learning_rate),
                loss=loss,
                metrics=['accuracy']
            )
            
            # Early stopping to prevent overfitting
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            )
            
            # Train model
            model.fit(
                X_train, y_train,
                batch_size=batch_size,
                epochs=epochs,
                validation_split=0.2,
                callbacks=[early_stopping],
                verbose=0
            )
            
            return model
        
        except ImportError:
            logger.error("TensorFlow/Keras not installed. Defaulting to Random Forest.")
            return self._train_random_forest(X_train, y_train)
    
    def predict(self, X):
        """Make predictions with the trained model
        
        Args:
            X (pandas.DataFrame): Feature DataFrame
            
        Returns:
            numpy.ndarray: Predicted classes
        """
        if self.model is None:
            logger.error("Model not trained or loaded. Cannot make predictions.")
            return np.array([])
        
        # Ensure X has the same columns as training data
        missing_cols = set(self.feature_columns) - set(X.columns)
        if missing_cols:
            logger.warning(f"Missing columns in prediction data: {missing_cols}")
            for col in missing_cols:
                X[col] = 0
        
        # Reorder columns to match training data
        X = X[self.feature_columns]
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Make predictions
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X):
        """Make probability predictions with the trained model
        
        Args:
            X (pandas.DataFrame): Feature DataFrame
            
        Returns:
            numpy.ndarray: Predicted probabilities
        """
        if self.model is None:
            logger.error("Model not trained or loaded. Cannot make predictions.")
            return np.array([])
        
        # Check if model supports predict_proba
        if not hasattr(self.model, 'predict_proba'):
            logger.warning("Model does not support probability predictions")
            return self.predict(X)
        
        # Ensure X has the same columns as training data
        missing_cols = set(self.feature_columns) - set(X.columns)
        if missing_cols:
            logger.warning(f"Missing columns in prediction data: {missing_cols}")
            for col in missing_cols:
                X[col] = 0
        
        # Reorder columns to match training data
        X = X[self.feature_columns]
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Make probability predictions
        return self.model.predict_proba(X_scaled)
    
    def _calculate_metrics(self, y_true, y_pred):
        """Calculate evaluation metrics
        
        Args:
            y_true (pandas.Series): True target values
            y_pred (numpy.ndarray): Predicted target values
            
        Returns:
            dict: Evaluation metrics
        """
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted'),
            'recall': recall_score(y_true, y_pred, average='weighted'),
            'f1': f1_score(y_true, y_pred, average='weighted'),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
        
        logger.info(f"Model evaluation metrics: Accuracy={metrics['accuracy']:.4f}, F1={metrics['f1']:.4f}")
        
        return metrics
    
    def _save_model(self):
        """Save the trained model to disk"""
        if self.model is None:
            logger.error("No model to save")
            return
        
        try:
            # Create model filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"{self.model_type}_{timestamp}.joblib"
            model_path = os.path.join(self.model_dir, model_filename)
            
            # Save model and scaler
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'model_type': self.model_type,
                'timestamp': timestamp
            }
            
            joblib.dump(model_data, model_path)
            logger.info(f"Model saved to {model_path}")
            
            # Update config with latest model path
            if self.config:
                if 'model' not in self.config:
                    self.config['model'] = {}
                self.config['model']['latest_model_path'] = model_path
        
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
    
    def load_model(self, model_path=None):
        """Load a trained model from disk
        
        Args:
            model_path (str, optional): Path to the model file. Defaults to None (latest model).
            
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            # If no model path provided, try to get from config or find latest
            if model_path is None:
                if self.config and 'model' in self.config and 'latest_model_path' in self.config['model']:
                    model_path = self.config['model']['latest_model_path']
                else:
                    # Find latest model file
                    model_files = [f for f in os.listdir(self.model_dir) if f.endswith('.joblib')]
                    if not model_files:
                        logger.warning("No saved models found")
                        return False
                    
                    # Sort by timestamp (assuming filename format: model_type_timestamp.joblib)
                    model_files.sort(reverse=True)
                    model_path = os.path.join(self.model_dir, model_files[0])
            
            # Load model data
            model_data = joblib.load(model_path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.model_type = model_data['model_type']
            
            logger.info(f"Model loaded from {model_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def needs_retraining(self):
        """Check if the model needs retraining
        
        Returns:
            bool: True if model needs retraining, False otherwise
        """
        # If no model, definitely needs training
        if self.model is None:
            return True
        
        # If no last_trained timestamp, needs training
        if self.last_trained is None:
            return True
        
        # Check if it's been longer than retrain_interval days
        retrain_interval = self.model_config.get('retrain_interval', 7)  # Default: 7 days
        days_since_trained = (datetime.now() - self.last_trained).days
        
        return days_since_trained >= retrain_interval