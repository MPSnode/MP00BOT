import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
import logging
from config import config

logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self):
        self.exchange = self._init_exchange()
        self.candle_cache = {}
        self.last_update = {}
        
    def _init_exchange(self) -> ccxt.Exchange:
        """Initialize exchange connection"""
        exchange_class = getattr(ccxt, config.exchange_name)
        
        exchange_config = {
            'apiKey': config.api_key,
            'secret': config.secret,
            'sandbox': config.sandbox,
            'enableRateLimit': True,
        }
        
        exchange = exchange_class(exchange_config)
        logger.info(f"Initialized {config.exchange_name} exchange")
        return exchange
        
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol and timeframe
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            current_time = datetime.now()
            
            # Use cache if data is fresh (less than 1 minute old for < 1h TF, 5 minutes for >= 1h TF)
            cache_timeout = 60 if timeframe in ['1m', '5m', '15m', '30m'] else 300
            
            if (cache_key in self.candle_cache and 
                cache_key in self.last_update and
                (current_time - self.last_update[cache_key]).seconds < cache_timeout):
                logger.debug(f"Using cached data for {cache_key}")
                return self.candle_cache[cache_key].copy()
            
            # Fetch fresh data
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"No data received for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Cache the data
            self.candle_cache[cache_key] = df.copy()
            self.last_update[cache_key] = current_time
            
            logger.debug(f"Fetched {len(df)} candles for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} {timeframe}: {str(e)}")
            return pd.DataFrame()
    
    def get_mtf_data(self, symbol: str, timeframes: List[str], limit: int = 500) -> Dict[str, pd.DataFrame]:
        """
        Fetch multi-timeframe data for a symbol
        
        Args:
            symbol: Trading pair symbol
            timeframes: List of timeframes to fetch
            limit: Number of candles per timeframe
            
        Returns:
            Dictionary with timeframe as key and DataFrame as value
        """
        mtf_data = {}
        
        for tf in timeframes:
            df = self.fetch_ohlcv(symbol, tf, limit)
            if not df.empty:
                mtf_data[tf] = df
            else:
                logger.warning(f"Failed to fetch data for {symbol} {tf}")
                
        return mtf_data
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None
    
    def get_market_info(self, symbol: str) -> Dict:
        """Get market information for a symbol"""
        try:
            market = self.exchange.market(symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'symbol': symbol,
                'base': market['base'],
                'quote': market['quote'],
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'spread': ticker['ask'] - ticker['bid'] if ticker['ask'] and ticker['bid'] else None,
                'spread_pct': ((ticker['ask'] - ticker['bid']) / ticker['last'] * 100) if ticker['ask'] and ticker['bid'] and ticker['last'] else None,
                'volume_24h': ticker['quoteVolume'],
                'min_notional': market.get('limits', {}).get('cost', {}).get('min', 0),
                'min_qty': market.get('limits', {}).get('amount', {}).get('min', 0),
                'precision': {
                    'price': market.get('precision', {}).get('price', 8),
                    'amount': market.get('precision', {}).get('amount', 8)
                }
            }
        except Exception as e:
            logger.error(f"Error fetching market info for {symbol}: {str(e)}")
            return {}
    
    def validate_market_conditions(self, symbol: str) -> Tuple[bool, str]:
        """
        Validate if market conditions are suitable for signal generation
        
        Returns:
            (is_valid, reason)
        """
        try:
            market_info = self.get_market_info(symbol)
            
            if not market_info:
                return False, "Failed to fetch market info"
            
            # Check spread
            if market_info.get('spread_pct', 0) > 0.1:  # 0.1% max spread
                return False, f"Spread too wide: {market_info['spread_pct']:.3f}%"
            
            # Check volume (minimum 24h volume threshold)
            min_volume = 1000000  # $1M minimum daily volume
            if market_info.get('volume_24h', 0) < min_volume:
                return False, f"Low volume: ${market_info['volume_24h']:,.0f}"
            
            return True, "Market conditions OK"
            
        except Exception as e:
            logger.error(f"Error validating market conditions for {symbol}: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def clear_cache(self):
        """Clear all cached data"""
        self.candle_cache.clear()
        self.last_update.clear()
        logger.info("Cleared data cache")
    
    def get_cache_status(self) -> Dict:
        """Get cache status information"""
        current_time = datetime.now()
        cache_status = {}
        
        for cache_key in self.candle_cache.keys():
            last_update = self.last_update.get(cache_key)
            age_seconds = (current_time - last_update).seconds if last_update else None
            cache_status[cache_key] = {
                'rows': len(self.candle_cache[cache_key]),
                'last_update': last_update,
                'age_seconds': age_seconds
            }
        
        return cache_status

# Singleton instance
data_handler = DataHandler()