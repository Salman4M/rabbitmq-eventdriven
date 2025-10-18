from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from order_service.models import Base
from decouple import config

DATABASE_URL = config(
    'DATABASE_URL',
    default='postgresql+psycopg://postgres:postgres123@localhost:5435/order_db'
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)