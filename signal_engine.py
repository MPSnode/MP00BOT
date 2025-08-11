import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

from config import config
from data_handler import data_handler
from indicators import indicator_analysis

logger = logging.getLogger(__name__)

@dataclass
class SignalResult:
    """Signal detection result"""
    symbol: str
    mode: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    score: int
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'
    trend_note: str
    adx_value: float
    volume_boost: float
    atr_value: float
    code: str
    timestamp: datetime
    primary_tf_data: pd.DataFrame
    confirm_tf_data: pd.DataFrame
    
class SignalEngine:
    """Main signal detection engine"""
    
    def __init__(self):
        self.active_signals = {}  # Track active signals per symbol/mode
        self.cooldowns = {}  # Track cooldown periods
        
    def analyze_symbol(self, symbol: str, mode: str) -> Optional[SignalResult]:
        """
        Analyze a symbol for signal generation
        
        Args:
            symbol: Trading pair symbol
            mode: Trading mode ('SCALPING', 'INTRADAY', 'SWING')
            
        Returns:
            SignalResult if signal detected, None otherwise
        """
        try:
            mode_config = config.modes[mode]
            
            # Check if symbol is in cooldown
            if self._is_in_cooldown(symbol, mode):
                logger.debug(f"{symbol} {mode} in cooldown")
                return None
            
            # Check market conditions
            market_valid, market_reason = data_handler.validate_market_conditions(symbol)
            if not market_valid:
                logger.debug(f"{symbol} market conditions invalid: {market_reason}")
                return None
            
            # Get multi-timeframe data
            timeframes = [mode_config.primary_tf, mode_config.confirm_tf]
            mtf_data = data_handler.get_mtf_data(symbol, timeframes)
            
            if len(mtf_data) != 2:
                logger.warning(f"Insufficient data for {symbol} {mode}")
                return None
            
            primary_df = mtf_data[mode_config.primary_tf]
            confirm_df = mtf_data[mode_config.confirm_tf]
            
            # Calculate indicators
            primary_df = indicator_analysis.calculate_all_indicators(primary_df)
            confirm_df = indicator_analysis.calculate_all_indicators(confirm_df)
            
            # Mode-specific signal detection
            if mode == 'SCALPING':
                signal = self._detect_scalping_signal(symbol, primary_df, confirm_df, mode_config)
            elif mode == 'INTRADAY':
                signal = self._detect_intraday_signal(symbol, primary_df, confirm_df, mode_config)
            elif mode == 'SWING':
                signal = self._detect_swing_signal(symbol, primary_df, confirm_df, mode_config)
            else:
                logger.error(f"Unknown mode: {mode}")
                return None
            
            if signal:
                signal.primary_tf_data = primary_df
                signal.confirm_tf_data = confirm_df
                logger.info(f"Signal detected: {signal.symbol} {signal.mode} {signal.direction} Score: {signal.score}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} {mode}: {str(e)}")
            return None
    
    def _detect_scalping_signal(self, symbol: str, primary_df: pd.DataFrame, 
                               confirm_df: pd.DataFrame, mode_config) -> Optional[SignalResult]:
        """Detect scalping signals (Primary: 1m, Confirm: 5m)"""
        try:
            # Get trend bias from 5m EMA200
            trend_bias = indicator_analysis.get_trend_bias(confirm_df, 'SCALPING')
            if trend_bias == 'NEUTRAL':
                return None
            
            # Check ADX on 5m
            confirm_latest = confirm_df.iloc[-1]
            if pd.isna(confirm_latest['adx']) or confirm_latest['adx'] < mode_config.adx_min:
                return None
            
            # Check volume boost on 1m
            volume_valid, volume_boost = indicator_analysis.check_volume_boost(
                primary_df, mode_config.volume_boost_min
            )
            if not volume_valid:
                return None
            
            primary_latest = primary_df.iloc[-1]
            
            # Signal detection logic
            for direction in ['LONG', 'SHORT']:
                score = 0
                
                # Trend HTF alignment (+20)
                if trend_bias == direction:
                    score += 20
                
                # ADX strength (+10)
                if confirm_latest['adx'] >= mode_config.adx_min:
                    score += 10
                
                # RSI cross on 1m (+10)
                rsi_direction = 'up' if direction == 'LONG' else 'down'
                if indicator_analysis.detect_rsi_cross(primary_df, rsi_direction):
                    score += 10
                
                # StochRSI trigger (+10)
                stoch_signal_type = 'long' if direction == 'LONG' else 'short'
                if indicator_analysis.detect_stoch_rsi_signal(primary_df, stoch_signal_type):
                    score += 10
                
                # Volume boost (+10)
                if volume_valid:
                    score += 10
                
                # EMA50 retest (+10)
                if indicator_analysis.detect_ema_retest(primary_df, 50):
                    score += 10
                
                # Bollinger band confluence (+5)
                if self._check_bb_confluence(primary_df, direction):
                    score += 5
                
                # Check minimum score
                if score >= mode_config.score_min:
                    entry_price = self._calculate_entry_price(primary_df, direction, 'SCALPING')
                    if entry_price:
                        sl, tp = self._calculate_sl_tp(primary_df, entry_price, direction, mode_config)
                        quantity = self._calculate_quantity(symbol, entry_price, sl)
                        
                        trend_note = f"EMA200(5m){trend_bias.lower()}"
                        
                        return SignalResult(
                            symbol=symbol,
                            mode='SCALPING',
                            direction=direction,
                            entry_price=entry_price,
                            stop_loss=sl,
                            take_profit=tp,
                            quantity=quantity,
                            score=score,
                            confidence=self._get_confidence_level(score),
                            trend_note=trend_note,
                            adx_value=confirm_latest['adx'],
                            volume_boost=volume_boost,
                            atr_value=primary_latest['atr'],
                            code=self._generate_signal_code(),
                            timestamp=datetime.now()
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting scalping signal for {symbol}: {str(e)}")
            return None
    
    def _detect_intraday_signal(self, symbol: str, primary_df: pd.DataFrame, 
                               confirm_df: pd.DataFrame, mode_config) -> Optional[SignalResult]:
        """Detect intraday signals (Primary: 15m, Confirm: 1h)"""
        try:
            # Get trend bias from 1h EMA200
            trend_bias = indicator_analysis.get_trend_bias(confirm_df, 'INTRADAY')
            if trend_bias == 'NEUTRAL':
                return None
            
            confirm_latest = confirm_df.iloc[-1]
            
            # Check volume boost on 15m
            volume_valid, volume_boost = indicator_analysis.check_volume_boost(
                primary_df, mode_config.volume_boost_min
            )
            if not volume_valid:
                return None
            
            primary_latest = primary_df.iloc[-1]
            
            # Signal detection logic
            for direction in ['LONG', 'SHORT']:
                score = 0
                
                # Trend HTF alignment (+20)
                if trend_bias == direction:
                    score += 20
                
                # MACD cross on 15m or 1h (+20)
                macd_direction = 'up' if direction == 'LONG' else 'down'
                if (indicator_analysis.detect_macd_cross(primary_df, macd_direction) or
                    indicator_analysis.detect_macd_cross(confirm_df, macd_direction)):
                    score += 20
                
                # Volume boost (+10)
                if volume_valid:
                    score += 10
                
                # EMA50 retest on 15m (+10)
                if indicator_analysis.detect_ema_retest(primary_df, 50):
                    score += 10
                
                # Fibonacci confluence (+10)
                if self._check_fib_confluence(primary_df, direction):
                    score += 10
                
                # ADX strength (+10)
                if pd.notna(confirm_latest['adx']) and confirm_latest['adx'] >= mode_config.adx_min:
                    score += 10
                
                # RSI healthy level (+5)
                if self._check_rsi_healthy(confirm_latest, direction):
                    score += 5
                
                # Check minimum score
                if score >= mode_config.score_min:
                    entry_price = self._calculate_entry_price(primary_df, direction, 'INTRADAY')
                    if entry_price:
                        sl, tp = self._calculate_sl_tp(primary_df, entry_price, direction, mode_config)
                        quantity = self._calculate_quantity(symbol, entry_price, sl)
                        
                        trend_note = f"EMA200(1H){trend_bias.lower()}"
                        if pd.notna(primary_latest['macd_line']) and pd.notna(primary_latest['macd_signal']):
                            macd_status = "↑" if primary_latest['macd_line'] > primary_latest['macd_signal'] else "↓"
                            trend_note += f" | MACD(15m) {macd_status}"
                        
                        return SignalResult(
                            symbol=symbol,
                            mode='INTRADAY',
                            direction=direction,
                            entry_price=entry_price,
                            stop_loss=sl,
                            take_profit=tp,
                            quantity=quantity,
                            score=score,
                            confidence=self._get_confidence_level(score),
                            trend_note=trend_note,
                            adx_value=confirm_latest.get('adx', 0),
                            volume_boost=volume_boost,
                            atr_value=primary_latest['atr'],
                            code=self._generate_signal_code(),
                            timestamp=datetime.now()
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting intraday signal for {symbol}: {str(e)}")
            return None
    
    def _detect_swing_signal(self, symbol: str, primary_df: pd.DataFrame, 
                            confirm_df: pd.DataFrame, mode_config) -> Optional[SignalResult]:
        """Detect swing signals (Primary: 4h, Confirm: 1d)"""
        try:
            # Get trend bias from 1d (EMA200 + Ichimoku cloud)
            trend_bias = indicator_analysis.get_trend_bias(confirm_df, 'SWING')
            if trend_bias == 'NEUTRAL':
                return None
            
            # Check volume boost on 4h
            volume_valid, volume_boost = indicator_analysis.check_volume_boost(
                primary_df, mode_config.volume_boost_min
            )
            if not volume_valid:
                return None
            
            primary_latest = primary_df.iloc[-1]
            confirm_latest = confirm_df.iloc[-1]
            
            # Signal detection logic
            for direction in ['LONG', 'SHORT']:
                score = 0
                
                # Trend HTF alignment (EMA200 + Cloud) (+20)
                if trend_bias == direction:
                    score += 20
                
                # MACD alignment on 4h (+20)
                macd_direction = 'up' if direction == 'LONG' else 'down'
                if indicator_analysis.detect_macd_cross(primary_df, macd_direction):
                    score += 20
                
                # OBV alignment (+15)
                if self._check_obv_alignment(primary_df, direction):
                    score += 15
                
                # Volume boost (+10)
                if volume_valid:
                    score += 10
                
                # ADX strength on daily (+10)
                if pd.notna(confirm_latest['adx']) and confirm_latest['adx'] >= mode_config.adx_min:
                    score += 10
                
                # HVN/Edge retest (Volume Profile approximation) (+10)
                if self._check_volume_profile_confluence(primary_df, direction):
                    score += 10
                
                # Additional confluence (+5)
                if self._check_swing_confluence(primary_df, confirm_df, direction):
                    score += 5
                
                # Check minimum score
                if score >= mode_config.score_min:
                    entry_price = self._calculate_entry_price(primary_df, direction, 'SWING')
                    if entry_price:
                        sl, tp = self._calculate_sl_tp(primary_df, entry_price, direction, mode_config)
                        quantity = self._calculate_quantity(symbol, entry_price, sl)
                        
                        cloud_status = "Above Cloud" if trend_bias == 'LONG' else "Below Cloud"
                        macd_status = "↑" if primary_latest['macd_line'] > primary_latest['macd_signal'] else "↓"
                        obv_status = "↑" if self._check_obv_alignment(primary_df, direction) else "↓"
                        
                        trend_note = f"{cloud_status}(1D) | MACD(4H){macd_status} | OBV{obv_status}"
                        
                        return SignalResult(
                            symbol=symbol,
                            mode='SWING',
                            direction=direction,
                            entry_price=entry_price,
                            stop_loss=sl,
                            take_profit=tp,
                            quantity=quantity,
                            score=score,
                            confidence=self._get_confidence_level(score),
                            trend_note=trend_note,
                            adx_value=confirm_latest.get('adx', 0),
                            volume_boost=volume_boost,
                            atr_value=primary_latest['atr'],
                            code=self._generate_signal_code(),
                            timestamp=datetime.now()
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting swing signal for {symbol}: {str(e)}")
            return None
    
    def _calculate_entry_price(self, df: pd.DataFrame, direction: str, mode: str) -> Optional[float]:
        """Calculate optimal entry price based on mode and direction"""
        try:
            latest = df.iloc[-1]
            current_price = latest['close']
            
            if mode == 'SCALPING':
                # EMA50 retest or current price
                if pd.notna(latest['ema_50']):
                    ema_distance = abs(current_price - latest['ema_50']) / current_price
                    if ema_distance <= 0.002:  # Within 0.2%
                        return latest['ema_50']
                return current_price
                
            elif mode == 'INTRADAY':
                # Fibonacci 0.5-0.618 zone or EMA50
                if pd.notna(latest['ema_50']):
                    return latest['ema_50']
                return current_price
                
            elif mode == 'SWING':
                # Volume profile HVN approximation or current price
                return current_price
                
        except Exception as e:
            logger.error(f"Error calculating entry price: {str(e)}")
            return None
    
    def _calculate_sl_tp(self, df: pd.DataFrame, entry_price: float, direction: str, 
                        mode_config) -> Tuple[float, float]:
        """Calculate stop loss and take profit"""
        try:
            latest = df.iloc[-1]
            atr = latest['atr']
            
            if direction == 'LONG':
                sl = entry_price - (atr * mode_config.sl_atr_mult)
                tp = entry_price + (atr * mode_config.tp_atr_mult_min)
            else:  # SHORT
                sl = entry_price + (atr * mode_config.sl_atr_mult)
                tp = entry_price - (atr * mode_config.tp_atr_mult_min)
            
            return sl, tp
            
        except Exception as e:
            logger.error(f"Error calculating SL/TP: {str(e)}")
            return entry_price * 0.98, entry_price * 1.02  # Fallback
    
    def _calculate_quantity(self, symbol: str, entry_price: float, stop_loss: float) -> float:
        """Calculate position quantity based on risk management"""
        try:
            risk_amount = config.initial_equity * config.risk_per_trade
            stop_distance = abs(entry_price - stop_loss)
            
            if stop_distance == 0:
                return 0
            
            # Basic quantity calculation (simplified)
            quantity = risk_amount / stop_distance
            
            # Round to appropriate precision
            return round(quantity, 6)
            
        except Exception as e:
            logger.error(f"Error calculating quantity: {str(e)}")
            return 0.001  # Fallback minimum
    
    def _check_bb_confluence(self, df: pd.DataFrame, direction: str) -> bool:
        """Check Bollinger Bands confluence"""
        try:
            latest = df.iloc[-1]
            
            if direction == 'LONG':
                # Price near lower band, bouncing up
                return (latest['close'] <= latest['bb_lower'] * 1.01 and
                        latest['bb_pband'] <= 0.2)
            else:  # SHORT
                # Price near upper band, bouncing down
                return (latest['close'] >= latest['bb_upper'] * 0.99 and
                        latest['bb_pband'] >= 0.8)
                        
        except Exception as e:
            return False
    
    def _check_fib_confluence(self, df: pd.DataFrame, direction: str) -> bool:
        """Check Fibonacci retracement confluence"""
        try:
            # Simplified - check if price is in 0.5-0.618 zone
            # In real implementation, calculate based on recent swing high/low
            latest = df.iloc[-1]
            
            # Look for recent high/low in last 20 candles
            recent_data = df.tail(20)
            if direction == 'LONG':
                swing_high = recent_data['high'].max()
                swing_low = recent_data['low'].min()
            else:
                swing_high = recent_data['high'].max()
                swing_low = recent_data['low'].min()
            
            # Check if current price is in 0.5-0.618 zone
            fib_levels = indicator_analysis.ti.fibonacci_retracement(swing_high, swing_low)
            current_price = latest['close']
            
            return (fib_levels['fib_618'] <= current_price <= fib_levels['fib_500'])
            
        except Exception as e:
            return False
    
    def _check_rsi_healthy(self, latest_data: pd.Series, direction: str) -> bool:
        """Check if RSI is in healthy range"""
        try:
            rsi = latest_data['rsi']
            if pd.isna(rsi):
                return False
            
            if direction == 'LONG':
                return 30 <= rsi <= 70
            else:  # SHORT
                return 30 <= rsi <= 70
                
        except Exception:
            return False
    
    def _check_obv_alignment(self, df: pd.DataFrame, direction: str) -> bool:
        """Check OBV trend alignment"""
        try:
            if len(df) < 5:
                return False
            
            # Check if OBV is trending in same direction
            obv_values = df['obv'].tail(5)
            
            if direction == 'LONG':
                return obv_values.iloc[-1] > obv_values.iloc[0]
            else:  # SHORT
                return obv_values.iloc[-1] < obv_values.iloc[0]
                
        except Exception:
            return False
    
    def _check_volume_profile_confluence(self, df: pd.DataFrame, direction: str) -> bool:
        """Simplified volume profile confluence check"""
        try:
            # Simplified: check if volume is above average in recent range
            recent_volume = df['volume'].tail(10).mean()
            current_volume = df['volume'].iloc[-1]
            
            return current_volume > recent_volume * 1.2
            
        except Exception:
            return False
    
    def _check_swing_confluence(self, primary_df: pd.DataFrame, confirm_df: pd.DataFrame, 
                              direction: str) -> bool:
        """Additional confluence checks for swing signals"""
        try:
            # Check if both timeframes show aligned momentum
            primary_latest = primary_df.iloc[-1]
            confirm_latest = confirm_df.iloc[-1]
            
            if direction == 'LONG':
                primary_bullish = (pd.notna(primary_latest['macd_line']) and 
                                 primary_latest['macd_line'] > primary_latest['macd_signal'])
                confirm_bullish = (pd.notna(confirm_latest['macd_line']) and 
                                 confirm_latest['macd_line'] > confirm_latest['macd_signal'])
                return primary_bullish and confirm_bullish
            else:  # SHORT
                primary_bearish = (pd.notna(primary_latest['macd_line']) and 
                                 primary_latest['macd_line'] < primary_latest['macd_signal'])
                confirm_bearish = (pd.notna(confirm_latest['macd_line']) and 
                                 confirm_latest['macd_line'] < confirm_latest['macd_signal'])
                return primary_bearish and confirm_bearish
                
        except Exception:
            return False
    
    def _get_confidence_level(self, score: int) -> str:
        """Convert score to confidence level"""
        if score >= 80:
            return 'HIGH'
        elif score >= 65:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_signal_code(self) -> str:
        """Generate unique signal code"""
        return f"SIG{datetime.now().strftime('%m%d%H%M')}{str(uuid.uuid4())[:4].upper()}"
    
    def _is_in_cooldown(self, symbol: str, mode: str) -> bool:
        """Check if symbol/mode is in cooldown period"""
        key = f"{symbol}_{mode}"
        if key in self.cooldowns:
            cooldown_until = self.cooldowns[key]
            if datetime.now() < cooldown_until:
                return True
            else:
                del self.cooldowns[key]
        return False
    
    def add_cooldown(self, symbol: str, mode: str, minutes: int):
        """Add cooldown period for symbol/mode"""
        key = f"{symbol}_{mode}"
        cooldown_until = datetime.now() + pd.Timedelta(minutes=minutes)
        self.cooldowns[key] = cooldown_until
        logger.info(f"Added cooldown for {key} until {cooldown_until}")

# Singleton instance
signal_engine = SignalEngine()