# src/game_routes.py
from src.db.models import Session
from fastapi import Depends, Request, status
from src.utils.utils import JSONResponse, uuid, requests, json, datetime
from src.utils.transactions import logging, colorama
from src.db.models import User, Session, Game, GameType, GameConfig, LottoStats
from src.utils.transactions import create_transaction, get_current_user
from src.dependencies import get_db_session, get_config , get_pi_network, Depends, Request, status, app, APIRouter

game_router = APIRouter()


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

@app.post("/submit-ticket")
async def submit_ticket(request: Request, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
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

@app.get("/api/ticket-details")
async def get_ticket_details(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user), pi_network = Depends(get_pi_network)):
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
