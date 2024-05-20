# src/db/database.py

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, Session, Ticket, Game, Transaction, after_insert_ticket, after_update_ticket, after_update_game_winner
from src.utils.utils import load_config
from sqlalchemy.sql import func
import datetime

# Load configuration
config = load_config()

# Configure the database connection
engine = create_engine(config['database']['uri'])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

# Attach the listeners to the Ticket and Game models
event.listen(Ticket, 'after_insert', after_insert_ticket)
event.listen(Ticket, 'after_update', after_update_ticket)
event.listen(Game, 'after_update', after_update_game_winner)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_pool_amount():
    session = SessionLocal()
    try:
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

def cancel_old_pending_lotto_entries():
    session = SessionLocal()
    try:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=8)

        # Update transactions that are 'lotto_entry', 'pending', and older than 8 hours
        session.query(Transaction).filter(
            Transaction.transaction_type == 'lotto_entry',
            Transaction.status == 'pending',
            Transaction.dateModified <= cutoff_time
        ).update({"status": "cancelled"}, synchronize_session='fetch')

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error updating pending lotto transactions to cancelled: {e}")
    finally:
        session.close()
