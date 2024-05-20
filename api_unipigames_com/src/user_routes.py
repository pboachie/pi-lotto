# src/user_routes.py
from src.db.models import Session
from fastapi import Depends, status, APIRouter
from src.utils.utils import JSONResponse
from src.utils.transactions import logging
from src.db.models import User, Game, Ticket, LottoStats, GameConfig
from src.utils.transactions import get_current_user
from src.dependencies import get_db_session

user_router = APIRouter()

@user_router.get("/user-tickets")
async def get_user_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db_session)):
    user = db.query(User).filter(User.uid == current_user.uid).first()
    if not user:
        return JSONResponse({'error': 'User not found'}, status_code=status.HTTP_404_NOT_FOUND)

    tickets = db.query(Ticket).filter(Ticket.user_id == user.id).all()
    if not tickets:
        return JSONResponse({'tickets': []}, status_code=status.HTTP_200_OK)

    ticket_data = []
    for ticket in tickets:
        game = db.query(Game).filter(Game.id == ticket.game_id).first()
        if not game:
            continue

        stats = db.query(LottoStats).filter(LottoStats.game_id == game.id, LottoStats.user_id == user.id).first()
        won = stats.win_amount > 0 if stats else False
        prize_claimed = getattr(stats, 'prize_claimed', False) if stats else False

        ticket_info = {
            'ticket_id': ticket.id,
            'game_id': game.id,
            'game_name': game.name,
            'numbers_played': ticket.numbers_played,
            'power_number': ticket.power_number,
            'date_purchased': ticket.date_purchased.isoformat(),
            'won': won,
            'prize_claimed': prize_claimed
        }
        ticket_data.append(ticket_info)

    return JSONResponse({'tickets': ticket_data}, status_code=status.HTTP_200_OK)
