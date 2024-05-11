# main.py

import multiprocessing
import spacy
from fastapi import FastAPI, Request, status
from fastapi.routing import APIRouter
from src.utils.utils import logging, JSONResponse
from src.dependencies import get_config, app

# Import the route files
from src.auth_routes import auth_router
from src.payment_routes import payment_router
from src.game_routes import game_router

# Load the config file
config = get_config()

# Create an instance of APIRouter
api_router = APIRouter()

# Include the route files
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(payment_router, prefix="/payments", tags=["Payments"])
api_router.include_router(game_router, prefix="/games", tags=["Games"])

# Mount the APIRouter
app.include_router(api_router)

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    # Log the exception
    logging.error(f"Unhandled exception: {str(exc)}")

    # Return an appropriate error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An internal server error occurred"},
    )

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Pi Lotto API"}

@app.get("/loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf/")
async def loaderio_verification():
    return 'loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf'

def serve(
    model: str,
    #   api_key: str = typer.Option(NO_API_KEY, prompt=True, hide_input=True, show_default=True, confirmation_prompt=True),
    host: str = config['app']['host'],
    port: int = config['app']['port'],
    use_gunicorn: bool = False,
    n_workers: int = (multiprocessing.cpu_count() * 2) + 1,
):

    import uvicorn
    from starlette.requests import Request

    nlp = spacy.load(model)

    @app.middleware("http")
    async def update_request_state(request: Request, call_next):
        request.state.nlp = nlp
        # request.state.api_key = api_key
        response = await call_next(request)
        return response

    if use_gunicorn:
        from gunicorn.app.wsgiapp import WSGIApplication

        class FastAPIApplication(WSGIApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                config = {
                    key: value
                    for key, value in self.options.items()
                    if key in self.cfg.settings and value is not None
                }
                for key, value in config.items():
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        options = {
            "bind": f"{host}:{port}",
            "workers": n_workers,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }
        FastAPIApplication(app, options).run()
    else:
        uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import uvicorn
    # Run with 4 workers
    # serve("en_core_web_sm", use_gunicorn=True, n_workers=4)
    uvicorn.run(app, host=config['app']['host'], port=config['app']['port'])
