import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from config import config
from data_handler import data_handler
from database import db_manager, Signal
from telegram_bot import telegram_manager

logger = logging.getLogger(__name__)

class SignalMonitor:
    """Monitor active signals for TP/SL hits and manage lifecycle"""
    
    def __init__(self):
        self.active_signals: Dict[str, Signal] = {}  # code -> Signal
        self.price_cache: Dict[str, float] = {}  # symbol -> current_price
        self.trailing_stops: Dict[str, float] = {}  # signal_code -> trailing_stop_price
        self.monitoring = False
        
    async def start_monitoring(self):
        """Start signal monitoring"""
        self.monitoring = True
        logger.info("Signal monitoring started")
        
        # Load active signals from database
        await self._load_active_signals()
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_signals())
        asyncio.create_task(self._update_prices())
        asyncio.create_task(self._check_expired_signals())
    
    async def stop_monitoring(self):
        """Stop signal monitoring"""
        self.monitoring = False
        logger.info("Signal monitoring stopped")
    
    async def _load_active_signals(self):
        """Load active signals from database"""
        try:
            active_signals = db_manager.get_active_signals()
            
            for signal in active_signals:
                self.active_signals[signal.code] = signal
                
                # Initialize trailing stop if signal is filled
                if signal.status == 'FILLED' and signal.fill_price:
                    self._initialize_trailing_stop(signal)
            
            logger.info(f"Loaded {len(active_signals)} active signals for monitoring")
            
        except Exception as e:
            logger.error(f"Error loading active signals: {str(e)}")
    
    async def add_signal_to_monitoring(self, signal_code: str):
        """Add new signal to monitoring"""
        try:
            signal = db_manager.get_signal_by_code(signal_code)
            if signal and signal.status in ['NEW', 'FILLED']:
                self.active_signals[signal_code] = signal
                
                if signal.status == 'FILLED' and signal.fill_price:
                    self._initialize_trailing_stop(signal)
                
                logger.info(f"Added signal {signal_code} to monitoring")
                
        except Exception as e:
            logger.error(f"Error adding signal to monitoring: {str(e)}")
    
    def _initialize_trailing_stop(self, signal: Signal):
        """Initialize trailing stop for a filled signal"""
        try:
            mode_config = config.modes[signal.mode]
            trailing_distance = signal.atr_value * mode_config.sl_atr_mult * 0.5  # Half ATR for trailing
            
            if signal.direction == 'LONG':
                # Trailing stop starts below entry price
                initial_trailing = signal.fill_price - trailing_distance
                self.trailing_stops[signal.code] = max(initial_trailing, signal.stop_loss)
            else:
                # Trailing stop starts above entry price  
                initial_trailing = signal.fill_price + trailing_distance
                self.trailing_stops[signal.code] = min(initial_trailing, signal.stop_loss)
            
            logger.debug(f"Initialized trailing stop for {signal.code}: {self.trailing_stops[signal.code]}")
            
        except Exception as e:
            logger.error(f"Error initializing trailing stop: {str(e)}")
    
    async def _monitor_signals(self):
        """Main signal monitoring loop"""
        while self.monitoring:
            try:
                # Monitor each active signal
                signals_to_remove = []
                
                for signal_code, signal in self.active_signals.items():
                    result = await self._check_signal_status(signal)
                    
                    if result:
                        signals_to_remove.append(signal_code)
                
                # Remove completed signals
                for signal_code in signals_to_remove:
                    self.active_signals.pop(signal_code, None)
                    self.trailing_stops.pop(signal_code, None)
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in signal monitoring loop: {str(e)}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_signal_status(self, signal: Signal) -> bool:
        """
        Check individual signal status
        
        Returns:
            True if signal is completed (remove from monitoring)
        """
        try:
            current_price = self.price_cache.get(signal.symbol)
            if not current_price:
                return False
            
            # Check for expired NEW signals
            if signal.status == 'NEW':
                if datetime.utcnow() > signal.validity_until:
                    await self._handle_signal_expired(signal)
                    return True
                
                # Check if entry price is hit
                if self._is_entry_hit(signal, current_price):
                    await self._handle_signal_filled(signal, current_price)
                    return False  # Continue monitoring as FILLED
            
            # Check filled signals for TP/SL/Trailing
            elif signal.status == 'FILLED':
                # Check take profit
                if self._is_take_profit_hit(signal, current_price):
                    await self._handle_take_profit(signal, current_price)
                    return True
                
                # Check trailing stop
                if signal.code in self.trailing_stops:
                    if self._is_trailing_stop_hit(signal, current_price):
                        await self._handle_trailing_stop(signal, current_price)
                        return True
                    else:
                        # Update trailing stop
                        self._update_trailing_stop(signal, current_price)
                
                # Check regular stop loss
                elif self._is_stop_loss_hit(signal, current_price):
                    await self._handle_stop_loss(signal, current_price)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking signal {signal.code}: {str(e)}")
            return False
    
    def _is_entry_hit(self, signal: Signal, current_price: float) -> bool:
        """Check if entry price is hit"""
        tolerance = 0.001  # 0.1% tolerance
        
        if signal.direction == 'LONG':
            # For long, entry when price drops to or below entry level
            return current_price <= signal.entry_price * (1 + tolerance)
        else:
            # For short, entry when price rises to or above entry level
            return current_price >= signal.entry_price * (1 - tolerance)
    
    def _is_take_profit_hit(self, signal: Signal, current_price: float) -> bool:
        """Check if take profit is hit"""
        if signal.direction == 'LONG':
            return current_price >= signal.take_profit
        else:
            return current_price <= signal.take_profit
    
    def _is_stop_loss_hit(self, signal: Signal, current_price: float) -> bool:
        """Check if stop loss is hit"""
        if signal.direction == 'LONG':
            return current_price <= signal.stop_loss
        else:
            return current_price >= signal.stop_loss
    
    def _is_trailing_stop_hit(self, signal: Signal, current_price: float) -> bool:
        """Check if trailing stop is hit"""
        trailing_stop = self.trailing_stops.get(signal.code)
        if not trailing_stop:
            return False
        
        if signal.direction == 'LONG':
            return current_price <= trailing_stop
        else:
            return current_price >= trailing_stop
    
    def _update_trailing_stop(self, signal: Signal, current_price: float):
        """Update trailing stop based on current price"""
        try:
            if signal.code not in self.trailing_stops:
                return
            
            mode_config = config.modes[signal.mode]
            trailing_distance = current_price * mode_config.trailing_pct
            
            current_trailing = self.trailing_stops[signal.code]
            
            if signal.direction == 'LONG':
                # Move trailing stop up if price moves favorably
                new_trailing = current_price - trailing_distance
                if new_trailing > current_trailing:
                    self.trailing_stops[signal.code] = new_trailing
                    logger.debug(f"Updated trailing stop for {signal.code}: {new_trailing}")
            else:
                # Move trailing stop down if price moves favorably
                new_trailing = current_price + trailing_distance
                if new_trailing < current_trailing:
                    self.trailing_stops[signal.code] = new_trailing
                    logger.debug(f"Updated trailing stop for {signal.code}: {new_trailing}")
                    
        except Exception as e:
            logger.error(f"Error updating trailing stop: {str(e)}")
    
    async def _handle_signal_expired(self, signal: Signal):
        """Handle expired signal"""
        try:
            db_manager.update_signal_status(signal.code, 'CANCELLED', close_reason='EXPIRED')
            logger.info(f"Signal {signal.code} expired")
            
            # Send notification (optional)
            await telegram_manager.queue_system_alert(
                'INFO', 
                f"Signal {signal.code} ({signal.symbol}) expired without entry"
            )
            
        except Exception as e:
            logger.error(f"Error handling expired signal: {str(e)}")
    
    async def _handle_signal_filled(self, signal: Signal, fill_price: float):
        """Handle signal entry fill"""
        try:
            db_manager.update_signal_status(
                signal.code, 
                'FILLED', 
                fill_price=fill_price
            )
            
            # Update local signal object
            signal.status = 'FILLED'
            signal.fill_price = fill_price
            signal.filled_at = datetime.utcnow()
            
            # Initialize trailing stop
            self._initialize_trailing_stop(signal)
            
            logger.info(f"Signal {signal.code} filled at {fill_price}")
            
            # Record execution
            db_manager.add_signal_execution(signal.code, 'ENTRY', fill_price, signal.quantity)
            
        except Exception as e:
            logger.error(f"Error handling signal fill: {str(e)}")
    
    async def _handle_take_profit(self, signal: Signal, close_price: float):
        """Handle take profit hit"""
        try:
            db_manager.update_signal_status(
                signal.code, 
                'WIN', 
                close_price=close_price,
                close_reason='TP'
            )
            
            logger.info(f"Signal {signal.code} hit TP at {close_price}")
            
            # Record execution
            db_manager.add_signal_execution(signal.code, 'TP', close_price, signal.quantity)
            
            # Send result notification
            await telegram_manager.queue_signal_result(
                signal.code, 
                'WIN',
                entry_price=signal.fill_price,
                close_price=close_price,
                quantity=signal.quantity
            )
            
        except Exception as e:
            logger.error(f"Error handling take profit: {str(e)}")
    
    async def _handle_stop_loss(self, signal: Signal, close_price: float):
        """Handle stop loss hit"""
        try:
            db_manager.update_signal_status(
                signal.code, 
                'LOSE', 
                close_price=close_price,
                close_reason='SL'
            )
            
            logger.info(f"Signal {signal.code} hit SL at {close_price}")
            
            # Record execution
            db_manager.add_signal_execution(signal.code, 'SL', close_price, signal.quantity)
            
            # Send result notification
            await telegram_manager.queue_signal_result(
                signal.code, 
                'LOSE',
                entry_price=signal.fill_price,
                close_price=close_price,
                quantity=signal.quantity
            )
            
            # Add cooldown for this symbol/mode
            mode_config = config.modes[signal.mode]
            cooldown_until = datetime.utcnow() + timedelta(minutes=mode_config.cooldown_minutes)
            db_manager.add_cooldown(signal.symbol, signal.mode, 'LOSS', cooldown_until)
            
        except Exception as e:
            logger.error(f"Error handling stop loss: {str(e)}")
    
    async def _handle_trailing_stop(self, signal: Signal, close_price: float):
        """Handle trailing stop hit"""
        try:
            # Trailing stop hit is considered a win if price moved favorably first
            result_type = 'WIN' if self._was_profitable_before_trailing(signal) else 'LOSE'
            
            db_manager.update_signal_status(
                signal.code, 
                result_type, 
                close_price=close_price,
                close_reason='TRAILING'
            )
            
            logger.info(f"Signal {signal.code} hit trailing stop at {close_price}")
            
            # Record execution
            db_manager.add_signal_execution(signal.code, 'TRAILING', close_price, signal.quantity)
            
            # Send result notification
            await telegram_manager.queue_signal_result(
                signal.code, 
                result_type,
                entry_price=signal.fill_price,
                close_price=close_price,
                quantity=signal.quantity
            )
            
        except Exception as e:
            logger.error(f"Error handling trailing stop: {str(e)}")
    
    def _was_profitable_before_trailing(self, signal: Signal) -> bool:
        """Check if signal was profitable before trailing stop hit"""
        try:
            # Simple heuristic: if trailing stop is better than original SL, it was profitable
            if signal.direction == 'LONG':
                return self.trailing_stops.get(signal.code, signal.stop_loss) > signal.stop_loss
            else:
                return self.trailing_stops.get(signal.code, signal.stop_loss) < signal.stop_loss
        except:
            return False
    
    async def _update_prices(self):
        """Update current prices for all monitored symbols"""
        while self.monitoring:
            try:
                # Get unique symbols from active signals
                symbols = set(signal.symbol for signal in self.active_signals.values())
                
                # Update prices
                for symbol in symbols:
                    price = data_handler.get_current_price(symbol)
                    if price:
                        self.price_cache[symbol] = price
                
                # Update every 5 seconds
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error updating prices: {str(e)}")
                await asyncio.sleep(10)
    
    async def _check_expired_signals(self):
        """Check for expired signals periodically"""
        while self.monitoring:
            try:
                current_time = datetime.utcnow()
                expired_signals = []
                
                for signal_code, signal in self.active_signals.items():
                    if (signal.status == 'NEW' and 
                        signal.validity_until and 
                        current_time > signal.validity_until):
                        expired_signals.append(signal)
                
                # Handle expired signals
                for signal in expired_signals:
                    await self._handle_signal_expired(signal)
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error checking expired signals: {str(e)}")
                await asyncio.sleep(60)
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            'monitoring': self.monitoring,
            'active_signals': len(self.active_signals),
            'symbols_tracked': len(set(s.symbol for s in self.active_signals.values())),
            'new_signals': len([s for s in self.active_signals.values() if s.status == 'NEW']),
            'filled_signals': len([s for s in self.active_signals.values() if s.status == 'FILLED']),
            'trailing_stops': len(self.trailing_stops),
            'last_update': datetime.utcnow().isoformat()
        }

class PerformanceAnalyzer:
    """Analyze and report performance metrics"""
    
    def __init__(self):
        pass
    
    def calculate_daily_metrics(self, date: datetime = None) -> Dict:
        """Calculate comprehensive daily metrics"""
        if not date:
            date = datetime.utcnow()
        
        try:
            # Calculate overall metrics
            overall_metrics = self._calculate_metrics_for_period(date)
            
            # Calculate mode-specific metrics
            mode_metrics = {}
            for mode in ['SCALPING', 'INTRADAY', 'SWING']:
                mode_metrics[f'{mode.lower()}_metrics'] = self._calculate_metrics_for_period(date, mode=mode)
            
            # Calculate symbol-specific metrics (top performers)
            symbol_metrics = self._calculate_top_symbols(date)
            
            # Combine all metrics
            daily_metrics = {
                **overall_metrics,
                **mode_metrics,
                'top_symbols': symbol_metrics,
                'calculation_date': date.date().isoformat()
            }
            
            # Store in database
            db_manager.calculate_daily_metrics(date)
            
            return daily_metrics
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {str(e)}")
            return {}
    
    def _calculate_metrics_for_period(self, date: datetime, mode: str = None, symbol: str = None) -> Dict:
        """Calculate metrics for specific period/mode/symbol"""
        try:
            # This would typically query the database
            # For now, return sample metrics structure
            return {
                'total_signals': 0,
                'win_signals': 0,
                'lose_signals': 0,
                'win_rate': 0.0,
                'avg_rr': 0.0,
                'total_pnl_percent': 0.0,
                'avg_adx': 0.0,
                'avg_volume_boost': 0.0,
                'best_hour': 0,
                'worst_hour': 0
            }
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}
    
    def _calculate_top_symbols(self, date: datetime, limit: int = 5) -> List[Dict]:
        """Calculate top performing symbols for the day"""
        try:
            # This would query database for symbol performance
            return []
        except Exception as e:
            logger.error(f"Error calculating top symbols: {str(e)}")
            return []
    
    def generate_weekly_report(self) -> Dict:
        """Generate comprehensive weekly performance report"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            # Calculate weekly metrics
            weekly_metrics = {
                'period': f"{start_date.date()} to {end_date.date()}",
                'total_signals': 0,
                'win_rate': 0.0,
                'avg_rr': 0.0,
                'total_pnl': 0.0,
                'best_day': None,
                'worst_day': None,
                'mode_breakdown': {},
                'symbol_breakdown': {},
                'hourly_performance': {}
            }
            
            return weekly_metrics
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {str(e)}")
            return {}

class RiskManager:
    """Manage risk and exposure limits"""
    
    def __init__(self):
        self.daily_pnl = 0.0
        self.active_risk = 0.0
        
    def check_daily_loss_limit(self) -> Tuple[bool, float]:
        """Check if daily loss limit is reached"""
        try:
            # Calculate current daily PnL
            today = datetime.utcnow().date()
            # This would query database for today's PnL
            daily_pnl_pct = 0.0  # Placeholder
            
            loss_limit = config.daily_loss_cap
            
            if daily_pnl_pct <= -loss_limit:
                return False, daily_pnl_pct
            
            return True, daily_pnl_pct
            
        except Exception as e:
            logger.error(f"Error checking daily loss limit: {str(e)}")
            return True, 0.0
    
    def check_concurrent_signals_limit(self, symbol: str = None, mode: str = None) -> bool:
        """Check if concurrent signals limit is reached"""
        try:
            active_signals = db_manager.get_active_signals()
            
            # Check overall limit
            if len(active_signals) >= config.max_concurrent_signals:
                return False
            
            # Check per symbol/mode limits if specified
            if symbol:
                symbol_signals = [s for s in active_signals if s.symbol == symbol]
                if len(symbol_signals) >= 2:  # Max 2 per symbol
                    return False
            
            if mode:
                mode_signals = [s for s in active_signals if s.mode == mode]
                if len(mode_signals) >= 3:  # Max 3 per mode
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking concurrent signals limit: {str(e)}")
            return False
    
    def calculate_position_risk(self, entry_price: float, stop_loss: float, quantity: float) -> float:
        """Calculate position risk amount"""
        try:
            risk_per_unit = abs(entry_price - stop_loss)
            total_risk = risk_per_unit * quantity
            return total_risk
            
        except Exception as e:
            logger.error(f"Error calculating position risk: {str(e)}")
            return 0.0

# Global instances
signal_monitor = SignalMonitor()
performance_analyzer = PerformanceAnalyzer()
risk_manager = RiskManager()