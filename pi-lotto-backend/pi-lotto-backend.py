# pi-lotto-backend.py
import sys
import yaml
import logging
import requests
import uuid
import json
import colorama
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from src.pi_python import PiNetwork
from src.db.models import db, Game, UserGame, User, Wallet, Transaction, TransactionLog, AccountTransaction, Payment, LottoStats, UserScopes, TransactionData


def create_app(config_path):
    app = Flask(__name__)
    jwt = JWTManager(app)
    CORS(app, resources={r"/*": {"origins": "*"}}, origins="*")

    # Load configuration from config.yml
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)

    # Configure logging
    logging.basicConfig(level=config['logging']['level'],
                        format=config['logging']['format'],
                        handlers=[logging.StreamHandler()])

    # Add file handler if log file path is provided
    file_handler = logging.FileHandler(config['logging']['filePath'], mode='a', encoding=None, delay=False)
    logging.getLogger().addHandler(file_handler)


    # Set colorama to autoreset
    colorama.init(autoreset=True)

    # Debug mode
    app.config["DEBUG"] = config['app']['debug']
    app.config["app_version"] = config['app']['version']

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database']['uri']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config['database']['track_modifications']
    db.init_app(app)

    # Server API Key and Base URL
    app.config["SERVER_API_KEY"] = config['api']['server_api_key']
    app.config["BASE_URL"] = config['api']['base_url']

    app.config["APP_WALLET_SEED"] = config['api']['app_wallet_seed']
    app.config["APP_WALLET_ADDRESS"] = config['api']['app_wallet_address']

    # JWT Configuration
    app.config["JWT_SECRET_KEY"] = config['jwt']['secret_key']

    # Stellar Network Configuration
    pi_network = PiNetwork()
    pi_network.initialize(config['api']['base_url'], config['api']['server_api_key'], config['api']['app_wallet_seed'], config['api']['network'])


    # Function to store user data in the database
    def update_user_data(user_data):
        user = User.query.filter_by(username=user_data['username']).first()
        if user is None:
            new_user = User(username=user_data['username'], uid=user_data['uid'])
            db.session.add(new_user)
            db.session.commit()
        else:
            new_user = user

        # Add the user's scopes to the database. Deactivate any scopes that are not in the user's credentials
        for scope in user_data['credentials']['scopes']:
            user_scope = UserScopes.query.filter_by(user_id=new_user.id, scope=scope).first()
            if user_scope is None:
                new_user_scope = UserScopes(user_id=new_user.id, scope=scope)
                db.session.add(new_user_scope)
                db.session.commit()
            else:
                user_scope.active = True
                db.session.commit()

        # Deactivate any scopes that are not in the user's credentials
        user_scopes = UserScopes.query.filter_by(user_id=new_user.id).all()
        for user_scope in user_scopes:
            if user_scope.scope not in user_data['credentials']['scopes']:
                user_scope.active = False
                db.session.commit()

        return new_user

    # Function to generate a unique game_id. It verifies that the game_id is unique in the database
    def generate_game_id():
        game_id = str(uuid.uuid4())
        game = Game.query.filter_by(game_id=game_id).first()
        if game is not None:
            return generate_game_id()
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

    def update_user_balance(user_id, transaction_amount, transaction_type):
        try:
            user = User.query.get(user_id)
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

                db.session.commit()

                return True
            else:
                raise ValueError('User not found')
        except Exception as e:
            db.session.rollback()
            logging.error(colorama.Fore.RED + f"ERROR: Failed to update users balance. User ID: {user_id}. {str(e)}")
            return False

    def create_transaction_log(transaction_id, log_message):
        try:
            log_entry = TransactionLog(transaction_id=transaction_id, log_message=log_message)
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating transaction log: {str(e)}")

    def create_transaction(user_id, ref_id, wallet_id, amount, transaction_type, memo, status, id=None, transactionData=None):
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
            db.session.add(transaction)

            # Add transaction data if provided and is json. If already exists in db, log the occurrence
            if transactionData is not None and isinstance(transactionData , dict):
                existing_transaction_data = TransactionData.query.filter_by(transaction_id=transaction_id).first()
                if existing_transaction_data is not None:
                    logging.warning(f"Transaction data already exists for transaction: {transaction_id}. Ignoring new data.")
                else:
                    transaction_data = TransactionData(transaction_id=transaction_id, data=transactionData)
                    db.session.add(transaction_data)
            else:
                logging.warning(f"Transaction data is not provided or is not a dictionary. Ignoring data. Transaction ID: {transaction_id}. User ID: {user_id}")

            db.session.commit()
            create_transaction_log(transaction_id, f"Transaction created: {transaction_id}")
            return transaction
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating transaction: {str(e)}")
            return None

    def complete_transaction(transaction_id, txid):
        try:
            transaction = Transaction.query.get(transaction_id)
            if transaction:
                transaction.transaction_id = txid
                transaction.status = 'completed'

                # Create payment record
                payment = Payment(id=transaction_id, user_id=transaction.user_id, amount=transaction.amount, memo=transaction.memo, transaction_id=txid, status='completed')
                db.session.add(payment)

                db.session.commit()
                create_transaction_log(transaction_id, f"Transaction completed: {transaction_id}")


                if update_user_balance(transaction.user_id, transaction.amount, transaction.transaction_type):
                    return True
                else:
                    raise ValueError('Failed to update user balance')
            else:
                raise ValueError('Transaction not found')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error completing transaction: {str(e)}")
            return False


    @app.route("/create_deposit", methods=["POST"], endpoint="create_deposit")
    @jwt_required()
    def create_deposit():
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            amount = data["amount"]

            # Check if the user exists
            user = User.query.filter_by(uid=user_id).first()
            if user is None:
                return jsonify({'error': 'User not found. Unable to create deposit'}), 404

            # Check if the amount is a positive number
            if amount <= 0:
                return jsonify({'error': 'Invalid amount. Amount must be a positive number'}), 400

            deposit_id = str(uuid.uuid4())

            # get last 6 digits of user id
            last6uid = user_id[-6:]

            # Generate memo and metadata
            memo = f"Deposit to Uni Pi Games account# {last6uid}"
            metadata = {
                "app_version": f"{app.config['app_version']}",
                "deposit_id": deposit_id
            }

            # if debug mode is enabled, append "test: true" to the metadata
            if app.config['DEBUG'] == True:
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
            transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=float(amount), transaction_type='deposit', memo=str(memo), status='pending', id=deposit_id, transactionData=payment_data)

            if transaction is None:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to create transaction for user: {user.username} in the amount of {amount}. Deposit ID: {deposit_id}")
                return jsonify({'error': 'Failed to create transaction'}), 500

            logging.info(colorama.Fore.GREEN + f"DEPOSIT: Deposit started for user : {user.username} in the amount of {amount}. Deposit ID: {deposit_id}")
            return jsonify(payment_data)

        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to create deposit'}), 500


    @app.route("/create_withdrawal", methods=["POST"], endpoint="create_withdrawal")
    @jwt_required()
    def create_withdrawal():
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            trans_fee = 0.01 # Fetch from db or api
            amount = float(data["amount"]) + trans_fee

            # Check if the user exists
            user = User.query.filter_by(uid=user_id).first()
            if user is None:
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: User not found. Unable to create withdrawal for user: {user_id}")
                return jsonify({'error': 'User not found. Unable to create withdrawal'}), 404

            # Check if the amount is a positive number
            if amount <= 0:
                return jsonify({'error': 'Invalid amount. Amount must be a positive number'}), 400

            # Check if minimum withdrawal amount is met (0.019)
            if amount < 0.019:
                return jsonify({'error': 'Invalid amount. Minimum withdrawal amount is 0.019'}), 400

            # Get user's balance
            if user.balance < amount:
                return jsonify({'error': 'Insufficient balance'}), 400

            # Get app wallet balance, if none, set to 0
            app_wallet_balance = pi_network.get_balance()

            if app_wallet_balance is None:
                logging.error(colorama.Fore.RED + f"PAYMENT ERROR: Failed to get app wallet balance. Unable to create withdrawal for user: {user.username}")
                app_wallet_balance = 0

            # Check if the app wallet has enough balance to process the withdrawal
            if app_wallet_balance < amount:
                logging.error(colorama.Fore.RED + f"PAYMENT ERROR: **Insufficient balance in app wallet. Unable to create withdrawal for user: {user.username} in the amount of {amount}**")
                return jsonify({'error': 'Server is currently under maintenance. Please try again later'}), 503

            withdrawal_id = str(uuid.uuid4())

            # get last 6 digits of user id
            last6uid = user_id[-6:]

            # Generate memo and metadata
            memo = f"Withdrawal from Uni Pi Games account# {last6uid}"
            metadata = {
                "app_version": f"{app.config['app_version']}",
                "withdrawal_id": withdrawal_id
            }

            # if debug mode is enabled, append "test: true" to the metadata
            if app.config['DEBUG'] == True:
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
            transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=float(amount), transaction_type='withdrawal', memo=str(memo), status='pending', id=withdrawal_id, transactionData=payment_data)

            if transaction is None:
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Failed to create transaction for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
                return jsonify({'error': 'Failed to create transaction'}), 500

            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }

            # Get transaction from db using withdrawal_id in pending status to not overpay
            payment = Transaction.query.filter_by(id=withdrawal_id, status='pending').first()

            if payment is None:
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Failed to create withdrawal for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}. Payment not found or already completed")
                return jsonify({'error': 'Failed to create withdrawal. Server error. Please try again later or contact support for assistance'}), 500

            payment_id = pi_network.create_payment(payment_data['payment'])

            if payment_id is None:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to create withdrawal for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}.")
                return jsonify({'error': 'Failed to create withdrawal. Server error. Please try again later or contact support for assistance'}), 500


            logging.info(colorama.Fore.GREEN + f"WITHDRAWAL: Withdrawal started for user : {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
            print(payment_id)

            #Update the transaction status to pending
            payment.status = 'approved'
            payment.ref_id = payment_id
            db.session.commit()

            # Approve the transaction
            txid = pi_network.submit_payment(payment_id, False)

            print(txid)  # Debugging
            # if response status is not 200, return an error
            if txid is None:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Failed to approve payment. Payment ID: {withdrawal_id}.")
                return jsonify({'error': 'Failed to approve payment'}), 500

            #Complete the transaction
            paymentData = pi_network.complete_payment(payment_id, txid)

            print(paymentData)  # Debugging

            # if paymentData is None:
            #     logging.error(colorama.Fore.RED + f"ERROR: Failed to complete transaction for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
            #     return jsonify({'error': 'Failed to complete transaction'}), 500

            if not complete_transaction(payment.id, txid):
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Failed to complete transaction for user: {user.username} in the amount of {amount}. Payment ID: {withdrawal_id}")
                return jsonify({'error': 'Failed to complete transaction'}), 500

            logging.info(colorama.Fore.GREEN + f"APPROVE: Withdrawl approved successfully for user: {user.username} with amount: {amount}. Payment ID: {withdrawal_id}")

            # Get new user balance
            user = User.query.filter_by(uid=user_id).first()
            user_balance = user.balance

            return jsonify({'message': 'Withdrawal Completed Successfully', 'balance': user_balance}), 200

        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to create withdrawal'}), 500

    @app.route("/approve_payment/<payment_id>", methods=["POST"], endpoint="approve_payment")
    def approve_payment(payment_id):
        # Validate userID and check if the user has the required scope
        verify_jwt_in_request()
        try:
            user_id = get_jwt_identity()
            user = User.query.filter_by(uid=user_id).first()

            if user is None:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. User not found")
                return jsonify({'error': 'User not found'}), 404

            user_scope = UserScopes.query.filter_by(user_id=user.id, scope='payments').first()
            if user_scope is None or not user_scope.active:
                return jsonify({'error': 'Unauthorized'}), 401

            # Get deposit_id from metadata
            try:
                print(request.get_json())
                req_depost_id = request.get_json()['paymentData']['payment']['metadata']['deposit_id']
            except KeyError:
                req_depost_id = None

            # if deposit_id is not provided, return an error
            if req_depost_id is None:

                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Deposit ID not provided")

                return jsonify({'error': 'Deposit ID is required'}), 400

            # Get Transction from db using deposit_id
            payment = Transaction.query.filter_by(id=req_depost_id).first()

            # If payment is not found, return an error
            if payment is None:

                # if debug mode is enabled, log the error
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Payment not found for user: {user.username}. Payment ID: {req_depost_id}")

                return jsonify({'error': 'Invalid payment request. Please try again or contact support'}), 400

            # Get transaction Data from db using deposit_id
            db_data = TransactionData.query.filter_by(transaction_id=req_depost_id).first()

            if db_data is None:

                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Transaction data not found for user: {user.username}. Payment ID: {req_depost_id}")

                return jsonify({'error': 'Invalid payment request. Please try again or contact support'}), 400

            data = db_data.data

            if data is None:
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Transaction data not found for user: {user.username}. Payment ID: {req_depost_id}")
                return jsonify({'error': 'Invalid payment request. Please try again or contact support'}), 400

            pl_cost = data['payment']['amount']

            # If amount is not provided or is less than 0, return an error
            if pl_cost is None or pl_cost <= 0:
                return jsonify({'error': 'Invalid amount'}), 400

            logging.info(colorama.Fore.GREEN + f"APPROVE: Creating a new payment for user: {user.username} in the amount of {pl_cost}. Payment ID: {req_depost_id}")

            # approveStatus = pi_network.get_payment(payment_id)
            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }
            response = requests.post(f"{app.config['BASE_URL']}/v2/payments/" + payment_id + "/approve/", headers=headers)

            # Save contents to json file localy using payment_id as filename
            with open(f"resources/approvals/{payment_id}_approval.json", "w") as f:
                json.dump(response.json(), f)

            # if response status is not 200, return an error
            if response.status_code != 200:
                logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Failed to approve payment. Payment ID: {payment_id}. Response: {response.content}")
                return jsonify({'error': 'Failed to approve payment'}), 500

            # Update the transaction status to Approved
            payment.status = 'approved'
            payment.ref_id = payment_id
            db.session.commit()

            logging.info(colorama.Fore.GREEN + f"APPROVE: Payment approved successfully for user: {user.username}. Payment ID: {payment_id}")
            return jsonify(response.json())
        except Exception as err:
            logging.error(err)
            return jsonify({'error': 'Failed to approve payment'}), 500


    @app.route("/complete_payment/<payment_id>", methods=["POST"], endpoint="complete_payment")
    def complete_payment(payment_id):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            # Check if user exists
            user = User.query.filter_by(uid=user_id).first()
            if user is None:
                return jsonify({'error': 'User not found'}), 404

            try:
                req_depost_id = request.get_json()['paymentData']['payment']['metadata']['deposit_id']
            except KeyError:
                req_depost_id = None

            txid = request.get_json()['txid']


            # if deposit_id is not provided, return an error
            if req_depost_id is None:
                return jsonify({'error': 'Deposit ID is required'}), 400

            # Get Transction from db using deposit_id in approved status
            payment = Transaction.query.filter_by(id=req_depost_id, status='approved').first()

            if payment is None:

                # if debug mode is enabled, log the error
                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Complete payment failed. Payment not found or was not approved for user: {user.username}. Payment ID: {req_depost_id}")

                return jsonify({'error': 'Payment not found or already completed'}), 404

            # Get transaction Data from db using deposit_id
            data = TransactionData.query.filter_by(transaction_id=req_depost_id).first()

            if data is None:

                if app.config['DEBUG'] == True:
                    logging.error(colorama.Fore.RED + f"ERROR: Approve payment failed. Transaction data not found for user: {user.username}. Payment ID: {req_depost_id}")

                return jsonify({'error': 'Invalid payment request. Please try again or contact support'}), 400


            # Check if the payment ID and transaction ID are provided
            if payment_id is None or txid is None:
                return jsonify({'error': 'Payment ID and transaction ID are required'}), 400

            # Complete the payment using the Python SDK
            # completeStatus = pi_network.complete_payment(payment_id, txid)
            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }
            response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

            # Save contents to json file localy using payment_id as filename ({payment_id}_confirmed.json) in path resources/confirmations/
            with open(f"resources/confirmations/{req_depost_id}_confirmed.json", "w") as f:
                json.dump(response.json(), f)

            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete payment'}), 500

            # Complete the transaction
            if not complete_transaction(payment.id, txid):
                return jsonify({'error': 'Failed to complete transaction'}), 500

            db.session.commit()

            logging.info(colorama.Fore.GREEN + f"COMPLETE: Payment completed successfully for user: {user.username}. Payment ID: {req_depost_id}")
            return jsonify({'message': 'Payment completed successfully'}), 200
        except Exception as err:
            logging.error(colorama.Fore.RED + f"ERROR: Complete payment failed. {str(err)}")
            return jsonify({'error': 'Failed to complete payment'}), 500

    @app.route('/signin', methods=['POST'])
    def signin():
        auth_result = request.json['authResult']
        access_token = auth_result['accessToken']

        try:
            # Verify with the user's access token
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f"{app.config['BASE_URL']}/v2/me", headers=headers)
            response.raise_for_status()
            user_data = response.json()

            # if status is not 200, return an error message
            if response.status_code != 200:
                return jsonify({'error': 'Invalid authorization'}), 401

            # Check if response user data is not empty
            if user_data is None:
                return jsonify({'error': 'User not found'}), 404

            # Store user data in the database
            user = update_user_data(user_data)

            # Generate JWT token for the user
            jwt_token = create_access_token(identity=user.uid)

            logging.info(colorama.Fore.GREEN + f"SIGNIN: User {user.username} signed in successfully")
            return jsonify({'access_token': jwt_token}), 200
        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'User not authorized'}), 401



    @app.route('/incomplete/<payment_id>', methods=['POST'])
    @jwt_required()
    def handle_incomplete_payment(payment_id):
        # Get post data
        data = request.get_json()

        payment_id = data['payment']['identifier'] if 'identifier' in data['payment'] else None
        amount = data['payment']['amount'] if 'amount' in data['payment'] else 0
        user_id = data['payment']['user_uid'] if 'user_uid' in data['payment'] else None
        txid=None

        logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Incomplete payment received for user: {user_id}. Payment ID: {payment_id}. Amount: {amount}")

        try:
            trans_type = data['payment']['metadata']['transType']
        except KeyError:
            trans_type="deposit"

        try:
            txid = data['payment']['transaction']['txid']
        except KeyError:
            txid=None

        statuses = data['payment']['status'] if 'status' in data['payment'] else None

        deposit_id = data['payment']['metadata']['deposit_id'] if 'deposit_id' in data['payment']['metadata'] else None

        # Check if the payment exists
        payment = Transaction.query.filter_by(id=deposit_id).first()

        # if payment is not found, return an error
        if payment is None:
            if app.config['DEBUG'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Incomplete payment not found for user: {user_id}. Payment ID: {deposit_id}")

            return jsonify({'error': 'Payment not found. Please contact support for assistance. Payment ID: {deposit_id}'}), 404

        # Check if payment status is not approved, return an error, else approve the payment
        if payment.status != 'approved':
            if app.config['DEBUG'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Incomplete payment not approved for user: {user_id}. Payment ID: {deposit_id}")

            return jsonify({'error': 'Payment not approved or already completed. Please contact support for assistance. Payment ID: {deposit_id}'}), 400

        # Update the transaction status to pending
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}",
            "Content-Type": "application/json"
        }

        logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Payment already approved for user: {user_id} in database. Payment ID: {deposit_id}. Submitting to server")

        response = requests.post(f"{app.config['BASE_URL']}/v2/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

        # Save contents to json file localy using payment_id as filename
        with open(f"resources/confirmations/{payment_id}_confirmed.json", "w") as f:
            json.dump(response.json(), f)

        if response.status_code != 200:
            if app.config['DEBUG'] == True:
                logging.error(colorama.Fore.RED + f"ERROR: Failed to complete payment for user: {user_id}. Payment ID: {deposit_id}")
                logging.error(colorama.Fore.RED + f"ERROR: Response: {response.content}")
            # Need to alert admins of manual intervention
            return jsonify({'error': 'Failed to complete payment'}), 500


        # Update status to completed if developer_approved and transaction_verified are true
        if statuses['developer_approved'] and statuses['transaction_verified']:

            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }

            logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Payment approved for user: {user_id}. Payment ID: {deposit_id}. Submitting to server")
            response = requests.post(f"{app.config['BASE_URL']}/v2/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

            # Save contents to json file localy using payment_id as filename
            with open(f"resources/confirmations/{deposit_id}_confirmed.json", "w") as f:
                json.dump(response.json(), f)

            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete payment'}), 500

            # Complete the transaction
            if not complete_transaction(payment.id, txid):
                return jsonify({'error': 'Failed to complete transaction'}), 500

        logging.info(colorama.Fore.LIGHTRED_EX + f"INCOMPLETE: Incomplete payment completed for user: {user_id}. Payment ID: {deposit_id}. Amount: {amount}")
        # Return success message
        return jsonify({'message': 'Payment completed successfully'}), 200

    @app.route('/loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf/')
    def loaderio_verification():
        return 'loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf'


    @app.route("/api/lotto-pool", methods=["GET"])
    @jwt_required()
    def get_lotto_pool():
        try:
            # get the current balance of the app wallet
            balance = pi_network.get_balance()

            # Check if the balance is not None, else return maintenance message
            if balance is None:
                return jsonify({'error': 'The system is currently under maintenance. Please try again later'}), 503

            return jsonify({'balance': balance})

        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to fetch lotto pool amount'}), 500

    @app.route('/api/user-balance', methods=['GET'])
    @jwt_required()
    def get_user_balance():
        user_id = get_jwt_identity()
        user = User.query.filter_by(uid=user_id).first()
        if user is None:
            return jsonify({'error': 'User not found'}), 404

        # if debug mode is enabled, return the balance as 1000
        if app.config['DEBUG'] == True:
            logging.info(colorama.Fore.YELLOW + f"FETCH: Fetching user balance for user: {user.username} with balance: {user.balance}")

        return jsonify({'balance': user.balance}), 200

    @app.route('/submit-ticket', methods=['POST'])
    @jwt_required()
    def submit_ticket():
        user_id = get_jwt_identity()
        user = User.query.filter_by(uid=user_id).first()
        if user is None:
            return jsonify({'error': 'User not found'}), 404

        data = request.json
        game_id = data.get('game_id')
        lotto_numbers = data.get('lotto_numbers')
        powerball_number = data.get('powerball_number')
        ticket_number = data.get('ticket_number')
        estimated_fees = data.get('estimated_fees')

        # Validate that all required fields are provided and not empty
        if game_id is None or lotto_numbers is None or powerball_number is None or ticket_number is None or estimated_fees is None:
            return jsonify({'error': 'All fields are required'}), 400

        # Validation
        if len(lotto_numbers) != 6:
            return jsonify({'error': 'Invalid lotto numbers'}), 400

        if not all(isinstance(number, int) for number in lotto_numbers):
            return jsonify({'error': 'Invalid lotto numbers'}), 400

        if not isinstance(powerball_number, int):
            return jsonify({'error': 'Invalid powerball number'}), 400

        # Ticket number contains no special characters
        if not ticket_number.isalnum():
            return jsonify({'error': 'Invalid ticket number'}), 400

        # Check if game exists
        game = Game.query.filter_by(game_id=game_id).first()
        if game is None:
            return jsonify({'error': 'Game not found'}), 404

        # Validate the ticket price by checking with the API
        try:
            ticket_details = get_ticket_details()
            ticket_price = ticket_details['ticketPrice']
            base_fee = ticket_details['baseFee']
            service_fee = ticket_details['serviceFee']
            total_cost = ticket_price + base_fee + service_fee

            if estimated_fees != total_cost:
                return jsonify({'error': 'Ticket price mismatch'}), 400

            # Check if the user has enough balance to purchase the ticket
            if user.balance < total_cost:
                return jsonify({'error': 'Insufficient balance'}), 400
        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to validate ticket price'}), 500

        # Save the ticket details
        new_lotto_stats = LottoStats(
            user_id=user.id,
            game_id=game_id,
            numbers_played=','.join(map(str, lotto_numbers)),
            win_amount=0
        )
        db.session.add(new_lotto_stats)
        db.session.commit()

        # Create account transactions
        transactionCreated = create_account_transaction(user.id, 'lotto_entry', total_cost, reference_id=new_lotto_stats.id)

        # if transactionCreated = false, undo the transaction
        if not transactionCreated:
            db.session.refresh(new_lotto_stats)
            db.session.delete(new_lotto_stats)
            db.session.commit()
            return jsonify({'error': 'Failed to create account transaction'}), 500

        return jsonify({'message': 'Ticket submitted successfully'}), 200

    @app.route("/create_payment", methods=["POST"], endpoint="create_payment")
    @jwt_required()
    def create_payment():
        data = request.get_json()
        payment_data = {
            "payment": {
                "amount": data["amount"],
                "memo": data["memo"],
                "metadata": data["metadata"],
                "uid": data["uid"]
            }
        }
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{app.config['BASE_URL']}/v2/payments", json=payment_data, headers=headers)
        return jsonify(response.json())

    @app.route("/get_payment/<payment_id>", methods=["GET"], endpoint="get_payment")
    def get_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.get(f"{app.config['BASE_URL']}/v2/payments/{payment_id}", headers=headers)
        return jsonify(response.json())



    @app.route("/cancel_payment/<payment_id>", methods=["POST"], endpoint="cancel_payment")
    @jwt_required()
    def cancel_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.post(f"{app.config['BASE_URL']}/v2/payments/{payment_id}/cancel", headers=headers)
        return jsonify(response.json())

    @app.route("/api/ticket-details", methods=["GET"])
    @jwt_required()
    def get_ticket_details():
        try:
            user_id = get_jwt_identity()

            user = User.query.filter_by(uid=user_id).first()
            if user is None:
                return jsonify({'error': 'User not found'}), 404

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
            transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=total_cost, transaction_type='lotto_entry', memo='Uni-Games Ticket Purchase', status='pending', id=ticketID)
            if transaction is None:
                return jsonify({'error': 'Failed to create transaction'}), 500

            return jsonify(ticket_details)
        except requests.exceptions.RequestException as err:
            logging.error(colorama.Fore.RED + f"ERROR: Failed to fetch ticket details for user: {user.username}. {str(err)}")
            return jsonify({'error': 'Failed to fetch ticket details'}), 500

    @app.route('/admin/create-game', methods=['POST'])
    @jwt_required()
    def create_game():
        uid = get_jwt_identity()
        if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json
        # if end_time is not provided, return an error in json format
        end_time, status_code = validate_end_time(data)

        if status_code != 200:
            return jsonify(end_time), status_code

        # Convert the end_time string to a datetime object
        end_time = datetime.fromisoformat(end_time)

        # Generate a unique game_id
        game_id = generate_game_id()
        # Get current wallet balance
        balance = pi_network.get_balance()
        # Set pool amount to 2% of the wallet balance
        pool_amount = balance * 0.02
        # set the number of players to 1
        num_players = 1

        try:
            new_game = Game(game_id=game_id, pool_amount=pool_amount, num_players=num_players, end_time=end_time)
            db.session.add(new_game)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create game'}), 500

        isTest = ''

        # if env is development, , set the pool amount to 2π
        if app.config['DEBUG'] != True:
            isTest = " Test"

        return jsonify({'message': 'Game created successfully with ' + str(pool_amount) + isTest + 'π'}), 201

    @app.route('/admin/update-game/<game_id>', methods=['PUT'])
    @jwt_required()
    def update_game(game_id):
        username = get_jwt_identity()
        if username != 'pboachie':
            return jsonify({'error': 'Unauthorized'}), 401

        game = Game.query.filter_by(game_id=game_id).first()
        if game is None:
            return jsonify({'error': 'Game not found'}), 404

        data = request.json
        game.pool_amount = data.get('pool_amount', game.pool_amount)
        game.num_players = data.get('num_players', game.num_players)
        game.end_time = datetime.fromisoformat(data.get('end_time', game.end_time.isoformat()))
        game.status = data.get('status', game.status)
        db.session.commit()

        return jsonify({'message': 'Game updated successfully'}), 200

    @app.route('/join-game/<game_id>', methods=['POST'])
    @jwt_required()
    def join_game(game_id):
        user_id = get_jwt_identity()
        game = Game.query.filter_by(game_id=game_id).first()
        if game is None:
            return jsonify({'error': 'Game not found'}), 404

        user_game = UserGame.query.filter_by(user_id=user_id, game_id=game.id).first()
        if user_game is not None:
            return jsonify({'error': 'User has already joined this game'}), 400

        new_user_game = UserGame(user_id=user_id, game_id=game.id)
        db.session.add(new_user_game)

        game.num_players += 1
        db.session.commit()

        return jsonify({'message': 'User joined game successfully'}), 200

    @app.route('/game-details/<game_id>', methods=['GET'])
    @jwt_required()
    def get_game_details(game_id):
        game = Game.query.filter_by(game_id=game_id).first()
        if game is None:
            return jsonify({'error': 'Game not found'}), 404

        game_details = {
            'game_id': game.game_id,
            'pool_amount': game.pool_amount,
            'num_players': game.num_players,
            'end_time': game.end_time.isoformat(),
            'status': game.status
        }
        return jsonify(game_details), 200

    @app.route('/user-games', methods=['GET'])
    @jwt_required()
    def get_user_games():
        user_id = get_jwt_identity()
        user_games = UserGame.query.filter_by(user_id=user_id).all()

        game_ids = [user_game.game_id for user_game in user_games]
        games = Game.query.filter(Game.id.in_(game_ids)).all()

        game_details = []
        for game in games:
            game_detail = {
                'game_id': game.game_id,
                'pool_amount': game.pool_amount,
                'num_players': game.num_players,
                'end_time': game.end_time.isoformat(),
                'status': game.status
            }
            game_details.append(game_detail)

        return jsonify(game_details), 200

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    return app

def validate_config(config):
    required_keys = ['app', 'database', 'api', 'jwt', 'logging']
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required configuration key: {key}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python pi-lotto-backend.py <config_path>")
        sys.exit(1)

    config_path = sys.argv[1]
    app = create_app(config_path)

    with app.app_context():
        # Validate configuration
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        validate_config(config)

        # Create the database tables
        db.create_all()

    app.run(host=config['app']['host'], port=config['app']['port'])

