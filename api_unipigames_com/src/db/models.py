from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql import func
from pydantic import BaseModel

Base = declarative_base()

# ==== Sign in request and response models =====
class Session(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class bm_valid_until(BaseModel):
    timestamp: int
    iso8601: str

class bm_credentials(BaseModel):
    scopes: list
    valid_until: bm_valid_until

class bm_user(BaseModel):
    uid: str
    credentials: bm_credentials
    username: str

class bm_authResult(BaseModel):
    user: bm_user
    accessToken: str


class SignInRequest(BaseModel):
    authResult: bm_authResult

class SignInResponse(BaseModel):
    access_token: str
    refresh_token: str
# ================================================

# ==== User request and response models =====

# ================================================
def after_insert_ticket(mapper, connection, target):
    # Create a new LottoStats entry for the new ticket
    new_lotto_stats = LottoStats(
        user_id=target.user_id,
        game_id=target.game_id,
        numbers_played=target.numbers_played,
        win_amount=0.0  # Initially set win_amount to 0.0
    )
    session = Session(bind=connection)
    session.add(new_lotto_stats)
    session.commit()

# Listener for after_update event on Ticket
def after_update_ticket(mapper, connection, target):
    # Update the corresponding LottoStats entry for the ticket
    session = Session(bind=connection)
    lotto_stats = session.query(LottoStats).filter_by(
        user_id=target.user_id,
        game_id=target.game_id
    ).first()
    if lotto_stats:
        lotto_stats.numbers_played = target.numbers_played
        session.commit()

# Listener for after_insert event on UserGame
def after_insert_user_game(mapper, connection, target):
    """Create a new LottoStats entry for the new UserGame"""
    new_lotto_stats = LottoStats(
        user_id=target.user_id,
        game_id=target.game_id,
        numbers_played="",  # Initially set numbers_played to an empty string
        win_amount=0.0      # Initially set win_amount to 0.0
    )
    session = Session(bind=connection)
    session.add(new_lotto_stats)
    session.commit()

# Listener for after_update event on UserGame
def after_update_user_game(mapper, connection, target):
    """Update the corresponding LottoStats entry for the UserGame"""
    session = Session(bind=connection)
    lotto_stats = session.query(LottoStats).filter_by(
        user_id=target.user_id,
        game_id=target.game_id
    ).first()
    if lotto_stats:
        # Update any fields in LottoStats based on UserGame update
        session.commit()

# ================================================

# ==== User request and response models =====
class Game(Base):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True)
    game_type_id = Column(Integer, ForeignKey('game_type.id'), nullable=False)
    name = Column(String(100), nullable=False)
    pool_amount = Column(Float, nullable=False, default=0)
    entry_fee = Column(Float, nullable=False, default=0)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default='active')
    winner_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    dateCreated = Column(DateTime, default=func.current_timestamp())
    dateModified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    max_players = Column(Integer, nullable=False, default=0)
    user_games = relationship('UserGame', backref='game', lazy='dynamic')

class UserGame(Base):
    __tablename__ = 'user_game'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    game_id = Column(Integer, ForeignKey('game.id'), nullable=False)
    dateJoined = Column(DateTime, default=func.current_timestamp())

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    uid = Column(String(36), unique=True, nullable=False)
    balance = Column(Float, default=0)
    active = Column(Boolean, default=True)
    dateCreated = Column(DateTime, default=func.current_timestamp())
    dateModified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

class Wallet(Base):
    __tablename__ = 'wallet'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    address = Column(String(100), unique=True, nullable=False)
    dateCreated = Column(DateTime, default=func.current_timestamp())

class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(String(100), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    wallet_id = Column(Integer, ForeignKey('wallet.id'), nullable=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'deposit' or 'withdrawal'
    memo = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    reference_id = Column(String(100), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    dateCreated = Column(DateTime, default=func.current_timestamp())
    dateModified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

class TransactionLog(Base):
    __tablename__ = 'transaction_log'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100), ForeignKey('transaction.id'), nullable=False)
    log_message = Column(String(255), nullable=False)
    log_timestamp = Column(DateTime, default=func.current_timestamp())

class AccountTransaction(Base):
    __tablename__ = 'account_transaction'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'deposit', 'withdrawal', 'game_entry', etc.
    amount = Column(Float, nullable=False)
    reference_id = Column(String(100), nullable=True)  # Reference to the associated transaction or game entry
    dateCreated = Column(DateTime, default=func.current_timestamp())

class Payment(Base):
    __tablename__ = 'payment'

    id = Column(String(100), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    amount = Column(Float, nullable=False)
    memo = Column(String(100), nullable=False)
    transaction_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False)

class LottoStats(Base):
    __tablename__ = 'lotto_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    game_id = Column(String(100), nullable=False)
    numbers_played = Column(String(100), nullable=False)
    win_amount = Column(Float, nullable=False)

class UserScopes(Base):
    __tablename__ = 'user_scopes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    scope = Column(String(20), nullable=False)
    active = Column(Boolean, default=True)
    dateCreated = Column(DateTime, default=func.current_timestamp())

class TransactionData(Base):
    __tablename__ = 'transaction_data'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100), ForeignKey('transaction.id'), nullable=False)
    data = Column(JSON, nullable=False)
    dateCreated = Column(DateTime, default=func.current_timestamp())
    dateModified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

class GameType(Base):
    __tablename__ = 'game_type'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    dateCreated = Column(DateTime, default=func.current_timestamp())
    dateModified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

class GameConfig(Base):
    __tablename__ = 'game_config'

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'), nullable=True)
    game_type_id = Column(Integer, ForeignKey('game_type.id'), nullable=False)
    config_key = Column(String(100), nullable=False)
    config_value = Column(String(255), nullable=False)
    dateCreated = Column(DateTime, default=func.current_timestamp())
    dateModified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

class Ticket(Base):
    __tablename__ = 'ticket'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    game_id = Column(Integer, ForeignKey('game.id'), nullable=False)
    transaction_id = Column(String(100), ForeignKey('transaction.id'), nullable=False)
    numbers_played = Column(String(100), nullable=False)
    power_number = Column(Integer, nullable=False)
    date_purchased = Column(DateTime, default=func.current_timestamp())

# ================================================
