# src/db/database.py

from sqlalchemy import create_engine, event
from src.db.models import Base, sessionmaker, Session, Ticket, after_insert_ticket, after_update_ticket
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

# ==== Database triggers =====
# Attach the listeners to the Ticket model
event.listen(Ticket, 'after_insert', after_insert_ticket)
event.listen(Ticket, 'after_update', after_update_ticket)