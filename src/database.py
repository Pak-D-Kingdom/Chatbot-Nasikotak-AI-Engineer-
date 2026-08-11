import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure data directory exists
os.makedirs("data", exist_ok=True)
DB_PATH = "sqlite:///data/nasikotak.db"

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    minimum_order = Column(Integer, default=1)
    menu = Column(Text, nullable=True)  # Store as JSON string or plain text
    suitable_for = Column(Text, nullable=True) # JSON list string
    image_url = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Promotion(Base):
    __tablename__ = "promotions"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String, nullable=False) # 'percentage', 'fixed'
    discount_value = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    conditions = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    budget = Column(Float, nullable=True)
    event_type = Column(String, nullable=True)
    event_date = Column(String, nullable=True)
    location = Column(String, nullable=True)
    product_id = Column(String, nullable=True)
    purchase_intent = Column(String, nullable=True)
    status = Column(String, default="new")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True)
    sender = Column(String, nullable=False) # 'user' or 'bot'
    message = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    purchase_intent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
