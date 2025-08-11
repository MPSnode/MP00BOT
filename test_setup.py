#!/usr/bin/env python3
"""
Test Script for Futures Signal Bot

This script tests all major components to ensure the bot is properly configured.
Run this before starting the main bot to verify everything works.
"""

import asyncio
import sys
from datetime import datetime
import logging

# Configure minimal logging for tests
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from config import config
        print("  ✅ Config module imported")
        
        from data_handler import data_handler
        print("  ✅ Data handler imported")
        
        from indicators import indicator_analysis
        print("  ✅ Indicators module imported")
        
        from signal_engine import signal_engine
        print("  ✅ Signal engine imported")
        
        from telegram_bot import telegram_manager
        print("  ✅ Telegram bot imported")
        
        from monitoring_system import signal_monitor, performance_analyzer, risk_manager
        print("  ✅ Monitoring system imported")
        
        from database import db_manager
        print("  ✅ Database manager imported")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {str(e)}")
        return False

def test_configuration():
    """Test configuration settings"""
    print("\n🔍 Testing configuration...")
    
    try:
        from config import config
        
        # Check required config
        required_fields = [
            'telegram_token', 'telegram_chat_id', 'symbols', 
            'exchange_name', 'initial_equity'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(config, field, None):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"  ❌ Missing configuration: {', '.join(missing_fields)}")
            return False
        
        print(f"  ✅ Exchange: {config.exchange_name}")
        print(f"  ✅ Symbols: {len(config.symbols)} configured")
        print(f"  ✅ Risk per trade: {config.risk_per_trade*100:.1f}%")
        print(f"  ✅ Daily loss cap: {config.daily_loss_cap*100:.1f}%")
        
        # Test mode configurations
        for mode_name, mode_config in config.modes.items():
            print(f"  ✅ {mode_name}: {mode_config.primary_tf}/{mode_config.confirm_tf}, score_min={mode_config.score_min}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {str(e)}")
        return False

def test_database():
    """Test database connection and tables"""
    print("\n🔍 Testing database...")
    
    try:
        from database import db_manager
        
        # Test database connection
        session = db_manager.get_session()
        session.close()
        print("  ✅ Database connection successful")
        
        # Test getting active signals (should work even if empty)
        active_signals = db_manager.get_active_signals()
        print(f"  ✅ Found {len(active_signals)} active signals")
        
        # Test logging
        db_manager.log_event('INFO', 'Test setup script running', module='test_setup')
        print("  ✅ Event logging works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {str(e)}")
        return False

def test_exchange_connection():
    """Test exchange API connection"""
    print("\n🔍 Testing exchange connection...")
    
    try:
        from data_handler import data_handler
        
        # Test getting current price
        test_symbol = 'BTCUSDT'
        price = data_handler.get_current_price(test_symbol)
        
        if price and price > 0:
            print(f"  ✅ Exchange API works (BTC: ${price:,.2f})")
        else:
            print("  ❌ Failed to get price from exchange")
            return False
        
        # Test market info
        market_info = data_handler.get_market_info(test_symbol)
        if market_info:
            print(f"  ✅ Market info retrieved (spread: {market_info.get('spread_pct', 0):.4f}%)")
        else:
            print("  ❌ Failed to get market info")
            return False
        
        # Test market validation
        is_valid, reason = data_handler.validate_market_conditions(test_symbol)
        print(f"  ✅ Market validation: {is_valid} ({reason})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Exchange connection error: {str(e)}")
        return False

async def test_telegram():
    """Test Telegram bot connection"""
    print("\n🔍 Testing Telegram connection...")
    
    try:
        from telegram_bot import telegram_manager
        
        # Test connection
        connected = await telegram_manager.test_connection()
        
        if connected:
            print("  ✅ Telegram bot connected successfully")
            return True
        else:
            print("  ❌ Telegram bot connection failed")
            return False
        
    except Exception as e:
        print(f"  ❌ Telegram error: {str(e)}")
        return False

def test_indicators():
    """Test technical indicators calculation"""
    print("\n🔍 Testing indicators...")
    
    try:
        from data_handler import data_handler
        from indicators import indicator_analysis
        import pandas as pd
        import numpy as np
        
        # Get test data
        test_symbol = 'BTCUSDT'
        df = data_handler.fetch_ohlcv(test_symbol, '1h', limit=100)
        
        if df.empty:
            print("  ❌ No data retrieved for indicator testing")
            return False
        
        print(f"  ✅ Retrieved {len(df)} candles for testing")
        
        # Test indicator calculations
        df_with_indicators = indicator_analysis.calculate_all_indicators(df)
        
        # Check if indicators were calculated
        required_indicators = ['ema_20', 'ema_50', 'ema_200', 'rsi', 'atr', 'adx', 'macd_line']
        
        for indicator in required_indicators:
            if indicator in df_with_indicators.columns:
                non_nan_count = df_with_indicators[indicator].notna().sum()
                print(f"  ✅ {indicator}: {non_nan_count}/{len(df)} values calculated")
            else:
                print(f"  ❌ {indicator}: missing")
                return False
        
        # Test trend bias detection
        trend_bias = indicator_analysis.get_trend_bias(df_with_indicators, 'INTRADAY')
        print(f"  ✅ Trend bias detection: {trend_bias}")
        
        # Test volume boost check
        has_boost, boost_ratio = indicator_analysis.check_volume_boost(df_with_indicators, 0.15)
        print(f"  ✅ Volume boost check: {has_boost} ({boost_ratio:.2%})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Indicators error: {str(e)}")
        return False

def test_signal_engine():
    """Test signal engine functionality"""
    print("\n🔍 Testing signal engine...")
    
    try:
        from signal_engine import signal_engine
        from config import config
        
        # Test cooldown functionality
        test_symbol = config.symbols[0] if config.symbols else 'BTCUSDT'
        
        # Check if we can generate signals (should be True initially)
        can_generate_scalping = not signal_engine._is_in_cooldown(test_symbol, 'SCALPING')
        can_generate_intraday = not signal_engine._is_in_cooldown(test_symbol, 'INTRADAY')
        
        print(f"  ✅ Cooldown check - Scalping: {can_generate_scalping}, Intraday: {can_generate_intraday}")
        
        # Test signal code generation
        signal_code = signal_engine._generate_signal_code()
        print(f"  ✅ Signal code generation: {signal_code}")
        
        # Test confidence level calculation
        confidence_high = signal_engine._get_confidence_level(85)
        confidence_medium = signal_engine._get_confidence_level(70)
        confidence_low = signal_engine._get_confidence_level(55)
        
        print(f"  ✅ Confidence levels: HIGH={confidence_high}, MEDIUM={confidence_medium}, LOW={confidence_low}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Signal engine error: {str(e)}")
        return False

async def test_full_signal_generation():
    """Test complete signal generation process"""
    print("\n🔍 Testing signal generation (dry run)...")
    
    try:
        from signal_engine import signal_engine
        from config import config
        
        test_symbol = config.symbols[0] if config.symbols else 'BTCUSDT'
        
        print(f"  Testing signal generation for {test_symbol}...")
        
        # Test each mode
        for mode in ['SCALPING', 'INTRADAY', 'SWING']:
            try:
                signal_result = signal_engine.analyze_symbol(test_symbol, mode)
                
                if signal_result:
                    print(f"  ✅ {mode}: Signal generated! {signal_result.direction} score={signal_result.score}")
                else:
                    print(f"  ℹ️  {mode}: No signal (market conditions not met)")
                    
            except Exception as e:
                print(f"  ❌ {mode}: Error - {str(e)}")
                
        return True
        
    except Exception as e:
        print(f"  ❌ Signal generation error: {str(e)}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Futures Signal Bot Setup Tests\n")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Database", test_database),
        ("Exchange Connection", test_exchange_connection),
        ("Telegram Connection", test_telegram),
        ("Indicators", test_indicators),
        ("Signal Engine", test_signal_engine),
        ("Signal Generation", test_full_signal_generation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"  ❌ Test failed with exception: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("="*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your bot is ready to run.")
        print("🚀 You can now start the bot with: python main.py")
        return True
    else:
        print(f"\n⚠️  {total-passed} tests failed. Please fix the issues before running the bot.")
        print("📚 Check the README.md for setup instructions.")
        return False

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║                  🧪 SIGNAL BOT SETUP TEST 🧪                 ║
    ║                                                               ║
    ║  This script verifies your bot configuration and components   ║
    ║  Run this before starting the main bot for the first time    ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        sys.exit(1)