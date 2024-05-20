# main.py

import multiprocessing
import sys
from src.utils.utils import logging, JSONResponse
from src.dependencies import get_config, app, APIRouter, Request, status
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.db.database import update_pool_amount, cancel_old_pending_lotto_entries
from src.utils.utils import load_config

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
    msg = 'loaderio-28b24b7ab3f2743ac5e4b68dcdf851bf'
    header = {'Content-Type': 'application/json'}
    # return msg without quotes
    return JSONResponse(content=msg, headers=header)


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_pool_amount, 'interval', minutes=1, id='update_pool_amount')
    scheduler.add_job(cancel_old_pending_lotto_entries, CronTrigger(hour=3, minute=0), id='cancel_lotto_transactions_daily') # Schedule to run once a day at 3 AM
    scheduler.start()

def serve(use_gunicorn, n_workers, host, port):
    import uvicorn
    from starlette.requests import Request

    if use_gunicorn:
        print(f"Starting server with suggested workers of {n_workers}.")
    else:
        print("Starting server. To use Gunicorn, run with --enableWorker flag. To specify number of workers, use --workers flag.")

    @app.middleware("http")
    async def update_request_state(request: Request, call_next):
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
    start_scheduler()

    use_gunicorn: bool = False
    n_workers: int = 1
    host: str = config['app']['host']
    port: int = config['app']['port']
    n_workers: int = (multiprocessing.cpu_count() * 2) + 1

    for arg in sys.argv:
        if arg.startswith("--enableWorker"):
            use_gunicorn = True

        if arg.startswith("--workers="):
            n_workers = int(arg.split("=")[1])

        if arg.startswith("--host="):
            host = arg.split("=")[1]

        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

        # help flag
        if arg.startswith("--help"):
            # Print default values
            print(f"Default values: use_gunicorn: {use_gunicorn}, n_workers: {n_workers}, host: {host}, port: {port}")
            print("Usage: python main.py [--enableWorker] [--workers=2] [--host=localhost] [--port=5000]")
            print("--enableWorker: Enable Gunicorn server")
            print("--workers: Number of workers for Gunicorn server")
            print("--host: Host address")
            print("--port: Port number")
            sys.exit()

    serve(use_gunicorn=use_gunicorn, n_workers=n_workers, host=host, port=port)
