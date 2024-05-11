from fastapi import Depends, FastAPI, Request, status, HTTPException, APIRouter
from sqlalchemy.orm import Session
from src.db.database import SessionLocal
from src.utils.utils import load_config, configure_logging
from src.pi_network.pi_python import PiNetwork
from fastapi.middleware.cors import CORSMiddleware

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_config():
    return load_config()

def get_pi_network():
    return pi_network

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify the allowed origins or use "*" to allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # You can specify the allowed HTTP methods or use "*" to allow all methods
    allow_headers=["*"],  # You can specify the allowed headers or use "*" to allow all headers
)

config = get_config()
configure_logging(config)

pi_network = PiNetwork()
pi_network.initialize(config['api']['base_url'], config['api']['server_api_key'], config['api']['app_wallet_seed'], config['api']['network'])

