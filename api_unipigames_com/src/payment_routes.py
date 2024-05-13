
#src/payment_routes.py

from src.db.models import Session
from src.utils.utils import JSONResponse, uuid, logging, colorama, requests, json
from src.db.models import User, Session, Transaction, TransactionData, UserScopes
from src.utils.transactions import create_transaction, get_current_user, complete_transaction
from src.dependencies import get_db_session, get_config , get_pi_network, Depends, Request, status, app, APIRouter

payment_router = APIRouter()

@app.post("/create_deposit")
async def create_deposit(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
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
async def create_withdrawal(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), config: dict = Depends(get_config), pi_network = Depends(get_pi_network)):
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
async def approve_payment(payment_id: str, request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
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
async def complete_payment(payment_id: str, request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
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
async def handle_incomplete_payment(payment_id: str, request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
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

@app.post("/create_payment")
async def create_payment(request: Request, current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
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
async def get_payment(payment_id: str, current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
    headers = {
        "Authorization": f"Key {config['api']['server_api_key']}"
    }
    response = requests.get(f"{config['api']['base_url']}/v2/payments/{payment_id}", headers=headers)
    return JSONResponse(response.json())

@app.post("/cancel_payment/{payment_id}")
async def cancel_payment(payment_id: str, current_user: User = Depends(get_current_user), config: dict = Depends(get_config)):
    headers = {
        "Authorization": f"Key {config['api']['server_api_key']}"
    }
    response = requests.post(f"{config['api']['base_url']}/v2/payments/{payment_id}/cancel", headers=headers)
    return JSONResponse(response.json())

