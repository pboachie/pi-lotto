# main.py

import yaml
import logging
import requests
import uuid
import json
import colorama
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from src.db.models import Base, Game, UserGame, User, Wallet, Transaction, TransactionLog, AccountTransaction, Payment, LottoStats, UserScopes, TransactionData, GameType, GameConfig
from src.pi_python import PiNetwork

app = FastAPI()


# Load configuration from config.yml
with open("config/config.yml", 'r') as config_file:
    config = yaml.safe_load(config_file)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify the allowed origins or use "*" to allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # You can specify the allowed HTTP methods or use "*" to allow all methods
    allow_headers=["*"],  # You can specify the allowed headers or use "*" to allow all headers
)

# Configure logging
logging.basicConfig(level=config['logging']['level'],
                    format=config['logging']['format'],
                    handlers=[logging.StreamHandler()])

# Add file handler if log file path is provided
file_handler = logging.FileHandler(config['logging']['filePath'], mode='a', encoding=None, delay=False)
logging.getLogger().addHandler(file_handler)

# Set colorama to autoreset
colorama.init(autoreset=True)

SECRET_KEY = config['jwt']['secret_key']
ALGORITHM = config['jwt']['algorithm']
ACCESS_TOKEN_EXPIRE_MINUTES = config['jwt']['access_token_expire_minutes']

# Configure the database connection
engine = create_engine(config['database']['uri'])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency to get the current user
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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

# Initialize Pi Network
pi_network = PiNetwork()
pi_network.initialize(config['api']['base_url'], config['api']['server_api_key'], config['api']['app_wallet_seed'], config['api']['network'])

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

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    # Log the exception
    logging.error(f"Unhandled exception: {str(exc)}")

    # Return an appropriate error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An internal server error occurred"},
    )

@app.post("/signin")
async def signin(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        auth_result = data['authResult']
        access_token = auth_result['accessToken']

        # Verify with the user's access token
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"{config['api']['base_url']}/v2/me", headers=headers)
        response.raise_for_status()
        user_data = response.json()

        # Check if the response status is 200
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization')

        # Check if response user data is not empty
        if user_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

        # Store user data in the database
        user = update_user_data(user_data, db)

        # Generate JWT token for the user
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

        # Generate refresh token for the user
        refresh_token_expires = timedelta(hours=5)
        refresh_token = create_access_token(data={"sub": user.username}, expires_delta=refresh_token_expires)


        logging.info(colorama.Fore.GREEN + f"SIGNIN: User {user.username} signed in successfully")
        return JSONResponse({'access_token': access_token, 'refresh_token': refresh_token})

    except json.JSONDecodeError:
        logging.error("Invalid JSON format in request body")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid JSON format in request body"},
        )

    except KeyError as e:
        logging.error(f"Missing key in request body: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"Missing key in request body: {str(e)}"},
        )

    except requests.exceptions.RequestException as err:
        logging.error(err)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not authorized')

@app.post("/refresh-token")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + "Refresh token is missing")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token is missing")

        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Generate a new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)


        return {"access_token": access_token}

    except HTTPException as e:
        logging.error(f"Error refreshing token: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh token")

@app.post("/create_deposit")
async def create_deposit(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.uid
        data = await request.json()
        amount = data["amount"]

        # Check if the user exists
        user = db.query(User).filter(User.uid == user_id).first()
        if user is None:
            return JSONResponse({'error': 'User not found. Unable to create deposit'}, status_code=status.HTTP_404_NOT_FOUND)

        # Check if the amount is a positive number
        if amount <= 0:
            return JSONResponse({'error': 'Invalid amount. Amount must be a positive number'}, status_code=status.HTTP_400_BAD_REQUEST)

        deposit_id = str(uuid.uuid4())

        # get last 6 digits of user id
        last6uid = user_id[-6:]

        # Generate memo and metadata
        memo = f"Deposit to Uni Pi Games account# {last6uid}"
        metadata = {
            "app_version": f"{config['app']['version']}",
            "deposit_id": deposit_id
        }

        # if debug mode is enabled, append "test: true" to the metadata
        if config['app']['debug'] == True:
            metadata["test"] = True

        # Make sure the amount is in the correct format and a float
        amount = float(amount)

        payment_data = {
            "payment": {
                "amount": amount,
                "memo": memo,
                "metadata": metadata,
                "uid": user_id
            }
        }

        # Create a transaction record
        transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=float(amount), transaction_type='deposit', memo=str(memo), status='pending', id=deposit_id, transactionData=payment_data, db=db)

        if transaction is None:
            logging.error(colorama.Fore.RED + f"ERROR: Failed to create transaction for user: {user.username} in the amount of {amount}. Deposit ID: {deposit_id}")
            return JSONResponse({'error': 'Failed to create transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logging.info(colorama.Fore.GREEN + f"DEPOSIT: Deposit started for user : {user.username} in the amount of {amount}. Deposit ID: {deposit_id}")
        return JSONResponse(payment_data)

    except requests.exceptions.RequestException as err:
        logging.error(err)
        return JSONResponse({'error': 'Failed to create deposit'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.post("/create_withdrawal")
async def create_withdrawal(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.uid
        data = await request.json()
        trans_fee = 0.01  # Fetch from db or api
        amount = float(data["amount"]) + trans_fee

        # Check if the user exists
        user = db.query(User).filter(User.uid == user_id).first()
        if user is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: User not found. Unable to create withdrawal for user: {user_id}")
            return JSONResponse({'error': 'User not found. Unable to create withdrawal'}, status_code=status.HTTP_404_NOT_FOUND)

        # Check if the amount is a positive number
        if amount <= 0:
            return JSONResponse({'error': 'Invalid amount. Amount must be a positive number'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Check if minimum withdrawal amount is met (0.019)
        if amount < 0.019:
            return JSONResponse({'error': 'Invalid amount. Minimum withdrawal amount is 0.019'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get user's balance
        if user.balance < amount:
            return JSONResponse({'error': 'Insufficient balance'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get app wallet balance, if none, set to 0
        app_wallet_balance = pi_network.get_balance()

        if app_wallet_balance is None:
            logging.error(colorama.Fore.RED + f"PAYMENT ERROR: Failed to get app wallet balance. Unable to create withdrawal for user: {user.username}")
            app_wallet_balance = 0

        # Check if the app wallet has enough balance to process the withdrawal
        if app_wallet_balance < amount:
            logging.error(colorama.Fore.RED + f"PAYMENT ERROR: **Insufficient balance in app wallet. Unable to create withdrawal for user: {user.username} in the amount of {amount}**")
            return JSONResponse({'error': 'Server is currently under maintenance. Please try again later'}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

        withdrawal_id = str(uuid.uuid4())

        # get last 6 digits of user id
        last6uid = user_id[-6:]

        # Generate memo and metadata
        memo = f"Withdrawal from Uni Pi Games account# {last6uid}"
        metadata = {
            "app_version": f"{config['app']['version']}",
            "withdrawal_id": withdrawal_id
        }

        # if debug mode is enabled, append "test: true" to the metadata
        if config['app']['debug'] == True:
            metadata["test"] = True

        payment_data = {
            "payment": {
                "amount": amount,
                "memo": memo,
                "metadata": metadata,
                "uid": user_id
            }
        }

        # Create a transaction record
        transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=float(amount), transaction_type='withdrawal', memo=str(memo), status='pending', id=withdrawal_id, transactionData=payment_data, db=db)

        if transaction is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to create transaction for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
            return JSONResponse({'error': 'Failed to create transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get transaction from db using withdrawal_id in pending status to not overpay
        payment = db.query(Transaction).filter(Transaction.id == withdrawal_id, Transaction.status == 'pending').first()

        if payment is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to create withdrawal for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}. Payment not found or already completed")
            return JSONResponse({'error': 'Failed to create withdrawal. Server error. Please try again later or contact support for assistance'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payment_id = pi_network.create_payment(payment_data['payment'])

        if payment_id is None:
            logging.error(colorama.Fore.RED + f"ERROR: Failed to create withdrawal for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}.")
            return JSONResponse({'error': 'Failed to create withdrawal. Server error. Please try again later or contact support for assistance'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logging.info(colorama.Fore.GREEN + f"WITHDRAWAL: Withdrawal started for user : {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")

        # Update the transaction status to pending
        payment.status = 'approved'
        payment.ref_id = payment_id
        db.commit()

        # Approve the transaction
        txid = pi_network.submit_payment(payment_id, False)

        # if response status is not 200, return an error
        if txid is None:
            logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Failed to approve payment. Payment ID: {withdrawal_id}.")
            return JSONResponse({'error': 'Failed to approve payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Complete the transaction
        paymentData = pi_network.complete_payment(payment_id, txid)

        if paymentData is None:
            logging.error(colorama.Fore.RED + f"ERROR: Failed to complete transaction for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
            return JSONResponse({'error': 'Failed to complete transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not complete_transaction(payment.id, txid, db):
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to complete transaction for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
            return JSONResponse({'error': 'Failed to complete transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logging.info(colorama.Fore.GREEN + f"APPROVE: Withdrawal approved successfully for user: {user.username} with amount: {amount}. Payment ID: {withdrawal_id}")

        # Get new user balance
        user = db.query(User).filter(User.uid == user_id).first()
        user_balance = user.balance

        return JSONResponse({'message': 'Withdrawal Completed Successfully', 'balance': user_balance}, status_code=status.HTTP_200_OK)

    except requests.exceptions.RequestException as err:
        logging.error(err)
        return JSONResponse({'error': 'Failed to create withdrawal'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.post("/approve_payment/{payment_id}")
async def approve_payment(payment_id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.uid
        user = db.query(User).filter(User.uid == user_id).first()

        if user is None:
            logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. User not found")
            return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

        user_scope = db.query(UserScopes).filter(UserScopes.user_id == user.id, UserScopes.scope == 'payments').first()
        if user_scope is None or not user_scope.active:
            return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

        # Get deposit_id from metadata
        try:
            data = await request.json()
            req_deposit_id = data['paymentData']['payment']['metadata']['deposit_id']
        except KeyError:
            req_deposit_id = None

        # if deposit_id is not provided, return an error
        if req_deposit_id is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Deposit ID not provided")
            return JSONResponse({'error': 'Deposit ID is required'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get Transaction from db using deposit_id
        payment = db.query(Transaction).filter(Transaction.id == req_deposit_id).first()

        # If payment is not found, return an error
        if payment is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Payment not found for user: {user.username}. Payment ID: {req_deposit_id}")
            return JSONResponse({'error': 'Invalid payment request. Please try again or contact support'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get transaction Data from db using deposit_id
        db_data = db.query(TransactionData).filter(TransactionData.transaction_id == req_deposit_id).first()

        if db_data is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Transaction data not found for user: {user.username}. Payment ID: {req_deposit_id}")
            return JSONResponse({'error': 'Invalid payment request. Please try again or contact support'}, status_code=status.HTTP_400_BAD_REQUEST)

        data = db_data.data

        if data is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Transaction data not found for user: {user.username}. Payment ID: {req_deposit_id}")
            return JSONResponse({'error': 'Invalid payment request. Please try again or contact support'}, status_code=status.HTTP_400_BAD_REQUEST)

        pl_cost = data['payment']['amount']

        # If amount is not provided or is less than 0, return an error
        if pl_cost is None or pl_cost <= 0:
            return JSONResponse({'error': 'Invalid amount'}, status_code=status.HTTP_400_BAD_REQUEST)

        logging.info(colorama.Fore.GREEN + f"APPROVE: Creating a new payment for user: {user.username} in the amount of {pl_cost}. Payment ID: {req_deposit_id}")

        # approveStatus = pi_network.get_payment(payment_id)
        headers = {
            "Authorization": f"Key {config['api']['server_api_key']}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{config['api']['base_url']}/v2/payments/" + payment_id + "/approve/", headers=headers)

        # Save contents to json file locally using payment_id as filename
        with open(f"resources/approvals/{payment_id}_approval.json", "w") as f:
            json.dump(response.json(), f)

        # if response status is not 200, return an error
        if response.status_code != 200:
            logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Failed to approve payment. Payment ID: {payment_id}. Response: {response.content}")
            return JSONResponse({'error': 'Failed to approve payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update the transaction status to Approved
        payment.status = 'approved'
        payment.ref_id = payment_id
        db.commit()

        logging.info(colorama.Fore.GREEN + f"APPROVE: Payment approved successfully for user: {user.username}. Payment ID: {payment_id}")
        return JSONResponse(response.json())
    except Exception as err:
        logging.error(err)
        return JSONResponse({'error': 'Failed to approve payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.post("/complete_payment/{payment_id}")
async def complete_payment(payment_id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.uid

        # Check if user exists
        user = db.query(User).filter(User.uid == user_id).first()
        if user is None:
            return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

        try:
            data = await request.json()
            req_deposit_id = data['paymentData']['payment']['metadata']['deposit_id']
        except KeyError:
            req_deposit_id = None

        txid = data['txid']

        # if deposit_id is not provided, return an error
        if req_deposit_id is None:
            return JSONResponse({'error': 'Deposit ID is required'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get Transaction from db using deposit_id in approved status
        payment = db.query(Transaction).filter(Transaction.id == req_deposit_id, Transaction.status == 'approved').first()

        if payment is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Complete payment failed. Payment not found or was not approved for user: {user.username}. Payment ID: {req_deposit_id}")
            return JSONResponse({'error': 'Payment not found or already completed'}, status_code=status.HTTP_404_NOT_FOUND)

        # Get transaction Data from db using deposit_id
        data = db.query(TransactionData).filter(TransactionData.transaction_id == req_deposit_id).first()

        if data is None:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Transaction data not found for user: {user.username}. Payment ID: {req_deposit_id}")
            return JSONResponse({'error': 'Invalid payment request. Please try again or contact support'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Check if the payment ID and transaction ID are provided
        if payment_id is None or txid is None:
            return JSONResponse({'error': 'Payment ID and transaction ID are required'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Complete the payment using the Python SDK
        # completeStatus = pi_network.complete_payment(payment_id, txid)
        headers = {
            "Authorization": f"Key {config['api']['server_api_key']}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{config['api']['base_url']}/v2/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

        # Save contents to json file locally using payment_id as filename ({payment_id}_confirmed.json) in path resources/confirmations/
        with open(f"resources/confirmations/{req_deposit_id}_confirmed.json", "w") as f:
            json.dump(response.json(), f)

        if response.status_code != 200:
            return JSONResponse({'error': 'Failed to complete payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Complete the transaction
        if not complete_transaction(payment.id, txid, db):
            return JSONResponse({'error': 'Failed to complete transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        db.commit()

        logging.info(colorama.Fore.GREEN + f"COMPLETE: Payment completed successfully for user: {user.username}. Payment ID: {req_deposit_id}")
        return JSONResponse({'message': 'Payment completed successfully'}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logging.error(colorama.Fore.RED + f"ERROR: Complete payment failed. {str(err)}")
        return JSONResponse({'error': 'Failed to complete payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.post("/incomplete/{payment_id}")
async def handle_incomplete_payment(payment_id: str, request: Request, db: Session = Depends(get_db)):
    # Get post data
    data = await request.json()

    payment_id = data['payment']['identifier'] if 'identifier' in data['payment'] else None
    amount = data['payment']['amount'] if 'amount' in data['payment'] else 0
    user_id = data['payment']['user_uid'] if 'user_uid' in data['payment'] else None
    txid = None

    logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Incomplete payment received for user: {user_id}. Payment ID: {payment_id}. Amount: {amount}")

    try:
        trans_type = data['payment']['metadata']['transType']
    except KeyError:
        trans_type = "deposit"

    try:
        txid = data['payment']['transaction']['txid']
    except KeyError:
        txid = None

    statuses = data['payment']['status'] if 'status' in data['payment'] else None

    deposit_id = data['payment']['metadata']['deposit_id'] if 'deposit_id' in data['payment']['metadata'] else None

    # Check if the payment exists
    payment = db.query(Transaction).filter(Transaction.id == deposit_id).first()

    # if payment is not found, return an error
    if payment is None:
        if config['app']['debug'] == True:
            logging.error(colorama.Fore.RED + f"ERROR: Incomplete payment not found for user: {user_id}. Payment ID: {deposit_id}")
        return JSONResponse({'error': 'Payment not found. Please contact support for assistance. Payment ID: {deposit_id}'}, status_code=status.HTTP_404_NOT_FOUND)

    # Check if payment status is not approved, return an error, else approve the payment
    if payment.status != 'approved':
        if config['app']['debug'] == True:
            logging.error(colorama.Fore.RED + f"ERROR: Incomplete payment not approved for user: {user_id}. Payment ID: {deposit_id}")
        return JSONResponse({'error': 'Payment not approved or already completed. Please contact support for assistance. Payment ID: {deposit_id}'}, status_code=status.HTTP_400_BAD_REQUEST)

    # Update the transaction status to pending
    headers = {
        "Authorization": f"Key {config['api']['server_api_key']}",
        "Content-Type": "application/json"
    }

    logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Payment already approved for user: {user_id} in database. Payment ID: {deposit_id}. Submitting to server")

    response = requests.post(f"{config['api']['base_url']}/v2/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

    # Save contents to json file locally using payment_id as filename
    with open(f"resources/confirmations/{payment_id}_confirmed.json", "w") as f:
        json.dump(response.json(), f)

    if response.status_code != 200:
        if config['app']['debug'] == True:
            logging.error(colorama.Fore.RED + f"ERROR: Failed to complete payment for user: {user_id}. Payment ID: {deposit_id}")
            logging.error(colorama.Fore.RED + f"ERROR: Response: {response.content}")
        # Need to alert admins of manual intervention
        return JSONResponse({'error': 'Failed to complete payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Update status to completed if developer_approved and transaction_verified are true
    if statuses['developer_approved'] and statuses['transaction_verified']:
        headers = {
            "Authorization": f"Key {config['api']['server_api_key']}",
            "Content-Type": "application/json"
        }

        logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Payment approved for user: {user_id}. Payment ID: {deposit_id}. Submitting to server")
        response = requests.post(f"{config['api']['base_url']}/v2/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

        # Save contents to json file locally using payment_id as filename
        with open(f"resources/confirmations/{deposit_id}_confirmed.json", "w") as f:
            json.dump(response.json(), f)

        if response.status_code != 200:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to complete payment for user: {user_id}. Payment ID: {deposit_id}")
                logging.error(colorama.Fore.RED + f"ERROR: Response: {response.content}")
            return JSONResponse({'error': 'Failed to complete payment'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Complete the transaction
        if not complete_transaction(payment.id, txid, db):
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to complete transaction for user: {user_id}. Payment ID: {deposit_id}")
            return JSONResponse({'error': 'Failed to complete transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Incomplete payment completed for user: {user_id}. Payment ID: {deposit_id}. Amount: {amount}")
    # Return success message
    return JSONResponse({'message': 'Payment completed successfully'}, status_code=status.HTTP_200_OK)

@app.get("/loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf/")
async def loaderio_verification():
    return 'loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf'

@app.get("/api/lotto-pool")
async def get_lotto_pool(current_user: User = Depends(get_current_user)):
    try:
        # get the current balance of the app wallet
        balance = pi_network.get_balance()

        # Check if the balance is not None, else return maintenance message
        if balance is None:
            return JSONResponse({'error': 'The system is currently under maintenance. Please try again later'}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

        return JSONResponse({'balance': balance})

    except requests.exceptions.RequestException as err:
        logging.error(err)
        return JSONResponse({'error': 'Failed to fetch lotto pool amount'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/api/user-balance")
async def get_user_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.uid
    user = db.query(User).filter(User.uid == user_id).first()
    if user is None:
        return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

    # if debug mode is enabled, return the balance as 1000
    if config['app']['debug'] == True:
        logging.info(colorama.Fore.YELLOW + f"FETCH: Fetching user balance for user: {user.username} with balance: {user.balance}")

    return JSONResponse({'balance': user.balance}, status_code=status.HTTP_200_OK)

@app.post("/submit-ticket")
async def submit_ticket(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.uid
    user = db.query(User).filter(User.uid == user_id).first()
    if user is None:
        return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

    data = await request.json()
    game_id = data.get('game_id')
    lotto_numbers = data.get('lotto_numbers')
    powerball_number = data.get('powerball_number')
    ticket_number = data.get('ticket_number')
    estimated_fees = data.get('estimated_fees')

    # Validate that all required fields are provided and not empty
    if game_id is None or lotto_numbers is None or powerball_number is None or ticket_number is None or estimated_fees is None:
        return JSONResponse({'error': 'All fields are required'}, status_code=status.HTTP_400_BAD_REQUEST)

    # Validation
    if len(lotto_numbers) != 6:
        return JSONResponse({'error': 'Invalid lotto numbers'}, status_code=status.HTTP_400_BAD_REQUEST)

    if not all(isinstance(number, int) for number in lotto_numbers):
        return JSONResponse({'error': 'Invalid lotto numbers'}, status_code=status.HTTP_400_BAD_REQUEST)

    if not isinstance(powerball_number, int):
        return JSONResponse({'error': 'Invalid powerball number'}, status_code=status.HTTP_400_BAD_REQUEST)

    # Ticket number contains no special characters
    if not ticket_number.isalnum():
        return JSONResponse({'error': 'Invalid ticket number'}, status_code=status.HTTP_400_BAD_REQUEST)

    # Check if game exists
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if game is None:
        return JSONResponse({'error': 'Game not found'}, status_code=status.HTTP_404_NOT_FOUND)

    # Validate the ticket price by checking with the API
    try:
        ticket_details = await get_ticket_details(db, current_user)
        ticket_price = ticket_details['ticketPrice']
        base_fee = ticket_details['baseFee']
        service_fee = ticket_details['serviceFee']
        total_cost = ticket_price + base_fee + service_fee

        if estimated_fees != total_cost:
            return JSONResponse({'error': 'Ticket price mismatch'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Check if the user has enough balance to purchase the ticket
        if user.balance < total_cost:
            return JSONResponse({'error': 'Insufficient balance'}, status_code=status.HTTP_400_BAD_REQUEST)
    except requests.exceptions.RequestException as err:
        logging.error(err)
        return JSONResponse({'error': 'Failed to validate ticket price'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Save the ticket details
    new_lotto_stats = LottoStats(
        user_id=user.id,
        game_id=game_id,
        numbers_played=','.join(map(str, lotto_numbers)),
        win_amount=0
    )
    db.add(new_lotto_stats)
    db.commit()

    # Create account transactions
    transactionCreated = create_account_transaction(user.id, 'lotto_entry', total_cost, reference_id=new_lotto_stats.id, db=db)

    # if transactionCreated = false, undo the transaction
    if not transactionCreated:
        db.refresh(new_lotto_stats)
        db.delete(new_lotto_stats)
        db.commit()
        return JSONResponse({'error': 'Failed to create account transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse({'message': 'Ticket submitted successfully'}, status_code=status.HTTP_200_OK)

@app.post("/create_payment")
async def create_payment(request: Request, current_user: User = Depends(get_current_user)):
    data = await request.json()
    payment_data = {
        "payment": {
            "amount": data["amount"],
            "memo": data["memo"],
            "metadata": data["metadata"],
            "uid": data["uid"]
        }
    }
    headers = {
        "Authorization": f"Key {config['api']['server_api_key']}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{config['api']['base_url']}/v2/payments", json=payment_data, headers=headers)
    return JSONResponse(response.json())

@app.get("/get_payment/{payment_id}")
async def get_payment(payment_id: str):
    headers = {
        "Authorization": f"Key {config['api']['server_api_key']}"
    }
    response = requests.get(f"{config['api']['base_url']}/v2/payments/{payment_id}", headers=headers)
    return JSONResponse(response.json())

@app.post("/cancel_payment/{payment_id}")
async def cancel_payment(payment_id: str, current_user: User = Depends(get_current_user)):
    headers = {
        "Authorization": f"Key {config['api']['server_api_key']}"
    }
    response = requests.post(f"{config['api']['base_url']}/v2/payments/{payment_id}/cancel", headers=headers)
    return JSONResponse(response.json())

@app.get("/api/ticket-details")
async def get_ticket_details(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.uid

        user = db.query(User).filter(User.uid == user_id).first()
        if user is None:
            return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

        try:
            # Divide the base fee by 10000000 to get the actual fee
            baseFee = int(pi_network.fee) / 10000000
        except requests.exceptions.RequestException as err:
            logging.error(colorama.Fore.RED + f"ERROR: Failed to fetch ticket details for user: {user.username}. {str(err)}")
            baseFee = 0.01

        # TicketID randomly generated
        ticketID = str(uuid.uuid4())

        ticket_details = {
            "ticketPrice": float(2.00),
            "baseFee": float(baseFee),
            "serviceFee": float(0.0125),
            "txID": str(ticketID)
        }

        # Get total cost
        total_cost = ticket_details['ticketPrice'] + ticket_details['baseFee'] + ticket_details['serviceFee']

        # Create a transaction record
        transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=total_cost, transaction_type='lotto_entry', memo='Uni-Games Ticket Purchase', status='pending', id=ticketID, db=db)
        if transaction is None:
            return JSONResponse({'error': 'Failed to create transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JSONResponse(ticket_details)
    except requests.exceptions.RequestException as err:
        logging.error(colorama.Fore.RED + f"ERROR: Failed to fetch ticket details for user: {user.username}. {str(err)}")
        return JSONResponse({'error': 'Failed to fetch ticket details'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.post("/admin/create-game-type")
async def create_game_type(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    data = await request.json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return JSONResponse({'error': 'Game type name is required'}, status_code=status.HTTP_400_BAD_REQUEST)

    existing_game_type = db.query(GameType).filter(GameType.name == name).first()
    if existing_game_type:
        return JSONResponse({'error': 'Game type with the same name already exists'}, status_code=status.HTTP_409_CONFLICT)

    game_type = GameType(name=name, description=description)
    db.add(game_type)
    db.commit()

    return JSONResponse({'message': 'Game type created successfully'}, status_code=status.HTTP_201_CREATED)

@app.post("/admin/create-game")
async def create_game(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    data = await request.json()
    game_type_id = data.get('game_type_id')
    name = data.get('name')
    entry_fee = data.get('entry_fee')
    max_players = data.get('max_players')
    end_time = data.get('end_time')

    if not all([game_type_id, name, entry_fee, max_players, end_time]):
        return JSONResponse({'error': 'Missing required fields'}, status_code=status.HTTP_400_BAD_REQUEST)

    game_type = db.query(GameType).get(game_type_id)
    if not game_type:
        return JSONResponse({'error': 'Invalid game type'}, status_code=status.HTTP_400_BAD_REQUEST)

    end_time = datetime.fromisoformat(end_time)

    game = Game(
        game_type_id=game_type_id,
        name=name,
        entry_fee=entry_fee,
        max_players=max_players,
        end_time=end_time
    )
    db.add(game)
    db.commit()

    return JSONResponse({'message': 'Game created successfully'}, status_code=status.HTTP_201_CREATED)

@app.put("/admin/update-game/{game_id}")
async def update_game(game_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    game = db.query(Game).get(game_id)
    if not game:
        return JSONResponse({'error': 'Game not found'}, status_code=status.HTTP_404_NOT_FOUND)

    data = await request.json()
    game.name = data.get('name', game.name)
    game.entry_fee = data.get('entry_fee', game.entry_fee)
    game.max_players = data.get('max_players', game.max_players)
    game.end_time = datetime.fromisoformat(data.get('end_time', game.end_time.isoformat()))
    game.status = data.get('status', game.status)
    db.commit()

    return JSONResponse({'message': 'Game updated successfully'}, status_code=status.HTTP_200_OK)

@app.post("/admin/create-game-config")
async def create_game_config(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    data = await request.json()
    game_type_id = data.get('game_type_id')
    game_id = data.get('game_id')
    configs = data.get('configs')

    if not game_type_id or not configs:
        return JSONResponse({'error': 'Missing required fields'}, status_code=status.HTTP_400_BAD_REQUEST)

    if not game_id and not db.query(Game).get(game_id):
        return JSONResponse({'error': 'Invalid game'}, status_code=status.HTTP_400_BAD_REQUEST)

    game_type = db.query(GameType).get(game_type_id)
    if not game_type:
        return JSONResponse({'error': 'Invalid game type'}, status_code=status.HTTP_400_BAD_REQUEST)

    for config in configs:
        config_key = config.get('config_key')
        config_value = config.get('config_value')

        if not config_key or not config_value:
            return JSONResponse({'error': 'Missing required fields in configuration'}, status_code=status.HTTP_400_BAD_REQUEST)

        game_config = GameConfig(
            game_id=game_id,
            game_type_id=game_type_id,
            config_key=config_key,
            config_value=config_value
        )
        db.add(game_config)

    db.commit()

    return JSONResponse({'message': 'Game configurations created successfully'}, status_code=status.HTTP_201_CREATED)

@app.put("/admin/update-game-config/{config_id}")
async def update_game_config(config_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    game_config = db.query(GameConfig).get(config_id)
    if not game_config:
        return JSONResponse({'error': 'Game configuration not found'}, status_code=status.HTTP_404_NOT_FOUND)

    data = await request.json()
    game_config.config_value = data.get('config_value', game_config.config_value)
    db.commit()

    return JSONResponse({'message': 'Game configuration updated successfully'}, status_code=status.HTTP_200_OK)

@app.get("/game-types")
async def get_game_types(db: Session = Depends(get_db)):
    game_types = db.query(GameType).all()
    result = []
    for game_type in game_types:
        result.append({
            'id': game_type.id,
            'name': game_type.name,
            'description': game_type.description
        })
    return JSONResponse(result, status_code=status.HTTP_200_OK)

@app.get("/api/games")
async def get_games(request: Request, db: Session = Depends(get_db)):
    try:
        game_type_name = request.query_params.get('game_type')

        if game_type_name:
            game_type = db.query(GameType).filter(GameType.name == game_type_name).first()
            if game_type:
                games = db.query(Game).filter(Game.game_type_id == game_type.id).all()
            else:
                games = []
        else:
            games = db.query(Game).all()

        game_data = []
        for game in games:
            game_type = db.query(GameType).get(game.game_type_id)

            # Fetch game configurations
            game_configs = db.query(GameConfig).filter(GameConfig.game_id == game.id).all()
            config_data = {}
            for config in game_configs:
                config_data[config.config_key] = config.config_value

            game_info = {
                "id": game.id,
                "name": game.name,
                "game_type": game_type.name if game_type else None,
                "pool_amount": game.pool_amount,
                "entry_fee": game.entry_fee,
                "end_time": game.end_time.isoformat() if game.end_time else None,
                "status": game.status,
                "winner_id": game.winner_id,
                "dateCreated": game.dateCreated.isoformat() if game.dateCreated else None,
                "dateModified": game.dateModified.isoformat() if game.dateModified else None,
                "max_players": game.max_players,
                "game_config": config_data
            }
            game_data.append(game_info)

        return JSONResponse({"games": game_data}, status_code=status.HTTP_200_OK)

    except Exception as err:
        logging.error(err)
        return JSONResponse({'error': 'Failed to fetch games'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/games/{game_id}")
async def get_game_details(game_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).get(game_id)
    if not game:
        return JSONResponse({'error': 'Game not found'}, status_code=status.HTTP_404_NOT_FOUND)

    result = {
        'id': game.id,
        'game_type_id': game.game_type_id,
        'name': game.name,
        'entry_fee': game.entry_fee,
        'max_players': game.max_players,
        'end_time': game.end_time.isoformat(),
        'status': game.status
    }
    return JSONResponse(result, status_code=status.HTTP_200_OK)

@app.get("/game-configs")
async def get_game_configs(request: Request, db: Session = Depends(get_db)):
    game_type_id = request.query_params.get('game_type_id')
    if not game_type_id:
        return JSONResponse({'error': 'game_type_id is required'}, status_code=status.HTTP_400_BAD_REQUEST)

    game_configs = db.query(GameConfig).filter(GameConfig.game_type_id == game_type_id).all()
    result = []
    for game_config in game_configs:
        result.append({
            'id': game_config.id,
            'game_id': game_config.game_id,
            'game_type_id': game_config.game_type_id,
            'config_key': game_config.config_key,
            'config_value': game_config.config_value
        })
    return JSONResponse(result, status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config['app']['host'], port=config['app']['port'])

