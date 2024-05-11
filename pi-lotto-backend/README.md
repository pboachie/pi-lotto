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

# Start the development server
python3 main.py
```