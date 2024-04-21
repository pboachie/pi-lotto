# app.py
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes and origins

# Your Server API Key
SERVER_API_KEY = "YOUR_SERVER_API_KEY"

# Base URL for the Pi Platform API
BASE_URL = "https://api.minepi.com/v2"

# JWT Configuration
app.config["JWT_SECRET_KEY"] = "YOUR_JWT_SECRET_KEY"  # Replace with your own secret key
jwt = JWTManager(app)

# User authentication endpoint
@app.route("/login", methods=["POST"], endpoint="login")
def login():
    data = request.get_json()
    user_id = data["uid"]

    # Verify the user's authentication here (e.g., check against your database)
    # For simplicity, let's assume the user is authenticated successfully

    access_token = create_access_token(identity=user_id)
    return jsonify(access_token=access_token), 200

# Protected route example
@app.route("/protected", methods=["GET"], endpoint="protected")
@jwt_required
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

@app.route("/create_payment", methods=["POST"], endpoint="create_payment")
@jwt_required
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
        "Authorization": f"Key {SERVER_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{BASE_URL}/payments", json=payment_data, headers=headers)
    return jsonify(response.json())

@app.route("/get_payment/<payment_id>", methods=["GET"], endpoint="get_payment")
@jwt_required
def get_payment(payment_id):
    headers = {
        "Authorization": f"Key {SERVER_API_KEY}"
    }
    response = requests.get(f"{BASE_URL}/payments/{payment_id}", headers=headers)
    return jsonify(response.json())

@app.route("/approve_payment/<payment_id>", methods=["POST"], endpoint="approve_payment")
@jwt_required
def approve_payment(payment_id):
    headers = {
        "Authorization": f"Key {SERVER_API_KEY}"
    }
    response = requests.post(f"{BASE_URL}/payments/{payment_id}/approve", headers=headers)
    return jsonify(response.json())

@app.route("/complete_payment/<payment_id>", methods=["POST"], endpoint="complete_payment")
@jwt_required
def complete_payment(payment_id):
    data = request.get_json()
    txid = data["txid"]
    headers = {
        "Authorization": f"Key {SERVER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "txid": txid
    }
    response = requests.post(f"{BASE_URL}/payments/{payment_id}/complete", json=payload, headers=headers)
    return jsonify(response.json())

@app.route("/cancel_payment/<payment_id>", methods=["POST"], endpoint="cancel_payment")
@jwt_required
def cancel_payment(payment_id):
    headers = {
        "Authorization": f"Key {SERVER_API_KEY}"
    }
    response = requests.post(f"{BASE_URL}/payments/{payment_id}/cancel", headers=headers)
    return jsonify(response.json())

@app.route("/incomplete_server_payments", methods=["GET"], endpoint="incomplete_server_payments")
@jwt_required
def incomplete_server_payments():
    headers = {
        "Authorization": f"Key {SERVER_API_KEY}"
    }
    response = requests.get(f"{BASE_URL}/payments/incomplete_server_payments", headers=headers)
    return jsonify(response.json())

if __name__ == "__main__":
    app.run()