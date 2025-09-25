from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    DECIMAL,
    ForeignKey,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL

# Database setup - Convert postgresql:// to postgresql+pg8000:// for pg8000 driver
database_url = DATABASE_URL
if database_url and database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

DEFAULT_USER_REF = "default"


class StrategyPreference(Base):
    __tablename__ = "strategy_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_ref = Column(String, unique=True, nullable=False, default=DEFAULT_USER_REF)
    product = Column(String, nullable=True)
    strategy = Column(String, nullable=True)
    direction_mode = Column(String, nullable=True)
    leverage = Column(Float, nullable=True)
    capital_allocation_percent = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    action = Column(String(10))
    symbol = Column(String(50))
    quantity = Column(DECIMAL(20, 8))
    price = Column(DECIMAL(20, 8))
    signal_time = Column(DateTime, nullable=True)
    strategy = Column(String(100), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    source = Column(String(50), default='tradingview')
    created_at = Column(DateTime, default=datetime.utcnow)


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    action = Column(String(10))
    symbol = Column(String(50))
    quantity = Column(DECIMAL(20, 8))
    status = Column(String(20))
    order_id = Column(String(100))
    execution_time = Column(DateTime)

    # Detailed timing tracking
    signal_sent_time = Column(DateTime, nullable=True)
    received_time = Column(DateTime, nullable=True)
    processed_time = Column(DateTime, nullable=True)
    sent_to_binance_time = Column(DateTime, nullable=True)
    binance_executed_time = Column(DateTime, nullable=True)

    # Additional execution details
    executed_price = Column(DECIMAL(20, 8), nullable=True)
    executed_quantity = Column(DECIMAL(20, 8), nullable=True)
    fees = Column(DECIMAL(20, 8), nullable=True)
    commission_asset = Column(String(10), nullable=True)
    leverage = Column(Integer, nullable=True)
    capital_percent = Column(DECIMAL(5, 2), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)




def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_preference(db: Session, user_ref: str = DEFAULT_USER_REF) -> StrategyPreference:
    preference = (
        db.query(StrategyPreference).filter(StrategyPreference.user_ref == user_ref).first()
    )
    if not preference:
        preference = StrategyPreference(user_ref=user_ref)
        db.add(preference)
        db.commit()
        db.refresh(preference)
    return preference


def store_signal(action, symbol, quantity, price, signal_time):
    """Store signal in database"""
    # Convert signal_time from UTC to IST if provided
    ist_signal_time = None
    if signal_time:
        try:
            from datetime import datetime
            import pytz
            utc_time = datetime.fromisoformat(signal_time.replace('Z', '+00:00'))
            ist_tz = pytz.timezone('Asia/Kolkata')
            ist_signal_time = utc_time.astimezone(ist_tz).replace(tzinfo=None)
        except:
            ist_signal_time = None

    db = SessionLocal()
    try:
        db_signal = Signal(
            action=action,
            symbol=symbol,
            quantity=quantity,
            price=price,
            signal_time=ist_signal_time
        )
        db.add(db_signal)
        db.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)

    # Balance information
    asset = Column(String(10), default='USDT')
    available_balance = Column(DECIMAL(20, 8), nullable=True)
    wallet_balance = Column(DECIMAL(20, 8), nullable=True)
    cross_wallet_balance = Column(DECIMAL(20, 8), nullable=True)
    total_wallet_balance = Column(DECIMAL(20, 8), nullable=True)
    total_unrealized_profit = Column(DECIMAL(20, 8), nullable=True)
    total_margin_balance = Column(DECIMAL(20, 8), nullable=True)

    # Account status
    can_trade = Column(Boolean, default=True)
    can_withdraw = Column(Boolean, default=True)
    can_deposit = Column(Boolean, default=True)

    # Snapshot trigger
    trigger_type = Column(String(50), nullable=True)
    trigger_details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=True)
    size = Column(DECIMAL(20, 8), nullable=True)
    entry_price = Column(DECIMAL(20, 8), nullable=True)
    mark_price = Column(DECIMAL(20, 8), nullable=True)
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=True)
    percentage = Column(DECIMAL(10, 4), nullable=True)

    # Position details
    leverage = Column(Integer, nullable=True)
    margin_type = Column(String(20), nullable=True)
    isolated_margin = Column(DECIMAL(20, 8), nullable=True)

    # Timestamps
    opened_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    binance_order_id = Column(String(100), unique=True, nullable=True)
    client_order_id = Column(String(100), nullable=True)

    # Order details
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=True)
    type = Column(String(20), nullable=True)
    quantity = Column(DECIMAL(20, 8), nullable=True)
    price = Column(DECIMAL(20, 8), nullable=True)

    # Execution details
    executed_quantity = Column(DECIMAL(20, 8), nullable=True)
    executed_price = Column(DECIMAL(20, 8), nullable=True)
    cumulative_quote_quantity = Column(DECIMAL(20, 8), nullable=True)

    # Order status
    status = Column(String(20), nullable=True)
    time_in_force = Column(String(10), nullable=True)

    # Fees
    commission = Column(DECIMAL(20, 8), nullable=True)
    commission_asset = Column(String(10), nullable=True)

    # Timestamps
    created_time = Column(DateTime, nullable=True)
    updated_time = Column(DateTime, nullable=True)
    working_time = Column(DateTime, nullable=True)

    # Relationship to our execution
    execution_id = Column(Integer, ForeignKey('executions.id'), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)

    # Log details
    level = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)

    # Context
    endpoint = Column(String(100), nullable=True)
    user_ref = Column(String(255), default=DEFAULT_USER_REF)
    session_id = Column(String(100), nullable=True)

    # Additional data
    log_metadata = Column(JSONB, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Request details
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(200), nullable=True)
    request_body = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    period_type = Column(String(20), nullable=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Trading metrics
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    failed_trades = Column(Integer, default=0)
    win_rate = Column(DECIMAL(5, 2), nullable=True)

    # P&L metrics
    total_pnl = Column(DECIMAL(20, 8), nullable=True)
    realized_pnl = Column(DECIMAL(20, 8), nullable=True)
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=True)
    total_fees = Column(DECIMAL(20, 8), nullable=True)
    net_pnl = Column(DECIMAL(20, 8), nullable=True)

    # Volume metrics
    total_volume = Column(DECIMAL(20, 8), nullable=True)
    buy_volume = Column(DECIMAL(20, 8), nullable=True)
    sell_volume = Column(DECIMAL(20, 8), nullable=True)

    # Risk metrics
    max_drawdown = Column(DECIMAL(20, 8), nullable=True)
    max_position_size = Column(DECIMAL(20, 8), nullable=True)
    avg_leverage = Column(DECIMAL(5, 2), nullable=True)

    # Balance tracking
    starting_balance = Column(DECIMAL(20, 8), nullable=True)
    ending_balance = Column(DECIMAL(20, 8), nullable=True)
    peak_balance = Column(DECIMAL(20, 8), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class ConfigurationChange(Base):
    __tablename__ = "configuration_changes"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)

    # What changed
    table_name = Column(String(50), nullable=True)
    record_id = Column(Integer, nullable=True)
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Who/what changed it
    changed_by = Column(String(100), default='system')
    change_source = Column(String(50), nullable=True)
    change_reason = Column(Text, nullable=True)

    # Request context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)

    # Service status
    service_name = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Details
    check_details = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics
    cpu_usage = Column(DECIMAL(5, 2), nullable=True)
    memory_usage = Column(DECIMAL(5, 2), nullable=True)
    disk_usage = Column(DECIMAL(5, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


def store_execution(action, symbol, quantity, status, order_id=None, timing_data=None, execution_details=None):
    """Store execution result in database with optional timing data and execution details"""
    execution_time = datetime.now()

    db = SessionLocal()
    try:
        db_execution = Execution(
            action=action,
            symbol=symbol,
            quantity=quantity,
            status=status,
            order_id=order_id or "N/A",
            execution_time=execution_time
        )

        # Add timing data if provided
        if timing_data:
            db_execution.signal_sent_time = timing_data.get('signal_sent')
            db_execution.received_time = timing_data.get('received')
            db_execution.processed_time = timing_data.get('processed')
            db_execution.sent_to_binance_time = timing_data.get('sent_to_binance')
            db_execution.binance_executed_time = timing_data.get('executed')

        # Add execution details if provided
        if execution_details:
            db_execution.executed_price = execution_details.get('executed_price')
            db_execution.executed_quantity = execution_details.get('executed_quantity')
            db_execution.fees = execution_details.get('fees')
            db_execution.commission_asset = execution_details.get('commission_asset')
            db_execution.leverage = execution_details.get('leverage')
            db_execution.capital_percent = execution_details.get('capital_percent')
            db_execution.error_message = execution_details.get('error_message')
            db_execution.error_code = execution_details.get('error_code')

        db.add(db_execution)
        db.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def store_account_snapshot(balance_data, trigger_type='manual', trigger_details=None):
    """Store account balance snapshot"""
    db = SessionLocal()
    try:
        snapshot = AccountSnapshot(
            asset=balance_data.get('asset', 'USDT'),
            available_balance=balance_data.get('available_balance'),
            wallet_balance=balance_data.get('wallet_balance'),
            cross_wallet_balance=balance_data.get('cross_wallet_balance'),
            total_wallet_balance=balance_data.get('total_wallet_balance'),
            total_unrealized_profit=balance_data.get('total_unrealized_profit'),
            total_margin_balance=balance_data.get('total_margin_balance'),
            can_trade=balance_data.get('can_trade', True),
            can_withdraw=balance_data.get('can_withdraw', True),
            can_deposit=balance_data.get('can_deposit', True),
            trigger_type=trigger_type,
            trigger_details=trigger_details
        )
        db.add(snapshot)
        db.commit()
        return True
    except Exception as e:
        print(f"Database error storing account snapshot: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def store_order(order_data, execution_id=None):
    """Store order information"""
    db = SessionLocal()
    try:
        order = Order(
            binance_order_id=order_data.get('orderId'),
            client_order_id=order_data.get('clientOrderId'),
            symbol=order_data.get('symbol'),
            side=order_data.get('side'),
            type=order_data.get('type'),
            quantity=order_data.get('origQty'),
            price=order_data.get('price'),
            executed_quantity=order_data.get('executedQty'),
            executed_price=order_data.get('avgPrice'),
            cumulative_quote_quantity=order_data.get('cummulativeQuoteQty'),
            status=order_data.get('status'),
            time_in_force=order_data.get('timeInForce'),
            created_time=datetime.fromtimestamp(order_data.get('time', 0) / 1000) if order_data.get('time') else None,
            updated_time=datetime.fromtimestamp(order_data.get('updateTime', 0) / 1000) if order_data.get('updateTime') else None,
            working_time=datetime.fromtimestamp(order_data.get('workingTime', 0) / 1000) if order_data.get('workingTime') else None,
            execution_id=execution_id
        )
        db.add(order)
        db.commit()
        return order.id
    except Exception as e:
        print(f"Database error storing order: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def store_system_log(level, category, message, **kwargs):
    """Store system log entry"""
    db = SessionLocal()
    try:
        log = SystemLog(
            level=level,
            category=category,
            message=message,
            endpoint=kwargs.get('endpoint'),
            user_ref=kwargs.get('user_ref', DEFAULT_USER_REF),
            session_id=kwargs.get('session_id'),
            log_metadata=kwargs.get('metadata'),
            stack_trace=kwargs.get('stack_trace'),
            request_method=kwargs.get('request_method'),
            request_path=kwargs.get('request_path'),
            request_body=kwargs.get('request_body'),
            response_status=kwargs.get('response_status'),
            response_time_ms=kwargs.get('response_time_ms')
        )
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        print(f"Database error storing system log: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def update_position(symbol, position_data):
    """Update or create position"""
    db = SessionLocal()
    try:
        # Find existing active position
        position = db.query(Position).filter(
            Position.symbol == symbol,
            Position.side == position_data.get('side'),
            Position.is_active == True
        ).first()

        if position:
            # Update existing position
            position.size = position_data.get('size')
            position.entry_price = position_data.get('entry_price')
            position.mark_price = position_data.get('mark_price')
            position.unrealized_pnl = position_data.get('unrealized_pnl')
            position.percentage = position_data.get('percentage')
            position.leverage = position_data.get('leverage')
            position.margin_type = position_data.get('margin_type')
            position.isolated_margin = position_data.get('isolated_margin')
            position.updated_at = datetime.utcnow()
        else:
            # Create new position
            position = Position(
                symbol=symbol,
                side=position_data.get('side'),
                size=position_data.get('size'),
                entry_price=position_data.get('entry_price'),
                mark_price=position_data.get('mark_price'),
                unrealized_pnl=position_data.get('unrealized_pnl'),
                percentage=position_data.get('percentage'),
                leverage=position_data.get('leverage'),
                margin_type=position_data.get('margin_type'),
                isolated_margin=position_data.get('isolated_margin'),
                opened_at=datetime.utcnow()
            )
            db.add(position)

        db.commit()
        return True
    except Exception as e:
        print(f"Database error updating position: {e}")
        db.rollback()
        return False
    finally:
        db.close()


