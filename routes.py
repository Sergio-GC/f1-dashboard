from flask import jsonify, render_template

from services.f1_service import get_current_races, get_driver_standings, get_constructor_standings, get_last_race_results, get_laptime_record
from services.news_service import get_news
from services.weather_service import get_race_weather

def register_routes(app):
    
    @app.route("/")
    def index():
        return render_template("index.html")
    
    @app.route("/api/data")
    def api_data():

        next_race, last_race = get_current_races()
        last_race_results = get_last_race_results(last_race)
        driver_standings = get_driver_standings()
        constructor_standings = get_constructor_standings()
        lap_record = get_laptime_record(next_race["circuit_id"])
        next_race_weather = get_race_weather(next_race["lat"], next_race["long"], next_race["date"])

        news = get_news()
        
        return jsonify({
            "next_race" : next_race,
            "lap_record": lap_record,
            "last_race": last_race,
            "last_race_results": last_race_results,
            "driver_standings": driver_standings,
            "constructor_standings": constructor_standings,
            "news": news,
            "weather": next_race_weather,
        })
    

    @app.route("/api/test-telegram")
    def test_telegram():
        from services.telegram_service import send_message
        send_message("🏎️ <b>Test!</b>\nYour F1 Dashboard is connected.")
        return jsonify({"status": "sent"})