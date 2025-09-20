import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    action = Column(String)
    symbol = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    signal_time = Column(DateTime)

def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

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