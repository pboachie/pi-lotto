import json
import requests
from src.db.models import SignInResponse, SignInRequest, Session
from src.utils.utils import JSONResponse
from src.utils.transactions import update_user_data, create_access_token, Annotated, logging, colorama
from src.auth import DEV_DOCS_PASSWORD, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, OAuth2PasswordRequestForm, JWTError, jwt
from src.db.models import User, Session
from datetime import timedelta
from src.dependencies import get_db_session, get_config , Depends, Request, status, app, HTTPException, APIRouter

auth_router = APIRouter()


@app.post("/signin", response_model=SignInResponse)
async def signin(request: SignInRequest, db: Session = Depends(get_db_session), config: dict = Depends(get_config)):

    """
    Sign in endpoint.

    This endpoint accepts the user's authentication result from the Pi Network API and generates access and refresh tokens.

    - **authResult**: The authentication result object obtained from the Pi Network API.
        - **accessToken**: The access token from the Pi Network API.

    Returns:
    - **access_token**: The generated JWT access token.
    - **refresh_token**: The generated JWT refresh token.

    Possible error responses:
    - **400 Bad Request**: Invalid JSON format in the request body or missing keys in the request body.
    - **401 Unauthorized**: Invalid authorization or user not authorized.
    - **404 Not Found**: User not found.
    - **500 Internal Server Error**: An internal server error occurred.
    """

    try:
        data = request.json()
        data = json.loads(data)
        auth_result = data['authResult']
        access_token = auth_result['accessToken']

        # Verify with the user's access token
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"{config['api']['base_url']}/v2/me", headers=headers)
        response.raise_for_status()
        user_data = response.json()

        # Check if the response status is 200
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization')

        # Check if response user data is not empty
        if user_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

        # Store user data in the database
        user = update_user_data(user_data, db)

        # Generate JWT token for the user
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

        # Generate refresh token for the user
        refresh_token_expires = timedelta(hours=5)
        refresh_token = create_access_token(data={"sub": user.username}, expires_delta=refresh_token_expires)


        logging.info(colorama.Fore.GREEN + f"SIGNIN: User {user.username} signed in successfully")
        return JSONResponse({'access_token': access_token, 'refresh_token': refresh_token})

    except KeyError as e:
            logging.error(f"Missing key in request body: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing key in request body: {str(e)}")

    except requests.exceptions.RequestException as err:
        logging.error(err)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not authorized')

# if debug mode is enabled, enable this endpoint
if get_config()['app']['debug'] == True:
    @app.post("/token")
    async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db_session)):
        try:
            user = db.query(User).filter(User.username == form_data.username).first()

            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

            if form_data.password != str(DEV_DOCS_PASSWORD):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

            if user.active:
                access_token_expires = timedelta(minutes=60)
                access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

                return {"access_token": access_token, "token_type": "bearer"}

            return {"error": "User not found"}
        except HTTPException as e:
            logging.error(f"Error logging in: {str(e)}")
            raise e

@app.post("/refresh-token")
async def refresh_token(request: Request, db: Session = Depends(get_db_session), config: dict = Depends(get_config)):
    try:
        data = await request.json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            if config['app']['debug'] == True:
                logging.error(colorama.Fore.RED + "Refresh token is missing")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token is missing")

        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Generate a new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)


        return {"access_token": access_token}

    except HTTPException as e:
        logging.error(f"Error refreshing token: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh token")
