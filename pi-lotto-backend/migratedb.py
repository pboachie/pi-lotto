from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from src.db.models import Game, UserGame, User, Wallet, Transaction, TransactionLog, AccountTransaction, Payment, LottoStats, UserScopes, TransactionData, GameType, GameConfig

# Instructions:
# Run export FLASK_APP=migratedb.py
# Run set FLASK_APP=migratedb.py
# Copy all classes from models.py and paste them here then fun flask db migrate -m "YOUR MESSAGE HERE" , then flask db upgrade

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pilotto.db'  # Replace with your database URI
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_type_id = db.Column(db.Integer, db.ForeignKey('game_type.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    pool_amount = db.Column(db.Float, nullable=False, default=0)
    entry_fee = db.Column(db.Float, nullable=False, default=0)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    max_players = db.Column(db.Integer, nullable=False, default=0)
    user_games = db.relationship('UserGame', backref='game', lazy='dynamic')


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

class GameType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class GameConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_type_id = db.Column(db.Integer, db.ForeignKey('game_type.id'), nullable=False)
    config_key = db.Column(db.String(100), nullable=False)
    config_value = db.Column(db.String(255), nullable=False)
    dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
    dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


if __name__ == '__main__':
    with app.app_context():
        # Initialize the migration repository if it doesn't exist
        if not migrate.directory():
            db.create_all()
            migrate.init()

        # Generate the migration script
        from flask_migrate import upgrade, migrate

        # Generate the migration script
        migrate(message='Updated database schema')

        # Apply the migration
        upgrade()

    print("Database schema updated successfully!")