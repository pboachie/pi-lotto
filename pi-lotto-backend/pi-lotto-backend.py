# pi-lotto-backend.py
import sys
import yaml
import logging
import requests
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from src.pi_python import PiNetwork


def create_app(config_path):
    app = Flask(__name__)
    jwt = JWTManager(app)
    CORS(app)

    # Load configuration from config.yml
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)

    # Configure logging
    logging.basicConfig(level=config['logging']['level'],
                        format=config['logging']['format'],
                        handlers=[logging.StreamHandler()])

    # Debug mode
    app.config["DEBUG"] = config['app']['debug']

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database']['uri']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config['database']['track_modifications']
    db = SQLAlchemy(app)

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

    # Game model
    class Game(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        game_id = db.Column(db.String(100), unique=True, nullable=False)
        pool_amount = db.Column(db.Float, nullable=False, default=0)
        num_players = db.Column(db.Integer, nullable=False, default=0)
        end_time = db.Column(db.DateTime, nullable=False)
        status = db.Column(db.String(20), nullable=False, default='active')
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
        dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # User Game model
    class UserGame(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
        dateJoined = db.Column(db.DateTime, default=db.func.current_timestamp())

    # User model
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(100), unique=True, nullable=False)
        uid = db.Column(db.String(36), unique=True, nullable=False)
        balance = db.Column(db.Float, default=0)
        active = db.Column(db.Boolean, default=True)
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
        dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Wallet model
    class Wallet(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        address = db.Column(db.String(100), unique=True, nullable=False)
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Transaction model
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

    # Transaction Log model
    class TransactionLog(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        transaction_id = db.Column(db.String(100), db.ForeignKey('transaction.id'), nullable=False)
        log_message = db.Column(db.String(255), nullable=False)
        log_timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Account Transaction model
    class AccountTransaction(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit', 'withdrawal', 'game_entry', etc.
        amount = db.Column(db.Float, nullable=False)
        reference_id = db.Column(db.String(100), nullable=True)  # Reference to the associated transaction or game entry
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Payment model
    class Payment(db.Model):
        id = db.Column(db.String(100), primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        amount = db.Column(db.Float, nullable=False)
        memo = db.Column(db.String(100), nullable=False)
        transaction_id = db.Column(db.String(100), nullable=True)
        status = db.Column(db.String(20), nullable=False)

    # Lotto stats model
    class LottoStats(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        game_id = db.Column(db.String(100), nullable=False)
        numbers_played = db.Column(db.String(100), nullable=False)
        win_amount = db.Column(db.Float, nullable=False)

    # Class to track user scopes
    class UserScopes(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        scope = db.Column(db.String(20), nullable=False)
        active = db.Column(db.Boolean, default=True)
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())

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
            print(data['end_time'])
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

                print("Transaction type: ", transaction_type)

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
            logging.error(f"Error updating user balance: {str(e)}")
            return False

    def create_transaction_log(transaction_id, log_message):
        try:
            log_entry = TransactionLog(transaction_id=transaction_id, log_message=log_message)
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating transaction log: {str(e)}")

    def create_transaction(user_id, ref_id, wallet_id, amount, transaction_type, memo, status, id=None):
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

    @app.route("/api/create_deposit", methods=["POST"], endpoint="create_deposit")
    @jwt_required()
    def create_deposit():
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            amount = data["amount"]

            uid = user_id["uid"]

            # Check if the user exists
            user = User.query.filter_by(uid=uid).first()
            if user is None:
                return jsonify({'error': 'User not found. Unable to create deposit'}), 404

            # Check if the amount is a positive number
            if amount <= 0:
                return jsonify({'error': 'Invalid amount. Amount must be a positive number'}), 400

            deposit_id = str(uuid.uuid4())

            # Generate memo and metadata
            memo = f"Deposit to Pi-Games account"
            metadata = {
                "app_version": "1.0",
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
                    "uid": uid
                }
            }

            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }

            response = requests.post(f"{app.config['BASE_URL']}/payments", json=payment_data, headers=headers)

            # get txid from the response
            txid = response.json().get('transaction', {}).get('txid')

            # Approve the payment using internal API
            response = approve_payment(deposit_id)
            return jsonify(response.json())

        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to create deposit'}), 500

    @app.route('/signin', methods=['POST'])
    def signin():
        auth_result = request.json['authResult']
        access_token = auth_result['accessToken']

        try:
            # Verify with the user's access token
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f"{app.config['BASE_URL']}/me", headers=headers)
            response.raise_for_status()
            user_data = response.json()

            # if status is not 200, return an error message
            if response.status_code != 200:
                return jsonify({'error': 'Invalid authorization'}), 401

            # Store user data in the database
            user = update_user_data(user_data)

            # Generate JWT token for the user
            jwt_token = create_access_token(identity=user.uid)

            return jsonify({'access_token': jwt_token}), 200
        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'User not authorized'}), 401

    @app.route('/incomplete', methods=['POST'])
    @jwt_required()
    def handle_incomplete_payment():
        payment = request.json['payment']
        payment_id = payment['identifier']
        txid = payment.get('transaction', {}).get('txid')
        tx_url = payment.get('transaction', {}).get('_link')

        # TODO: Verify the payment details (e.g., amount, memo) against your database
        # TODO: Mark the order as paid in your database if the payment is valid

        try:
            # Let Pi Servers know that the payment is completed
            headers = {'Authorization': f"Key {app.config['SERVER_API_KEY']}"}
            payload = {'txid': txid}
            response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/complete", json=payload, headers=headers)
            response.raise_for_status()

            return jsonify({'message': f'Handled the incomplete payment {payment_id}'}), 200
        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to complete the payment'}), 500

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
            print("User balance: ", user.balance)

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
        response = requests.post(f"{app.config['BASE_URL']}/payments", json=payment_data, headers=headers)
        return jsonify(response.json())

    @app.route("/get_payment/<payment_id>", methods=["GET"], endpoint="get_payment")
    def get_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.get(f"{app.config['BASE_URL']}/payments/{payment_id}", headers=headers)
        return jsonify(response.json())

    @app.route("/approve_payment/<payment_id>", methods=["POST"], endpoint="approve_payment")
    def approve_payment(payment_id):
        # Validate userID and check if the user has the required scope
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.filter_by(uid=user_id).first()

        if user is None:
            print("User not found")
            return jsonify({'error': 'User not found'}), 404

        user_scope = UserScopes.query.filter_by(user_id=user.id, scope='payments').first()
        if user_scope is None or not user_scope.active:
            return jsonify({'error': 'Unauthorized'}), 401

        # Get payment
        payment = Transaction.query.filter_by(id=payment_id).first()

        # If payment is not found, create it. If completed, return an error
        if payment is None:
            data = request.get_json()
            pl_cost = data['paymentData']['amount']

            # If amount is not provided or is less than 0, return an error
            if pl_cost is None or pl_cost <= 0:
                return jsonify({'error': 'Invalid amount'}), 400

            # approveStatus = pi_network.get_payment(payment_id)
            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }
            response = requests.post(f"{app.config['BASE_URL']}/payments/" + payment_id + "/approve/", headers=headers)
            print("Payment response: ", response.content)

            # Save contents to json file localy using payment_id as filename
            with open(f"{payment_id}_approval.json", "w") as f:
                json.dump(response.json(), f)

            # if response status is not 200, return an error
            if response.status_code != 200:
                print("Failed to approve payment")
                return jsonify({'error': 'Failed to approve payment'}), 500

            # Create a transaction record
            transaction = create_transaction(user_id=user.id, ref_id=None, wallet_id=None, amount=pl_cost, transaction_type='deposit', memo='Uni-Games Ticket Purchase', status='pending', id=payment_id)

            if transaction is None:
                return jsonify({'error': 'Failed to create transaction'}), 500

            return jsonify(response.json())


        elif payment.status == 'completed':
            return jsonify({'error': 'Payment already completed'}), 400

        # Need to handle when payment is panding

    @app.route("/complete_payment/<payment_id>", methods=["POST"], endpoint="complete_payment")
    def complete_payment(payment_id):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            # Check if user exists
            user = User.query.filter_by(uid=user_id).first()
            if user is None:
                return jsonify({'error': 'User not found'}), 404

            # Check if the payment exists and is pending
            payment = Transaction.query.filter_by(id=payment_id, status="pending").first()
            if payment is None:
                print("Payment not found")
                return jsonify({'error': 'Payment not found or already completed'}), 404

            data = request.get_json()
            payment_id = data["paymentId"]
            txid = data["txid"]

            print("Payment ID: ", payment_id)
            print("Transaction ID: ", txid)

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

            print("Complete payment response: ", response.content)

            # Save contents to json file localy using payment_id as filename
            with open(f"{payment_id}_confirmed.json", "w") as f:
                json.dump(response.json(), f)

            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete payment'}), 500

            # Complete the transaction
            if not complete_transaction(payment.id, txid):
                return jsonify({'error': 'Failed to complete transaction'}), 500

            db.session.commit()
            return jsonify({'message': 'Payment completed successfully'}), 200
        except Exception as err:
            logging.error(err)
            return jsonify({'error': 'Failed to complete payment'}), 500

    @app.route("/cancel_payment/<payment_id>", methods=["POST"], endpoint="cancel_payment")
    @jwt_required()
    def cancel_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/cancel", headers=headers)
        return jsonify(response.json())

    @app.route("/incomplete_server_payment/<payment_id>", methods=["POST"], endpoint="incomplete_server_payment")
    def incomplete_server_payment(payment_id):

        # Get post data
        data = request.get_json()


        payment_id = data['payment']['identifier'] if 'identifier' in data['payment'] else None
        amount = data['payment']['amount'] if 'amount' in data['payment'] else 0
        user_id = data['payment']['user_uid'] if 'user_uid' in data['payment'] else None
        memo = data['payment']['memo'] if 'memo' in data['payment'] else None
        trans_type=None
        txid=None
        try:
            trans_type = data['payment']['metadata']['transType']
        except KeyError:
            trans_type="deposit"

        try:
            txid = data['payment']['transaction']['txid']
        except KeyError:
            txid=None

        statuses = data['payment']['status'] if 'status' in data['payment'] else None

        # Check if the payment exists
        payment = Transaction.query.filter_by(id=payment_id).first()

        print(payment)

        # if payment is not found, create it
        if payment is None:
            transaction = create_transaction(user_id=user_id, ref_id=None, wallet_id=None, amount=amount, transaction_type=trans_type, memo=memo, status='pending', id=payment_id)

            # Check if the transaction was created successfully
            if transaction is None:
                return jsonify({'error': 'Failed to create transaction'}), 500

        # Check if payment status is completed in the database
        if payment.status == 'completed':
            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }

            response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

            print("Complete payment response: ", response.content)

            # Save contents to json file localy using payment_id as filename
            with open(f"{payment_id}_confirmed.json", "w") as f:
                json.dump(response.json(), f)

            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete payment'}), 500


        # Update status to completed if developer_approved and transaction_verified are true
        if statuses['developer_approved'] and statuses['transaction_verified']:

            headers = {
                "Authorization": f"Key {app.config['SERVER_API_KEY']}",
                "Content-Type": "application/json"
            }

            response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/complete", json={"txid": txid}, headers=headers)

            print("Complete payment response: ", response.content)

            # Save contents to json file localy using payment_id as filename
            with open(f"{payment_id}_confirmed.json", "w") as f:
                json.dump(response.json(), f)

            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete payment'}), 500

            # Complete the transaction
            if not complete_transaction(payment.id, txid):
                return jsonify({'error': 'Failed to complete transaction'}), 500

        # Return success message
        return jsonify({'message': 'Payment completed successfully'}), 200
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
                logging.error(err)
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
            logging.error(err)
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

        new_game = Game(game_id=game_id, pool_amount=pool_amount, num_players=num_players, end_time=end_time)
        db.session.add(new_game)
        db.session.commit()

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

    return app, db

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
    app, db = create_app(config_path)

    with app.app_context():
        # Validate configuration
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        validate_config(config)

        # Create the database tables
        db.create_all()

    app.run(host=config['app']['host'], port=config['app']['port'])
