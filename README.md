# 🎮 WELCOME TO PI-GAMES 🎮

This is a collection of games that can be played on almost any device using the Pi Network. The games are designed to be simple and fun, and can be played by anyone, regardless of age or skill level.

**🎉 Users can expect to win Pi coins for playing games, such as:**
- 🎰 Pi-Lotto
- 🎟️ Pi-Scratchers
- 🎲 And many more!

## 🚧 Development

This project is still in development, and we are constantly adding new games and features. If you have any suggestions or feedback, please feel free to contact us. We would love to hear from you!

## 🛠️ Installation

To get started, you will need to clone the repository and install the necessary dependencies. You will also need to create a `.env` file for the frontend and a `config.yml` file for the backend. You can use the `.env.example` and `config.yml.example` files as a template.

**⚠️ Important:**
- You must start the backend server before starting the frontend server.
- The backend server will be running on `http://localhost:5000` and the frontend server will be running on `http://localhost:3000`.
- To test the application, please reach out to the developers for the necessary API keys.

**🔗 LOCAL APPLICATION TEST URL:**
https://sandbox.minepi.com/app/image-enhancer

**Note:**
- If you do not have the Pi Application, see the developer to authorize your local application.
- If you are registering to Pi for the first time, please see the developer for a referral code.

## 📥 Cloning the Repository

To clone the repository, run the following command in your terminal:

```bash
git clone git@github.com:pboachie/pi-lotto.git
```

🖥️ Installation - Pi-Lotto (Frontend)
```bash
cd pi-lotto/pi-lotto

# Install npm
apt-get install npm

# Install the dependencies
npm install

# Copy the .env.example file to .env
cp .env.example .env

# Start the development server
npm start
```

🖥️ Installation - Pi-Lotto (Backend)
```bash
cd pi-lotto/pi-lotto-backend

# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install the dependencies
python3 -m pip install -r requirements.txt

# Start the production server with default settings
python3 main.py

# To start the development server with fastapi
fastapi dev  --port 5000 --host localhost

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



## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

If you have any questions or feedback, please feel free to contact us at [prince@wceverything.com](mailto:prince@wceverything.com).

## 🌐 Website
www.unipigames.com
```