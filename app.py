from flask import Flask
from routes import register_routes

from services.telegram_service import start_scheduler

from dotenv import load_dotenv
load_dotenv()

def create_app():
    app = Flask(__name__)
    register_routes(app)
    start_scheduler()
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3062, debug=True)