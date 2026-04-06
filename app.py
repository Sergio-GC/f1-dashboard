from flask import Flask
from routes import register_routes

from services.telegram_service import start_scheduler


def create_app():
    app = Flask(__name__)
    register_routes(app)
    start_scheduler()
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=3062, debug=True)