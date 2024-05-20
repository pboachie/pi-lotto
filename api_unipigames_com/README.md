🖥️ Installation - Pi-Lotto (Backend)
```bash
cd pi-lotto/pi-lotto-backend

# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install the dependencies
python3 -m pip install -r requirements.txt

# Copy the config.yml.example file to config.yml (and update the values as needed)
cp config/config.yml.example config.yml

# Start the development server with default settings
python3 main.py

# Start the development server with Gunicorn
Usage: python main.py [--enableWorker] [--workers=2] [--host=localhost] [--port=5000]
--enableWorker: Enable Gunicorn server
--workers: Number of workers for Gunicorn server
--host: Host address
--port: Port number

# Changes to models.py
# After making changes to models.py, run the following command to update the database:

```bash
alembic revision --autogenerate -m "YOUR COMMIT MESSAGE HERE"
alembic upgrade head
```