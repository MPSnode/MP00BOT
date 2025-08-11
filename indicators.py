import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Technical indicators calculator for the signal bot"""
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return ta.trend.EMAIndicator(close=data, window=period).ema_indicator()
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return ta.trend.SMAIndicator(close=data, window=period).sma_indicator()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        return ta.momentum.RSIIndicator(close=data, window=period).rsi()
    
    @staticmethod
    def stoch_rsi(data: pd.Series, window: int = 14, smooth1: int = 3, smooth2: int = 3) -> Dict[str, pd.Series]:
        """Stochastic RSI"""
        indicator = ta.momentum.StochRSIIndicator(
            close=data, 
            window=window, 
            smooth1=smooth1, 
            smooth2=smooth2
        )
        return {
            'stoch_rsi_k': indicator.stochrsi_k() * 100,
            'stoch_rsi_d': indicator.stochrsi_d() * 100
        }
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std: float = 2.0) -> Dict[str, pd.Series]:
        """Bollinger Bands"""
        indicator = ta.volatility.BollingerBands(close=data, window=period, window_dev=std)
        return {
            'bb_upper': indicator.bollinger_hband(),
            'bb_middle': indicator.bollinger_mavg(),
            'bb_lower': indicator.bollinger_lband(),
            'bb_width': indicator.bollinger_wband(),
            'bb_pband': indicator.bollinger_pband()
        }
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        return ta.volatility.AverageTrueRange(
            high=high, 
            low=low, 
            close=close, 
            window=period
        ).average_true_range()
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
        """Average Directional Index"""
        indicator = ta.trend.ADXIndicator(high=high, low=low, close=close, window=period)
        return {
            'adx': indicator.adx(),
            'adx_pos': indicator.adx_pos(),
            'adx_neg': indicator.adx_neg()
        }
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD"""
        indicator = ta.trend.MACD(close=data, window_fast=fast, window_slow=slow, window_sign=signal)
        return {
            'macd_line': indicator.macd(),
            'macd_signal': indicator.macd_signal(),
            'macd_histogram': indicator.macd_diff()
        }
    
    @staticmethod
    def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series, 
                 tenkan: int = 9, kijun: int = 26, senkou: int = 52) -> Dict[str, pd.Series]:
        """Ichimoku Cloud"""
        indicator = ta.trend.IchimokuIndicator(
            high=high, 
            low=low, 
            window1=tenkan, 
            window2=kijun, 
            window3=senkou
        )
        return {
            'tenkan_sen': indicator.ichimoku_conversion_line(),
            'kijun_sen': indicator.ichimoku_base_line(),
            'senkou_span_a': indicator.ichimoku_a(),
            'senkou_span_b': indicator.ichimoku_b(),
            'chikou_span': close.shift(-kijun)
        }
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On Balance Volume"""
        return ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
    
    @staticmethod
    def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Volume Simple Moving Average"""
        return ta.trend.SMAIndicator(close=volume, window=period).sma_indicator()
    
    @staticmethod
    def fibonacci_retracement(high_price: float, low_price: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        diff = high_price - low_price
        return {
            'fib_100': high_price,
            'fib_786': high_price - 0.786 * diff,
            'fib_618': high_price - 0.618 * diff,
            'fib_500': high_price - 0.500 * diff,
            'fib_382': high_price - 0.382 * diff,
            'fib_236': high_price - 0.236 * diff,
            'fib_000': low_price
        }
    
    @staticmethod
    def support_resistance_levels(data: pd.DataFrame, period: int = 20) -> Dict[str, List[float]]:
        """Identify support and resistance levels"""
        highs = data['high'].rolling(window=period).max()
        lows = data['low'].rolling(window=period).min()
        
        # Find pivot points
        pivot_highs = []
        pivot_lows = []
        
        for i in range(period, len(data) - period):
            # Pivot high
            if data['high'].iloc[i] == highs.iloc[i]:
                pivot_highs.append(data['high'].iloc[i])
            
            # Pivot low
            if data['low'].iloc[i] == lows.iloc[i]:
                pivot_lows.append(data['low'].iloc[i])
        
        return {
            'resistance_levels': sorted(list(set(pivot_highs)), reverse=True)[:5],
            'support_levels': sorted(list(set(pivot_lows)))[:5]
        }

class IndicatorAnalysis:
    """Advanced indicator analysis for signal generation"""
    
    def __init__(self):
        self.ti = TechnicalIndicators()
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators for a DataFrame"""
        result_df = df.copy()
        
        try:
            # Moving averages
            result_df['ema_20'] = self.ti.ema(df['close'], 20)
            result_df['ema_50'] = self.ti.ema(df['close'], 50)
            result_df['ema_200'] = self.ti.ema(df['close'], 200)
            
            # RSI
            result_df['rsi'] = self.ti.rsi(df['close'])
            
            # Stochastic RSI
            stoch_rsi = self.ti.stoch_rsi(df['close'])
            result_df['stoch_rsi_k'] = stoch_rsi['stoch_rsi_k']
            result_df['stoch_rsi_d'] = stoch_rsi['stoch_rsi_d']
            
            # Bollinger Bands
            bb = self.ti.bollinger_bands(df['close'])
            result_df['bb_upper'] = bb['bb_upper']
            result_df['bb_middle'] = bb['bb_middle']
            result_df['bb_lower'] = bb['bb_lower']
            result_df['bb_width'] = bb['bb_width']
            result_df['bb_pband'] = bb['bb_pband']
            
            # ATR
            result_df['atr'] = self.ti.atr(df['high'], df['low'], df['close'])
            
            # ADX
            adx = self.ti.adx(df['high'], df['low'], df['close'])
            result_df['adx'] = adx['adx']
            result_df['adx_pos'] = adx['adx_pos']
            result_df['adx_neg'] = adx['adx_neg']
            
            # MACD
            macd = self.ti.macd(df['close'])
            result_df['macd_line'] = macd['macd_line']
            result_df['macd_signal'] = macd['macd_signal']
            result_df['macd_histogram'] = macd['macd_histogram']
            
            # Ichimoku
            ichimoku = self.ti.ichimoku(df['high'], df['low'], df['close'])
            result_df['tenkan_sen'] = ichimoku['tenkan_sen']
            result_df['kijun_sen'] = ichimoku['kijun_sen']
            result_df['senkou_span_a'] = ichimoku['senkou_span_a']
            result_df['senkou_span_b'] = ichimoku['senkou_span_b']
            result_df['chikou_span'] = ichimoku['chikou_span']
            
            # OBV
            result_df['obv'] = self.ti.obv(df['close'], df['volume'])
            
            # Volume indicators
            result_df['volume_sma'] = self.ti.volume_sma(df['volume'])
            result_df['volume_ratio'] = df['volume'] / result_df['volume_sma']
            
            logger.debug(f"Calculated all indicators for {len(df)} candles")
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            
        return result_df
    
    def get_trend_bias(self, df: pd.DataFrame, mode: str = 'INTRADAY') -> str:
        """
        Determine trend bias based on EMA200 and Ichimoku cloud
        
        Returns: 'LONG', 'SHORT', or 'NEUTRAL'
        """
        try:
            latest = df.iloc[-1]
            
            # EMA200 bias
            ema_bias = 'NEUTRAL'
            if pd.notna(latest['ema_200']):
                if latest['close'] > latest['ema_200']:
                    ema_bias = 'LONG'
                elif latest['close'] < latest['ema_200']:
                    ema_bias = 'SHORT'
            
            # Ichimoku cloud bias (for swing mode)
            cloud_bias = 'NEUTRAL'
            if mode == 'SWING':
                if (pd.notna(latest['senkou_span_a']) and pd.notna(latest['senkou_span_b'])):
                    cloud_top = max(latest['senkou_span_a'], latest['senkou_span_b'])
                    cloud_bottom = min(latest['senkou_span_a'], latest['senkou_span_b'])
                    
                    if latest['close'] > cloud_top:
                        cloud_bias = 'LONG'
                    elif latest['close'] < cloud_bottom:
                        cloud_bias = 'SHORT'
            
            # Combine biases
            if mode == 'SWING':
                if ema_bias == 'LONG' and cloud_bias == 'LONG':
                    return 'LONG'
                elif ema_bias == 'SHORT' and cloud_bias == 'SHORT':
                    return 'SHORT'
                else:
                    return 'NEUTRAL'
            else:
                return ema_bias
                
        except Exception as e:
            logger.error(f"Error determining trend bias: {str(e)}")
            return 'NEUTRAL'
    
    def check_volume_boost(self, df: pd.DataFrame, min_boost: float = 0.15) -> Tuple[bool, float]:
        """
        Check if current volume shows boost compared to average
        
        Args:
            df: DataFrame with volume data
            min_boost: Minimum boost required (e.g., 0.15 for 15%)
            
        Returns:
            (has_boost, actual_boost_ratio)
        """
        try:
            latest = df.iloc[-1]
            
            if pd.isna(latest['volume_ratio']):
                return False, 0.0
            
            boost_ratio = latest['volume_ratio'] - 1.0
            has_boost = boost_ratio >= min_boost
            
            return has_boost, boost_ratio
            
        except Exception as e:
            logger.error(f"Error checking volume boost: {str(e)}")
            return False, 0.0
    
    def detect_ema_retest(self, df: pd.DataFrame, ema_period: int = 50, tolerance: float = 0.002) -> bool:
        """
        Detect if price is retesting EMA level
        
        Args:
            df: DataFrame with price and EMA data
            ema_period: EMA period to check (20, 50, 200)
            tolerance: Price tolerance around EMA (0.002 = 0.2%)
        """
        try:
            latest = df.iloc[-1]
            ema_col = f'ema_{ema_period}'
            
            if ema_col not in df.columns or pd.isna(latest[ema_col]):
                return False
            
            ema_value = latest[ema_col]
            price = latest['close']
            
            # Check if price is within tolerance of EMA
            distance_pct = abs(price - ema_value) / ema_value
            
            return distance_pct <= tolerance
            
        except Exception as e:
            logger.error(f"Error detecting EMA retest: {str(e)}")
            return False
    
    def detect_rsi_cross(self, df: pd.DataFrame, direction: str = 'up') -> bool:
        """
        Detect RSI cross above/below 50
        
        Args:
            direction: 'up' for bullish cross, 'down' for bearish cross
        """
        try:
            if len(df) < 2:
                return False
            
            current_rsi = df['rsi'].iloc[-1]
            previous_rsi = df['rsi'].iloc[-2]
            
            if pd.isna(current_rsi) or pd.isna(previous_rsi):
                return False
            
            if direction == 'up':
                return previous_rsi <= 50 and current_rsi > 50
            else:  # down
                return previous_rsi >= 50 and current_rsi < 50
                
        except Exception as e:
            logger.error(f"Error detecting RSI cross: {str(e)}")
            return False
    
    def detect_stoch_rsi_signal(self, df: pd.DataFrame, signal_type: str = 'long') -> bool:
        """
        Detect StochRSI signals
        
        Args:
            signal_type: 'long' or 'short'
        """
        try:
            if len(df) < 3:
                return False
            
            current_k = df['stoch_rsi_k'].iloc[-1]
            previous_k = df['stoch_rsi_k'].iloc[-2]
            
            if pd.isna(current_k) or pd.isna(previous_k):
                return False
            
            if signal_type == 'long':
                # Exit oversold and slope up
                oversold_exit = previous_k <= 20 and current_k > 20
                slope_up = current_k > previous_k
                return oversold_exit and slope_up
            else:  # short
                # Exit overbought and slope down
                overbought_exit = previous_k >= 80 and current_k < 80
                slope_down = current_k < previous_k
                return overbought_exit and slope_down
                
        except Exception as e:
            logger.error(f"Error detecting StochRSI signal: {str(e)}")
            return False
    
    def detect_macd_cross(self, df: pd.DataFrame, direction: str = 'up') -> bool:
        """
        Detect MACD line crossing signal line
        
        Args:
            direction: 'up' for bullish cross, 'down' for bearish cross
        """
        try:
            if len(df) < 2:
                return False
            
            current_macd = df['macd_line'].iloc[-1]
            current_signal = df['macd_signal'].iloc[-1]
            previous_macd = df['macd_line'].iloc[-2]
            previous_signal = df['macd_signal'].iloc[-2]
            
            if any(pd.isna(x) for x in [current_macd, current_signal, previous_macd, previous_signal]):
                return False
            
            if direction == 'up':
                return previous_macd <= previous_signal and current_macd > current_signal
            else:  # down
                return previous_macd >= previous_signal and current_macd < current_signal
                
        except Exception as e:
            logger.error(f"Error detecting MACD cross: {str(e)}")
            return False

# Singleton instance
indicator_analysis = IndicatorAnalysis()