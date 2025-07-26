#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Currency pairs configuration for TradeBOT
"""

# Dictionary of currency pairs with their settings
# Format: 'SYMBOL': {'timeframe': 'default timeframe', 'enabled': True/False, 'custom_settings': {}}
CURRENCY_PAIRS = {
    'EUR_USD': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Euro / US Dollar',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    },
    'GBP_USD': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'British Pound / US Dollar',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0025,  # 25 pips
            'take_profit': 0.0050,  # 50 pips
        }
    },
    'USD_JPY': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'US Dollar / Japanese Yen',
        'pip_value': 0.01,
        'custom_settings': {
            'stop_loss': 0.25,  # 25 pips
            'take_profit': 0.50,  # 50 pips
        }
    },
    'AUD_USD': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Australian Dollar / US Dollar',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    },
    'USD_CAD': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'US Dollar / Canadian Dollar',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    },
    'NZD_USD': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'New Zealand Dollar / US Dollar',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    },
    'EUR_GBP': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Euro / British Pound',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0015,  # 15 pips
            'take_profit': 0.0030,  # 30 pips
        }
    },
    'EUR_JPY': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Euro / Japanese Yen',
        'pip_value': 0.01,
        'custom_settings': {
            'stop_loss': 0.30,  # 30 pips
            'take_profit': 0.60,  # 60 pips
        }
    },
    'GBP_JPY': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'British Pound / Japanese Yen',
        'pip_value': 0.01,
        'custom_settings': {
            'stop_loss': 0.35,  # 35 pips
            'take_profit': 0.70,  # 70 pips
        }
    },
    'AUD_JPY': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Australian Dollar / Japanese Yen',
        'pip_value': 0.01,
        'custom_settings': {
            'stop_loss': 0.25,  # 25 pips
            'take_profit': 0.50,  # 50 pips
        }
    },
    'CHF_JPY': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Swiss Franc / Japanese Yen',
        'pip_value': 0.01,
        'custom_settings': {
            'stop_loss': 0.25,  # 25 pips
            'take_profit': 0.50,  # 50 pips
        }
    },
    'EUR_CHF': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Euro / Swiss Franc',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0015,  # 15 pips
            'take_profit': 0.0030,  # 30 pips
        }
    },
    'GBP_CHF': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'British Pound / Swiss Franc',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    },
    'USD_CHF': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'US Dollar / Swiss Franc',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    },
    'CAD_CHF': {
        'timeframe': '1m',
        'enabled': True,
        'description': 'Canadian Dollar / Swiss Franc',
        'pip_value': 0.0001,
        'custom_settings': {
            'stop_loss': 0.0020,  # 20 pips
            'take_profit': 0.0040,  # 40 pips
        }
    }
}


def get_enabled_pairs():
    """Get list of enabled currency pairs"""
    return {symbol: data for symbol, data in CURRENCY_PAIRS.items() if data['enabled']}


def get_pair_timeframe(pair):
    """Get the configured timeframe for a specific pair"""
    if pair in CURRENCY_PAIRS:
        return CURRENCY_PAIRS[pair]['timeframe']
    return '1m'  # Default timeframe


def get_pair_settings(pair):
    """Get all settings for a specific pair"""
    if pair in CURRENCY_PAIRS:
        return CURRENCY_PAIRS[pair]
    return None