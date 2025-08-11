from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import logging
from config import config
from typing import List
import pandas as pd

logger = logging.getLogger(__name__)

Base = declarative_base()

class Signal(Base):
    """Signal table for storing generated signals"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    mode = Column(String(20), nullable=False)  # SCALPING, INTRADAY, SWING
    direction = Column(String(10), nullable=False)  # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    score = Column(Integer, nullable=False)
    confidence = Column(String(10), nullable=False)  # HIGH, MEDIUM, LOW
    trend_note = Column(Text)
    adx_value = Column(Float)
    volume_boost = Column(Float)
    atr_value = Column(Float)
    status = Column(String(20), default='NEW')  # NEW, FILLED, CANCELLED, WIN, LOSE
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
    closed_at = Column(DateTime)
    fill_price = Column(Float)
    close_price = Column(Float)
    close_reason = Column(String(20))  # TP, SL, MANUAL, EXPIRED
    pnl_points = Column(Float)
    pnl_percent = Column(Float)
    pnl_usd = Column(Float)
    validity_until = Column(DateTime)
    
    # Relationships
    executions = relationship("SignalExecution", back_populates="signal")
    
class SignalExecution(Base):
    """Signal execution tracking"""
    __tablename__ = 'signal_executions'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('signals.id'), nullable=False)
    execution_type = Column(String(20), nullable=False)  # ENTRY, SL, TP, PARTIAL
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="executions")

class DailyMetrics(Base):
    """Daily performance metrics"""
    __tablename__ = 'daily_metrics'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    mode = Column(String(20))  # NULL for all modes, or specific mode
    symbol = Column(String(20))  # NULL for all symbols, or specific symbol
    
    # Signal counts
    signals_generated = Column(Integer, default=0)
    signals_filled = Column(Integer, default=0)
    signals_cancelled = Column(Integer, default=0)
    signals_win = Column(Integer, default=0)
    signals_lose = Column(Integer, default=0)
    
    # Performance metrics
    win_rate = Column(Float, default=0.0)
    avg_rr = Column(Float, default=0.0)
    total_pnl_points = Column(Float, default=0.0)
    total_pnl_percent = Column(Float, default=0.0)
    total_pnl_usd = Column(Float, default=0.0)
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    avg_trade_duration_minutes = Column(Float, default=0.0)
    
    # Market conditions
    avg_adx = Column(Float, default=0.0)
    avg_volatility = Column(Float, default=0.0)
    avg_volume_boost = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class MarketSession(Base):
    """Market session analysis"""
    __tablename__ = 'market_sessions'
    
    id = Column(Integer, primary_key=True)
    session_hour = Column(Integer, nullable=False)  # 0-23 UTC hour
    mode = Column(String(20))
    
    # Performance by hour
    signals_count = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_rr = Column(Float, default=0.0)
    avg_score = Column(Float, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow)

class Cooldown(Base):
    """Active cooldowns"""
    __tablename__ = 'cooldowns'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    mode = Column(String(20), nullable=False)
    reason = Column(String(50), nullable=False)  # LOSS, MANUAL
    cooldown_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemLog(Base):
    """System logs and events"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    module = Column(String(50))
    symbol = Column(String(20))
    mode = Column(String(20))
    additional_data = Column(Text)  # JSON string for extra data
    timestamp = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self):
        self.engine = create_engine(config.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.create_tables()
        
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def save_signal(self, signal_result) -> int:
        """Save signal to database"""
        try:
            session = self.get_session()
            
            # Calculate validity
            mode_config = config.modes[signal_result.mode]
            validity_until = signal_result.timestamp + pd.Timedelta(minutes=mode_config.order_validity_minutes)
            
            signal = Signal(
                code=signal_result.code,
                symbol=signal_result.symbol,
                mode=signal_result.mode,
                direction=signal_result.direction,
                entry_price=signal_result.entry_price,
                stop_loss=signal_result.stop_loss,
                take_profit=signal_result.take_profit,
                quantity=signal_result.quantity,
                score=signal_result.score,
                confidence=signal_result.confidence,
                trend_note=signal_result.trend_note,
                adx_value=signal_result.adx_value,
                volume_boost=signal_result.volume_boost,
                atr_value=signal_result.atr_value,
                validity_until=validity_until
            )
            
            session.add(signal)
            session.commit()
            signal_id = signal.id
            session.close()
            
            logger.info(f"Signal saved to database: {signal_result.code}")
            return signal_id
            
        except Exception as e:
            logger.error(f"Error saving signal: {str(e)}")
            session.rollback()
            session.close()
            return None
    
    def update_signal_status(self, code: str, status: str, **kwargs):
        """Update signal status and related fields"""
        try:
            session = self.get_session()
            signal = session.query(Signal).filter_by(code=code).first()
            
            if signal:
                signal.status = status
                
                # Update optional fields
                if 'fill_price' in kwargs:
                    signal.fill_price = kwargs['fill_price']
                    signal.filled_at = datetime.utcnow()
                
                if 'close_price' in kwargs:
                    signal.close_price = kwargs['close_price']
                    signal.closed_at = datetime.utcnow()
                    signal.close_reason = kwargs.get('close_reason', 'UNKNOWN')
                    
                    # Calculate PnL
                    if signal.fill_price:
                        if signal.direction == 'LONG':
                            pnl_points = signal.close_price - signal.fill_price
                        else:
                            pnl_points = signal.fill_price - signal.close_price
                        
                        signal.pnl_points = pnl_points
                        signal.pnl_percent = (pnl_points / signal.fill_price) * 100
                        signal.pnl_usd = pnl_points * signal.quantity
                
                session.commit()
                logger.info(f"Signal {code} status updated to {status}")
            else:
                logger.warning(f"Signal {code} not found for status update")
                
            session.close()
            
        except Exception as e:
            logger.error(f"Error updating signal status: {str(e)}")
            session.rollback()
            session.close()
    
    def add_signal_execution(self, signal_code: str, execution_type: str, price: float, quantity: float):
        """Add signal execution record"""
        try:
            session = self.get_session()
            signal = session.query(Signal).filter_by(code=signal_code).first()
            
            if signal:
                execution = SignalExecution(
                    signal_id=signal.id,
                    execution_type=execution_type,
                    price=price,
                    quantity=quantity
                )
                session.add(execution)
                session.commit()
                logger.info(f"Execution recorded for {signal_code}: {execution_type} @ {price}")
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error adding signal execution: {str(e)}")
            session.rollback()
            session.close()
    
    def get_active_signals(self) -> List[Signal]:
        """Get all active signals (NEW, FILLED)"""
        try:
            session = self.get_session()
            signals = session.query(Signal).filter(
                Signal.status.in_(['NEW', 'FILLED'])
            ).all()
            session.close()
            return signals
        except Exception as e:
            logger.error(f"Error getting active signals: {str(e)}")
            return []
    
    def get_signal_by_code(self, code: str) -> Signal:
        """Get signal by code"""
        try:
            session = self.get_session()
            signal = session.query(Signal).filter_by(code=code).first()
            session.close()
            return signal
        except Exception as e:
            logger.error(f"Error getting signal by code: {str(e)}")
            return None
    
    def get_cooldowns(self) -> List[Cooldown]:
        """Get active cooldowns"""
        try:
            session = self.get_session()
            cooldowns = session.query(Cooldown).filter(
                Cooldown.cooldown_until > datetime.utcnow()
            ).all()
            session.close()
            return cooldowns
        except Exception as e:
            logger.error(f"Error getting cooldowns: {str(e)}")
            return []
    
    def add_cooldown(self, symbol: str, mode: str, reason: str, cooldown_until: datetime):
        """Add cooldown period"""
        try:
            session = self.get_session()
            
            # Remove existing cooldown for same symbol/mode
            session.query(Cooldown).filter_by(symbol=symbol, mode=mode).delete()
            
            cooldown = Cooldown(
                symbol=symbol,
                mode=mode,
                reason=reason,
                cooldown_until=cooldown_until
            )
            session.add(cooldown)
            session.commit()
            session.close()
            
            logger.info(f"Cooldown added for {symbol} {mode} until {cooldown_until}")
            
        except Exception as e:
            logger.error(f"Error adding cooldown: {str(e)}")
            session.rollback()
            session.close()
    
    def calculate_daily_metrics(self, date: datetime, mode: str = None, symbol: str = None):
        """Calculate and store daily metrics"""
        try:
            session = self.get_session()
            
            # Base query
            query = session.query(Signal).filter(
                Signal.created_at >= date.replace(hour=0, minute=0, second=0),
                Signal.created_at < date.replace(hour=23, minute=59, second=59)
            )
            
            if mode:
                query = query.filter(Signal.mode == mode)
            if symbol:
                query = query.filter(Signal.symbol == symbol)
            
            signals = query.all()
            
            if not signals:
                session.close()
                return
            
            # Calculate metrics
            total_signals = len(signals)
            filled_signals = [s for s in signals if s.status in ['FILLED', 'WIN', 'LOSE']]
            win_signals = [s for s in signals if s.status == 'WIN']
            lose_signals = [s for s in signals if s.status == 'LOSE']
            
            win_rate = len(win_signals) / len(filled_signals) if filled_signals else 0
            
            # Calculate average RR
            avg_rr = 0
            if filled_signals:
                rr_values = []
                for signal in filled_signals:
                    if signal.pnl_points and signal.stop_loss and signal.entry_price:
                        risk = abs(signal.entry_price - signal.stop_loss)
                        reward = abs(signal.pnl_points)
                        if risk > 0:
                            rr_values.append(reward / risk)
                avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0
            
            # Other metrics
            total_pnl_points = sum(s.pnl_points for s in signals if s.pnl_points)
            total_pnl_percent = sum(s.pnl_percent for s in signals if s.pnl_percent)
            total_pnl_usd = sum(s.pnl_usd for s in signals if s.pnl_usd)
            
            avg_adx = sum(s.adx_value for s in signals if s.adx_value) / total_signals if total_signals else 0
            avg_volume_boost = sum(s.volume_boost for s in signals if s.volume_boost) / total_signals if total_signals else 0
            
            # Check if metrics already exist
            existing = session.query(DailyMetrics).filter_by(
                date=date.date(),
                mode=mode,
                symbol=symbol
            ).first()
            
            if existing:
                # Update existing
                existing.signals_generated = total_signals
                existing.signals_filled = len(filled_signals)
                existing.signals_win = len(win_signals)
                existing.signals_lose = len(lose_signals)
                existing.win_rate = win_rate
                existing.avg_rr = avg_rr
                existing.total_pnl_points = total_pnl_points
                existing.total_pnl_percent = total_pnl_percent
                existing.total_pnl_usd = total_pnl_usd
                existing.avg_adx = avg_adx
                existing.avg_volume_boost = avg_volume_boost
            else:
                # Create new
                metrics = DailyMetrics(
                    date=date.date(),
                    mode=mode,
                    symbol=symbol,
                    signals_generated=total_signals,
                    signals_filled=len(filled_signals),
                    signals_win=len(win_signals),
                    signals_lose=len(lose_signals),
                    win_rate=win_rate,
                    avg_rr=avg_rr,
                    total_pnl_points=total_pnl_points,
                    total_pnl_percent=total_pnl_percent,
                    total_pnl_usd=total_pnl_usd,
                    avg_adx=avg_adx,
                    avg_volume_boost=avg_volume_boost
                )
                session.add(metrics)
            
            session.commit()
            session.close()
            
            logger.info(f"Daily metrics calculated for {date.date()} {mode or 'ALL'} {symbol or 'ALL'}")
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {str(e)}")
            session.rollback()
            session.close()
    
    def log_event(self, level: str, message: str, module: str = None, symbol: str = None, 
                  mode: str = None, additional_data: str = None):
        """Log system event"""
        try:
            session = self.get_session()
            
            log_entry = SystemLog(
                level=level,
                message=message,
                module=module,
                symbol=symbol,
                mode=mode,
                additional_data=additional_data
            )
            
            session.add(log_entry)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error logging event: {str(e)}")
            session.rollback()
            session.close()

# Global database manager instance
db_manager = DatabaseManager()