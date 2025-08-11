import asyncio
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime
import logging
from config import config
from signal_engine import SignalResult
from database import db_manager

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram bot for sending signal notifications"""
    
    def __init__(self):
        self.bot = Bot(token=config.telegram_token)
        self.chat_id = config.telegram_chat_id
        
    async def send_new_signal(self, signal: SignalResult) -> bool:
        """Send new signal notification"""
        try:
            message = self._format_new_signal_message(signal)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Signal notification sent: {signal.code}")
            return True
            
        except TelegramError as e:
            logger.error(f"Error sending signal notification: {str(e)}")
            return False
    
    async def send_signal_result(self, signal_code: str, result_type: str, 
                               entry_price: float = None, close_price: float = None,
                               quantity: float = None) -> bool:
        """Send signal result (WIN/LOSE) notification"""
        try:
            # Get signal from database
            signal = db_manager.get_signal_by_code(signal_code)
            if not signal:
                logger.error(f"Signal {signal_code} not found for result notification")
                return False
            
            message = self._format_result_message(signal, result_type, entry_price, close_price, quantity)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Result notification sent: {signal_code} {result_type}")
            return True
            
        except TelegramError as e:
            logger.error(f"Error sending result notification: {str(e)}")
            return False
    
    async def send_daily_summary(self, date: datetime, metrics: dict) -> bool:
        """Send daily performance summary"""
        try:
            message = self._format_daily_summary(date, metrics)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Daily summary sent for {date.date()}")
            return True
            
        except TelegramError as e:
            logger.error(f"Error sending daily summary: {str(e)}")
            return False
    
    async def send_system_alert(self, level: str, message: str) -> bool:
        """Send system alert/warning"""
        try:
            alert_message = self._format_system_alert(level, message)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=alert_message,
                parse_mode='HTML'
            )
            logger.info(f"System alert sent: {level}")
            return True
            
        except TelegramError as e:
            logger.error(f"Error sending system alert: {str(e)}")
            return False
    
    def _format_new_signal_message(self, signal: SignalResult) -> str:
        """Format new signal message according to specification"""
        direction_emoji = "🟩" if signal.direction == "LONG" else "🟥"
        
        # Calculate RR ratio
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Format volume boost
        volume_boost_pct = signal.volume_boost * 100
        
        # Format ATR percentage
        atr_pct = (signal.atr_value / signal.entry_price) * 100
        
        # Calculate trailing percentage
        mode_config = config.modes[signal.mode]
        trailing_pct = mode_config.trailing_pct * 100
        
        message = f"""<b>🚀 NEW SIGNAL</b>

<b>PAIR</b>      : {signal.symbol}
<b>MODE</b>      : {signal.mode}
<b>SIGNAL</b>    : {signal.direction} {direction_emoji} | Trend: {signal.trend_note} | ADX: {signal.adx_value:.1f}
<b>ENTRY</b>     : {signal.entry_price:.6f}   (qty {signal.quantity:.6f})
<b>SL/TP</b>     : {signal.stop_loss:.6f}  | {signal.take_profit:.6f}   (RR 1:{rr_ratio:.1f}, trail {trailing_pct:.1f}%)
<b>VOL/ATR</b>   : Vol +{volume_boost_pct:.1f}% vs 20-candle | ATR(14)={atr_pct:.2f}%
<b>CODE</b>      : {signal.code}

<i>Score: {signal.score} | Confidence: {signal.confidence}</i>"""
        
        return message
    
    def _format_result_message(self, signal, result_type: str, entry_price: float = None, 
                             close_price: float = None, quantity: float = None) -> str:
        """Format signal result message"""
        direction_emoji = "🟩" if signal.direction == "LONG" else "🟥"
        result_emoji = "✅" if result_type == "WIN" else "❌"
        
        # Use provided prices or signal defaults
        entry = entry_price or signal.entry_price
        close = close_price or (signal.take_profit if result_type == "WIN" else signal.stop_loss)
        qty = quantity or signal.quantity
        
        message = f"""<b>{result_emoji} SIGNAL RESULT</b>

<b>CODE</b>      : {signal.code}
<b>PAIR</b>      : {signal.symbol}
<b>SIGNAL</b>    : {signal.direction} {direction_emoji}
<b>ENTRY</b>     : {entry:.6f}   (qty {qty:.6f})
<b>INFO</b>      : HIT {'TP' if result_type == 'WIN' else 'SL'} | {close:.6f} | <b>{result_type}</b>"""
        
        # Add PnL info if available
        if signal.pnl_percent:
            pnl_emoji = "💰" if signal.pnl_percent > 0 else "💸"
            message += f"\n<b>PnL</b>       : {signal.pnl_percent:.2f}% {pnl_emoji}"
        
        return message
    
    def _format_daily_summary(self, date: datetime, metrics: dict) -> str:
        """Format daily summary message"""
        total_signals = metrics.get('total_signals', 0)
        win_signals = metrics.get('win_signals', 0)
        lose_signals = metrics.get('lose_signals', 0)
        win_rate = metrics.get('win_rate', 0) * 100
        avg_rr = metrics.get('avg_rr', 0)
        total_pnl = metrics.get('total_pnl_percent', 0)
        
        message = f"""<b>📊 DAILY SUMMARY - {date.strftime('%Y-%m-%d')}</b>

<b>Signals Generated:</b> {total_signals}
<b>Results:</b> {win_signals} WIN | {lose_signals} LOSE
<b>Win Rate:</b> {win_rate:.1f}%
<b>Avg RR:</b> 1:{avg_rr:.2f}
<b>Total PnL:</b> {total_pnl:+.2f}%

<b>By Mode:</b>"""
        
        # Add mode breakdown if available
        for mode in ['SCALPING', 'INTRADAY', 'SWING']:
            mode_metrics = metrics.get(f'{mode.lower()}_metrics', {})
            if mode_metrics:
                mode_signals = mode_metrics.get('signals', 0)
                mode_wr = mode_metrics.get('win_rate', 0) * 100
                message += f"\n• {mode}: {mode_signals} signals, {mode_wr:.1f}% WR"
        
        # Market conditions
        avg_adx = metrics.get('avg_adx', 0)
        avg_vol_boost = metrics.get('avg_volume_boost', 0) * 100
        
        message += f"""

<b>Market Conditions:</b>
• Avg ADX: {avg_adx:.1f}
• Avg Volume Boost: +{avg_vol_boost:.1f}%"""
        
        return message
    
    def _format_system_alert(self, level: str, message: str) -> str:
        """Format system alert message"""
        level_emojis = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '🚨',
            'CRITICAL': '🔴'
        }
        
        emoji = level_emojis.get(level, 'ℹ️')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        return f"""<b>{emoji} SYSTEM {level}</b>

<b>Time:</b> {timestamp}
<b>Message:</b> {message}"""

class TelegramManager:
    """Async Telegram manager for handling notifications"""
    
    def __init__(self):
        self.notifier = TelegramNotifier()
        self.notification_queue = asyncio.Queue()
        self.running = False
        
    async def start(self):
        """Start the telegram manager"""
        self.running = True
        logger.info("Telegram manager started")
        
        # Start the notification processor
        asyncio.create_task(self._process_notifications())
    
    async def stop(self):
        """Stop the telegram manager"""
        self.running = False
        logger.info("Telegram manager stopped")
    
    async def _process_notifications(self):
        """Process notification queue"""
        while self.running:
            try:
                # Wait for notification with timeout
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=1.0
                )
                
                # Process the notification
                await self._handle_notification(notification)
                
            except asyncio.TimeoutError:
                # Continue loop on timeout
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {str(e)}")
    
    async def _handle_notification(self, notification: dict):
        """Handle individual notification"""
        try:
            notification_type = notification.get('type')
            
            if notification_type == 'new_signal':
                signal = notification['signal']
                await self.notifier.send_new_signal(signal)
                
            elif notification_type == 'signal_result':
                await self.notifier.send_signal_result(**notification['data'])
                
            elif notification_type == 'daily_summary':
                date = notification['date']
                metrics = notification['metrics']
                await self.notifier.send_daily_summary(date, metrics)
                
            elif notification_type == 'system_alert':
                level = notification['level']
                message = notification['message']
                await self.notifier.send_system_alert(level, message)
                
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                
        except Exception as e:
            logger.error(f"Error handling notification: {str(e)}")
    
    async def queue_new_signal(self, signal: SignalResult):
        """Queue new signal notification"""
        notification = {
            'type': 'new_signal',
            'signal': signal
        }
        await self.notification_queue.put(notification)
        logger.debug(f"Queued new signal notification: {signal.code}")
    
    async def queue_signal_result(self, signal_code: str, result_type: str, **kwargs):
        """Queue signal result notification"""
        notification = {
            'type': 'signal_result',
            'data': {
                'signal_code': signal_code,
                'result_type': result_type,
                **kwargs
            }
        }
        await self.notification_queue.put(notification)
        logger.debug(f"Queued signal result notification: {signal_code} {result_type}")
    
    async def queue_daily_summary(self, date: datetime, metrics: dict):
        """Queue daily summary notification"""
        notification = {
            'type': 'daily_summary',
            'date': date,
            'metrics': metrics
        }
        await self.notification_queue.put(notification)
        logger.debug(f"Queued daily summary notification for {date.date()}")
    
    async def queue_system_alert(self, level: str, message: str):
        """Queue system alert notification"""
        notification = {
            'type': 'system_alert',
            'level': level,
            'message': message
        }
        await self.notification_queue.put(notification)
        logger.debug(f"Queued system alert: {level}")
    
    # Synchronous wrappers for non-async contexts
    def send_new_signal_sync(self, signal: SignalResult):
        """Synchronous wrapper for sending new signal"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If event loop is running, create task
            asyncio.create_task(self.queue_new_signal(signal))
        else:
            # If no event loop, run it
            loop.run_until_complete(self.queue_new_signal(signal))
    
    def send_signal_result_sync(self, signal_code: str, result_type: str, **kwargs):
        """Synchronous wrapper for sending signal result"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.queue_signal_result(signal_code, result_type, **kwargs))
        else:
            loop.run_until_complete(self.queue_signal_result(signal_code, result_type, **kwargs))
    
    def send_daily_summary_sync(self, date: datetime, metrics: dict):
        """Synchronous wrapper for sending daily summary"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.queue_daily_summary(date, metrics))
        else:
            loop.run_until_complete(self.queue_daily_summary(date, metrics))
    
    def send_system_alert_sync(self, level: str, message: str):
        """Synchronous wrapper for sending system alert"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.queue_system_alert(level, message))
        else:
            loop.run_until_complete(self.queue_system_alert(level, message))
    
    async def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            bot_info = await self.notifier.bot.get_me()
            logger.info(f"Telegram bot connected: @{bot_info.username}")
            
            # Send test message
            await self.notifier.bot.send_message(
                chat_id=self.notifier.chat_id,
                text="🤖 <b>Signal Bot Connected</b>\n\nBot is online and ready to send signals!",
                parse_mode='HTML'
            )
            
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram bot connection failed: {str(e)}")
            return False

# Global telegram manager instance
telegram_manager = TelegramManager()