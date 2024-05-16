# src/game_routes.py
from src.db.models import Session
from fastapi import Depends, Request, status
from src.utils.utils import JSONResponse, uuid, requests, json, datetime
from src.utils.transactions import logging, colorama
from src.db.models import User, Session, Game, GameType, GameConfig, LottoStats, Transaction, TransactionData, Ticket
from src.utils.transactions import create_transaction, get_current_user, create_account_transaction
from src.dependencies import get_db_session, get_config , get_pi_network, Depends, Request, status, app, APIRouter

game_router = APIRouter()

def validate_lotto_numbers(lotto_numbers, power_number, main_range, power_range):
    if len(lotto_numbers) != 5:
        return False
    if not all(main_range[0] <= num <= main_range[1] for num in lotto_numbers):
        return False
    if not (power_range[0] <= power_number <= power_range[1]):
        return False
    return True

@app.get("/api/lotto-pool")
async def get_lotto_pool(current_user: User = Depends(get_current_user), pi_network = Depends(get_pi_network)):
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
async def get_user_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db_session), config = Depends(get_config)):
    user_id = current_user.uid
    user = db.query(User).filter(User.uid == user_id).first()
    if user is None:
        return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

    # if debug mode is enabled, return the balance as 1000
    if config['app']['debug'] == True:
        logging.info(colorama.Fore.YELLOW + f"FETCH: Fetching user balance for user: {user.username} with balance: {user.balance}")

    return JSONResponse({'balance': user.balance}, status_code=status.HTTP_200_OK)

@app.post("/api/submit-ticket")
async def submit_ticket(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.uid
        user = db.query(User).filter(User.uid == user_id).first()
        if user is None:
            return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

        # Get ticketID from data
        data = await request.json()
        ticket_id = data.get('txID')

        # Check if transaction exists in pending state
        transaction = db.query(Transaction).filter(Transaction.id == ticket_id, Transaction.status == 'pending').first()
        if transaction is None:
            return JSONResponse({'error': 'Transaction not found'}, status_code=status.HTTP_404_NOT_FOUND)

        # Get transaction data from the TransactionData table
        transaction_data = db.query(TransactionData).filter(TransactionData.transaction_id == ticket_id).first()
        if transaction_data is None:
            return JSONResponse({'error': 'Unable to process transaction. Please contact support'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get the game details
        game_id = transaction_data.data.get('gameID')
        game = db.query(Game).filter(Game.id == game_id).first()
        if game is None:
            return JSONResponse({'error': 'Game not found'}, status_code=status.HTTP_404_NOT_FOUND)

        # Get game fees and number range from config
        game_configs = db.query(GameConfig).filter(GameConfig.game_id == game_id).all()
        config_data = {}
        for config in game_configs:
            config_data[config.config_key] = config.config_value

        try:
            entry_fee:float = transaction_data.data.get('ticketPrice')
            service_fee:float = transaction_data.data.get('serviceFee')
            network_fee:float = transaction_data.data.get('baseFee')
            max_players:int = config_data.get('max_players')
            number_range = json.loads(config_data.get('number_range'))
            main_number_range = number_range['main']
            power_number_range = number_range['power']
            lotto_numbers = transaction_data.data.get('numbers').get('lotto_numbers')
            power_number:int = transaction_data.data.get('numbers').get('power_number')

            # Print all the values
            # print('entry_fee:', entry_fee)
            # print('service_fee:', service_fee)
            # print('network_fee:', network_fee)
            # print('max_players:', max_players)
            # print('main_number_range:', main_number_range)
            # print('power_number_range:', power_number_range)
            # print('lotto_numbers:', lotto_numbers)
            # print('power_number:', power_number)
        except KeyError as e:
            logging.error(f"Key error while fetching game details: {e}")
            return JSONResponse({'error': 'Error fetching game details'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Validate the ticket price
        if not entry_fee or not service_fee or not network_fee:
            logging.error(f"Configuration data missing for the game: {game_id}")
            return JSONResponse({'error': 'Configuration data missing for the game'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check if user has sufficient balance
        total_cost = entry_fee + service_fee + network_fee
        if user.balance < total_cost:
            logging.error(f"Insufficient balance for user: {user.username}")
            return JSONResponse({'error': 'Insufficient balance'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get the number of players in the game
        currentPlayers = db.query(LottoStats).filter(LottoStats.game_id == game_id).count()
        if int(currentPlayers) >= int(max_players):
            logging.error(f"Game is full: {game_id}")
            return JSONResponse({'error': 'Game is full'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Validate lotto numbers using dynamic range
        if not validate_lotto_numbers(lotto_numbers, power_number, main_number_range, power_number_range):
            logging.error(f"Invalid lotto numbers: {lotto_numbers}")
            return JSONResponse({'error': 'Invalid lotto numbers'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Save the ticket details
        new_ticket = Ticket(
            user_id=user.id,
            game_id=game_id,
            transaction_id=ticket_id,
            numbers_played=','.join(map(str, lotto_numbers)),
            power_number=power_number
        )
        db.add(new_ticket)
        db.commit()

        # Create account transaction
        transactionCreated = create_account_transaction(user.id, 'lotto_entry', total_cost, reference_id=new_ticket.id, db=db)

        # if transactionCreated = false, undo the transaction
        if not transactionCreated:
            db.refresh(new_ticket)
            db.delete(new_ticket)
            db.commit()
            return JSONResponse({'error': 'Failed to create account transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update transaction status
        transaction.status = 'completed'
        db.commit()

        return JSONResponse({'message': 'Ticket submitted successfully'}, status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(e)
        return JSONResponse({'error': 'Failed to submit ticket'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.put("/api/ticket-details/{game_id}")
async def get_ticket_details(game_id: int, request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), pi_network = Depends(get_pi_network)):
    try:
        # Get the current user
        user_id = current_user.uid
        user = db.query(User).filter(User.uid == user_id).first()
        if not user:
            logging.error(f"User not found: {user_id}")
            return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

        # Get the game details
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            logging.error(f"Game not found: {game_id}")
            return JSONResponse({'error': 'Game not found'}, status_code=status.HTTP_404_NOT_FOUND)

        if game.status != 'active':
            logging.warning(f"Game not active: {game_id}")
            return JSONResponse({'error': 'This game is not active or has ended'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Fetch the request data
        data = await request.json()
        numbers = data.get('numbers')
        power = data.get('PiLotto')

        # Validate numbers
        if not isinstance(numbers, list) or len(numbers) != 5 or not all(isinstance(num, int) for num in numbers):
            logging.error(f"Invalid lotto numbers: {numbers}")
            return JSONResponse({'error': 'Invalid lotto numbers'}, status_code=status.HTTP_400_BAD_REQUEST)

        if not isinstance(power, int):
            logging.error(f"Invalid power number: {power}")
            return JSONResponse({'error': 'Invalid power number'}, status_code=status.HTTP_400_BAD_REQUEST)

        # Get game details
        try:
            game_configs = db.query(GameConfig).filter(GameConfig.game_id == game_id).all()
            if not game_configs:
                logging.error(f"No game configurations found for game_id: {game_id}")
                return JSONResponse({'error': 'Game configurations not found'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            game_details = {config.config_key: config.config_value for config in game_configs}

            entry_fee = game_details.get('entry_fee')
            service_fee = game_details.get('service_fee')
            base_fee = int(pi_network.fee) / 10000000

            if entry_fee is None or service_fee is None:
                logging.error(f"Missing fee details in game configurations for game_id: {game_id}")
                return JSONResponse({'error': 'Missing fee details in game configurations'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except requests.exceptions.RequestException as err:
            logging.error(f"Failed to fetch ticket details for user: {user.username}. Error: {err}")
            return JSONResponse({'error': 'Failed to fetch ticket details'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except KeyError as e:
            logging.error(f"Key error while fetching game details: {e}")
            return JSONResponse({'error': 'Error fetching game details'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Calculate total cost
        total_cost = float(entry_fee) + float(service_fee) + float(base_fee)

        # TicketID generation
        ticketID = str(uuid.uuid4())

        # Prepare ticket details
        ticket_details = {
            "gameID": game_id,
            "ticketPrice": float(entry_fee),
            "baseFee": float(base_fee),
            "serviceFee": float(service_fee),
            "txID": str(ticketID),
            "numbers": {
                "lotto_numbers": numbers,
                "power_number": int(power)
            }
        }

        # Create transaction record
        transaction = create_transaction(
            user_id=user.id,
            ref_id=None,
            wallet_id=None,
            amount=total_cost,
            transaction_type='lotto_entry',
            memo='Uni-Games Ticket Purchase',
            status='pending',
            id=ticketID,
            db=db,
            transactionData=ticket_details
        )
        if not transaction:
            logging.error(f"Failed to create transaction: {ticketID}")
            return JSONResponse({'error': 'Failed to create transaction'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JSONResponse(ticket_details, status_code=status.HTTP_200_OK)

    except requests.exceptions.RequestException as err:
        logging.error(f"Failed to fetch ticket details for user: {user.username}. Error: {err}")
        return JSONResponse({'error': 'Failed to fetch ticket details'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse({'error': 'An unexpected error occurred'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/admin/create-game-type")
async def create_game_type(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
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
async def create_game(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
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

    game_type = db.get(GameType, game_type_id)
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
async def update_game(game_id: int, request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    game = db.get(Game, game_id)
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
async def create_game_config(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    data = await request.json()
    game_type_id = data.get('game_type_id')
    game_id = data.get('game_id')
    configs = data.get('configs')

    if not game_type_id or not configs:
        return JSONResponse({'error': 'Missing required fields'}, status_code=status.HTTP_400_BAD_REQUEST)

    if not game_id and not db.get(Game, game_id):
        return JSONResponse({'error': 'Invalid game'}, status_code=status.HTTP_400_BAD_REQUEST)

    game_type = db.get(GameType, game_type_id)
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
async def update_game_config(config_id: int, request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    uid = current_user.uid
    if uid != 'cfed0fd5-0b20-46bf-b54d-3e6d8746ad4c':
        return JSONResponse({'error': 'Unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

    game_config = db.get(GameConfig, config_id)
    if not game_config:
        return JSONResponse({'error': 'Game configuration not found'}, status_code=status.HTTP_404_NOT_FOUND)

    data = await request.json()
    game_config.config_value = data.get('config_value', game_config.config_value)
    db.commit()

    return JSONResponse({'message': 'Game configuration updated successfully'}, status_code=status.HTTP_200_OK)

@app.get("/game-types")
async def get_game_types(db: Session = Depends(get_db_session)):
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
# Add current_user: User = Depends(get_current_user) if not debugging
async def get_games(request: Request, db: Session = Depends(get_db_session)):
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
            game_type = db.get(GameType, game.game_type_id)

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
async def get_game_details(game_id: int, db: Session = Depends(get_db_session)):
    if not game_id:
        return JSONResponse({'error': 'game_id is required'}, status_code=status.HTTP_400_BAD_REQUEST)

    game = db.get(Game, game_id)
    result = []

    if game:
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

@app.get("/game-configs/{game_id}")
async def get_game_configs(game_id: int, db: Session = Depends(get_db_session)):
    if not game_id:
        return JSONResponse({'error': 'game_id is required'}, status_code=status.HTTP_400_BAD_REQUEST)

    game_configs = db.query(GameConfig).filter(GameConfig.game_id == game_id).all()
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
