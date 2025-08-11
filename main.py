#!/usr/bin/env python3
"""
Futures Signal Bot - Main Orchestrator

This is the main entry point for the futures signal bot.
It coordinates all components and runs the signal generation and monitoring system.
"""

import asyncio
import schedule
import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import signal as signal_handler

# Import all bot components
from config import config
from data_handler import data_handler
from signal_engine import signal_engine
from telegram_bot import telegram_manager
from monitoring_system import signal_monitor, performance_analyzer, risk_manager
from database import db_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class SignalBotOrchestrator:
    """Main orchestrator for the signal bot"""
    
    def __init__(self):
        self.running = False
        self.startup_complete = False
        self.last_signal_check = {}  # symbol_mode -> last_check_time
        
    async def start(self):
        """Start the signal bot"""
        try:
            logger.info("🚀 Starting Futures Signal Bot...")
            
            # Initialize components
            await self._initialize_components()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Schedule periodic tasks
            self._schedule_tasks()
            
            self.running = True
            self.startup_complete = True
            
            logger.info("✅ Signal Bot started successfully!")
            
            # Send startup notification
            await telegram_manager.queue_system_alert(
                'INFO', 
                'Signal Bot started successfully and is now monitoring markets 24/7'
            )
            
            # Start main event loop
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Error starting signal bot: {str(e)}")
            await self._emergency_shutdown()
            
    async def stop(self):
        """Stop the signal bot"""
        logger.info("🛑 Stopping Signal Bot...")
        
        self.running = False
        
        # Stop components
        await signal_monitor.stop_monitoring()
        await telegram_manager.stop()
        
        # Send shutdown notification
        await telegram_manager.queue_system_alert(
            'INFO', 
            'Signal Bot stopped gracefully'
        )
        
        logger.info("✅ Signal Bot stopped")
    
    async def _initialize_components(self):
        """Initialize all bot components"""
        logger.info("Initializing bot components...")
        
        # Test exchange connection
        try:
            # Test data handler
            test_price = data_handler.get_current_price('BTCUSDT')
            if not test_price:
                raise Exception("Failed to fetch test price from exchange")
            logger.info(f"✅ Exchange connection OK (BTC: ${test_price:,.2f})")
            
        except Exception as e:
            logger.error(f"❌ Exchange connection failed: {str(e)}")
            raise
        
        # Test Telegram connection
        try:
            telegram_connected = await telegram_manager.test_connection()
            if not telegram_connected:
                raise Exception("Failed to connect to Telegram")
            logger.info("✅ Telegram connection OK")
            
        except Exception as e:
            logger.error(f"❌ Telegram connection failed: {str(e)}")
            raise
        
        # Test database
        try:
            # Test database connection by getting active signals
            active_signals = db_manager.get_active_signals()
            logger.info(f"✅ Database connection OK ({len(active_signals)} active signals)")
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            raise
        
        logger.info("✅ All components initialized successfully")
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        logger.info("Starting background tasks...")
        
        # Start telegram manager
        await telegram_manager.start()
        
        # Start signal monitoring
        await signal_monitor.start_monitoring()
        
        logger.info("✅ Background tasks started")
    
    def _schedule_tasks(self):
        """Schedule periodic tasks"""
        logger.info("Scheduling periodic tasks...")
        
        # Signal generation schedules (different frequencies for different modes)
        schedule.every(1).minutes.do(self._schedule_async_task, self._check_scalping_signals)
        schedule.every(5).minutes.do(self._schedule_async_task, self._check_intraday_signals)
        schedule.every(15).minutes.do(self._schedule_async_task, self._check_swing_signals)
        
        # Daily summary at 23:50 UTC
        schedule.every().day.at("23:50").do(self._schedule_async_task, self._send_daily_summary)
        
        # Cleanup expired signals every hour
        schedule.every().hour.do(self._schedule_async_task, self._cleanup_expired_signals)
        
        # Update daily metrics every 6 hours
        schedule.every(6).hours.do(self._schedule_async_task, self._update_daily_metrics)
        
        # Clear data cache every 30 minutes
        schedule.every(30).minutes.do(self._clear_data_cache)
        
        logger.info("✅ Periodic tasks scheduled")
    
    def _schedule_async_task(self, coro):
        """Schedule async task to run in event loop"""
        if self.running:
            asyncio.create_task(coro())
    
    async def _main_loop(self):
        """Main event loop"""
        logger.info("Entering main event loop...")
        
        while self.running:
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Health checks
                await self._health_check()
                
                # Sleep for a short time
                await asyncio.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_scalping_signals(self):
        """Check for scalping signals on all symbols"""
        if not self.running:
            return
            
        logger.debug("Checking scalping signals...")
        
        try:
            # Check risk limits first
            risk_ok, daily_pnl = risk_manager.check_daily_loss_limit()
            if not risk_ok:
                logger.warning(f"Daily loss limit reached ({daily_pnl:.2f}%), skipping signals")
                return
            
            signals_generated = 0
            
            for symbol in config.symbols:
                try:
                    # Check cooldowns and limits
                    if not self._can_generate_signal(symbol, 'SCALPING'):
                        continue
                    
                    # Analyze symbol for signals
                    signal_result = signal_engine.analyze_symbol(symbol, 'SCALPING')
                    
                    if signal_result:
                        # Process the signal
                        success = await self._process_new_signal(signal_result)
                        if success:
                            signals_generated += 1
                            
                except Exception as e:
                    logger.error(f"Error checking scalping signal for {symbol}: {str(e)}")
            
            if signals_generated > 0:
                logger.info(f"Generated {signals_generated} scalping signals")
                
        except Exception as e:
            logger.error(f"Error in scalping signal check: {str(e)}")
    
    async def _check_intraday_signals(self):
        """Check for intraday signals on all symbols"""
        if not self.running:
            return
            
        logger.debug("Checking intraday signals...")
        
        try:
            # Check risk limits first
            risk_ok, daily_pnl = risk_manager.check_daily_loss_limit()
            if not risk_ok:
                logger.warning(f"Daily loss limit reached ({daily_pnl:.2f}%), skipping signals")
                return
            
            signals_generated = 0
            
            for symbol in config.symbols:
                try:
                    # Check cooldowns and limits
                    if not self._can_generate_signal(symbol, 'INTRADAY'):
                        continue
                    
                    # Analyze symbol for signals
                    signal_result = signal_engine.analyze_symbol(symbol, 'INTRADAY')
                    
                    if signal_result:
                        # Process the signal
                        success = await self._process_new_signal(signal_result)
                        if success:
                            signals_generated += 1
                            
                except Exception as e:
                    logger.error(f"Error checking intraday signal for {symbol}: {str(e)}")
            
            if signals_generated > 0:
                logger.info(f"Generated {signals_generated} intraday signals")
                
        except Exception as e:
            logger.error(f"Error in intraday signal check: {str(e)}")
    
    async def _check_swing_signals(self):
        """Check for swing signals on all symbols"""
        if not self.running:
            return
            
        logger.debug("Checking swing signals...")
        
        try:
            # Check risk limits first
            risk_ok, daily_pnl = risk_manager.check_daily_loss_limit()
            if not risk_ok:
                logger.warning(f"Daily loss limit reached ({daily_pnl:.2f}%), skipping signals")
                return
            
            signals_generated = 0
            
            for symbol in config.symbols:
                try:
                    # Check cooldowns and limits
                    if not self._can_generate_signal(symbol, 'SWING'):
                        continue
                    
                    # Analyze symbol for signals
                    signal_result = signal_engine.analyze_symbol(symbol, 'SWING')
                    
                    if signal_result:
                        # Process the signal
                        success = await self._process_new_signal(signal_result)
                        if success:
                            signals_generated += 1
                            
                except Exception as e:
                    logger.error(f"Error checking swing signal for {symbol}: {str(e)}")
            
            if signals_generated > 0:
                logger.info(f"Generated {signals_generated} swing signals")
                
        except Exception as e:
            logger.error(f"Error in swing signal check: {str(e)}")
    
    def _can_generate_signal(self, symbol: str, mode: str) -> bool:
        """Check if we can generate a signal for symbol/mode"""
        try:
            # Check concurrent signals limit
            if not risk_manager.check_concurrent_signals_limit(symbol, mode):
                return False
            
            # Check for recent signal generation (prevent spam)
            key = f"{symbol}_{mode}"
            now = datetime.utcnow()
            
            if key in self.last_signal_check:
                time_since_last = (now - self.last_signal_check[key]).total_seconds()
                min_interval = 300  # 5 minutes minimum between checks for same symbol/mode
                
                if time_since_last < min_interval:
                    return False
            
            # Update last check time
            self.last_signal_check[key] = now
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal generation capability: {str(e)}")
            return False
    
    async def _process_new_signal(self, signal_result) -> bool:
        """Process a new signal"""
        try:
            # Save signal to database
            signal_id = db_manager.save_signal(signal_result)
            
            if not signal_id:
                logger.error(f"Failed to save signal {signal_result.code}")
                return False
            
            # Send Telegram notification
            await telegram_manager.queue_new_signal(signal_result)
            
            # Add to monitoring
            await signal_monitor.add_signal_to_monitoring(signal_result.code)
            
            # Log event
            db_manager.log_event(
                'INFO',
                f"Signal generated: {signal_result.symbol} {signal_result.mode} {signal_result.direction}",
                module='signal_generation',
                symbol=signal_result.symbol,
                mode=signal_result.mode
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing new signal: {str(e)}")
            return False
    
    async def _send_daily_summary(self):
        """Send daily performance summary"""
        if not self.running:
            return
            
        try:
            logger.info("Generating daily summary...")
            
            # Calculate daily metrics
            today = datetime.utcnow()
            metrics = performance_analyzer.calculate_daily_metrics(today)
            
            if metrics:
                # Send summary via Telegram
                await telegram_manager.queue_daily_summary(today, metrics)
                logger.info("Daily summary sent")
            else:
                logger.warning("No metrics available for daily summary")
                
        except Exception as e:
            logger.error(f"Error sending daily summary: {str(e)}")
    
    async def _cleanup_expired_signals(self):
        """Clean up expired signals"""
        if not self.running:
            return
            
        try:
            # This is handled by the signal monitor, but we can add additional cleanup here
            logger.debug("Running signal cleanup...")
            
        except Exception as e:
            logger.error(f"Error in signal cleanup: {str(e)}")
    
    async def _update_daily_metrics(self):
        """Update daily metrics in database"""
        if not self.running:
            return
            
        try:
            logger.debug("Updating daily metrics...")
            
            today = datetime.utcnow()
            
            # Update overall metrics
            db_manager.calculate_daily_metrics(today)
            
            # Update mode-specific metrics
            for mode in ['SCALPING', 'INTRADAY', 'SWING']:
                db_manager.calculate_daily_metrics(today, mode=mode)
            
            # Update symbol-specific metrics
            for symbol in config.symbols:
                db_manager.calculate_daily_metrics(today, symbol=symbol)
            
            logger.debug("Daily metrics updated")
            
        except Exception as e:
            logger.error(f"Error updating daily metrics: {str(e)}")
    
    def _clear_data_cache(self):
        """Clear data cache periodically"""
        if not self.running:
            return
            
        try:
            data_handler.clear_cache()
            logger.debug("Data cache cleared")
            
        except Exception as e:
            logger.error(f"Error clearing data cache: {str(e)}")
    
    async def _health_check(self):
        """Perform health checks"""
        try:
            # Check if components are still running
            if not signal_monitor.monitoring:
                logger.warning("Signal monitor not running, restarting...")
                await signal_monitor.start_monitoring()
            
            if not telegram_manager.running:
                logger.warning("Telegram manager not running, restarting...")
                await telegram_manager.start()
            
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
    
    async def _emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.error("🚨 Initiating emergency shutdown...")
        
        try:
            # Send emergency alert
            await telegram_manager.queue_system_alert(
                'CRITICAL',
                'Signal Bot encountered a critical error and is shutting down'
            )
            
            # Stop components
            await self.stop()
            
        except Exception as e:
            logger.error(f"Error during emergency shutdown: {str(e)}")
    
    def get_status(self) -> Dict:
        """Get bot status"""
        return {
            'running': self.running,
            'startup_complete': self.startup_complete,
            'uptime_seconds': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            'monitoring_status': signal_monitor.get_monitoring_status(),
            'last_signal_checks': dict(self.last_signal_check),
            'scheduled_jobs': len(schedule.jobs)
        }

# Global orchestrator instance
orchestrator = SignalBotOrchestrator()

def signal_handler_func(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    orchestrator.running = False

async def main():
    """Main entry point"""
    try:
        # Set up signal handlers for graceful shutdown
        signal_handler.signal(signal_handler.SIGINT, signal_handler_func)
        signal_handler.signal(signal_handler.SIGTERM, signal_handler_func)
        
        # Start the bot
        await orchestrator.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        # Ensure clean shutdown
        await orchestrator.stop()

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║               🚀 FUTURES SIGNAL BOT 🚀                       ║
    ║                                                               ║
    ║  Multi-Timeframe Technical Analysis Signal Generator          ║
    ║  Modes: Scalping | Intraday | Swing                          ║
    ║  24/7 Automated Signal Detection & Monitoring                ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check if configuration is valid
    if not config.telegram_token or not config.telegram_chat_id:
        print("❌ Error: Telegram configuration missing!")
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file")
        sys.exit(1)
    
    if not config.symbols:
        print("❌ Error: No symbols configured!")
        print("Please set SYMBOLS in your .env file")
        sys.exit(1)
    
    print(f"📊 Configured symbols: {', '.join(config.symbols)}")
    print(f"💰 Risk per trade: {config.risk_per_trade*100:.1f}%")
    print(f"📱 Telegram chat: {config.telegram_chat_id}")
    print("\nStarting bot...\n")
    
    # Run the bot
    asyncio.run(main())