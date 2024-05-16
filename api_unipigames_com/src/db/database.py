# src/db/database.py

from sqlalchemy import create_engine, event
from src.db.models import Base, sessionmaker, Session, Ticket, Game, Transaction, after_insert_ticket, after_update_ticket, after_update_game_winner, after_insert_ticket
from src.utils.utils import load_config
from sqlalchemy.sql import func
import datetime

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

# Attach the listeners to the Ticket and Game models
event.listen(Ticket, 'after_insert', after_insert_ticket)
event.listen(Game, 'after_update', after_update_game_winner)

def update_pool_amount():
    try:
        session = SessionLocal()

        # Get all active games
        games = session.query(Game).filter(Game.status == 'active').all()
        for game in games:
            # Calculate the new pool amount by summing the entry fees of all completed transactions related to ticket purchases
            total_entry_fees = session.query(func.sum(Transaction.amount)).\
                join(Ticket, Ticket.transaction_id == Transaction.id).\
                filter(Transaction.transaction_type == 'lotto_entry',
                       Ticket.game_id == game.id,
                       Transaction.status == 'completed').scalar() or 0

            game.pool_amount = total_entry_fees

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error updating pool amounts: {e}")
    finally:
        session.close()
