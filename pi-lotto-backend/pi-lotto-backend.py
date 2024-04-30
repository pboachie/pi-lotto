# pi-lotto-backend.py
import sys
import yaml
import logging
import requests
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from src.pi_python import PiNetwork


def create_app(config_path):
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes and origins

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
    jwt = JWTManager(app)

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
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
        amount = db.Column(db.Float, nullable=False)
        transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit' or 'withdrawal'
        transaction_id = db.Column(db.String(100), unique=True, nullable=False)
        status = db.Column(db.String(20), nullable=False)
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
        dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        amount = db.Column(db.Float, nullable=False)
        transaction_id = db.Column(db.String(100), unique=True, nullable=False)
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

    # Function to validate the transaction
    def validate_tx(tx_url):
        try:
            response = requests.get(tx_url)
            response.raise_for_status()
            tx_data = response.json()
            logging.info(tx_data)

            # Check if the transaction is valid
            if tx_data['status'] == 'success':
                return True
            else:
                return False
        except requests.exceptions.RequestException as err:
            logging.error(err)
            return False

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
        user = User.query.get(user_id)
        if user:
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
                return jsonify({'error': 'Invalid transaction type'}), 400

            db.session.commit()
            return jsonify({'message': 'User balance updated successfully'}), 200

    def create_account_transaction(user_id, transaction_type, amount, reference_id=None):
        transaction = AccountTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            reference_id=reference_id
        )
        db.session.add(transaction)
        db.session.commit()

        balanceIsUpdated = update_user_balance(user_id, amount, transaction_type)

        if balanceIsUpdated.status_code != 200:
            logging.error(balanceIsUpdated.json())
            db.session.refresh(transaction)
            db.session.delete(transaction)
            return False
        else:
            return True


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

        # Check the transaction on the Pi blockchain using the tx_url
        isValidTX = validate_tx(tx_url)

        if not isValidTX:
            return jsonify({'error': 'Invalid transaction'}), 400

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

            # Check if the balance is not None, else return maintanance message
            if balance is None:
                return jsonify({'error': 'The system is currently under maintenance. Please try again later'}), 503

            return jsonify({'balance': balance})

        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'Failed to fetch lotto pool amount'}), 500

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
    @jwt_required()
    def get_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.get(f"{app.config['BASE_URL']}/payments/{payment_id}", headers=headers)
        return jsonify(response.json())

    @app.route("/approve_payment/<payment_id>", methods=["POST"], endpoint="approve_payment")
    @jwt_required()
    def approve_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/approve", headers=headers)
        return jsonify(response.json())

    @app.route("/complete_payment/<payment_id>", methods=["POST"], endpoint="complete_payment")
    @jwt_required()
    def complete_payment(payment_id):
        data = request.get_json()
        txid = data["txid"]
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}",
            "Content-Type": "application/json"
        }
        payload = {
            "txid": txid
        }
        response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/complete", json=payload, headers=headers)
        return jsonify(response.json())

    @app.route("/cancel_payment/<payment_id>", methods=["POST"], endpoint="cancel_payment")
    @jwt_required()
    def cancel_payment(payment_id):
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.post(f"{app.config['BASE_URL']}/payments/{payment_id}/cancel", headers=headers)
        return jsonify(response.json())

    @app.route("/incomplete_server_payments", methods=["GET"], endpoint="incomplete_server_payments")
    @jwt_required()
    def incomplete_server_payments():
        headers = {
            "Authorization": f"Key {app.config['SERVER_API_KEY']}"
        }
        response = requests.get(f"{app.config['BASE_URL']}/payments/incomplete_server_payments", headers=headers)
        return jsonify(response.json())

    @app.route("/api/ticket-details", methods=["GET"])
    @jwt_required()
    def get_ticket_details():

        try:
            # Divide the base fee by 10000000 to get the actual fee
            baseFee = int(pi_network.fee) / 10000000
        except requests.exceptions.RequestException as err:
            logging.error(err)
            baseFee = 0.01

        # TODO: Hardcoded values should come from config
        ticket_details = {
            "ticketPrice": 2.00,
            "baseFee": float(baseFee),
            "serviceFee": 0.0125
        }
        return jsonify(ticket_details)

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

        return jsonify({'message': 'User joined the game successfully'}), 200

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