#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TradeBOT - AI-Powered Forex Trading Bot
Model Training Script
"""

import os
import argparse
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Local imports
from src.data_fetcher import DataFetcher
from src.preprocessor import DataPreprocessor
from src.indicators import TechnicalIndicators
from src.ml_model import MLModel
from config.config import Config
from config.pairs import CURRENCY_PAIRS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradeBOT.Training")

# Load environment variables
load_dotenv()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="TradeBOT - ML Model Training")
    parser.add_argument('--pairs', type=str, nargs='+', default=None,
                        help='Specific currency pairs to train on (default: all configured pairs)')
    parser.add_argument('--timeframe', type=str, default='1h',
                        help='Trading timeframe (e.g., 1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--days', type=int, default=90,
                        help='Number of days of historical data to use for training')
    parser.add_argument('--model-type', type=str, default='random_forest',
                        choices=['random_forest', 'gradient_boosting', 'neural_network'],
                        help='Type of ML model to train')
    parser.add_argument('--optimize', action='store_true',
                        help='Perform hyperparameter optimization')
    parser.add_argument('--test-size', type=float, default=0.2,
                        help='Proportion of data to use for testing (0.0-1.0)')
    return parser.parse_args()


def train_model_for_pair(pair, timeframe, days, model_type, optimize, test_size, config):
    """Train a model for a specific currency pair
    
    Args:
        pair (str): Currency pair to train on
        timeframe (str): Timeframe to use
        days (int): Number of days of historical data
        model_type (str): Type of ML model
        optimize (bool): Whether to perform hyperparameter optimization
        test_size (float): Proportion of data to use for testing
        config (dict): Configuration dictionary
        
    Returns:
        bool: True if training was successful, False otherwise
    """
    try:
        logger.info(f"Training model for {pair} on {timeframe} timeframe using {days} days of data")
        
        # Initialize components
        data_fetcher = DataFetcher(config)
        preprocessor = DataPreprocessor()
        indicators = TechnicalIndicators(config)
        
        # Fetch historical data
        start_date = datetime.now() - timedelta(days=days)
        logger.info(f"Fetching historical data from {start_date.strftime('%Y-%m-%d')}")
        
        historical_data = data_fetcher.get_historical_data(
            pair, timeframe, start=start_date, limit=None
        )
        
        if historical_data.empty:
            logger.error(f"No historical data available for {pair}")
            return False
        
        logger.info(f"Fetched {len(historical_data)} data points")
        
        # Preprocess data
        processed_data = preprocessor.process(historical_data)
        
        # Calculate technical indicators
        data_with_indicators = indicators.calculate_all(processed_data)
        
        # Initialize ML model with specific type
        ml_config = config.get('ml_model', {})
        ml_config['model_type'] = model_type
        config['ml_model'] = ml_config
        
        ml_model = MLModel(config)
        
        # Train the model
        logger.info(f"Training {model_type} model")
        success = ml_model.train(
            data_with_indicators, 
            test_size=test_size,
            optimize=optimize
        )
        
        if success:
            # Save the model
            model_path = ml_model.save_model(pair=pair, timeframe=timeframe)
            logger.info(f"Model saved to {model_path}")
            
            # Evaluate the model
            metrics = ml_model.evaluate()
            logger.info(f"Model evaluation metrics:")
            for metric, value in metrics.items():
                logger.info(f"  {metric}: {value}")
            
            return True
        else:
            logger.error(f"Failed to train model for {pair}")
            return False
    
    except Exception as e:
        logger.error(f"Error training model for {pair}: {str(e)}")
        return False


def main():
    """Main function for training ML models"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = Config().get_config()
    
    # Use specified pairs or all configured pairs
    pairs = args.pairs if args.pairs else list(CURRENCY_PAIRS.keys())
    
    # Train models for each pair
    successful_pairs = []
    failed_pairs = []
    
    for pair in pairs:
        logger.info(f"\n{'='*50}\nProcessing {pair}\n{'='*50}")
        
        success = train_model_for_pair(
            pair=pair,
            timeframe=args.timeframe,
            days=args.days,
            model_type=args.model_type,
            optimize=args.optimize,
            test_size=args.test_size,
            config=config
        )
        
        if success:
            successful_pairs.append(pair)
        else:
            failed_pairs.append(pair)
    
    # Print summary
    logger.info("\n\n" + "="*50)
    logger.info("Training Summary")
    logger.info("="*50)
    logger.info(f"Total pairs: {len(pairs)}")
    logger.info(f"Successful: {len(successful_pairs)}")
    logger.info(f"Failed: {len(failed_pairs)}")
    
    if successful_pairs:
        logger.info("\nSuccessful pairs:")
        for pair in successful_pairs:
            logger.info(f"  - {pair}")
    
    if failed_pairs:
        logger.info("\nFailed pairs:")
        for pair in failed_pairs:
            logger.info(f"  - {pair}")


if __name__ == "__main__":
    main()