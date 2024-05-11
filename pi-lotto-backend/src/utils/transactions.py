# src/utils/transactions.py
from typing import Optional
from typing_extensions import Annotated
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from src.db.database import get_db
from datetime import datetime, timedelta, timezone
from src.utils.utils import colorama, logging, uuid
from src.auth import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, OAUTH2_SCHEME
from src.db.models import User, UserScopes, Game, Transaction, TransactionData, Payment, TransactionLog, Session


# Function to store user data in the database
def update_user_data(user_data, db: Session):
    user = db.query(User).filter(User.username == user_data['username']).first()
    if user is None:
        new_user = User(username=user_data['username'], uid=user_data['uid'])
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    else:
        new_user = user

    # Add the user's scopes to the database. Deactivate any scopes that are not in the user's credentials
    for scope in user_data['credentials']['scopes']:
        user_scope = db.query(UserScopes).filter(UserScopes.user_id == new_user.id, UserScopes.scope == scope).first()
        if user_scope is None:
            new_user_scope = UserScopes(user_id=new_user.id, scope=scope)
            db.add(new_user_scope)
            db.commit()
        else:
            user_scope.active = True
            db.commit()

    # Deactivate any scopes that are not in the user's credentials
    user_scopes = db.query(UserScopes).filter(UserScopes.user_id == new_user.id).all()
    for user_scope in user_scopes:
        if user_scope.scope not in user_data['credentials']['scopes']:
            user_scope.active = False
            db.commit()

    return new_user

# Function to generate a unique game_id. It verifies that the game_id is unique in the database
def generate_game_id(db: Session):
    game_id = str(uuid.uuid4())
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if game is not None:
        return generate_game_id(db)
    return game_id

# Function to validate the end_time
def validate_end_time(data):
    if 'end_time' not in data:
        return {'error': 'end_time is required'}, 400

    try:
        # check if the end_time is a valid datetime object
        end_time = datetime.fromisoformat(data['end_time'])

        # Check if the end_time is at least 24 hours from now (date time)
        if end_time < datetime.now() + timedelta(days=1):
            return {'error': 'end_time must be at least 24 hours from now'}, 400

        # Check if the date time is correct format for db
        end_time = end_time.isoformat()
    except ValueError:
        return {'error': 'Invalid date format. Valid format is YYYY-MM-DDTHH:MM:SS'}, 400

    return end_time, 200

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def update_user_balance(user_id: int, transaction_amount: float, transaction_type: str, db: Session):
    try:
        user = db.query(User).get(user_id)
        if user:
            logging.info(colorama.Fore.GREEN + f"UPDATE: Updating user balance for user: {user.username} with transaction amount: {transaction_amount} and transaction type: {transaction_type}")

            if transaction_type == 'deposit':
                user.balance += transaction_amount
            elif transaction_type == 'withdrawal':
                user.balance -= transaction_amount
            elif transaction_type == 'game_entry':
                user.balance -= transaction_amount
            elif transaction_type == 'game_winnings':
                user.balance += transaction_amount
            elif transaction_type == 'lotto_winnings':
                user.balance += transaction_amount
            elif transaction_type == 'lotto_entry':
                user.balance -= transaction_amount
            else:
                raise ValueError('Invalid transaction type')

            db.commit()
            return True
        else:
            raise ValueError('User not found')
    except Exception as e:
        db.rollback()
        logging.error(colorama.Fore.RED + f"ERROR: Failed to update users balance. User ID: {user_id}. {str(e)}")
        return False

def create_transaction_log(transaction_id: str, log_message: str, db: Session):
    try:
        log_entry = TransactionLog(transaction_id=transaction_id, log_message=log_message)
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating transaction log: {str(e)}")

def create_transaction(user_id: int, ref_id: str, wallet_id: int, amount: float, transaction_type: str, memo: str, status: str, id: str = None, transactionData: dict = None, db: Session = Depends(get_db)):
    try:
        if id is None:
            transaction_id = str(uuid.uuid4())
        else:
            transaction_id = id

        transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            reference_id=ref_id,
            wallet_id=wallet_id,
            amount=amount,
            transaction_type=transaction_type,
            memo=memo,
            status=status
        )
        db.add(transaction)

        # Add transaction data if provided and is json. If already exists in db, log the occurrence
        if transactionData is not None and isinstance(transactionData, dict):
            existing_transaction_data = db.query(TransactionData).filter(TransactionData.transaction_id == transaction_id).first()
            if existing_transaction_data is not None:
                logging.warning(f"Transaction data already exists for transaction: {transaction_id}. Ignoring new data.")
            else:
                transaction_data = TransactionData(transaction_id=transaction_id, data=transactionData)
                db.add(transaction_data)
        else:
            logging.warning(f"Transaction data is not provided or is not a dictionary. Ignoring data. Transaction ID: {transaction_id}. User ID: {user_id}")

        db.commit()
        create_transaction_log(transaction_id, f"Transaction created: {transaction_id}", db)
        return transaction
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating transaction: {str(e)}")
        return None

def complete_transaction(transaction_id: str, txid: str, db: Session):
    try:
        transaction = db.query(Transaction).get(transaction_id)
        if transaction:
            transaction.transaction_id = txid
            transaction.status = 'completed'

            # Create payment record
            payment = Payment(id=transaction_id, user_id=transaction.user_id, amount=transaction.amount, memo=transaction.memo, transaction_id=txid, status='completed')
            db.add(payment)

            db.commit()
            create_transaction_log(transaction_id, f"Transaction completed: {transaction_id}", db)

            if update_user_balance(transaction.user_id, transaction.amount, transaction.transaction_type, db):
                return True
            else:
                raise ValueError('Failed to update user balance')
        else:
            raise ValueError('Transaction not found')
    except Exception as e:
        db.rollback()
        logging.error(f"Error completing transaction: {str(e)}")
        return False

# Dependency to get the current user
async def get_current_user(token: str = Depends(OAUTH2_SCHEME), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user
