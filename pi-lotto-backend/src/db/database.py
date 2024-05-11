# src/db/database.py

from sqlalchemy import create_engine
from .models import Base, sessionmaker, Session
from src.utils.utils import load_config

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configure the database connection

config = load_config()

engine = create_engine(config['database']['uri'])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)