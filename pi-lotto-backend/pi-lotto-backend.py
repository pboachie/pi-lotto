# pi-lotto-backend.py
import sys
import yaml
import logging
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from src.pi_python import PiNetwork
import requests

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


    # User model
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(100), unique=True, nullable=False)
        uid = db.Column(db.String(36), unique=True, nullable=False)
        active = db.Column(db.Boolean, default=True)
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
        dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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

    # Class to keep a list of all the transactions
    class Transaction(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        amount = db.Column(db.Float, nullable=False)
        transaction_id = db.Column(db.String(100), unique=True, nullable=False)
        status = db.Column(db.String(20), nullable=False)
        dateCreated = db.Column(db.DateTime, default=db.func.current_timestamp())
        dateModified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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

            # Store user data in the database
            user = update_user_data(user_data)

            # Generate JWT token for the user
            jwt_token = create_access_token(identity=user.uid)

            return jsonify({'access_token': jwt_token}), 200
        except requests.exceptions.RequestException as err:
            logging.error(err)
            return jsonify({'error': 'User not authorized'}), 401

    @app.route('/incomplete', methods=['POST'])
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