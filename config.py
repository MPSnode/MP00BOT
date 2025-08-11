import os
from dataclasses import dataclass
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ModeConfig:
    name: str
    primary_tf: str
    confirm_tf: str
    adx_min: int
    volume_boost_min: float
    sl_atr_mult: float
    tp_atr_mult_min: float
    tp_atr_mult_max: float
    trailing_pct: float
    score_min: int
    order_validity_minutes: int
    cooldown_minutes: int

@dataclass
class Config:
    # Exchange settings
    exchange_name: str = os.getenv('EXCHANGE_NAME', 'binance')
    api_key: str = os.getenv('EXCHANGE_API_KEY', '')
    secret: str = os.getenv('EXCHANGE_SECRET', '')
    sandbox: bool = os.getenv('EXCHANGE_SANDBOX', 'true').lower() == 'true'
    
    # Telegram settings
    telegram_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Database
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///signals.db')
    
    # Risk management
    initial_equity: float = float(os.getenv('INITIAL_EQUITY', '10000'))
    risk_per_trade: float = float(os.getenv('RISK_PER_TRADE', '0.01'))
    daily_loss_cap: float = float(os.getenv('DAILY_LOSS_CAP', '0.03'))
    max_concurrent_signals: int = int(os.getenv('MAX_CONCURRENT_SIGNALS', '3'))
    
    # Symbols
    symbols: List[str] = os.getenv('SYMBOLS', 'BTCUSDT,ETHUSDT,SOLUSDT').split(',')
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Mode configurations
    modes: Dict[str, ModeConfig] = None
    
    def __post_init__(self):
        self.modes = {
            'SCALPING': ModeConfig(
                name='SCALPING',
                primary_tf='1m',
                confirm_tf='5m',
                adx_min=22,
                volume_boost_min=0.15,  # 15%
                sl_atr_mult=1.0,
                tp_atr_mult_min=1.5,
                tp_atr_mult_max=2.0,
                trailing_pct=0.003,  # 0.3%
                score_min=55,
                order_validity_minutes=15,
                cooldown_minutes=15
            ),
            'INTRADAY': ModeConfig(
                name='INTRADAY',
                primary_tf='15m',
                confirm_tf='1h',
                adx_min=20,
                volume_boost_min=0.20,  # 20%
                sl_atr_mult=1.25,
                tp_atr_mult_min=2.0,
                tp_atr_mult_max=3.0,
                trailing_pct=0.005,  # 0.5%
                score_min=60,
                order_validity_minutes=75,
                cooldown_minutes=60
            ),
            'SWING': ModeConfig(
                name='SWING',
                primary_tf='4h',
                confirm_tf='1d',
                adx_min=18,
                volume_boost_min=0.10,  # 10%
                sl_atr_mult=1.5,
                tp_atr_mult_min=2.5,
                tp_atr_mult_max=3.5,
                trailing_pct=0.008,  # 0.8%
                score_min=65,
                order_validity_minutes=720,  # 12 hours
                cooldown_minutes=240  # 4 hours
            )
        }

# Global config instance
config = Config()