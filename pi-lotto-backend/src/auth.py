# src/auth.py
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from src.utils.utils import load_config

config = load_config()

SECRET_KEY = config['jwt']['secret_key']
ALGORITHM = config['jwt']['algorithm']
ACCESS_TOKEN_EXPIRE_MINUTES = config['jwt']['access_token_expire_minutes']
DEV_DOCS_PASSWORD = config['dev_docs']['password']

# OAuth2 scheme for authentication
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="token")