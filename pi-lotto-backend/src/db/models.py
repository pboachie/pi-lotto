from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(100), unique=True, nullable=False)
    pool_amount = db.Column(db.Float, nullable=False, default=0)
    num_players = db.Column(db.Integer, nullable=False, default=0)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class UserGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    dateJoined = db.Column(db.DateTime, default=db.func.current_timestamp())

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    uid = db.Column(db.String(36), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0)
    active = db.Column(db.Boolean, default=True)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address = db.Column(db.String(100), unique=True, nullable=False)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())

class Transaction(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit' or 'withdrawal'
    memo = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    reference_id = db.Column(db.String(100), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class TransactionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), db.ForeignKey('transaction.id'), nullable=False)
    log_message = db.Column(db.String(255), nullable=False)
    log_timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class AccountTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit', 'withdrawal', 'game_entry', etc.
    amount = db.Column(db.Float, nullable=False)
    reference_id = db.Column(db.String(100), nullable=True)  # Reference to the associated transaction or game entry
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())

class Payment(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    memo = db.Column(db.String(100), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False)

class LottoStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.String(100), nullable=False)
    numbers_played = db.Column(db.String(100), nullable=False)
    win_amount = db.Column(db.Float, nullable=False)

class UserScopes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scope = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())

class TransactionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), db.ForeignKey('transaction.id'), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())